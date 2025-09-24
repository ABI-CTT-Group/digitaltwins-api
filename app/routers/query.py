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
def programs(get_details=False, valid=Depends(validate_credentials)):
    programs = querier.get_programs(get_details=get_details)
    return {"programs": programs}
@router.get("/programs/{program_id}", tags=["query"])
def program(program_id=None, valid=Depends(validate_credentials)):
    program = querier.get_program(program_id)
    return {"program": program}

