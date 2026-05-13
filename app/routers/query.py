"""
Query Routings.

This module provides various API endpoints for querying digital twins resources, such as
programs, projects, investigations, studies, assays, workflows, tools, and datasets via the Querier.
"""
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query

from digitaltwins import Querier
from .auth import validate_credentials

load_dotenv()
querier = Querier()
router = APIRouter()

@router.post("/cache/clear", tags=["cache"])
def clear_cache(valid=Depends(validate_credentials)):
    """
    Invalidate the in-memory SEEK response cache.
    Call this after making changes in SEEK so the dashboard reflects them immediately
    rather than waiting for the TTL to expire.
    """
    cache = querier._seek_querier._cache if querier._seek_querier else {}
    count = len(cache)
    cache.clear()
    return {"cleared": count}


@router.get("/programs", tags=["query"])
def get_programs(get_details: bool = False, valid=Depends(validate_credentials)):
    """
    Retrieve a list of programs.

    Args:
        get_details (bool, optional): If True, returns detailed information about each program. Defaults to False.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of programs under the 'programs' key.
    """
    programs = querier.get_programs(get_details=get_details)
    return {"programs": programs}


@router.get("/programs/{program_id}", tags=["query"])
def get_program(program_id=None, valid=Depends(validate_credentials)):
    """
    Retrieve a specific program by its ID.

    Args:
        program_id (str, optional): The ID of the program to retrieve.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the program details under the 'program' key.
    """
    program = querier.get_program(program_id)
    return {"program": program}


@router.get("/projects", tags=["query"])
def get_projects(get_details: bool = False, valid=Depends(validate_credentials)):
    """
    Retrieve a list of projects.

    Args:
        get_details (bool, optional): If True, returns detailed information about each project. Defaults to False.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of projects under the 'projects' key.
    """
    projects = querier.get_projects(get_details=get_details)
    return {"projects": projects}


@router.get("/projects/{project_id}", tags=["query"])
def get_project(project_id=None, valid=Depends(validate_credentials)):
    """
    Retrieve a specific project by its ID.

    Args:
        project_id (str, optional): The ID of the project to retrieve.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the project details under the 'project' key.
    """
    project = querier.get_project(project_id)
    return {"project": project}


@router.get("/investigations", tags=["query"])
def get_investigations(get_details: bool = False, valid=Depends(validate_credentials)):
    """
    Retrieve a list of investigations.

    Args:
        get_details (bool, optional): If True, returns detailed information about each investigation. Defaults to False.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of investigations under the 'investigations' key.
    """
    investigations = querier.get_investigations(get_details=get_details)
    return {"investigations": investigations}


@router.get("/investigations/{investigation_id}", tags=["query"])
def get_investigation(investigation_id=None, valid=Depends(validate_credentials)):
    """
    Retrieve a specific investigation by its ID.

    Args:
        investigation_id (str, optional): The ID of the investigation to retrieve.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the investigation details under the 'investigation' key.
    """
    investigation = querier.get_investigation(investigation_id)
    return {"investigation": investigation}


@router.get("/studies", tags=["query"])
def get_studies(get_details: bool = False, valid=Depends(validate_credentials)):
    """
    Retrieve a list of studies.

    Args:
        get_details (bool, optional): If True, returns detailed information about each study. Defaults to False.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of studies under the 'studies' key.
    """
    studies = querier.get_studies(get_details=get_details)
    return {"studies": studies}


@router.get("/studies/{study_id}", tags=["query"])
def get_study(study_id=None, valid=Depends(validate_credentials)):
    """
    Retrieve a specific study by its ID.

    Args:
        study_id (str, optional): The ID of the study to retrieve.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the study details under the 'study' key.
    """
    study = querier.get_study(study_id)
    return {"study": study}


@router.get("/assays", tags=["query"])
def get_assays(get_details: bool = False, valid=Depends(validate_credentials)):
    """
    Retrieve a list of assays.

    Args:
        get_details (bool, optional): If True, returns detailed information about each assay. Defaults to False.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of assays under the 'assays' key.
    """
    assays = querier.get_assays(get_details=get_details)
    return {"assays": assays}


@router.get("/assays/{assay_id}", tags=["query"])
def get_assay(assay_id=None, get_configs: bool = False, valid=Depends(validate_credentials)):
    """
    Retrieve a specific assay by its ID, with optional parameters.

    Args:
        assay_id (str, optional): The ID of the assay to retrieve.
        get_configs (bool, optional): If True, retrieves additional parameters related to the assay. Defaults to False.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the assay details under the 'assay' key.
    """
    assay = querier.get_assay(assay_id, get_configs=get_configs)
    return {"assay": assay}

