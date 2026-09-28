"""
Dataset upload sessions (resumable, chunked) for measurement datasets.

A session is created, its files arrive as parts, and finalize validates the
assembled dataset. With ``commit_mode=on_finalize`` (REST default) finalize
queues the commit (Postgres + MinIO) and returns 202. With ``on_approve``
(portal) the dataset is staged: its FHIR annotation draft can be edited, and
``/approve`` queues the commit. Clients poll ``GET /datasets/uploads/{id}``.
"""
import os
import shutil
import zipfile
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from digitaltwins.core.connection import Connection
from digitaltwins.measurements import jobs, sessions
from digitaltwins.measurements.chunk_store import PART_SIZE, ChunkStore, ChunkStoreError
from digitaltwins.measurements.fhir_service import build_fhir_json
from digitaltwins.measurements.pipeline import check_descriptions_match
from digitaltwins.measurements.staging import chunk_root, dataset_dir
from digitaltwins.measurements.tree import build_tree
from digitaltwins.measurements.validation import (
    extract_uploaded_archive,
    resolve_project_root,
    sampleless_subjects,
    validate_sparc_structure,
)

from .auth import require_upload_role, validate_credentials

router = APIRouter(prefix="/datasets/uploads", tags=["dataset uploads"])

# Categories ingested through sessions. Only measurements for now; other
# categories keep using the one-shot POST /datasets.
INGEST_CATEGORIES = {"measurements"}

# Sessions not yet committed, as listed for the portal overview.
_OPEN_STATUSES = ["receiving", "staged", "processing", "failed"]


def _max_upload_bytes() -> int:
    try:
        mb = int(os.getenv("MAX_UPLOAD_MB", "20480"))
    except ValueError:
        mb = 20480
    return max(mb, 1) * 1024 * 1024


def _chunk_store() -> ChunkStore:
    return ChunkStore(chunk_root())


def get_conn():
    conn, _ = Connection().connect()
    try:
        yield conn
    finally:
        conn.close()


def _session_or_404(conn, upload_id: str) -> Dict[str, Any]:
    session = sessions.get_session(conn, upload_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found")
    return session


def _require_status(session: Dict[str, Any], *allowed: str) -> None:
    if session["status"] not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Upload session is {session['status']}; expected {' or '.join(allowed)}.",
        )


def _session_view(session: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("upload_id", "name", "description", "category", "source_kind", "commit_mode", "status",
            "failure_stage", "failure_message", "fhir_mode", "dataset_uuid", "created_at", "updated_at")
    return {k: session[k] for k in keys}


# ── Models ─────────────────────────────────────────────────────────────


class ManifestEntry(BaseModel):
    rel_path: str
    size: int
    parts: int


class SessionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "measurements"
    source_kind: Literal["folder", "zip"]
    manifest: List[ManifestEntry]
    commit_mode: Literal["on_finalize", "on_approve"] = "on_finalize"
    fhir: Literal["none", "auto"] = "none"
    fhir_descriptions: Optional[Dict[str, Any]] = None


class AnnotationBody(BaseModel):
    descriptions: Dict[str, Any]


# ── Session lifecycle ──────────────────────────────────────────────────


@router.get("/config")
def get_upload_config(_creds: dict = Depends(validate_credentials)):
    return {"max_upload_bytes": _max_upload_bytes(), "max_part_size": PART_SIZE}


@router.get("")
def list_uploads(conn=Depends(get_conn), _creds: dict = Depends(validate_credentials)):
    return {"uploads": [_session_view(s) for s in sessions.list_sessions(conn, _OPEN_STATUSES)]}


@router.post("")
def create_upload(body: SessionCreate, conn=Depends(get_conn), _creds: dict = Depends(require_upload_role)):
    if body.category not in INGEST_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload sessions support categories: {', '.join(sorted(INGEST_CATEGORIES))}",
        )
    fhir_mode = "descriptions" if body.fhir_descriptions is not None else body.fhir
    upload_id = sessions.create_session(
        conn, category=body.category, name=body.name, description=body.description,
        source_kind=body.source_kind, commit_mode=body.commit_mode,
        fhir_mode=fhir_mode, fhir_descriptions=body.fhir_descriptions,
    )
    try:
        _chunk_store().init(upload_id, body.source_kind, [e.model_dump() for e in body.manifest])
    except (ChunkStoreError, ValueError) as exc:
        sessions.delete_session(conn, upload_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"upload_id": upload_id, "max_part_size": PART_SIZE}


@router.put("/{upload_id}/parts/{rel_path:path}")
async def upload_part(
    upload_id: str, rel_path: str, n: int, of: int, request: Request,
    conn=Depends(get_conn), _creds: dict = Depends(require_upload_role),
):
    """One raw ``application/octet-stream`` part of ``rel_path`` (``n`` of ``of``)."""
    _require_status(_session_or_404(conn, upload_id), "receiving")
    data = await request.body()
    try:
        received = _chunk_store().write_part(upload_id, rel_path, n, of, data)
    except (ChunkStoreError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"rel_path": rel_path, "bytes_received": received}


