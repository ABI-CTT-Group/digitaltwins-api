"""Staging volume layout (``DATASET_STAGING_DIR``, default ``./dataset_staging``).

    <root>/chunks/upload_<upload_id>/   chunk-store parts (see chunk_store.py)
    <root>/datasets/<upload_id>/        validated dataset root: staged until commit,
                                        then kept as the local cache for FHIR build
"""
import os
from pathlib import Path


def staging_root() -> Path:
    return Path(os.getenv("DATASET_STAGING_DIR", "./dataset_staging"))


def chunk_root() -> Path:
    return staging_root() / "chunks"


def dataset_dir(upload_id: str) -> Path:
    return staging_root() / "datasets" / str(upload_id)
