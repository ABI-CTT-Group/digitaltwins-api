"""Upload router definitions."""

import tempfile
import traceback
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict

from src.digitaltwins.core.uploader import Uploader
from .auth import validate_credentials

router = APIRouter()


def get_uploader() -> Uploader:
    """
    Build an Uploader() instance for dependency injection.
    """
    return Uploader()


# --- Pydantic Models for Assay Upload ---

class AssayInputModel(BaseModel):
    name: str = ""
    category: str = ""
    dataset_uuid: str = ""
    sample_type: str = ""

class AssayOutputModel(BaseModel):
    name: str = ""
    category: str = ""
    dataset_name: str = ""
    sample_name: str = ""

class AssayDataModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    assay_uuid: Optional[str] = ""
    assay_seek_id: int
    workflow_seek_id: int
    cohort: List[str]
    ready: bool
    inputs: Optional[List[AssayInputModel]] = []
    outputs: Optional[List[AssayOutputModel]] = []

# ----------------------------------------


@router.post("/dataset", tags=["upload"])
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
        description="Dataset category used as the MinIO bucket name (e.g. 'primary').",
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
                import zipfile
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
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while processing dataset upload.",
        ) from exc

    return {
        "message": "Dataset uploaded successfully.",
        "dataset_uuid": dataset_uuid,
    }


@router.post("/assay", tags=["upload"])
async def configure_assay(
    assay_data: AssayDataModel,
    uploader: Uploader = Depends(get_uploader),
    _valid: bool = Depends(validate_credentials),
) -> dict[str, Any]:
    """Configure an assay through PostgreSQL.
    
    Accepts an AssayDataModel JSON payload containing the assay configuration
    as well as inputs and outputs mapping. Directly invokes
    `uploader.configure_assay(assay_data.model_dump())` to persist the 
    configuration in the PostgreSQL database.
    """
    try:
        # Convert Pydantic payload to dictionary string exactly as the DB layer expects
        payload = assay_data.model_dump()
        assay_uuid = uploader.configure_assay(payload)

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure assay: {exc}",
        ) from exc

    return {
        "message": "Assay configured successfully.",
        "assay_uuid": assay_uuid,
    }
