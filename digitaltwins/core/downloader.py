import configparser
import os
from pathlib import Path

from digitaltwins import IRODS


class Downloader(object):
    def __init__(self, config_file):
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._save_dir = Path(r"./tmp")

        self._irods = IRODS(self._configs)

    def download(self, dataset_name=None, save_dir=None):
        if dataset_name is None:
            raise ValueError("Dataset not specified")
        if save_dir is None:
            save_dir = self._save_dir

        os.makedirs(str(save_dir), exist_ok=True)

        print("Downloading dataset " + dataset_name)

        self._irods.download(dataset_name, save_dir)

        print("Dataset successfully downloaded")

    def _download_collection(self, session, collection_path, save_dir):
        dataset = session.collections.get(collection_path)
        save_dir = save_dir.joinpath(dataset.name)
        os.makedirs(save_dir, exist_ok=True)

        for obj in dataset.data_objects:
            session.data_objects.get(obj.path, os.path.join(save_dir, obj.name))

        if dataset.subcollections:
            for subcollection in dataset.subcollections:
                self._download_collection(session, subcollection.path, save_dir)
        else:
            return
