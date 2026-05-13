

import requests
import os
import time

from dotenv import load_dotenv

load_dotenv()

_CACHE_TTL = 60  # seconds — how long to serve cached SEEK responses before re-fetching


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

        # Persistent session so TCP connections to SEEK are reused across calls
        # rather than opened and closed on every request.
        self._session = requests.Session()
        self._session.headers.update(self._headers)

        # Simple URL-keyed TTL cache. SEEK data (programmes, projects, etc.)
        # changes rarely — serving from cache eliminates round-trips to SEEK
        # for repeated navigation within the TTL window.
        self._cache: dict = {}

    def _get(self, url: str):
        """Fetch url via the persistent session, returning cached data when fresh."""
        now = time.time()
        if url in self._cache:
            data, ts = self._cache[url]
            if now - ts < _CACHE_TTL:
                return data
        resp = self._session.get(url)
        data = self._format_resp(resp)
        self._cache[url] = (data, now)
        return data

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
        data = self._get(self._base_url + "/programmes")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_program(record_id)

                data[idx]["details"] = details

        return data

    def get_program(self, program_id):
        return self._get(self._base_url + "/programmes/" + str(program_id))

    def get_projects(self, get_details=False):
        data = self._get(self._base_url + "/projects")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_project(record_id)

                data[idx]["details"] = details

        return data

    def get_project(self, project_id):
        return self._get(self._base_url + "/projects/" + str(project_id))

    def get_investigations(self, get_details=False):
        data = self._get(self._base_url + "/investigations")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_investigation(record_id)

                data[idx]["details"] = details

        return data

    def get_investigation(self, investigation_id):
        return self._get(self._base_url + "/investigations/" + str(investigation_id))

    def get_studies(self, get_details=False):
        data = self._get(self._base_url + "/studies")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_study(record_id)

                data[idx]["details"] = details

        return data

    def get_study(self, study_id):
        return self._get(self._base_url + "/studies/" + str(study_id))

    def get_assays(self, get_details=False):
        data = self._get(self._base_url + "/assays")

        if get_details:
            for idx, record in enumerate(data):
                record_id = record.get("id")
                details = self.get_assay(record_id)

                data[idx]["details"] = details

        return data

    def get_assay(self, assay_id):
        return self._get(self._base_url + "/assays/" + str(assay_id))

    def get_sops(self, get_details=False):
        """
        SOP == workflow
        :return:
        :rtype:
        """
        data = self._get(self._base_url + "/sops")

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
        return self._get(self._base_url + "/sops/" + str(sop_id))

    def get_workflows(self):
        return self._get(self._base_url + "/workflows?filter%5Btag%5D=workflow")

    def get_workflow(self, workflow_id):
        return self._get(self._base_url + "/workflows/" + str(workflow_id) + ".json")

    def get_tools(self):
        return self._get(self._base_url + "/workflows?filter%5Btag%5D=tool")

    def get_tool(self, tool_id):
        return self._get(self._base_url + "/workflows/" + str(tool_id) + ".json")
