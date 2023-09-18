import configparser

from gen3.submission import Gen3Submission
from gen3.auth import Gen3Auth



class MetadataQuerier(object):
    """
    Class for querying Gen3.
    Also accepts queries in GraphQL syntax.
    """
    def __init__(self, config_file):
        """
        Constructor

        :param auth: Gen3 authentication object created by the Auth class
        :type auth: object
        """
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._endpoint = self._configs["gen3"].get("endpoint")
        self._cred_file = self._configs["gen3"].get("cred_file")
        self._program = self._configs["gen3"].get("program")
        self._project = self._configs["gen3"].get("project")

        self._ssl_cert = self._configs["gen3"].get("ssl_cert")
        if self._ssl_cert:
            os.environ["REQUESTS_CA_BUNDLE"] = self._ssl_cert

        self._auth = Gen3Auth(self._endpoint, str(self._cred_file))

        self._querier = Gen3Submission(self._auth)

    def _get_project_id(self, program, project):
        if program is None:
            program = self._program
        if project is None:
            project = self._project

        project_id = program + '-' + project
        return project_id

    def get_program(self):
        return self._program

    def get_project(self):
        return self._project

    def graphql_query(self, query_string, variables=None):
        """
        Sending a GraphQL query to Gen3

        :param query_string: query in GraphQL syntax
        :type query_string: string
        :param variables: query variables (optional)
        :type variables: dict
        :return: query response
        :rtype: dict
        """
        response = self._querier.query(query_string, variables).get("data")

        return response

    def get_programs_all(self):
        """
        Getting all programs that the user have access to

        :return: List of programs
        :rtype: list
        """
        response = self._querier.get_programs()

        programs = list()
        for resp in response.get("links"):
            program = resp.split('/')[-1]
            programs.append(program)

        return programs

    def get_projects_by_program(self, program):
        """
        Getting the projects by program name

        :param program: Name of a Gen3 program
        :type program: str
        :return: List of projects
        :rtype: list
        """
        response = self._querier.get_projects(program)

        projects = list()
        for resp in response.get("links"):
            project = resp.split('/')[-1]
            projects.append(project)

        return projects

    def get_datasets(self, program=None, project=None):
        project_id = self._get_project_id(program, project)

        query_string = f"""
        {{
          experiment (project_id: "{project_id}"){{
              id,
              submitter_id
          }}
        }}
        """
        response = self.graphql_query(query_string).get("experiment")


        datasets = list()
        for element in response:
            submitter_id = element.get("submitter_id")
            datasets.append(submitter_id)

        return datasets

    def get_subjects(self, dataset_id, program=None, project=None):
        project_id = self._get_project_id(program, project)

        query_string = f"""
        {{
          experiment(project_id: "{project_id}", submitter_id: "{dataset_id}"){{
            cases{{
              subject_id
            }}
          }}
        }}
        """
        response = self.graphql_query(query_string)
        experiment = response.get("experiment")[0]
        cases = experiment.get("cases")
        return cases

    def get_dataset_descriptions(self, dataset_id, program=None, project=None):
        project_id = self._get_project_id(program, project)
        query_string = f"""
        {{
          experiment(project_id: "{project_id}", submitter_id: "{dataset_id}"){{
            dataset_descriptions{{
              metadata_version,
              dataset_type,
              title,
              subtitle,
              keywords,
              funding,
              acknowledgments,
              study_purpose,
              study_data_collection,
              study_primary_conclusion,
              study_organ_system,
              study_approach,
              study_technique,
              study_collection_title,
              contributor_name,
              contributor_orcid,
              contributor_affiliation,
              contributor_role,
              identifier_description,
              relation_type,
              identifier,
              identifier_type,
              number_of_subjects,
              number_of_samples,
              dataset_type,
              title,
              subtitle,
              keywords,
              funding,
              acknowledgments,
              study_purpose,
              study_data_collection,
              study_primary_conclusion,
              study_organ_system,
              study_approach,
              study_technique,
              study_collection_title,
              contributor_name,
              contributor_orcid,
              contributor_affiliation,
              contributor_role,
              identifier_description,
              relation_type,
              identifier,
              identifier_type,
              number_of_subjects,
              number_of_samples
            }}
          }}
        }}
        """

        response = self.graphql_query(query_string)
        dataset = response.get("experiment")[0]
        dataset_descriptions = dataset.get("dataset_descriptions")

        return dataset_descriptions

    def get_node_records(self, node, program, project):
        """
        Getting all the records in a Gen3 node

        :param node: Name of the target node
        :type node: str
        :param program: program name
        :type program: str
        :param project: project name
        :type project: str
        :return: A list of records in dictionary format
        :rtype: list
        """
        response = self._querier.export_node(program, project, node, "json")
        data = response.get("data")
        return data

    def get_dataset_records(self, dataset_id, program=None, project=None):
        project_id = self._get_project_id(program, project)

        query_string = f"""
                {{
                  experiment(project_id: "{project_id}", submitter_id: "{dataset_id}"){{
                    id,
                    cases{{
                      id,
                      samples{{
                        id,
                      }}
                    }},
                    dataset_descriptions{{
                      id,
                    }},
                    manifests{{
                      id
                    }}
                  }}
                }}
                """
        response = self.graphql_query(query_string)
        datasets = response.get("experiment")
        if len(datasets) == 0:
            return None

        records = list()
        uuid_tag = "id"
        # uuid_tag = "submitter_id"

        dataset = datasets[0]
        records.insert(0, dataset.get(uuid_tag))

        cases = dataset.get("cases")
        for case in cases:
            records.insert(0, case.get(uuid_tag))
            samples = case.get("samples")
            for sample in samples:
                records.insert(0, sample.get(uuid_tag))

        dataset_descriptions = dataset.get("dataset_descriptions")
        for dataset_desc in dataset_descriptions:
            records.insert(0, dataset_desc.get(uuid_tag))

        manifests = dataset.get("manifests")
        for manifest in manifests:
            records.insert(0, manifest.get(uuid_tag))

        return records




