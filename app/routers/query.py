import os

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi import Depends

from digitaltwins import Querier

from app.routers.auth import validate_credentials

load_dotenv()
CONFIG_FILE_PATH = os.getenv("CONFIG_FILE_PATH")


router = APIRouter()

querier = Querier(CONFIG_FILE_PATH)


@router.get("/programs", tags=["query"])
def programs(program_id=None, get_details=False, valid=Depends(validate_credentials)):
    if program_id:
        program = querier.get_program(program_id)
        return {"program": program}
    else:
        programs = querier.get_programs(get_details=get_details)
        return {"programs": programs}

