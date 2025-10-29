import os

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi import Depends

from digitaltwins import Querier
from .auth import validate_credentials

load_dotenv()
CONFIG_FILE_PATH = os.getenv("CONFIG_FILE_PATH")

router = APIRouter()

querier = Querier(CONFIG_FILE_PATH)


@router.get("/programs", tags=["query"])
def get_programs(get_details=False, valid=Depends(validate_credentials)):
    programs = querier.get_programs(get_details=get_details)
    return {"programs": programs}


@router.get("/programs/{program_id}", tags=["query"])
def get_program(program_id=None, valid=Depends(validate_credentials)):
    program = querier.get_program(program_id)
    return {"program": program}


@router.get("/projects", tags=["query"])
def get_projects(get_details=False, valid=Depends(validate_credentials)):
    projects = querier.get_projects(get_details=get_details)
    return {"projects": projects}


@router.get("/projects/{project_id}", tags=["query"])
def get_project(project_id=None, valid=Depends(validate_credentials)):
    project = querier.get_project(project_id)
    return {"project": project}


@router.get("/investigations", tags=["query"])
def get_investigations(get_details=False, valid=Depends(validate_credentials)):
    investigations = querier.get_investigations(get_details=get_details)
    return {"investigations": investigations}


@router.get("/investigations/{investigation_id}", tags=["query"])
def get_investigation(investigation_id=None, valid=Depends(validate_credentials)):
    investigation = querier.get_investigation(investigation_id)
    return {"investigation": investigation}


@router.get("/studies", tags=["query"])
def get_studies(get_details=False, valid=Depends(validate_credentials)):
    studies = querier.get_studies(get_details=get_details)
    return {"studies": studies}


@router.get("/studies/{study_id}", tags=["query"])
def get_study(study_id=None, valid=Depends(validate_credentials)):
    study = querier.get_study(study_id)
    return {"study": study}


@router.get("/assays", tags=["query"])
def get_assays(get_details=False, valid=Depends(validate_credentials)):
    assays = querier.get_assays(get_details=get_details)
    return {"assays": assays}


@router.get("/assays/{assay_id}", tags=["query"])
def get_assay(assay_id=None, get_params=False, valid=Depends(validate_credentials)):
    assay = querier.get_assay(assay_id, get_params=get_params)
    return {"assay": assay}

@router.get("/workflows", tags=["query"])
def get_workflows(valid=Depends(validate_credentials)):
    workflows = querier.get_workflows()
    return {"workflows": workflows}


@router.get("/workflows/{workflow_id}", tags=["query"])
def get_workflow(workflow_id=None, valid=Depends(validate_credentials)):
    workflow = querier.get_workflow(workflow_id)
    return {"workflow": workflow}

@router.get("/tools", tags=["query"])
def get_tools(valid=Depends(validate_credentials)):
    tools = querier.get_tools()
    return {"tools": tools}


@router.get("/tools/{tool_id}", tags=["query"])
def get_tool(tool_id=None, valid=Depends(validate_credentials)):
    tool = querier.get_tool(tool_id)
    return {"tool": tool}
