"""
Program Router.
"""
from fastapi import APIRouter, Depends

from digitaltwins import Querier
from .dependencies import get_querier


router = APIRouter()


@router.get("/programs", tags=["programs"])
def get_programs(get_details: bool = False, querier: Querier = Depends(get_querier)):
    """
    Retrieve a list of programs.

    Args:
        get_details (bool, optional): If True, returns detailed information about each program. Defaults to False.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of programs under the 'programs' key.
    """
    programs = querier.get_programs(get_details=get_details)
    return {"programs": programs}


@router.get("/programs/{program_id}", tags=["programs"])
def get_program(program_id: int, querier: Querier = Depends(get_querier)):
    """
    Retrieve a specific program by its ID.

    Args:
        program_id (int): The ID of the program to retrieve.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the program details under the 'program' key.
    """
    program = querier.get_program(program_id)
    return {"program": program}
