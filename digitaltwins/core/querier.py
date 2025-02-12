from ..abstract.abstract_querier import AbstractQuerier

from ..postgres.querier import Querier as PostgresQuerier
from ..gen3.querier import Querier as Gen3Querier
from ..seek.querier import Querier as SeekQuerier


class Querier(AbstractQuerier):

    def __init__(self, config_file):

        super().__init__(config_file)

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

    def get_programs(self):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_programs()
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

    def get_projects(self):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_projects()
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

    def get_investigations(self):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_investigations()
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_investigation(self, investigation_id):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_investigation(investigation_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_studies(self):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_studies()
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_study(self, study_id):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_study(study_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_assays(self):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_assays()
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_assay(self, assay_id):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_assay(assay_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_sops(self):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_sops()
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results

    def get_sop(self, sop_id):
        if self._configs.getboolean("seek", "enabled"):
            results = self._seek_querier.get_sop(sop_id)
        else:
            raise ValueError("Missing metadata service: SEEK")

        return results
