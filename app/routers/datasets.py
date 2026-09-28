"""
Dataset Router.

Consolidates all dataset endpoints: list, get, sample-types, samples,
upload, download, and delete.
"""

import json
import logging
import os
import shutil
import tempfile
import traceback
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from digitaltwins import Querier, Uploader, Downloader, Deleter
from digitaltwins.core.connection import Connection
from digitaltwins.measurements import jobs, sessions
from digitaltwins.measurements.pipeline import check_descriptions_match
from digitaltwins.measurements.staging import dataset_dir as staged_dataset_dir, staging_root
from digitaltwins.measurements.validation import (
    extract_uploaded_archive,
    resolve_project_root,
    validate_sparc_structure,
)
from . import dataset_uploads
from .auth import require_upload_role, validate_credentials
from .dataset_uploads import _max_upload_bytes
from .dependencies import get_querier, get_uploader, get_downloader, get_deleter

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Query endpoints ───────────────────────────────────────────────────


@router.get("/datasets", tags=["datasets"])
def get_datasets(
    descriptions: bool = False,
    categories: Optional[List[str]] = Query(default=None),
    keywords: Optional[str] = Query(default=None, description="JSON string of keyword filters, e.g. '{\"key\": \"value\"}'"),
    querier: Querier = Depends(get_querier),
):
    """
    Retrieve a list of datasets.

    Args:
        descriptions (bool, optional): If True, includes description fields for each dataset. Defaults to False.
        categories (List[str], optional): Filter datasets by one or more categories (e.g. "workflow", "primary").
        keywords (str, optional): JSON-encoded dict of keyword filters (e.g. '{"organ": "heart"}').
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of datasets under the 'datasets' key.

    Examples:
        GET /datasets
        GET /datasets?categories=workflow
        GET /datasets?categories=primary&categories=workflow
    """
    kw = {}
    if keywords:
        try:
            kw = json.loads(keywords)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="'keywords' must be a valid JSON object string.")

    datasets = querier.get_datasets(
        descriptions=descriptions,
        categories=categories,
        keywords=kw if kw else None,
    )
    return {"datasets": datasets}


@router.get("/datasets/{dataset_uuid}", tags=["datasets"])
def get_dataset(
    dataset_uuid: str,
    get_cwl: bool = False,
    querier: Querier = Depends(get_querier),
):
    """
    Retrieve a specific dataset by its UUID.

    Args:
        dataset_uuid (str): The UUID of the dataset to retrieve. Example: abdc7a8a-33ce-11f1-a982-0242ac120007
        get_cwl (bool, optional): If True, also fetches and returns the associated CWL file (tool datasets only).
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the dataset details under the 'dataset' key.
    """
    dataset = querier.get_dataset(dataset_uuid=dataset_uuid, get_cwl=get_cwl)
    return {"dataset": dataset}


@router.get("/datasets/{dataset_uuid}/sample-types", tags=["datasets"])
def get_dataset_sample_types(
    dataset_uuid: str,
    querier: Querier = Depends(get_querier),
):
    """
    Retrieve all sample types present in a dataset.

    Args:
        dataset_uuid (str): The UUID of the dataset. Example: abdc7a8a-33ce-11f1-a982-0242ac120007
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of sample types under the 'sample_types' key.
    """
    sample_types = querier.get_dataset_sample_types(dataset_uuid=dataset_uuid)
    return {"sample_types": sample_types}


@router.get("/datasets/{dataset_uuid}/samples", tags=["datasets"])
def get_dataset_samples(
    dataset_uuid: str,
    sample_type: Optional[str] = Query(default=None, description="Filter samples by type, e.g. 'ax dyn pre'"),
    querier: Querier = Depends(get_querier),
):
    """
    Retrieve samples belonging to a dataset, optionally filtered by sample type.

    Args:
        dataset_uuid (str): The UUID of the dataset. Example: abdc7a8a-33ce-11f1-a982-0242ac120007
        sample_type (str, optional): Filter samples by this sample type (e.g. "ax dyn pre").
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of samples under the 'samples' key.
    """
    samples = querier.get_dataset_samples(dataset_uuid=dataset_uuid, sample_type=sample_type)
    return {"samples": samples}


# ── Upload endpoint ───────────────────────────────────────────────────


