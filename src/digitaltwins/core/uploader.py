import os

from dotenv import load_dotenv
load_dotenv()

from ..utils.config_loader import is_truthy

from ..postgres.uploader import Uploader as PostgresUploader
from ..irods.uploader import Uploader as IRODSUploader


class Uploader(object):
    def __init__(self):
        self._postgres_enabled = is_truthy(os.getenv("POSTGRES_ENABLED"))
        self._gen3_enabled = is_truthy(os.getenv("GEN3_ENABLED"))
        self._irods_enabled = is_truthy(os.getenv("IRODS_ENABLED"))

        if self._postgres_enabled and self._gen3_enabled:
            raise ValueError("Metadata service conflict. Only one of 'postgres' or 'gen3' can be enabled")

        self._postgres_uploader = None
        self._gen3_uploader = None
        self._irods_uploader = None

        if self._postgres_enabled:
            self._postgres_uploader = PostgresUploader()
        else:
            self._postgres_uploader = None

        # if self._gen3_enabled:
        #     self._gen3_uploader = Gen3Uploader()
        #

        if self._irods_enabled:
            self._irods_uploader = IRODSUploader()
        else:
            self._irods_uploader = None


    def upload_assay(self, assay_data):
        if self._postgres_enabled:
            self._postgres_uploader.upload_assay(assay_data)
