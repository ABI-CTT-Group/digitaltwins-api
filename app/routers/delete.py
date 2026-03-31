"""Delete router definitions."""

import traceback

from fastapi import APIRouter, Depends, HTTPException, status

from src.digitaltwins.core.deleter import Deleter
from .auth import validate_credentials

router = APIRouter()


def get_deleter() -> Deleter:
    """Build a Deleter() instance for dependency injection."""
    return Deleter()


@router.delete("/datasets/{dataset_uuid}", tags=["delete"])
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
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while deleting dataset.",
        ) from exc

    return {
        "message": "Dataset deleted successfully.",
        "dataset_uuid": result["dataset_uuid"],
        "minio_objects_deleted": result["minio_objects_deleted"],
    }
