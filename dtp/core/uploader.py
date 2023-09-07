import configparser

from pathlib import Path

from dtp import MetadataConvertor
from dtp import MetadataUploader
from dtp.irods.irods import IRODS


class Uploader(object):
    def __init__(self, config_file):
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._data_storage_configs = ConfigLoader.load_from_json(data_storage_config)

        self._data_storage = self._data_storage_configs.get("storage")
        if data_storage_type:
            self._data_storage = data_storage_type
        else:
            self._data_storage = self._data_storage_configs.get("storage")

        if gen3_config:
            self._gen3_config = ConfigLoader.load_from_json(gen3_config)
            self._gen3_endpoint = self._gen3_config.get("gen3_endpoint")
            self._gen3_cred_file = self._gen3_config.get("gen3_cred_file")
            self._gen3_auth = Auth(self._gen3_endpoint, self._gen3_cred_file)
            self._gen3_queryer = MetadataQuerier(self._gen3_auth)
            self._gen3_uploader = MetadataUploader(self._gen3_endpoint, self._gen3_cred_file)

        if self._data_storage == "pacs":
            self._pacs_ip = self._data_storage_configs.get("pacs_ip")
            self._pacs_port = self._data_storage_configs.get("pacs_port")
            self._pacs_aec = self._data_storage_configs.get("pacs_aec")
            self._pacs_aet = self._data_storage_configs.get("pacs_aet")

        elif self._data_storage == "irods":
            self._irods = IRODS(data_storage_config)

    def upload(self, dataset_dir, project):
        dataset_dir = Path(dataset_dir)
        self._verify_dataset(dataset_dir, project)

        self.upload_metadata(dataset_dir, project)
        self.upload_files(dataset_dir)

    def upload_metadata(self, dataset_dir):
        program = self._configs["gen3"].get("program")
        project = self._configs["gen3"].get("project")
        meta_dir = dataset_dir.joinpath(self._tmp_meta_dir)
        # convert sds metadata to gen3
        convertor = MetadataConvertor(project=project, experiment=dataset_dir.name)
        convertor.execute(source_dir=dataset_dir, dest_dir="./")

        # upload metadata
        MetadataUploader
        pass

    def upload_files(self, dataset_dir):
        # TODO
        pass

    def _verify_dataset(self, dataset_dir, project):
        if dataset_dir.is_dir():
            dataset_name = dataset_dir.name
        else:
            raise NotADirectoryError("Dataset directory not found")

        # check if dataset exists
        # todo
        pass

