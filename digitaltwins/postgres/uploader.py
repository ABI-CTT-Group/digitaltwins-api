import psycopg2
from pathlib import Path

from ..utils.config_loader import ConfigLoader


class Uploader(object):
    def __init__(self, config_file):
        self._config_file = Path(config_file)
        self._configs = ConfigLoader.load_from_ini(config_file)

        configs_postgres = self._configs["postgres"]
        self._host = configs_postgres["host"]
        self._port = configs_postgres["port"]
        self._database = configs_postgres["database"]
        self._user = configs_postgres["user"]
        self._password = configs_postgres["password"]

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


    def upload_assay(self, assay_data):
        self._connect()

        assay_uuid = assay_data.get("assay_uuid")
        assay_seek_id = assay_data.get("assay_seek_id")
        workflow_seek_id = assay_data.get("workflow_seek_id")
        cohort = assay_data.get("cohort")
        ready = assay_data.get("ready")

        if assay_uuid:
            sql = r"UPDATE assay SET workflow_seek_id = %s, cohort = %s, ready = %s WHERE assay_uuid = %s RETURNING *;"
            values = (workflow_seek_id, cohort, ready, assay_uuid)
            column_names, inserted = self._exec(sql, values)
        else:
            sql = r"""INSERT INTO assay (assay_seek_id, workflow_seek_id, cohort, ready) VALUES (%s, %s, %s, %s) RETURNING *;"""
            values = (assay_seek_id, workflow_seek_id, cohort, ready)
            column_names, inserted = self._exec(sql, values)
            inserted_record = dict(zip(column_names, inserted[0]))
            assay_uuid = inserted_record.get("assay_uuid")

        if assay_uuid:
            self._delete_assay_inputs_outputs(assay_uuid)
        # inputs
        inputs = assay_data.get("inputs")
        for input in inputs:
            sql = r"""INSERT INTO assay_input (assay_uuid, name, dataset_uuid, sample_type, category) VALUES (%s, %s, %s, %s, %s) RETURNING *;"""
            values = (assay_uuid, input.get("name"), input.get("dataset_uuid"), input.get("sample_type"), input.get("category"))
            column_names, inserted = self._exec(sql, values)

        # outputs
        outputs = assay_data.get("outputs")
        for output in outputs:
            sql = r"""INSERT INTO assay_output (assay_uuid, name, dataset_name, sample_name, category) VALUES (%s, %s, %s, %s, %s) RETURNING *;"""
            values = (assay_uuid, output.get("name"), output.get("dataset_name"),
                      output.get("sample_name"), output.get("category"))
            column_names, inserted = self._exec(sql, values)

        self._disconnect()

        # testing: multiple input
        # values = [(item['name'], item['dataset_uuid'], item['sample_type'], item['category']) for item in inputs]
        #
        # args = ','.join(self._cur.mogrify("(%s,%s,%s,%s)", i).decode('utf-8')
        #                 for i in values)
        # sql = "INSERT INTO assay_input (name, dataset_uuid, sample_type, category) VALUES " + (args)
        # self._exec(sql, values)

