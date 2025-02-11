from ..abstract.abstract_querier import AbstractQuerier

import psycopg2


class Querier(AbstractQuerier):
    def __init__(self, config_file):
        """
        Constructor inherited and expanded from AbstractQuerier
        """
        super(Querier, self).__init__(config_file)

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

    def _query(self, sql):
        self._connect()

        self._cur.execute(sql)
        resp = self._cur.fetchall()

        self._disconnect()

        results = self._format_results(resp)

        return results

    def _format_results(self, results):
        column_names = []

        # Iterate over the cursor description to extract column names
        for desc in self._cur.description:
            column_name = desc[0]  # Get the column name from the description tuple
            column_names.append(column_name)  # Add the column name to the list

        results_formated = []
        for result in results:
            row_dict = {}
            for i in range(len(result)):
                column_name = column_names[i]
                row_value = result[i]
                # Add the column name and value to the dictionary
                row_dict[column_name] = row_value
            # Convert the dictionary to a JSON object and add it to the list
            # datasets_formated.append(json.dumps(row_dict))
            results_formated.append(row_dict)
        return results_formated

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

    def get_datasets(self, descriptions=False, categories=list(), keywords=dict()):
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
