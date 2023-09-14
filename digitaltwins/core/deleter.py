import configparser
from pathlib import Path

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

    def execute(self, dataset_id):
        self._delete_metadata(dataset_id)
        self._delete_dataset(dataset_id)
        pass

    def _delete_metadata(self, dataset_id):
        querier = MetadataQuerier(self._config_)
        records = querier.get_dataset_records(dataset_id=datasset_id)
        pass

    def _delete_dataset(self, dataset_id):
        pass
