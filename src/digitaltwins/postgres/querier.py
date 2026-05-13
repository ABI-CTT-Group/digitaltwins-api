

import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()

class Querier(object):
    def __init__(self):
        """
        Constructor inherited and expanded from AbstractQuerier
        """
        self._host = os.getenv("POSTGRES_HOST")
        self._port = os.getenv("POSTGRES_PORT")
        self._database = os.getenv("POSTGRES_DB")
        self._user = os.getenv("POSTGRES_USER")
        self._password = os.getenv("POSTGRES_PASSWORD")

        for required in [self._host, self._port, self._database, self._user, self._password]:
            if not required:
                raise ValueError("Postgres configuration is incomplete. Please check your configuration file or environment variables.")

    def _query(self, sql, values=None):
        # Connection and cursor are local to this call — not stored on self.
        # Storing them as instance state caused race conditions when concurrent
        # requests shared the same Querier singleton.
        conn = psycopg2.connect(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._user,
            password=self._password)
        cur = conn.cursor()
        try:
            if values:
                cur.execute(sql, values)
            else:
                cur.execute(sql)
            resp = cur.fetchall()
            results = self._format_results(cur, resp)
        finally:
            cur.close()
            conn.close()
        return results

    @staticmethod
    def _format_results(cur, results):
        column_names = [desc[0] for desc in cur.description]
        return [dict(zip(column_names, row)) for row in results]

    def get_programs(self):
        """

        :return: a list of program names
        :rtype: list
        """
        sql = "SELECT * FROM program"
        results = self._query(sql)

        return results

    def get_projects(self):
        sql = "SELECT * FROM project"
        results = self._query(sql)

        return results

    def get_datasets(self, descriptions=False, categories=None, keywords=None):
        categories = list(categories) if categories is not None else []
        keywords = dict(keywords) if keywords is not None else {}

        if len(categories) == 0:
            sql = "SELECT * FROM dataset"
        else:
            formatted_categories_list = []

            # Loop through each category and format it
            for category in categories:
                formatted_category = f"'{category}'"
                formatted_categories_list.append(formatted_category)

            # Join the formatted categories into a single string
            formatted_categories = ', '.join(formatted_categories_list)

            sql = f"SELECT * FROM dataset WHERE category IN ({formatted_categories})"

        # Execute the query with the actual list of categories
        results = self._query(sql)

        return results

    def get_dataset(self, dataset_uuid):
        sql = "SELECT * FROM dataset WHERE dataset_uuid='{dataset_uuid}'".format(dataset_uuid=dataset_uuid)
        results = self._query(sql)

        return results[0]

    def get_dataset_uuid_by_seek_id(self, seek_id):
        sql = "SELECT dataset_uuid FROM dataset WHERE seek_id='{seek_id}'".format(seek_id=seek_id)
        results = self._query(sql)

        if len(results) > 0:
            dataset_uuid = results[0].get("dataset_uuid")
        else:
            print("No dataset found by seek_id '{}'".format(seek_id))
            dataset_uuid = None

        return dataset_uuid

    def get_dataset_descriptions(self, dataset_uuid):
        sql = "SELECT * FROM dataset_description WHERE dataset_uuid='{dataset_uuid}'".format(dataset_uuid=dataset_uuid)
        results = self._query(sql)

        return results

    def get_subjects(self, dataset_uuid):
        sql = "SELECT * FROM dataset_mapping WHERE dataset_uuid='{dataset_uuid}'".format(dataset_uuid=dataset_uuid)
        results = self._query(sql)

        return results

    def get_samples(self, dataset_uuid=None, subject_uuid=None):
        sql = r"""SELECT subject_sample.sample_uuid FROM subject_sample INNER JOIN dataset_mapping ON subject_sample.subject_uuid=dataset_mapping.subject_uuid"""
        if dataset_uuid and not subject_uuid:
            sql = sql + " WHERE dataset_uuid='{dataset_uuid}'".format(dataset_uuid=dataset_uuid)
        elif not dataset_uuid and subject_uuid:
            sql = sql + " WHERE subject_uuid='{subject_uuid}'".format(subject_uuid=subject_uuid)
        elif dataset_uuid and subject_uuid:
            sql = sql + " WHERE dataset_uuid='{dataset_uuid}' AND subject_uuid='{subject_uuid}'".format(
                dataset_uuid=dataset_uuid, subject_uuid=subject_uuid)

        results = self._query(sql)
        return results

    def get_subject_by_sample(self, sample_uuid):
        sql = "SELECT DISTINCT subject_uuid FROM dataset_mapping WHERE sample_uuid='{sample_uuid}'".format(sample_uuid=sample_uuid)
        resp = self._query(sql)
        subject_uuid = resp[0].get("subject_uuid")
        sql = "SELECT * FROM subject WHERE subject_uuid='{subject_uuid}'".format(subject_uuid=subject_uuid)
        result = self._query(sql)

        return result

    def get_sample(self, sample_uuid):
        sql = "SELECT * FROM sample WHERE sample_uuid='{sample_uuid}'".format(sample_uuid=sample_uuid)
        resp = self._query(sql)

        return resp

    def get_workflow(self, dataset_uuid):
        sql = "SELECT * FROM workflow WHERE dataset_uuid='{dataset_uuid}'".format(dataset_uuid=dataset_uuid)

        resp = self._query(sql)

        return resp

    def get_dataset_sample_types(self, dataset_uuid):
        sql = "SELECT DISTINCT dataset_uuid, sample_uuid FROM dataset_mapping WHERE dataset_uuid='{dataset_uuid}'".format(dataset_uuid=dataset_uuid)

        resp = self._query(sql)

        sample_uuids = list()
        for sample in resp:
            sample_uuid = sample.get("sample_uuid")
            sample_uuids.append(sample_uuid)

        formatted_sample_uuids_list = []

        # Loop through each category and format it
        for sample_uuid in sample_uuids:
            formatted_sample_uuids = f"'{sample_uuid}'"
            formatted_sample_uuids_list.append(formatted_sample_uuids)

        formatted_sample_uuids = ', '.join(formatted_sample_uuids_list)
        sql = f"SELECT sample_type FROM sample WHERE sample_uuid IN ({formatted_sample_uuids})"

        resp = self._query(sql)

        sample_types = list()
        for row in resp:
            sample_type = row.get("sample_type")
            if sample_type and sample_type not in sample_types:
                sample_types.append(sample_type)

        return sample_types

    def get_assay(self, seek_id=""):
        result = None
        sql = ("SELECT * FROM assay "
               "WHERE assay_seek_id = %s")
        resp = self._query(sql, (seek_id,))
        try:
            result = resp[0]
        except IndexError:
            result = None
            return result
        assay_uuid = result.get("assay_uuid")

        # inputs
        sql = ("SELECT * FROM assay_input "
               "WHERE assay_uuid = %s")
        resp = self._query(sql, (assay_uuid,))
        result["inputs"] = resp

        sql = ("SELECT * FROM assay_output "
               "WHERE assay_uuid = %s")
        resp = self._query(sql, (assay_uuid,))
        result["outputs"] = resp

        return result

    def get_dataset_samples(self, dataset_uuid, sample_type=None):
        sql = (r"SELECT * "
               r"FROM dataset_mapping "
               r"INNER JOIN sample ON dataset_mapping.sample_uuid = sample.sample_uuid "
               r"WHERE dataset_mapping.dataset_uuid='{dataset_uuid}' "
               r"AND sample.sample_type='{sample_type}'").format(dataset_uuid=dataset_uuid, sample_type=sample_type)

        resp = self._query(sql)

        return resp
