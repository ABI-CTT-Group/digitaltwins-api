import configparser
from pathlib import Path

from ..postgres.querier import Querier as PostgresQuerier
from ..gen3.querier import Querier as Gen3Querier


class QuerierFactory:
    """
    static factory
    """
    @staticmethod
    def create(config_file):
        """
        static method for creating Querier instance
        by the value of the metadata service field in the given configuration file

        :param config_file: path to the configuration file
        :type config_file: str or Path
        :return: a Querier instance
        :rtype: PostgresQuerier or Gen3Querier
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

