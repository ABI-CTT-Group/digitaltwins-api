"""
Project Router.
"""
from fastapi import APIRouter, Depends

from digitaltwins import Querier
from .dependencies import get_querier


router = APIRouter()


@router.get("/projects", tags=["projects"])
def get_projects(get_details: bool = False, querier: Querier = Depends(get_querier)):
    """
    Retrieve a list of projects.

    Args:
        get_details (bool, optional): If True, returns detailed information about each project. Defaults to False.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of projects under the 'projects' key.
    """
    projects = querier.get_projects(get_details=get_details)
    return {"projects": projects}


@router.get("/projects/{project_id}", tags=["projects"])
def get_project(project_id: int, querier: Querier = Depends(get_querier)):
    """
    Retrieve a specific project by its ID.

    Args:
        project_id (int): The ID of the project to retrieve.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the project details under the 'project' key.
    """
    project = querier.get_project(project_id)
    return {"project": project}
