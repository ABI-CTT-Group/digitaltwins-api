import os

import psycopg2

from dotenv import load_dotenv
load_dotenv()


class Uploader(object):
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
        self._cur = None
        self._conn = None

    def _connect(self):
        self._conn = psycopg2.connect(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._user,
            password=self._password)
        # create a cursor
        self._cur = self._conn.cursor()

    def _disconnect(self):
        self._cur.close()
        self._conn.close()

    def _exec(self, sql, values):
        column_names, inserted = None, None
        self._connect()

        if isinstance(values, tuple):
            self._cur.execute(sql, values)

        elif isinstance(values, list) and all(isinstance(item, tuple) for item in values):
            self._cur.execute(sql)
        else:
            raise ValueError("Values must be a tuple or a list of tuples")

        self._conn.commit()

        inserted = self._cur.fetchall()
        column_names = [desc[0] for desc in self._cur.description]

        self._disconnect()

        return column_names, inserted

    def _delete_assay(self, assay_seek_id):
        self._connect()

        sql = r"SELECT assay_uuid FROM assay WHERE assay_seek_id=%s"
        self._cur.execute(sql, (assay_seek_id,))
        record = self._cur.fetchone()
        column_names = [desc[0] for desc in self._cur.description]

        if record:
            # delete assay
            assay_uuid = record[0]
            sql = r"DELETE FROM assay_input WHERE assay_uuid=%s"
            self._cur.execute(sql, (assay_uuid,))
            sql = r"DELETE FROM assay_output WHERE assay_uuid=%s"
            self._cur.execute(sql, (assay_uuid,))
            sql = r"DELETE FROM assay WHERE assay_uuid=%s"
            self._cur.execute(sql, (assay_uuid,))

        self._conn.commit()
        self._disconnect()

    def _delete_assay_inputs_outputs(self, assay_uuid):
        self._connect()

        sql = r"DELETE FROM assay_input WHERE assay_uuid=%s"
        self._cur.execute(sql, (assay_uuid,))

        sql = r"DELETE FROM assay_output WHERE assay_uuid=%s"
        self._cur.execute(sql, (assay_uuid,))

        self._conn.commit()
        self._disconnect()


    def configure_assay(self, assay_data):
        """Upload or update an assay and its inputs/outputs to PostgreSQL.

        If ``assay_uuid`` is provided in *assay_data* the existing record is
        updated; otherwise a new record is inserted and the generated UUID is
        used for subsequent input/output rows.

        Returns:
            str: The ``assay_uuid`` of the inserted or updated assay.
        """
        assay_uuid = assay_data.get("assay_uuid") or None
        assay_seek_id = assay_data.get("assay_seek_id")
        workflow_seek_id = assay_data.get("workflow_seek_id")
        cohort = assay_data.get("cohort")
        ready = assay_data.get("ready")

        self._connect()
        try:
            # --- Check if assay_seek_id already exists if assay_uuid is missing ---
            if not assay_uuid and assay_seek_id is not None:
                self._cur.execute("SELECT assay_uuid FROM assay WHERE assay_seek_id = %s LIMIT 1;", (assay_seek_id,))
                existing_row = self._cur.fetchone()
                if existing_row:
                    assay_uuid = str(existing_row[0])

            # --- upsert assay record ---
            if assay_uuid:
                sql = (
                    "UPDATE assay SET workflow_seek_id = %s, cohort = %s, "
                    "ready = %s WHERE assay_uuid = %s RETURNING *;"
                )
                self._cur.execute(sql, (workflow_seek_id, cohort, ready, assay_uuid))
            else:
                sql = (
                    "INSERT INTO assay (assay_seek_id, workflow_seek_id, cohort, ready) "
                    "VALUES (%s, %s, %s, %s) RETURNING *;"
                )
                self._cur.execute(sql, (assay_seek_id, workflow_seek_id, cohort, ready))

            row = self._cur.fetchone()
            column_names = [desc[0] for desc in self._cur.description]
            inserted_record = dict(zip(column_names, row))
            assay_uuid = inserted_record.get("assay_uuid")

            # --- clear old inputs/outputs for this assay ---
            self._cur.execute("DELETE FROM assay_input WHERE assay_uuid = %s", (assay_uuid,))
            self._cur.execute("DELETE FROM assay_output WHERE assay_uuid = %s", (assay_uuid,))

            # --- insert inputs ---
            for inp in assay_data.get("inputs") or []:
                sql = (
                    "INSERT INTO assay_input (assay_uuid, name, dataset_uuid, sample_type, category) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING *;"
                )
                self._cur.execute(sql, (
                    assay_uuid, inp.get("name"), inp.get("dataset_uuid"),
                    inp.get("sample_type"), inp.get("category"),
                ))

            # --- insert outputs ---
            for out in assay_data.get("outputs") or []:
                sql = (
                    "INSERT INTO assay_output (assay_uuid, name, dataset_name, sample_name, category) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING *;"
                )
                self._cur.execute(sql, (
                    assay_uuid, out.get("name"), out.get("dataset_name"),
                    out.get("sample_name"), out.get("category"),
                ))

            self._conn.commit()
        except Exception:
            if self._conn:
                self._conn.rollback()
            raise
        finally:
            self._disconnect()

        return str(assay_uuid)

