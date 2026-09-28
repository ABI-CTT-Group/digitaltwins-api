"""Core orchestrator for dataset deletion.

Coordinates Postgres and MinIO deletions within a single transaction
so that either everything succeeds or everything is rolled back.
"""

import os
import logging
import shutil
from typing import Optional

import psycopg2

from dotenv import load_dotenv

load_dotenv()

from ..utils.config_loader import is_truthy

logger = logging.getLogger(__name__)


class Deleter(object):
    def __init__(self):
        self._postgres_enabled = is_truthy(os.getenv("POSTGRES_ENABLED"))
        self._minio_enabled = is_truthy(os.getenv("MINIO_ENABLED"))

        self._postgres_deleter = None
        self._minio_deleter = None

        if self._postgres_enabled:
            from ..postgres.deleter import Deleter as PostgresDeleter
            self._postgres_deleter = PostgresDeleter()

        if self._minio_enabled:
            from ..minio.deleter import Deleter as MinioDeleter
            self._minio_deleter = MinioDeleter()

    def delete_dataset(self, dataset_uuid: str) -> dict:
        """Delete a dataset from Postgres and MinIO.

        Args:
            dataset_uuid: The UUID of the dataset to delete.

        Returns:
            A summary dict with keys ``dataset_uuid`` and ``minio_objects_deleted``.

        Raises:
            ValueError: If the dataset UUID does not exist in Postgres.
            RuntimeError: If MinIO deletion fails (Postgres is rolled back).
        """
        # 1. Check existence
        if self._postgres_enabled and self._postgres_deleter:
            if not self._postgres_deleter.dataset_exists(dataset_uuid):
                raise ValueError(f"Dataset with UUID '{dataset_uuid}' not found")

        # 2. Open a Postgres transaction
        conn: Optional[psycopg2.extensions.connection] = None
        minio_deleted = 0
        cleanup = {"fhir_status": "none", "subject_uuids": [], "upload_ids": []}

        try:
            if self._postgres_enabled and self._postgres_deleter:
                conn = self._postgres_deleter.connect()
                conn.autocommit = False
                cur = conn.cursor()

            # 3. Delete MinIO objects first
            if self._minio_enabled and self._minio_deleter:
                minio_deleted = self._minio_deleter.delete_dataset_objects(dataset_uuid)
                logger.info("Deleted %d MinIO object(s) for dataset %s", minio_deleted, dataset_uuid)

            # 4. Delete Postgres rows
            if conn:
                cleanup = self._postgres_deleter.get_cleanup_info(cur, dataset_uuid)
                self._postgres_deleter.delete_dataset(cur, dataset_uuid)

            # 5. Commit
            if conn:
                conn.commit()
                logger.info("Postgres transaction committed for dataset %s", dataset_uuid)

        except Exception:
            if conn:
                conn.rollback()
                logger.error("Postgres transaction rolled back for dataset %s", dataset_uuid)
            raise
        finally:
            if conn:
                conn.close()

        # 6. Outside Postgres, best-effort: FHIR resources and local copies.
        fhir_deleted = (_delete_fhir_resources(dataset_uuid, cleanup["subject_uuids"])
                        if cleanup["fhir_status"] != "none" else {})
        _remove_local_copies(dataset_uuid, cleanup["upload_ids"])

        return {
            "dataset_uuid": dataset_uuid,
            "minio_objects_deleted": minio_deleted,
            "fhir_resources_deleted": fhir_deleted,
        }


def _delete_fhir_resources(dataset_uuid: str, subject_uuids: list) -> dict:
    """Remove the dataset's HAPI FHIR resources; log and carry on if HAPI is unreachable."""
    from ..measurements import fhir_service

    try:
        return fhir_service.delete_dataset_fhir_resources(dataset_uuid, subject_uuids, fhir_service.get_fhir_rest())
    except Exception as exc:
        logger.warning("FHIR cleanup failed for dataset %s: %s", dataset_uuid, exc)
        return {}


def _remove_local_copies(dataset_uuid: str, upload_ids: list) -> None:
    from ..measurements.staging import dataset_dir, staging_root

    for path in [dataset_dir(u) for u in upload_ids] + [staging_root() / "downloads" / dataset_uuid]:
        shutil.rmtree(path, ignore_errors=True)