@router.get("/workflows", tags=["query"])
def get_workflows(valid=Depends(validate_credentials)):
    """
    Retrieve a list of workflows.

    Args:
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of workflows under the 'workflows' key.
    """
    workflows = querier.get_workflows()
    return {"workflows": workflows}


@router.get("/workflows/{workflow_id}", tags=["query"])
# def get_workflow(workflow_id=None, valid=Depends(validate_credentials)):
def get_workflow(workflow_id=None):
    """
    Retrieve a specific workflow by its ID.

    Args:
        workflow_id (str, optional): The ID of the workflow to retrieve.

    Returns:
        dict: A dictionary containing the workflow details under the 'workflow' key.
    """
    workflow = querier.get_workflow(workflow_id)
    return {"workflow": workflow}

@router.get("/tools", tags=["query"])
def get_tools(valid=Depends(validate_credentials)):
    """
    Retrieve a list of tools.

    Args:
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of tools under the 'tools' key.
    """
    tools = querier.get_tools()
    return {"tools": tools}


@router.get("/tools/{tool_id}", tags=["query"])
def get_tool(tool_id=None, valid=Depends(validate_credentials)):
    """
    Retrieve a specific tool by its ID.

    Args:
        tool_id (str, optional): The ID of the tool to retrieve.
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the tool details under the 'tool' key.
    """
    tool = querier.get_tool(tool_id)
    return {"tool": tool}


@router.get("/datasets", tags=["datasets"])
def get_datasets(
    descriptions: bool = False,
    categories: Optional[List[str]] = Query(default=None),
    keywords: Optional[str] = Query(default=None, description="JSON string of keyword filters, e.g. '{\"key\": \"value\"}'"),
    valid=Depends(validate_credentials),
):
    """
    Retrieve a list of datasets.

    Args:
        descriptions (bool, optional): If True, includes description fields for each dataset. Defaults to False.
        categories (List[str], optional): Filter datasets by one or more categories (e.g. "workflow", "primary").
        keywords (str, optional): JSON-encoded dict of keyword filters (e.g. '{"organ": "heart"}').
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of datasets under the 'datasets' key.

    Examples:
        GET /datasets
        GET /datasets?categories=workflow
        GET /datasets?categories=primary&categories=workflow
    """
    import json
    kw = {}
    if keywords:
        try:
            kw = json.loads(keywords)
        except json.JSONDecodeError:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="'keywords' must be a valid JSON object string.")

    datasets = querier.get_datasets(
        descriptions=descriptions,
        categories=categories,
        keywords=kw if kw else None,
    )
    return {"datasets": datasets}


@router.get("/datasets/{dataset_uuid}", tags=["datasets"])
def get_dataset(
    dataset_uuid: str,
    get_cwl: bool = False,
    valid=Depends(validate_credentials),
):
    """
    Retrieve a specific dataset by its UUID.

    Args:
        dataset_uuid (str): The UUID of the dataset to retrieve. Example: abdc7a8a-33ce-11f1-a982-0242ac120007
        get_cwl (bool, optional): If True, also fetches and returns the associated CWL file (tool datasets only).
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the dataset details under the 'dataset' key.
    """
    dataset = querier.get_dataset(dataset_uuid=dataset_uuid, get_cwl=get_cwl)
    return {"dataset": dataset}


@router.get("/datasets/{dataset_uuid}/sample-types", tags=["datasets"])
def get_dataset_sample_types(
    dataset_uuid: str,
    valid=Depends(validate_credentials),
):
    """
    Retrieve all sample types present in a dataset.

    Args:
        dataset_uuid (str): The UUID of the dataset. Example: abdc7a8a-33ce-11f1-a982-0242ac120007
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of sample types under the 'sample_types' key.
    """
    sample_types = querier.get_dataset_sample_types(dataset_uuid=dataset_uuid)
    return {"sample_types": sample_types}


@router.get("/datasets/{dataset_uuid}/samples", tags=["datasets"])
def get_dataset_samples(
    dataset_uuid: str,
    sample_type: Optional[str] = Query(default=None, description="Filter samples by type, e.g. 'ax dyn pre'"),
    valid=Depends(validate_credentials),
):
    """
    Retrieve samples belonging to a dataset, optionally filtered by sample type.

    Args:
        dataset_uuid (str): The UUID of the dataset. Example: abdc7a8a-33ce-11f1-a982-0242ac120007
        sample_type (str, optional): Filter samples by this sample type (e.g. "ax dyn pre").
        valid (bool): Ensures valid credentials are provided.

    Returns:
        dict: A dictionary containing the list of samples under the 'samples' key.
    """
    samples = querier.get_dataset_samples(dataset_uuid=dataset_uuid, sample_type=sample_type)
    return {"samples": samples}

