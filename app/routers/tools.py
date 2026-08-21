"""
Tool Router.
"""
from fastapi import APIRouter, Depends

from digitaltwins import Querier
from .dependencies import get_querier


router = APIRouter()


@router.get("/tools", tags=["tools"])
def get_tools(querier: Querier = Depends(get_querier)):
    """
    Retrieve a list of tools.

    Args:
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of tools under the 'tools' key.
    """
    tools = querier.get_tools()
    return {"tools": tools}


@router.get("/tools/{tool_id}", tags=["tools"])
def get_tool(tool_id: int, querier: Querier = Depends(get_querier)):
    """
    Retrieve a specific tool by its ID.

    Args:
        tool_id (int): The ID of the tool to retrieve.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the tool details under the 'tool' key.
    """
    tool = querier.get_tool(tool_id)
    return {"tool": tool}
