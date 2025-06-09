
from pathlib import Path

from ..utils.config_loader import ConfigLoader

from ..postgres.uploader import Uploader as PostgresUploader
from ..irods.uploader import Uploader as IRODSUploader


class Uploader(object):
    def __init__(self, config_file):
        self._config_file = Path(config_file)
        self._configs = ConfigLoader.load_from_ini(config_file)

        if self._configs.getboolean("postgres", "enabled") and self._configs.getboolean("gen3", "enabled"):
            raise ValueError("Metadata service conflict. Only one of 'postgres' or 'gen3' can be enabled")

        self._postgres_uploader = None
        self._gen3_uploader = None
        self._irods_uploader = None

        if self._configs.getboolean("postgres", "enabled"):
            self._postgres_uploader = PostgresUploader(config_file)
        else:
            self._postgres_uploader = None

        # if self._configs.getboolean("gen3", "enabled"):
        #     self._gen3_uploader = Gen3Uploader(config_file)
        #

        if self._configs.getboolean("irods", "enabled"):
            self._irods_uploader = IRODSUploader(config_file)
        else:
            self._irods_uploader = None


    def upload_assay(self, assay_data):
        self._postgres_uploader.upload_assay(assay_data)