def _safe_rel_path(name: str) -> PurePosixPath:
    """A part's relative path, rejecting absolute paths and ``..`` components."""
    rel = PurePosixPath(name.replace("\\", "/"))
    if not name or rel.is_absolute() or any(part in ("", "..") for part in rel.parts):
        raise ValueError(f"Unsafe file path in upload: {name!r}")
    return rel


def _receive_upload(files: List[UploadFile], tmp_path: Path) -> Path:
    """Stream the parts to disk; return the dataset root (the common top-level folder).

    A single ``.zip`` part is extracted with zip-slip and size guards.
    """
    if len(files) == 1 and files[0].filename and files[0].filename.lower().endswith(".zip"):
        zip_path = tmp_path / "upload.zip"
        with open(zip_path, "wb") as out:
            shutil.copyfileobj(files[0].file, out)
        try:
            extracted = extract_uploaded_archive(tmp_path, zip_path, max_total_bytes=_max_upload_bytes())
        except zipfile.BadZipFile as exc:
            raise ValueError("Invalid zip file") from exc
        zip_path.unlink()
        items = [item for item in extracted.iterdir() if item.name != "__MACOSX"]
        return items[0] if len(items) == 1 and items[0].is_dir() else extracted

    received = tmp_path / "files"
    rels = [_safe_rel_path(upload.filename or "") for upload in files]
    for upload, rel in zip(files, rels):
        dest = received / Path(*rel.parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as out:
            shutil.copyfileobj(upload.file, out)
    # Pass the dataset root, not the tmp root, when every file shares a top-level folder.
    if all(len(r.parts) > 1 and r.parts[0] == rels[0].parts[0] for r in rels):
        return received / rels[0].parts[0]
    return received


def _ingest_measurements(dataset_root: Path, category: str, fhir: str, fhir_descriptions: Optional[str]) -> dict:
    """Validate, then commit synchronously through the upload-session pipeline."""
    ok, message = validate_sparc_structure(dataset_root)
    if not ok:
        raise ValueError(message)
    name = dataset_root.name
    root = resolve_project_root(dataset_root)
    descriptions = None
    if fhir_descriptions:
        try:
            descriptions = json.loads(fhir_descriptions)
        except json.JSONDecodeError as exc:
            raise ValueError("'fhir_descriptions' must be a JSON object") from exc
        check_descriptions_match(descriptions, root)

    conn, _ = Connection().connect()
    try:
        upload_id = sessions.create_session(
            conn, category=category,
            name=name, description=None, source_kind="folder", commit_mode="on_finalize",
            fhir_mode="descriptions" if descriptions is not None else fhir, fhir_descriptions=descriptions,
        )
        target = staged_dataset_dir(upload_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root), str(target))
        sessions.update_session(conn, upload_id, status="processing")
        jobs.run_commit_job(upload_id)
        session = sessions.get_session(conn, upload_id)
        if session["status"] != "completed":
            raise RuntimeError(session["failure_message"] or "commit failed")
        with conn.cursor() as cur:
            cur.execute("SELECT fhir_status FROM dataset WHERE dataset_uuid = %s", (session["dataset_uuid"],))
            fhir_status = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return {"dataset_uuid": session["dataset_uuid"], "fhir_status": fhir_status}


