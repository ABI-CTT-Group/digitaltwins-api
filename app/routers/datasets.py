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
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from digitaltwins import Querier, Uploader, Downloader, Deleter
from .auth import validate_credentials
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


@router.post("/datasets", tags=["datasets"])
async def upload_dataset(
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
    uploader: Uploader = Depends(get_uploader),
    _valid: bool = Depends(validate_credentials),
) -> dict[str, Any]:
    """Accept a folder upload and ingest it through ``Uploader.upload_dataset``.

    The client must send every file in the dataset folder as a separate
    multipart part, preserving the relative path in each part's
    ``filename`` field.  The server reconstructs the full directory tree
    inside a temporary directory, detects the dataset root from the
    common top-level folder name, then hands the path off to the core
    uploader.
    """
    # ── 1. Rebuild folder tree in a temp directory and call the uploader ─
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Check if this is a single .zip file upload
            if len(files) == 1 and files[0].filename and files[0].filename.lower().endswith(".zip"):
                zip_path = tmp_path / files[0].filename
                zip_path.write_bytes(await files[0].read())

                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(tmp_path)
                except zipfile.BadZipFile as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid zip file",
                    ) from exc

                zip_path.unlink() # remove the zip file itself

                # Detect common top-level directory
                extracted_items = [item for item in tmp_path.iterdir() if item.name != "__MACOSX"]
                if len(extracted_items) == 1 and extracted_items[0].is_dir():
                    dataset_dir = str(extracted_items[0])
                else:
                    dataset_dir = str(tmp_path)
            else:
                for upload in files:
                    # filename carries the relative path, e.g. "MyDataset/subjects.csv"
                    dest = tmp_path / (upload.filename or "")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(await upload.read())

                # Detect common top-level directory so we pass the dataset root,
                # not the tmp root, to upload_dataset.
                all_parts = [Path(f.filename).parts for f in files if f.filename]
                if all_parts and all(len(p) > 1 and p[0] == all_parts[0][0] for p in all_parts):
                    dataset_dir = str(tmp_path / all_parts[0][0])
                else:
                    dataset_dir = tmp_dir

            dataset_uuid = uploader.upload_dataset(
                dataset_path=dataset_dir,
                category=category,
            )

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

    return {
        "message": "Dataset uploaded successfully.",
        "dataset_uuid": dataset_uuid,
    }


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
    _valid: bool = Depends(validate_credentials),
) -> dict:
    """Delete a dataset and all associated data from Postgres and MinIO.

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
    }
