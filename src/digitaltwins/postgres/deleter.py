"""Postgres deletion operations for datasets."""

import os
import logging

import psycopg2

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Deleter(object):
    def __init__(self):
        self._host = os.getenv("POSTGRES_HOST")
        self._port = os.getenv("POSTGRES_PORT")
        self._database = os.getenv("POSTGRES_DB")
        self._user = os.getenv("POSTGRES_USER")
        self._password = os.getenv("POSTGRES_PASSWORD")

        missing_vars = [
            name
            for name, value in [
                ("POSTGRES_HOST", self._host),
                ("POSTGRES_PORT", self._port),
                ("POSTGRES_DB", self._database),
                ("POSTGRES_USER", self._user),
                ("POSTGRES_PASSWORD", self._password),
            ]
            if not value
        ]
        if missing_vars:
            raise ValueError(
                "Missing required environment variables for PostgreSQL connection: "
                + ", ".join(missing_vars)
            )

    def connect(self):
        """Create and return a new database connection."""
        return psycopg2.connect(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._user,
            password=self._password,
        )

    def dataset_exists(self, dataset_uuid: str) -> bool:
        """Check whether a dataset with the given UUID exists.

        Opens its own short-lived connection so that the existence check
        is independent of any ongoing transaction.
        """
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM dataset WHERE dataset_uuid = %s",
                (dataset_uuid,),
            )
            return cur.fetchone() is not None
        finally:
            conn.close()

    def delete_dataset(self, cur, dataset_uuid: str) -> None:
        """Delete all rows linked to *dataset_uuid* using the provided cursor.

        The caller is responsible for managing the transaction (commit /
        rollback) on the connection that owns *cur*.

        Deletion order respects foreign-key constraints:
          dataset_mapping → manifest → dataset_description → dataset
        """
        tables = [
            "dataset_mapping",
            "manifest",
            "dataset_description",
            "dataset",
        ]
        for table in tables:
            cur.execute(
                f"DELETE FROM {table} WHERE dataset_uuid = %s",
                (dataset_uuid,),
            )
            logger.info(
                "Deleted %d row(s) from %s for dataset %s",
                cur.rowcount, table, dataset_uuid,
            )
