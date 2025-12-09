import json
import configparser
import os
from pathlib import Path

from typing import Any, Dict


def _coerce_value(s: str) -> Any:
    v = s.strip()
    low = v.lower()
    if low in {"true", "yes", "on"}:
        return True
    if low in {"false", "no", "off"}:
        return False
    if low in {"none", "null"}:
        return None
    if v == "":
        return ""
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v

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

    @staticmethod
    def configs_to_dict(parser):
        result: Dict[str, Any] = {}

        for section in parser.sections():
            parts = section.split(".")
            target: Dict[str, Any] = result
            for part in parts:
                target = target.setdefault(part, {})
            for opt in parser.options(section):
                raw = parser.get(section, opt)
                target[opt] = _coerce_value(raw)

        return result
