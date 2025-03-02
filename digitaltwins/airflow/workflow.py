import json
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

from ..utils.config_loader import ConfigLoader

from digitaltwins import Querier


class Workflow(object):
    def __init__(self, config_file):
        self._config_file = Path(config_file)
        self._configs = ConfigLoader.load_from_ini(config_file)
        self._configs = self._configs["airflow"]

        self._airflow_api_url = self._configs.get('airflow_api_url')
        self._username = self._configs.get('username')
        self._password = self._configs.get('password')

    def run(self, assay):
        assay_seek_id = assay.get("id")

        # get dag_url
        workflow_seek_id = assay.get("params").get('workflow_seek_id')
        querier = Querier(self._config_file)
        workflow = querier.get_sop(sop_id=workflow_seek_id)
        workflow_dataset_uuid = workflow.get("dataset_uuid")
        dag_url = f"{self._airflow_api_url}/dags/{workflow_dataset_uuid}/dagRuns"


        params = {
            "assay_seek_id": assay_seek_id,
            "workspace": None,
            "platform_config_file": None,
        }

        response = requests.post(
            dag_url,
            auth=HTTPBasicAuth(self._username, self._password),
            headers={"Content-Type": "application/json"},
            data=json.dumps({"conf": params})
        )

