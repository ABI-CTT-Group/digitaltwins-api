from ..utils.config_loader import ConfigLoader

import requests
import os

from dotenv import load_dotenv

load_dotenv()


class Querier(object):
    def __init__(self, config_file):
        """
        Constructor inherited and expanded from AbstractQuerier
        """
        if not config_file and os.getenv("CONFIG_FILE_PATH"):
            config_file = os.getenv("CONFIG_FILE_PATH")

        if config_file:
            self._configs = ConfigLoader.load_from_ini(config_file)
            configs = self._configs["seek"]
            self._base_url = configs["base_url"]
            self._api_token = configs["api_token"]
        else:
            self._base_url = os.getenv("SEEK_BASE_URL")
            self._api_token = os.getenv("SEEK_API_TOKEN")

        for required in [self._base_url, self._api_token]:
            if not required:
                raise ValueError("SEEK configuration is incomplete. Please check your configuration file or environment variables.")

        self._headers = {
            "Authorization": "Bearer " + self._api_token,
            "Accept": "application/json"
        }

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
        url = self._base_url + "/programmes"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_program(record_id)

                data[idx]["details"] = details

        return data

    def get_program(self, program_id):
        url = self._base_url + "/programmes/" + str(program_id)
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data

    def get_projects(self, get_details=False):
        url = self._base_url + "/projects"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_project(record_id)

                data[idx]["details"] = details

        return data

    def get_project(self, project_id):
        url = self._base_url + "/projects/" + str(project_id)
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data

    def get_investigations(self, get_details=False):
        url = self._base_url + "/investigations"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_investigation(record_id)

                data[idx]["details"] = details

        return data

    def get_investigation(self, investigation_id):
        url = self._base_url + "/investigations/" + str(investigation_id)
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data

    def get_studies(self, get_details=False):
        url = self._base_url + "/studies"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_study(record_id)

                data[idx]["details"] = details

        return data

    def get_study(self, study_id):
        url = self._base_url + "/studies/" + str(study_id)
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data

    def get_assays(self, get_details=False):
        url = self._base_url + "/assays"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_assay(record_id)

                data[idx]["details"] = details

        return data

    def get_assay(self, assay_id):
        url = self._base_url + "/assays/" + str(assay_id)
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data

    def get_sops(self, get_details=False):
        """
        SOP == workflow
        :return:
        :rtype:
        """
        url = self._base_url + "/sops"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

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
        url = self._base_url + "/sops/" + str(sop_id)
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data

    def get_workflows(self):
        url = self._base_url + "/workflows?filter%5Btag%5D=workflow"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data

    def get_workflow(self, workflow_id):
        url = self._base_url + "/workflows/" + str(workflow_id) + ".json"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data

    def get_tools(self):
        url = self._base_url + "/workflows?filter%5Btag%5D=tool"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data

    def get_tool(self, tool_id):
        url = self._base_url + "/workflows/" + str(tool_id) + ".json"
        resp = requests.get(url, headers=self._headers)
        data = self._format_resp(resp)

        return data
