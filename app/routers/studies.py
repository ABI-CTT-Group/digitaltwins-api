"""
Study Router.
"""
from fastapi import APIRouter, Depends

from digitaltwins import Querier
from .dependencies import get_querier


router = APIRouter()


@router.get("/studies", tags=["studies"])
def get_studies(get_details: bool = False, querier: Querier = Depends(get_querier)):
    """
    Retrieve a list of studies.

    Args:
        get_details (bool, optional): If True, returns detailed information about each study. Defaults to False.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of studies under the 'studies' key.
    """
    studies = querier.get_studies(get_details=get_details)
    return {"studies": studies}


@router.get("/studies/{study_id}", tags=["studies"])
def get_study(study_id: int, querier: Querier = Depends(get_querier)):
    """
    Retrieve a specific study by its ID.

    Args:
        study_id (int): The ID of the study to retrieve.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the study details under the 'study' key.
    """
    study = querier.get_study(study_id)
    return {"study": study}
