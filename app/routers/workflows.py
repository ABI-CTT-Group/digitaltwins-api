"""
Workflow Router.
"""
from fastapi import APIRouter, Depends

from digitaltwins import Querier
from .dependencies import get_querier


router = APIRouter()


@router.get("/workflows", tags=["workflows"])
def get_workflows(querier: Querier = Depends(get_querier)):
    """
    Retrieve a list of workflows.

    Args:
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of workflows under the 'workflows' key.
    """
    workflows = querier.get_workflows()
    return {"workflows": workflows}


@router.get("/workflows/{workflow_id}", tags=["workflows"])
def get_workflow(workflow_id: int, querier: Querier = Depends(get_querier)):
    """
    Retrieve a specific workflow by its ID.

    Args:
        workflow_id (int): The ID of the workflow to retrieve.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the workflow details under the 'workflow' key.
    """
    workflow = querier.get_workflow(workflow_id)
    return {"workflow": workflow}
