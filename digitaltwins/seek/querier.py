from ..utils.config_loader import ConfigLoader

import requests


class Querier(object):
    def __init__(self, config_file):
        """
        Constructor inherited and expanded from AbstractQuerier
        """
        self._configs = ConfigLoader.load_from_ini(config_file)

        configs = self._configs["seek"]
        self._host = configs["host"]
        self._port = configs["port"]
        self._base_url = self._host + ':' + self._port
        self._api_token = configs["api_token"]

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
