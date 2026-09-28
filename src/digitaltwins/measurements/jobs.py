"""Background jobs for dataset ingest.

Jobs run in the API process (FastAPI ``BackgroundTasks``) after the 202
response; their state lives in Postgres (``upload_session.status``,
``dataset.fhir_status``), never in memory, so clients poll the rows. A job
never raises: failures are recorded on the row. A job cut short by a restart is
marked failed (and so retryable) by :func:`sweep_interrupted_jobs` at startup.
"""
import asyncio
import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.connection import Connection
from . import fhir_service, pipeline, sessions
from .staging import dataset_dir, staging_root
from .tree import build_tree

logger = logging.getLogger(__name__)

_INTERRUPTED = "Interrupted by an API restart; retry."


def _connect():
    conn, _ = Connection().connect()
    return conn


def set_fhir_status(conn, dataset_uuid: str, status: str, message: Optional[str] = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE dataset SET fhir_status = %s, fhir_failure_message = %s WHERE dataset_uuid = %s",
            (status, message, dataset_uuid),
        )
    conn.commit()


def _requested_descriptions(session: Dict[str, Any], root: Path) -> Optional[Dict[str, Any]]:
    """FHIR descriptions the session asked for: auto-annotated, supplied, or none."""
    if session["fhir_mode"] == "auto":
        return build_tree(root, session["name"])["descriptions"]
    if session["fhir_mode"] == "descriptions":
        return session["fhir_descriptions"]
    return None


def run_commit_job(upload_id: str) -> None:
    """Commit a ``processing`` session's staged dataset; complete or fail the session."""
    conn = _connect()
    try:
        session = sessions.get_session(conn, upload_id)
        root = dataset_dir(upload_id)
        try:
            result = pipeline.commit_dataset(
                root,
                category=session["category"],
                descriptions=_requested_descriptions(session, root),
                dataset_name=session["name"],
            )
        except Exception as exc:
            logger.exception("Commit failed for upload %s", upload_id)
            sessions.update_session(
                conn, upload_id, status="failed", failure_stage="commit", failure_message=str(exc)
            )
            return

        sessions.update_session(
            conn, upload_id, status="completed", dataset_uuid=result.dataset_uuid,
            failure_stage=None, failure_message=None,
        )
        if result.descriptions is not None:
            set_fhir_status(conn, result.dataset_uuid, "pending")
        logger.info("Committed upload %s as dataset %s", upload_id, result.dataset_uuid)
    finally:
        conn.close()


def run_commit_and_push(upload_id: str) -> None:
    """Commit, then push FHIR straight away when the session asked for it."""
    run_commit_job(upload_id)
    conn = _connect()
    try:
        session = sessions.get_session(conn, upload_id)
        dataset = pipeline.get_dataset_row(conn, session["dataset_uuid"]) if session["dataset_uuid"] else None
    finally:
        conn.close()
    if dataset and dataset["fhir_status"] == "pending":
        run_fhir_push_job(session["dataset_uuid"])


def public_base() -> str:
    """Public URL of this API, used for FHIR endpoint URLs."""
    return os.getenv("DIGITALTWINS_API_PUBLIC_URL", "http://localhost/digitaltwins-api")


def _replace_fhir_resources(conn, dataset_uuid: str, fhir_json: Dict[str, Any]) -> None:
    # digitaltwins-on-fhir keeps any resource whose identifier already exists,
    # so the previous graph must go first or an edited annotation never lands.
    subject_uuids = {subject_uuid for subject_uuid, _ in pipeline.fetch_mapping(conn, dataset_uuid).values()}
    removed = fhir_service.delete_dataset_fhir_resources(dataset_uuid, subject_uuids, fhir_service.get_fhir_rest())
    if removed:
        logger.info("Removed earlier FHIR resources for %s: %s", dataset_uuid, removed)
    asyncio.run(fhir_service.push_to_hapi_fhir(fhir_json, fhir_service.get_fhir_adapter()))


def run_fhir_push_job(dataset_uuid: str) -> None:
    """Build fhir.json from the stored annotation, store it in MinIO and (re)push it to HAPI.

    Earlier resources for the dataset are removed first, so a retry or re-push
    never duplicates. On failure the dataset stays committed with
    ``fhir_status=failed`` and its local copy is kept for the retry.
    """
    conn = _connect()
    try:
        set_fhir_status(conn, dataset_uuid, "pushing")
        try:
            descriptions = pipeline.load_annotation(conn, dataset_uuid)
            if descriptions is None:
                raise ValueError("No FHIR annotation stored for this dataset")
            dataset = pipeline.get_dataset_row(conn, dataset_uuid)
            root = pipeline.local_dataset(conn, dataset_uuid)
            descriptions = fhir_service.compute_endpoint_urls(descriptions, dataset_uuid, public_base())
            pipeline.save_annotation(conn, dataset_uuid, descriptions)
            fhir_json = fhir_service.build_fhir_json(root, descriptions)
            pipeline.store_fhir_json(dataset["category"], dataset_uuid, fhir_json)
            _replace_fhir_resources(conn, dataset_uuid, fhir_json)
        except Exception as exc:
            logger.exception("FHIR push failed for dataset %s", dataset_uuid)
            set_fhir_status(conn, dataset_uuid, "failed", str(exc))
            return
        set_fhir_status(conn, dataset_uuid, "completed")
        shutil.rmtree(root, ignore_errors=True)  # local copy no longer needed
        logger.info("Pushed FHIR for dataset %s", dataset_uuid)
    finally:
        conn.close()


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def sweep_stale_caches(conn, max_age_days: int = 7) -> None:
    """Remove local dataset copies untouched for ``max_age_days``.

    Only caches of committed datasets and MinIO re-downloads are removed;
    staged / receiving / failed sessions keep their files until approved or
    cancelled (they are the only copy).
    """
    cutoff = time.time() - max_age_days * 86400
    datasets = staging_root() / "datasets"
    for path in datasets.iterdir() if datasets.is_dir() else []:
        if path.stat().st_mtime >= cutoff or not _is_uuid(path.name):
            continue
        session = sessions.get_session(conn, path.name)
        if session is None or session["status"] == "completed":
            shutil.rmtree(path, ignore_errors=True)
    downloads = staging_root() / "downloads"
    for path in downloads.iterdir() if downloads.is_dir() else []:
        if path.stat().st_mtime < cutoff:
            shutil.rmtree(path, ignore_errors=True)


def sweep_interrupted_jobs(conn) -> None:
    """Fail jobs left mid-flight by a restart so clients can retry them."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE upload_session SET status = 'failed', failure_stage = 'commit', "
            "failure_message = %s, updated_at = now() WHERE status = 'processing'",
            (_INTERRUPTED,),
        )
        sessions_failed = cur.rowcount
        cur.execute(
            "UPDATE dataset SET fhir_status = 'failed', fhir_failure_message = %s "
            "WHERE fhir_status IN ('pending', 'pushing')",
            (_INTERRUPTED,),
        )
        fhir_failed = cur.rowcount
    conn.commit()
    if sessions_failed or fhir_failed:
        logger.warning("Startup sweep failed %d upload(s) and %d FHIR push(es)", sessions_failed, fhir_failed)


def sweep_on_startup() -> None:
    conn = _connect()
    try:
        sweep_interrupted_jobs(conn)
        sweep_stale_caches(conn)
    finally:
        conn.close()
