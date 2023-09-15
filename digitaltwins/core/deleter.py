import configparser
from pathlib import Path

from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission

from digitaltwins import MetadataQuerier


class Deleter(object):
    def __init__(self, config_file):
        self._config_file = Path(config_file)

        self._configs = configparser.ConfigParser()
        self._configs.read(str(config_file))

        self._program = self._configs["gen3"].get("program")
        self._project = self._configs["gen3"].get("project")
        self._gen3_endpoint = self._configs["gen3"].get("endpoint")
        self._gen3_cred_file = Path(self._configs["gen3"].get("cred_file"))

        self._auth = Gen3Auth(self._gen3_endpoint, refresh_file=str(self._gen3_cred_file))
        self._submission = Gen3Submission(self._gen3_endpoint, self._auth)

    def execute(self, dataset_id):
        self._delete_metadata(dataset_id)
        self._delete_dataset(dataset_id)
        pass

    def _delete_metadata(self, dataset_id):
        querier = MetadataQuerier(self._config_file)
        records = querier.get_dataset_records(dataset_id=dataset_id, program=self._program, project=self._project)
        self._submission.delete_records(program=self._program, project=self._project, uuids=records)
        pass

    def _delete_dataset(self, dataset_id):
        pass
