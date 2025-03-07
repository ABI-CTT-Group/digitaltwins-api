import json
import configparser
import os
from pathlib import Path


class ConfigLoader(object):
    def __init__(self, file=None):
        self._configs = None
        if file:
            self._configs = self.load_from_json(file)

    @staticmethod
    def load_from_json(file):
        with open(file) as f:
            configs = json.load(f)
        return configs

    @staticmethod
    def load_from_ini(config_file):
        config_file = Path(config_file)
        if not config_file.is_file():
            raise ValueError(f"Configuration file '{config_file}' does not exist.")

        configs = configparser.ConfigParser()
        configs.read(config_file)

        return configs
