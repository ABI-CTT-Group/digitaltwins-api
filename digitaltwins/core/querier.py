from ..utils.config_loader import ConfigLoader

from ..postgres.querier import Querier as PostgresQuerier
from ..gen3.querier import Querier as Gen3Querier
from ..seek.querier import Querier as SeekQuerier


class Querier(object):

    def __init__(self, config_file):
        self._configs = ConfigLoader.load_from_ini(config_file)

        if self._configs.getboolean("postgres", "enabled") and self._configs.getboolean("gen3", "enabled"):
            raise ValueError("Metadata service conflict. Only one of 'postgres' or 'gen3' can be enabled")

        if self._configs.getboolean("postgres", "enabled"):
            self._postgre_querier = PostgresQuerier(config_file)
        else:
            self._postgre_querier = None

        if self._configs.getboolean("gen3", "enabled"):
            self._gen3_querier = Gen3Querier(config_file)
        else:
            self._gen3_querier = None

        if self._configs.getboolean("seek", "enabled"):
            self._seek_querier = SeekQuerier(config_file)
        else:
            self._seek_querier = None

    def get_dependencies(self, data, target):
        relationships = self._seek_querier.get_dependencies(data, target)

        return relationships

    def get_programs(self, get_details=False):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_programs(get_details)
        elif self._configs.getboolean("postgres", "enabled"):
            results = self._postgre_querier.get_programs()
        elif self._configs.getboolean("gen3", "enabled"):
            results = self._gen3_querier.get_programs()
        else:
            raise ValueError("Missing metadata service")

        return results

    def get_program(self, program_id):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_program(program_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_projects(self, get_details=False):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_projects(get_details)
        elif self._configs.getboolean("postgres", "enabled"):
            results = self._postgre_querier.get_projects()
        elif self._configs.getboolean("gen3", "enabled"):
            results = self._gen3_querier.get_projects()
        else:
            raise ValueError("Missing metadata service")

        return results

    def get_project(self, project_id):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_project(project_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_investigations(self, get_details=False):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_investigations(get_details)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_investigation(self, investigation_id):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_investigation(investigation_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_studies(self, get_details=False):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_studies(get_details)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_study(self, study_id):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_study(study_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_assays(self, get_details=False):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_assays(get_details)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_assay(self, assay_id, get_params=False):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_assay(assay_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        if get_params:
            #  "created" means the actual assay has been created in the platform/postgres
            results_created_assay = self._postgre_querier.get_assay(seek_id=assay_id)
            results["params"] = results_created_assay

        return results

    def get_sops(self, get_details=False):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_sops(get_details)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_sop(self, sop_id):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_sop(sop_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        inputs = list()
        outputs = list()

        dataset_uuid = self._postgre_querier.get_dataset_uuid_by_seek_id(sop_id)
        results["dataset_uuid"] = dataset_uuid

        workflow_params = self._postgre_querier.get_workflow(dataset_uuid)

        for param in workflow_params:
            field_type = param.get("field_type")
            field_name = param.get("field_name")
            field_label = param.get("field_label")

            data = {
                "name": field_name,
                "category": field_label
            }

            if field_type == "input":
                inputs.append(data)
            elif field_type == "output":
                outputs.append(data)
            else:
                continue

        results["inputs"] = inputs
        results["outputs"] = outputs

        return results

    def get_datasets(self, descriptions=False, categories=list(), keywords=dict()):
        results = self._postgre_querier.get_datasets(descriptions=descriptions, categories=categories, keywords=keywords)

        return results

    def get_dataset(self, dataset_uuid):
        results = self._postgre_querier.get_dataset(dataset_uuid=dataset_uuid)

        return results

    def get_dataset_sample_types(self, dataset_uuid):
        results = self._postgre_querier.get_dataset_sample_types(dataset_uuid)

        return results

    def get_dataset_samples(self, dataset_uuid, sample_type=None):
        results = self._postgre_querier.get_dataset_samples(dataset_uuid=dataset_uuid, sample_type=sample_type)
        return results

