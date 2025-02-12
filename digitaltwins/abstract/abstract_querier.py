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
        if not self._config_file.is_file():
            raise ValueError(f"Configuration file '{config_file}' does not exist.")

        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._MAX_ATTEMPTS = 10

