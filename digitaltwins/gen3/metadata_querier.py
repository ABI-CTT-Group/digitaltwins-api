import configparser
import os
import time
from pathlib import Path

from gen3.submission import Gen3Submission
from gen3.auth import Gen3Auth, Gen3AuthError

from requests.exceptions import ConnectionError

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
        self._config_file = config_file
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._endpoint = self._configs["gen3"].get("endpoint")
        self._cred_file = Path(self._configs["gen3"].get("cred_file"))
        self._program = self._configs["gen3"].get("program")
        self._project = self._configs["gen3"].get("project")

        self._ssl_cert = self._configs["gen3"].get("ssl_cert")
        if self._ssl_cert:
            os.environ["REQUESTS_CA_BUNDLE"] = self._ssl_cert

        self._auth = Gen3Auth(self._endpoint, str(self._cred_file))

        self._querier = Gen3Submission(self._auth)

        self._MAX_ATTEMPTS = 10

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

    def graphql_query(self, query_string, variables=None, count=0):
        """
        Sending a GraphQL query to Gen3

        :param query_string: query in GraphQL syntax
        :type query_string: string
        :param variables: query variables (optional)
        :type variables: dict
        :return: query response
        :rtype: dict
        """
        if count >= self._MAX_ATTEMPTS:
            raise ValueError(f"Max attempts {count} exceeded. Please try again. If the error "
                             f"persists, please contact the developers".format(count=count))
        try:
            response = self._querier.query(query_string, variables)
            data = response.get("data")
            return data
        except Gen3AuthError as e:
            time.sleep(2)
            count = count + 1
            return self.graphql_query(query_string, variables=variables, count=count)
        except ConnectionError as e:
            raise ConnectionError("HTTP connection error: Please make sure you have access to the remote server. then "
                                  "try again!")

    def get_programs_all(self):
        """
        Getting all programs that the user have access to

        :return: List of programs
        :rtype: list
        """
        query_string = f"""
        {{
            program{{
                name
            }}
        }}
        """
        data = self.graphql_query(query_string)
        programs = data.get('program')

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
        if program is None and project is None:
            query_string = f"""
            {{
                program{{
                    name
                    projects{{
                        name
                        experiments{{
                            submitter_id
                        }}
                    }}
                }}
            }}
            """
        if program and project is None:
            query_string = f"""
            {{
                program (name: "{program}"){{
                    name
                    projects{{
                        name
                        experiments{{
                            submitter_id
                        }}
                    }}
                }}
            }}
            """
        if program is None and project:
            query_string = f"""
            {{
                program{{
                    name
                    projects (name: "{project}"){{
                        name
                        experiments{{
                            submitter_id
                        }}
                    }}
                }}
            }}
            """
        if program and project:
            query_string = f"""
            {{
                program (name: "{program}") {{
                    name
                    projects (name: "{project}"){{
                        name
                        experiments {{
                            submitter_id
                        }}
                    }}
                }}
            }}
            """
        data = self.graphql_query(query_string)

        datasets = list()
        programs = data.get('program')
        for program in programs:
            program_name = program.get("name")
            projects = program.get("projects")
            for project in projects:
                project_name = project.get("name")
                experiments = project.get("experiments")
                for experiment in experiments:
                    submitter_id = experiment.get("submitter_id")
                    dataset = Dataset(id=submitter_id, program=program_name, project=project_name)
                    datasets.append(dataset)

        return datasets

    def get_dataset(self, dataset_id, program=None, project=None):
        if program is None:
            program = self._program
        if project is None:
            project = self._project

        query_string = f"""
        {{
            program (name: "{program}"){{
                name
                projects (name: "{project}"){{
                    name
                    experiments (submitter_id: "{dataset_id}"){{
                        submitter_id
                    }}
                }}
            }}
        }}
        """
        data = self.graphql_query(query_string)

        dataset = None
        if data:
            dataset = Dataset(dataset_id, program, project, self._config_file)
        else:
            print("Dataset not found: " + str(dataset_id))

        return dataset


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




from digitaltwins.core.dataset import Dataset
