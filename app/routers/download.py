"""Download router definitions."""

import os
import shutil
import tempfile
import traceback
import zipfile

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.digitaltwins.core.downloader import Downloader
from .auth import validate_credentials

router = APIRouter()


def get_downloader() -> Downloader:
    """Build a Downloader() instance for dependency injection."""
    return Downloader()


@router.get("/datasets/{dataset_uuid}/download", tags=["download"])
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
        traceback.print_exc()
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
