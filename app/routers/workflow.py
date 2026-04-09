"""
Workflow Router.

This module provides endpoints to trigger Airflow DAG runs for assay processing.
"""
import os
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from requests import Response

from .auth import validate_credentials
from .query import get_assay

load_dotenv()

router = APIRouter()

# Airflow configs
AIRFLOW_ENABLED = os.getenv("AIRFLOW_ENABLED", "false").lower() == "true"
AIRFLOW_ENDPOINT = os.getenv("AIRFLOW_ENDPOINT")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")

PREPROCESSOR_DAG_ID = "preprocessor"

def _get_api_token():
    url = f"{AIRFLOW_ENDPOINT}/auth/token"
    headers = {"Content-Type": "application/json"}
    payload = {
        "username": AIRFLOW_USERNAME,
        "password": AIRFLOW_PASSWORD
    }
    response = requests.post(url, headers=headers, json=payload)
    access_token = response.json().get("access_token")
    return access_token

def _trigger_dag(dag_id: str, conf: dict) -> Response:
    """Trigger an Airflow DAG run via the Airflow REST API v2 (Airflow 3)."""
    url = f"{AIRFLOW_ENDPOINT}/api/v2/dags/{dag_id}/dagRuns"
    api_token = _get_api_token()
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    logical_date = datetime.now(timezone.utc).isoformat()

    payload = {
        "logical_date": logical_date,  # required
        "conf": conf
    }
    # payload = conf
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("Triggered DAG Run:", response.json())
    else:
        raise Exception(f"Airflow API Error {response.status_code}: {response.text}")

    return response


@router.post("/assays/{assay_id}/run", tags=["workflow"])
def run_assay(assay_id: int, valid=Depends(validate_credentials)):
    """
    Trigger the *preprocessor* Airflow DAG for a given assay.

    Args:
        assay_id (int): The ID of the assay to process.
        valid: Ensures valid credentials are provided.

    Returns:
        dict: The Airflow DAG-run object returned by the Airflow REST API.
    """
    if not AIRFLOW_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Airflow integration is disabled (AIRFLOW_ENABLED=false).",
        )

    conf = {"assay_id": assay_id}
    response = _trigger_dag(PREPROCESSOR_DAG_ID, conf)

    assay = get_assay(assay_id, get_configs=False)
    
    workflow_seek_id = None
    try:
        workflows = assay.get("assay", {}).get("relationships", {}).get("workflows", [])
        if workflows and isinstance(workflows, list) and workflows[0]:
            workflow_seek_id = workflows[0][0].get("id")
    except (IndexError, AttributeError, TypeError):
        pass

    if workflow_seek_id:
        monitor_url = f"{AIRFLOW_ENDPOINT}/dags/workflow_{workflow_seek_id}"
    else:
        monitor_url = f"{AIRFLOW_ENDPOINT}/dags/{PREPROCESSOR_DAG_ID}"

    return {"dag_run": response.json(), "monitor_url": monitor_url}
