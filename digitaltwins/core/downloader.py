import configparser
import os

from ..irods.irods import IRODS


class Downloader(object):
    def __init__(self, config_file):
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._irods_downloader = None

        if self._configs.getboolean("irods", "enabled"):
            self._irods_downloader = IRODS(self._configs)

    def download_dataset(self, dataset_id, save_dir="./"):
        if self._irods_downloader:
            os.makedirs(str(save_dir), exist_ok=True)

            print("Downloading dataset " + dataset_id)

            self._irods_downloader.download(dataset_id, save_dir)

            print("Dataset successfully downloaded")
        else:
            raise EnvironmentError("Missing Downloader. Please check your configurations for data storage.")