@router.get("/{upload_id}")
def get_upload(upload_id: str, conn=Depends(get_conn), _creds: dict = Depends(validate_credentials)):
    """Session state; while receiving, also per-file received parts for resume."""
    session = _session_or_404(conn, upload_id)
    view = _session_view(session)
    view["upload"] = _chunk_store().status(upload_id) if session["status"] == "receiving" else None
    return view


@router.post("/{upload_id}/finalize")
def finalize_upload(
    upload_id: str, background: BackgroundTasks,
    conn=Depends(get_conn), _creds: dict = Depends(require_upload_role),
):
    """Assemble + validate. 400 keeps the session ``receiving`` (parts kept) so the
    client can fix and retry; otherwise stage (on_approve) or queue the commit."""
    session = _session_or_404(conn, upload_id)
    _require_status(session, "receiving")
    store = _chunk_store()
    if not store.is_complete(upload_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload incomplete; not all parts received.")

    extracted = None
    try:
        assembled = store.assemble(upload_id)
        if session["source_kind"] == "zip":
            try:
                extracted = extract_uploaded_archive(chunk_root(), assembled, max_total_bytes=_max_upload_bytes())
            except zipfile.BadZipFile as exc:
                raise ValueError("Uploaded file is not a valid zip archive") from exc
            staging = extracted
        else:
            staging = assembled
        ok, message = validate_sparc_structure(staging)
        if not ok:
            raise ValueError(message)
        root = resolve_project_root(staging)
        if session["fhir_mode"] == "descriptions":
            check_descriptions_match(session["fhir_descriptions"], root)

        target = dataset_dir(upload_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root), str(target))
    except (ChunkStoreError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        if extracted is not None and extracted.exists():
            shutil.rmtree(extracted, ignore_errors=True)

    store.cleanup(upload_id)
    warnings = sampleless_subjects(target)

    if session["commit_mode"] == "on_approve":
        sessions.update_session(conn, upload_id, status="staged")
        return {"upload_id": upload_id, "status": "staged", "warnings": warnings}

    sessions.update_session(conn, upload_id, status="processing")
    background.add_task(jobs.run_commit_and_push, upload_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"upload_id": upload_id, "status": "processing", "warnings": warnings},
    )


@router.post("/{upload_id}/approve", status_code=status.HTTP_202_ACCEPTED)
def approve_upload(
    upload_id: str, background: BackgroundTasks,
    conn=Depends(get_conn), _creds: dict = Depends(require_upload_role),
):
    """Commit a staged session (the portal's Approval), or retry a failed commit."""
    _require_status(_session_or_404(conn, upload_id), "staged", "failed")
    sessions.update_session(conn, upload_id, status="processing", failure_stage=None, failure_message=None)
    background.add_task(jobs.run_commit_and_push, upload_id)
    return {"upload_id": upload_id, "status": "processing"}


@router.delete("/{upload_id}")
def cancel_upload(upload_id: str, conn=Depends(get_conn), _creds: dict = Depends(require_upload_role)):
    """Cancel a session that is not committed: drop its parts, staged files and row."""
    _require_status(_session_or_404(conn, upload_id), "receiving", "staged", "failed")
    _chunk_store().cleanup(upload_id)
    shutil.rmtree(dataset_dir(upload_id), ignore_errors=True)
    sessions.delete_session(conn, upload_id)
    return {"upload_id": upload_id, "deleted": True}


# ── Staged FHIR annotation draft ───────────────────────────────────────


def _staged(conn, upload_id: str) -> Dict[str, Any]:
    session = _session_or_404(conn, upload_id)
    _require_status(session, "staged", "failed")
    return session


@router.get("/{upload_id}/fhir/tree")
def get_staged_tree(upload_id: str, conn=Depends(get_conn), _creds: dict = Depends(validate_credentials)):
    """Prefilled descriptions for the staged dataset (UUIDs are assigned on approval)."""
    session = _staged(conn, upload_id)
    return build_tree(dataset_dir(upload_id), session["name"])


@router.get("/{upload_id}/fhir/annotation")
def get_staged_annotation(upload_id: str, conn=Depends(get_conn), _creds: dict = Depends(validate_credentials)):
    session = _session_or_404(conn, upload_id)
    if session["fhir_descriptions"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No annotation draft")
    return {"descriptions": session["fhir_descriptions"]}


@router.put("/{upload_id}/fhir/annotation")
def put_staged_annotation(
    upload_id: str, body: AnnotationBody,
    conn=Depends(get_conn), _creds: dict = Depends(require_upload_role),
):
    _staged(conn, upload_id)
    try:
        check_descriptions_match(body.descriptions, dataset_dir(upload_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    sessions.update_session(conn, upload_id, fhir_mode="descriptions", fhir_descriptions=body.descriptions)
    return {"descriptions": body.descriptions}


@router.get("/{upload_id}/fhir/preview")
def preview_staged_fhir(upload_id: str, conn=Depends(get_conn), _creds: dict = Depends(validate_credentials)):
    """Dry-run fhir.json for the draft (or the auto tree); UUIDs are placeholders until approval."""
    session = _staged(conn, upload_id)
    root = dataset_dir(upload_id)
    descriptions = session["fhir_descriptions"] or build_tree(root, session["name"])["descriptions"]
    return build_fhir_json(root, descriptions)
