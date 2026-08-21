"""
Investigation Router.
"""
from fastapi import APIRouter, Depends

from digitaltwins import Querier
from .dependencies import get_querier


router = APIRouter()


@router.get("/investigations", tags=["investigations"])
def get_investigations(get_details: bool = False, querier: Querier = Depends(get_querier)):
    """
    Retrieve a list of investigations.

    Args:
        get_details (bool, optional): If True, returns detailed information about each investigation. Defaults to False.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of investigations under the 'investigations' key.
    """
    investigations = querier.get_investigations(get_details=get_details)
    return {"investigations": investigations}


@router.get("/investigations/{investigation_id}", tags=["investigations"])
def get_investigation(investigation_id: int, querier: Querier = Depends(get_querier)):
    """
    Retrieve a specific investigation by its ID.

    Args:
        investigation_id (int): The ID of the investigation to retrieve.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the investigation details under the 'investigation' key.
    """
    investigation = querier.get_investigation(investigation_id)
    return {"investigation": investigation}
