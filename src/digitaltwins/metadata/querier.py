# from itertools import chain
class Querier(object):
    """
    Class for querying metadata.
    """
    # def __init__(self, config_file):
    #     pass

    def __init__(self, connection):
        """
        Constructor
        """
        self._connection = connection

        self._MAX_ATTEMPTS = 10

    def query(self, sql):
        cur = self._connection.get_cur()

        cur.execute(sql)
        resp = cur.fetchall()

        return resp

    def get_programs(self):
        sql = "SELECT * FROM program"
        resp = self.query(sql)

        results = self._format_results(resp)

        return results

    def get_projects(self):
        sql = "SELECT * FROM project"
        resp = self.query(sql)

        results = self._format_results(resp)

        return results

    def _format_results(self, results):
        cur = self._connection.get_cur()

        column_names = []

        # Iterate over the cursor description to extract column names
        for desc in cur.description:
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

    def get_datasets(self, categories=list()):
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
        resp = self.query(sql)

        results = self._format_results(resp)

        return results

    # def get_datasets_by_keywords(self, mappings={}):
    #     if mappings:
    #         conditions = ""
    #         for idx, key in enumerate(mappings):
    #             if idx == 0:
    #                 conditions = "WHERE {key} LIKE '%{value}%'".format(key=key, value=mappings[key])
    #             else:
    #                 conditions += " AND {key} LIKE '%{value}%'".format(key=key, value=mappings[key])
    #
    #         sql = "SELECT dataset_uuid, title FROM dataset_description {conditions}".format(conditions=conditions)
    #     else:
    #         sql = "SELECT * FROM dataset"
    #
    #
    #     resp = self.query(sql)
    #
    #     return resp

    def get_datasets_by_descriptions(self, mappings={}):
        if mappings:
            conditions = ""
            for idx, key in enumerate(mappings):
                if idx == 0:
                    conditions = "WHERE {key} LIKE '%{value}%'".format(key=key, value=mappings[key])
                else:
                    conditions += " AND {key} LIKE '%{value}%'".format(key=key, value=mappings[key])

            sql = "SELECT dataset_uuid, title FROM dataset_description {conditions}".format(conditions=conditions)
        else:
            sql = "SELECT dataset_uuid, title FROM dataset_description"

        resp = self.query(sql)

        return resp

    def get_datasets_by_categories(self, categories=list()):
        formatted_categories_list = []

        # Loop through each category and format it
        for category in categories:
            formatted_category = f"'{category}'"
            formatted_categories_list.append(formatted_category)

        # Join the formatted categories into a single string
        formatted_categories = ', '.join(formatted_categories_list)

        sql = f"SELECT dataset_id, category FROM dataset WHERE category IN ({formatted_categories})"
        # sql = f"SELECT dataset_uuid, dataset_id, category FROM dataset WHERE category IN ({formatted_categories})"

        # Execute the query with the actual list of categories
        resp = self.query(sql)

        return resp

    def get_dataset_descriptions(self, dataset_uuid):
        sql = "SELECT * FROM dataset_description WHERE dataset_uuid='{dataset_uuid}'".format(dataset_uuid=dataset_uuid)
        resp = self.query(sql)

        return resp


    def get_subjects(self, dataset_uuid):
        sql = "SELECT * FROM dataset_mapping WHERE dataset_uuid='{dataset_uuid}'".format(dataset_uuid=dataset_uuid)
        resp = self.query(sql)

        return resp

    def get_samples(self, dataset_uuid=None, subject_uuid=None):
        sql = r"""SELECT subject_sample.sample_uuid FROM subject_sample INNER JOIN dataset_mapping ON subject_sample.subject_uuid=dataset_mapping.subject_uuid"""
        if dataset_uuid and not subject_uuid:
            sql = sql + " WHERE dataset_uuid='{dataset_uuid}'".format(dataset_uuid=dataset_uuid)
        elif not dataset_uuid and subject_uuid:
            sql = sql + " WHERE subject_uuid='{subject_uuid}'".format(subject_uuid=subject_uuid)
        elif dataset_uuid and subject_uuid:
            sql = sql + " WHERE dataset_uuid='{dataset_uuid}' AND subject_uuid='{subject_uuid}'".format(dataset_uuid=dataset_uuid, subject_uuid=subject_uuid)

        resp = self.query(sql)
        return resp

