import configparser
import os

from ..irods.irods import IRODS


class Downloader(object):
    def __init__(self, config_file):
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._irods = IRODS(self._configs)

    def download_dataset(self, dataset_id, save_dir="./"):

        os.makedirs(str(save_dir), exist_ok=True)

        print("Downloading dataset " + dataset_id)

        self._irods.download(dataset_id, save_dir)

        print("Dataset successfully downloaded")
