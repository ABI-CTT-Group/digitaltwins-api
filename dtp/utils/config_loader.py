import json


class ConfigLoader(object):
    def __init__(self, file=None):
        self._configs = None
        if file:
            self._configs = self.load_from_json(file)

    @staticmethod
    def load_from_json(file):
        with open(file) as f:
            configs = json.loads(f)
        return configs
