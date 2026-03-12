import os
import psycopg2

from dotenv import load_dotenv
load_dotenv()


class Connection(object):
    """
    Class for connecting to the digitaltwins platform.
    """

    def __init__(self, host=None, port=None, database=None, user=None, password=None):

        self._cur = None
        self._conn = None

        self._host = host or os.getenv("POSTGRES_HOST")
        self._port = port or os.getenv("POSTGRES_PORT")
        self._database = database or os.getenv("POSTGRES_DB")
        self._user = user or os.getenv("POSTGRES_USER")
        self._password = password or os.getenv("POSTGRES_PASSWORD")


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
