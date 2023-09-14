import configparser
from pathlib import Path


class Deleter(object):
    def __init__(self, config_file):
        self.config_file = Path(config_file)

        self._configs = configparser.ConfigParser()
        self._configs.read(str(config_file))

        self._program = self._configs["gen3"].get("program")
        self._project = self._configs["gen3"].get("project")

        self._gen3_endpoint = self._configs["gen3"].get("endpoint")
        self._gen3_cred_file = Path(self._configs["gen3"].get("cred_file"))

    def execute(self, dataset_name):
        self._delete_metadata(dataset_name)
        self._delete_dataset(dataset_name)
        pass

    def _delete_metadata(self, dataset_name):
        pass

    def _delete_dataset(self, dataset_name):
        pass
