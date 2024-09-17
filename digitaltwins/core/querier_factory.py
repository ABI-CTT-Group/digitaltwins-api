# from ..abstract.abstract_factory import AbstractFactory

import configparser
from pathlib import Path

from ..postgres.querier import Querier as PostgresQuerier
from ..gen3.querier import Querier as Gen3Querier


class QuerierFactory:
    @staticmethod
    def create(config_file):
        """
        Constructor
        """
        config_file = Path(config_file)
        configs = configparser.ConfigParser()
        configs.read(config_file)

        metadata_service = configs["general"]["metadata_service"]
        if metadata_service == "postgres":
            return PostgresQuerier(config_file)
        elif metadata_service == "gen3":
            return Gen3Querier(config_file)
        else:
            raise ValueError("Unknown metadata service")


# class QuerierFactory(AbstractFactory):
#     def create(self, config_file):
#         """
#         Constructor
#         """
#         super().create(config_file)
#         # super(AbstractFactory, self).__init__(config_file)
#
#         self._metadata_service = self._configs["general"]["metadata_service"]
#         if self._metadata_service == "postgres":
#             return PostgresQuerier(config_file)
#         elif self._metadata_service == "gen3":
#             return Gen3Querier(config_file)
#         else:
#             raise ValueError("Unknown metadata service")

