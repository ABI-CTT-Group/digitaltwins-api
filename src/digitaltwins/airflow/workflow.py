import os
import json
from datetime import datetime, timezone

import requests
from requests.auth import HTTPBasicAuth

from ..utils.config_loader import ConfigLoader

from digitaltwins import Querier


class Workflow(object):
    def __init__(self, config_file=None):
        self._airflow_version = "3" # default version

        if not config_file and os.getenv("CONFIG_FILE_PATH"):
            config_file = os.getenv("CONFIG_FILE_PATH")

        if config_file:
            self._configs = ConfigLoader.load_from_ini(config_file)
            self._configs = self._configs["airflow"]

            self._airflow_version = self._configs.get('airflow_version') or self._airflow_version
            self._airflow_endpoint = self._configs.get('airflow_endpoint')
            self._airflow_api_url = self._configs.get('airflow_api_url')
            self._username = self._configs.get('username')
            self._password = self._configs.get('password')
            self._airflow_api_token = self._configs.get('airflow_api_token')
        else:
            self._airflow_version = os.getenv("AIRFLOW_VERSION") or self._airflow_version
            self._airflow_endpoint = os.getenv("AIRFLOW_ENDPOINT")
            self._airflow_api_url = os.getenv("AIRFLOW_API_URL")
            self._username = os.getenv("AIRFLOW_USERNAME")
            self._password = os.getenv("AIRFLOW_PASSWORD")
            self._airflow_api_token = os.getenv("AIRFLOW_API_TOKEN")

        for required in [self._airflow_version, self._airflow_endpoint, self._airflow_api_url, self._username, self._password]:
            if not required:
                raise ValueError("Airflow configuration is incomplete. Please check your configuration file.")

    def get_api_token(self):
        url = f"{self._airflow_endpoint}/auth/token"
        headers = {"Content-Type": "application/json"}
        payload = {
            "username": self._username,
            "password": self._password
        }
        response = requests.post(url, headers=headers, json=payload)
        access_token = response.json().get("access_token")
        return access_token

    def run(self, assay_id):
        querier = Querier(self._config_file)
        assay = querier.get_assay(assay_id, get_params=True)

        assay_seek_id = assay_id
        assay_params = assay.get("params")

        # todo. create assay workspace id and write into the assay table

        # get dag_url
        workflow_seek_id = assay_params.get('workflow_seek_id')
        querier = Querier(self._config_file)
        workflow = querier.get_sop(sop_id=workflow_seek_id)
        workflow_dataset_uuid = workflow.get("dataset_uuid")
        dag_url = f"{self._airflow_api_url}/dags/{workflow_dataset_uuid}/dagRuns"
        # dag_rul_ui = f"http://0.0.0.0:8080/dags/{workflow_dataset_uuid}/grid"
        dag_rul_ui = f"{self._airflow_endpoint}/dags/{workflow_dataset_uuid}/grid"

        if self._airflow_version == "2":
            subject_uuid = None
            params = {
                # "subject_uuid": subject_uuid,
                "assay_seek_id": assay_seek_id,
                "workspace": None,
                # "platform_configs": None,
            }

            preprocessor_dag_url = f"{self._airflow_api_url}/dags/preprocessor/dagRuns"
            response = requests.post(
                preprocessor_dag_url,
                auth=HTTPBasicAuth(self._username, self._password),
                headers={"Content-Type": "application/json"},
                data=json.dumps({"conf": params})
            )
        elif self._airflow_version == "3":
            api_token = self.get_api_token()
            url = f"{self._airflow_api_url}/dags/preprocessor/dagRuns"
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            logical_date = datetime.now(timezone.utc).isoformat()

            payload = {
                # "dag_run_id": f"manual__{logical_date}",  # optional
                "logical_date": logical_date,  # required
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

        return response, dag_rul_ui