@router.post("/datasets", tags=["datasets"])
async def upload_dataset(
    background: BackgroundTasks,
    files: List[UploadFile] = File(
        ...,
        description=(
            "All files inside the dataset folder. "
            "Each file's ``filename`` field must carry the relative path from the "
            "dataset root (e.g. ``MyDataset/subjects.csv``), exactly as a browser "
            "sends them when ``<input webkitdirectory>`` is used."
        ),
    ),
    category: str = Query(
        ...,
        description="Dataset category including measurements, models, tools & workflows",
    ),
    fhir: Literal["none", "auto"] = Query(
        "none", description="measurements only: 'auto' annotates and pushes FHIR after the commit",
    ),
    fhir_descriptions: Optional[str] = Form(
        None, description="measurements only: FHIR descriptions JSON, keyed by folder name (UUIDs are assigned)",
    ),
    uploader: Uploader = Depends(get_uploader),
    _creds: dict = Depends(require_upload_role),
) -> dict[str, Any]:
    """Accept a folder (or single ``.zip``) upload and ingest it in one request.

    The client must send every file in the dataset folder as a separate
    multipart part, preserving the relative path in each part's
    ``filename`` field. Parts are streamed to disk on the staging volume.
    Measurement datasets are SPARC-validated and committed through the
    upload-session pipeline (see /datasets/uploads for large, resumable
    uploads); other categories go straight to ``Uploader.upload_dataset``.
    """
    measurements = category in dataset_uploads.INGEST_CATEGORIES
    try:
        staging_root().mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=staging_root()) as tmp_dir:
            dataset_dir_path = _receive_upload(files, Path(tmp_dir))
            if measurements:
                result = await run_in_threadpool(
                    _ingest_measurements, dataset_dir_path, category, fhir, fhir_descriptions
                )
            else:
                result = {"dataset_uuid": uploader.upload_dataset(dataset_path=str(dataset_dir_path), category=category)}

    except (ValueError, TypeError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid upload payload: {exc}",
        ) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process dataset upload: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error while processing dataset upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while processing dataset upload.",
        ) from exc

    if result.get("fhir_status") == "pending":
        background.add_task(jobs.run_fhir_push_job, result["dataset_uuid"])
    return {"message": "Dataset uploaded successfully.", **result}


# ── Download endpoint ─────────────────────────────────────────────────


@router.get("/datasets/{dataset_uuid}/download", tags=["datasets"])
def download_dataset(
    dataset_uuid: str,
    downloader: Downloader = Depends(get_downloader),
    _valid: bool = Depends(validate_credentials),
) -> StreamingResponse:
    """Download all files for a dataset as a ZIP archive.

    Args:
        dataset_uuid: The UUID of the dataset to download.

    Returns:
        A streaming ZIP archive containing all dataset files.

    Raises:
        HTTPException 404: If no objects are found for the dataset UUID.
        HTTPException 503: If the storage backend is unreachable.
        HTTPException 500: If an unexpected error occurs.
    """
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, f"{dataset_uuid}.zip")

    try:
        # Download all dataset files into the temp directory
        save_dir = os.path.join(tmp_dir, "data")
        downloader.download_dataset(dataset_uuid, save_dir=save_dir)

        # Create a ZIP archive from the downloaded files
        dataset_dir = os.path.join(save_dir, dataset_uuid)
        if not os.path.isdir(dataset_dir):
            # Fallback: ZIP everything under save_dir
            dataset_dir = save_dir

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(dataset_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, dataset_dir)
                    zf.write(file_path, arcname)

    except FileNotFoundError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConnectionError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage backend unavailable: {exc}",
        ) from exc
    except (RuntimeError, EnvironmentError) as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download dataset: {exc}",
        ) from exc
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.exception("Unexpected error while downloading dataset")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while downloading dataset.",
        ) from exc

    def _stream_and_cleanup():
        """Stream the ZIP file and clean up the temp directory afterwards."""
        try:
            with open(zip_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return StreamingResponse(
        _stream_and_cleanup(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{dataset_uuid}.zip"',
        },
    )


# ── Delete endpoint ───────────────────────────────────────────────────


@router.delete("/datasets/{dataset_uuid}", tags=["datasets"])
def delete_dataset(
    dataset_uuid: str,
    deleter: Deleter = Depends(get_deleter),
    _creds: dict = Depends(require_upload_role),
) -> dict:
    """Delete a dataset and all associated data: Postgres (incl. its subject /
    sample rows), MinIO, HAPI FHIR resources and local copies.

    Args:
        dataset_uuid: The UUID of the dataset to delete.

    Returns:
        A confirmation message with deletion details.

    Raises:
        HTTPException 404: If the dataset UUID does not exist.
        HTTPException 500: If storage deletion fails.
    """
    try:
        result = deleter.delete_dataset(dataset_uuid)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage deletion failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error while deleting dataset")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while deleting dataset.",
        ) from exc

    return {
        "message": "Dataset deleted successfully.",
        "dataset_uuid": result["dataset_uuid"],
        "minio_objects_deleted": result["minio_objects_deleted"],
        "fhir_resources_deleted": result["fhir_resources_deleted"],
    }
