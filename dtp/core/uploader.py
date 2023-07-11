from dtp.utils.config_loader import ConfigLoader
from dtp.irods.irods import IRODS
from dtp.gen3.auth import Auth
from dtp.gen3.metadata_querier import MetadataQuerier

import pypacs


class Uploader(object):
    def __init__(self, data_storage_config, gen3_config=None, data_storage_type="pacs"):
        """
        Constructor

        :param data_storage_config: Path to the data storage (PACS or iRods) configuration file (json)
        :type data_storage_config: string
        :param gen3_config: (Optional)
        :type gen3_config: Path to the Gen3 configuration file (json)
        """
        self._data_storage_configs = ConfigLoader.load_from_json(data_storage_config)

        self._data_storage = self._data_storage_configs.get("storage")
        if data_storage_type:
            self._data_storage = data_storage_type
        else:
            self._data_storage = self._data_storage_configs.get("storage")

        if self._data_storage == "pacs":
            self._pacs_ip = self._data_storage_configs.get("pacs_ip")
            self._pacs_port = self._data_storage_configs.get("pacs_port")
            self._pacs_aec = self._data_storage_configs.get("pacs_aec")
            self._pacs_aet = self._data_storage_configs.get("pacs_aet")

            self._gen3_config = ConfigLoader.load_from_json(gen3_config)
            self._gen3_endpoint = self._gen3_config.get("gen3_endpoint")
            self._gen3_cred_file = self._gen3_config.get("gen3_cred_file")
            self._gen3_auth = Auth(self._gen3_endpoint, self._gen3_cred_file)
            self._gen3_queryer = MetadataQuerier(self._gen3_auth)

        elif self._data_storage == "irods":
            self._irods = IRODS(data_storage_config)

    def upload(self):
        pass

    def upload_metadata(self):
        # TODO
        pass

    def upload_files(self):
        # TODO
        pass
