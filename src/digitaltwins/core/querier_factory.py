import os

from dotenv import load_dotenv
load_dotenv()

from ..postgres.querier import Querier as PostgresQuerier
from ..gen3.querier import Querier as Gen3Querier


class QuerierFactory:
    """
    static factory
    """
    @staticmethod
    def create():
        """
        static method for creating Querier instance
        by the value of the METADATA_SERVICE environment variable

        :return: a Querier instance
        :rtype: PostgresQuerier or Gen3Querier
        """
        metadata_service = os.getenv("METADATA_SERVICE")
        if metadata_service == "postgres":
            return PostgresQuerier()
        elif metadata_service == "gen3":
            return Gen3Querier()
        else:
            raise ValueError("Unknown metadata service")

