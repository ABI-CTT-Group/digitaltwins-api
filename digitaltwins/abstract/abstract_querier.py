from abc import ABC, abstractmethod

import configparser
import os
from pathlib import Path


class AbstractQuerier(ABC):
    """
    Class for querying metadata.
    """
    # def __init__(self, config_file):
    #     pass

    def __init__(self, config_file):
        """
        Constructor
        """
        self._config_file = Path(config_file)
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._MAX_ATTEMPTS = 10

    @abstractmethod
    def get_programs(self):
        pass

    @abstractmethod
    def get_projects(self):
        pass

    @abstractmethod
    def get_datasets(self, descriptions=False, categories=list(), keywords=dict()):
        pass

    @abstractmethod
    def get_subjects(self, dataset_uuid):
        pass

    @abstractmethod
    def get_samples(self, dataset_uuid=None, subject_uuid=None):
        pass

