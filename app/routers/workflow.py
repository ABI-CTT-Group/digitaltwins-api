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
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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

HOSTNAME = os.getenv("HOSTNAME")
AIRFLOW_EXPOSE_PORT = os.getenv("AIRFLOW_PORT")

PREPROCESSOR_DAG_ID = "preprocessor"

def _get_service_account_token() -> str:
    """Get an Airflow JWT using the shared service account credentials."""
    url = f"{AIRFLOW_ENDPOINT}/auth/token"
    headers = {"Content-Type": "application/json"}
    payload = {
        "username": AIRFLOW_USERNAME,
        "password": AIRFLOW_PASSWORD
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json().get("access_token")


def _exchange_keycloak_token(keycloak_token: str) -> str | None:
    """
    Exchange a Keycloak Bearer token for an Airflow JWT scoped to that user.

    Calls the /keycloak/token/exchange endpoint added to Airflow by the
    keycloak_token_exchange plugin. Returns None if the exchange fails so
    callers can fall back to the service account.
    """
    url = f"{AIRFLOW_ENDPOINT}/keycloak/exchange"
    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {keycloak_token}"},
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        print(f"[workflow] Keycloak token exchange failed ({response.status_code}): {response.text}")
        return None
    except Exception as e:
        print(f"[workflow] Keycloak token exchange error: {e}")
        return None


def _get_api_token(user_keycloak_token: str = None) -> str:
    """
    Get an Airflow API token.

    If a user Keycloak token is provided, attempts to exchange it for a
    user-scoped Airflow token (so the DAG run is attributed to that user).
    Falls back to the service account token if exchange fails or no user
    token is given.
    """
    if user_keycloak_token:
        token = _exchange_keycloak_token(user_keycloak_token)
        if token:
            return token
        print("[workflow] Falling back to service account token")
    return _get_service_account_token()


def _trigger_dag(dag_id: str, conf: dict, user_keycloak_token: str = None) -> Response:
    """
    Trigger an Airflow DAG run via the Airflow REST API v2 (Airflow 3).

    If user_keycloak_token is provided the run will be attributed to that
    user in Airflow (via token exchange). Falls back to the service account.
    """
    url = f"{AIRFLOW_ENDPOINT}/api/v2/dags/{dag_id}/dagRuns"
    api_token = _get_api_token(user_keycloak_token)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    logical_date = datetime.now(timezone.utc).isoformat()

    payload = {
        "logical_date": logical_date,
        "conf": conf
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("Triggered DAG Run:", response.json())
    else:
        raise Exception(f"Airflow API Error {response.status_code}: {response.text}")

    return response


@router.post("/assays/{assay_id}/run", tags=["workflow"])
def run_assay(
    assay_id: int,
    valid=Depends(validate_credentials),
    bearer_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
):
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

    user_token = bearer_credentials.credentials if bearer_credentials else None
    conf = {"assay_id": assay_id}
    response = _trigger_dag(PREPROCESSOR_DAG_ID, conf, user_keycloak_token=user_token)

    assay = get_assay(assay_id, get_configs=False)

    workflow_seek_id = None
    try:
        workflows = assay.get("assay", {}).get("relationships", {}).get("workflows", [])
        if workflows and isinstance(workflows, list) and workflows[0]:
            workflow_seek_id = workflows[0][0].get("id")
    except (IndexError, AttributeError, TypeError):
        pass

    monitor_base_url = f"http://{HOSTNAME}:{AIRFLOW_EXPOSE_PORT}"

    if workflow_seek_id:
        monitor_url = f"{monitor_base_url}/dags/workflow_{workflow_seek_id}"
    else:
        monitor_url = f"{monitor_base_url}/dags/{PREPROCESSOR_DAG_ID}"

    return {"dag_run": response.json(), "monitor_url": monitor_url}
