import configparser
import psycopg2
from pathlib import Path


class Connection(object):
    """
    Class for connecting to the digitaltwins platform.
    """

    def __init__(self, config_file=None, host=None, port=None, database=None, user=None, password=None):

        self._cur = None
        self._conn = None

        if config_file:

            self._config_file = Path(config_file)
            self._configs = configparser.ConfigParser()
            self._configs.read(config_file)
            # print(self._configs.sections())

            configs_postgres = self._configs["postgres"]
            host = configs_postgres["host"]
            port = configs_postgres["port"]
            database = configs_postgres["database"]
            user = configs_postgres["user"]
            password = configs_postgres["password"]

        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password


    def get_cur(self):
        return self._cur

    def get_conn(self):
        return self._conn

    def connect(self):
        self._conn = psycopg2.connect(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._user,
            password=self._password)
        # create a cursor
        self._cur = self._conn.cursor()

        return self._conn, self._cur

    def disconnect(self):
        self._cur.close()
        self._conn.close()
