import os
import json
from datetime import datetime, timezone

import requests
from requests.auth import HTTPBasicAuth

from dotenv import load_dotenv
load_dotenv()

from digitaltwins import Querier


class Workflow(object):
    def __init__(self):
        self._airflow_version = os.getenv("AIRFLOW_VERSION") or "3"
        self._airflow_endpoint = os.getenv("AIRFLOW_ENDPOINT")
        self._airflow_api_url = os.getenv("AIRFLOW_API_URL")
        self._username = os.getenv("AIRFLOW_USERNAME")
        self._password = os.getenv("AIRFLOW_PASSWORD")
        self._airflow_api_token = os.getenv("AIRFLOW_API_TOKEN")

        for required in [self._airflow_version, self._airflow_endpoint, self._airflow_api_url, self._username, self._password]:
            if not required:
                raise ValueError("Airflow configuration is incomplete. Please check your environment variables.")

    def get_api_token(self):
        """Get an Airflow JWT using the service account credentials."""
        url = f"{self._airflow_endpoint}/auth/token"
        headers = {"Content-Type": "application/json"}
        payload = {
            "username": self._username,
            "password": self._password
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        access_token = response.json().get("access_token")
        return access_token

    def get_api_token_for_user(self, keycloak_token: str) -> str | None:
        """
        Exchange a Keycloak Bearer token for an Airflow JWT scoped to that user.

        This calls the /keycloak/token/exchange endpoint added by the
        keycloak_token_exchange Airflow plugin. If successful, DAG runs
        triggered with the returned token will be attributed to the actual user
        rather than the service account.

        Returns None if the exchange fails (e.g. user not yet provisioned in
        Airflow), so callers can fall back to the service account token.
        """
        url = f"{self._airflow_endpoint}/keycloak/exchange"
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {keycloak_token}"},
                timeout=10,
            )
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                import logging
                logging.getLogger(__name__).warning(
                    "Keycloak token exchange failed (%s): %s",
                    response.status_code,
                    response.text,
                )
                return None
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Keycloak token exchange request failed")
            return None

    def run(self, assay_id, user_keycloak_token: str = None):
        """
        Trigger an Airflow DAG run for the given assay.

        Args:
            assay_id: The assay seek ID.
            user_keycloak_token: Optional Keycloak Bearer token for the requesting user.
                If provided, the DAG run will be attributed to that user in Airflow.
                Falls back to the service account if exchange fails.
        """
        querier = Querier()
        assay = querier.get_assay(assay_id, get_configs=True)

        assay_seek_id = assay_id
        assay_params = assay.get("params")

        workflow_seek_id = assay_params.get('workflow_seek_id')
        dag_url = f"{self._airflow_api_url}/dags/{workflow_seek_id}/dagRuns"
        dag_url_ui = f"{self._airflow_endpoint}/dags/{workflow_seek_id}/grid"

        if self._airflow_version == "2":
            subject_uuid = None
            params = {
                "assay_seek_id": assay_seek_id,
                "workspace": None,
            }

            preprocessor_dag_url = f"{self._airflow_api_url}/dags/preprocessor/dagRuns"
            response = requests.post(
                preprocessor_dag_url,
                auth=HTTPBasicAuth(self._username, self._password),
                headers={"Content-Type": "application/json"},
                data=json.dumps({"conf": params})
            )
        elif self._airflow_version == "3":
            # Prefer a user-scoped token so the run is attributed to the actual user.
            # Fall back to the service account token if no user token is provided
            # or if the exchange fails (e.g. user not yet provisioned in Airflow).
            api_token = None
            if user_keycloak_token:
                api_token = self.get_api_token_for_user(user_keycloak_token)

            if api_token is None:
                api_token = self.get_api_token()

            url = f"{self._airflow_api_url}/dags/preprocessor/dagRuns"
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            logical_date = datetime.now(timezone.utc).isoformat()

            payload = {
                "logical_date": logical_date,
                "conf": {
                    "assay_seek_id": assay_seek_id,
                    "workspace": None
                }
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                print("Triggered DAG Run:", response.json())
            else:
                raise Exception(f"Airflow API Error {response.status_code}: {response.text}")
        else:
            raise Exception(f"Unsupported Airflow version: {self._airflow_version}")

        return response, dag_url_ui
