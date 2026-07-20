

import requests
import os
from requests import RequestException

from dotenv import load_dotenv

load_dotenv()


class Querier(object):
    def __init__(self):
        """
        Constructor inherited and expanded from AbstractQuerier
        """
        self._base_url = os.getenv("SEEK_BASE_URL")
        self._api_token = os.getenv("SEEK_API_TOKEN")

        for required in [self._base_url, self._api_token]:
            if not required:
                raise ValueError("SEEK configuration is incomplete. Please check your configuration file or environment variables.")

        self._headers = {
            "Authorization": "Bearer " + self._api_token,
            "Accept": "application/json"
        }

    def _request_json(self, path: str):
        url = f"{self._base_url}{path}"
        try:
            resp = requests.get(url, headers=self._headers, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
        except RequestException as exc:
            raise RuntimeError(f"SEEK request failed for {path}: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"SEEK returned a non-JSON response for {path}") from exc

        if isinstance(payload, dict):
            if "errors" in payload and payload["errors"]:
                raise RuntimeError(f"SEEK error for {path}: {payload['errors']}")
            return payload.get("data", payload)

        return payload

    @staticmethod
    def _format_resp(resp):
        data = resp.json().get("data")

        return data

    @staticmethod
    def get_dependencies(data, target):
        relationships = data.get("relationships")
        try:
            data = relationships.get(target).get("data")
        except AttributeError:
            raise AttributeError("Invalid target")

        return data

    def get_programs(self, get_details=False):
        """

        :return: a list of program names
        :rtype: list
        """
        data = self._request_json("/programmes")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_program(record_id)

                data[idx]["details"] = details

        return data

    def get_program(self, program_id):
        return self._request_json("/programmes/" + str(program_id))

    def get_projects(self, get_details=False):
        data = self._request_json("/projects")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_project(record_id)

                data[idx]["details"] = details

        return data

    def get_project(self, project_id):
        return self._request_json("/projects/" + str(project_id))

    def get_investigations(self, get_details=False):
        data = self._request_json("/investigations")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_investigation(record_id)

                data[idx]["details"] = details

        return data

    def get_investigation(self, investigation_id):
        return self._request_json("/investigations/" + str(investigation_id))

    def get_studies(self, get_details=False):
        data = self._request_json("/studies")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_study(record_id)

                data[idx]["details"] = details

        return data

    def get_study(self, study_id):
        return self._request_json("/studies/" + str(study_id))

    def get_assays(self, get_details=False):
        data = self._request_json("/assays")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_assay(record_id)

                data[idx]["details"] = details

        return data

    def get_assay(self, assay_id):
        return self._request_json("/assays/" + str(assay_id))

    def get_sops(self, get_details=False):
        """
        SOP == workflow
        :return:
        :rtype:
        """
        data = self._request_json("/sops")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_sop(record_id)

                data[idx]["details"] = details

        return data

    def get_sop(self, sop_id):
        """
        SOP == workflow
        :param sop_id:
        :type sop_id:
        :return:
        :rtype:
        """
        return self._request_json("/sops/" + str(sop_id))

    def get_workflows(self):
        return self._request_json("/workflows?filter%5Btag%5D=workflow")

    def get_workflow(self, workflow_id):
        return self._request_json("/workflows/" + str(workflow_id) + ".json")

    def get_tools(self):
        return self._request_json("/workflows?filter%5Btag%5D=tool")

    def get_tool(self, tool_id):
        return self._request_json("/workflows/" + str(tool_id) + ".json")
