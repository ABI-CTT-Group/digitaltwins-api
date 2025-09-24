from digitaltwins.gen3.querier import Querier


class Dataset(object):
    def __init__(self, id, program, project, config_file):
        self._program = program
        self._project = project
        self._id = id # submitter_id

        self._configs = config_file
        self._querier = Querier(self._configs)

    def get_program(self):
        return self._program

    def get_project(self):
        return self._project

    def get_id(self):
        return self._id

    def get_metadata(self, metadata):
        fields = self._get_feilds(metadata)

        if metadata == "dataset_description":
            metadata = "dataset_descriptions"
        elif metadata == "subjects":
            metadata = "cases"

        if metadata in ["samples", "sample"]:
            # sample is under the subject/case node
            query_string = f"""
            {{
                experiment (submitter_id: "{self._id}") {{
                    cases{{
                        samples{{
                            {' '.join(fields)}
                        }}
                    }}
                }}
            }}
            """
            response = self._querier.graphql_query(query_string=query_string)

            metadata = response.get("experiment")[0].get(metadata)
        else:
            query_string = f"""
            {{
                experiment (submitter_id: "{self._id}") {{
                    {metadata}{{
                        {' '.join(fields)}
                    }}
                }}
            }}
            """

            response = self._querier.graphql_query(query_string=query_string)
            metadata = response.get("experiment")[0].get(metadata)

        return metadata

    def _get_feilds(self, metadata):
        # TODO. load from schema
        fields = list()
        if metadata == "dataset_description":
            fields = [
                "metadata_version",
                "dataset_type",
                "title",
                "subtitle",
                "keywords",
                "funding",
                "acknowledgments",
                "study_purpose",
                "study_data_collection",
                "study_primary_conclusion",
                "study_organ_system",
                "study_approach",
                "study_technique",
                "study_collection_title",
                "contributor_name",
                "contributor_orcid",
                "contributor_affiliation",
                "contributor_role",
                "identifier_description",
                "relation_type",
                "identifier",
                "identifier_type",
                "number_of_subjects",
                "number_of_samples",
                "dataset_type",
                "title",
                "subtitle",
                "keywords",
                "funding",
                "acknowledgments",
                "study_purpose",
                "study_data_collection",
                "study_primary_conclusion",
                "study_organ_system",
                "study_approach",
                "study_technique",
                "study_collection_title",
                "contributor_name",
                "contributor_orcid",
                "contributor_affiliation",
                "contributor_role",
                "identifier_description",
                "relation_type",
                "identifier",
                "identifier_type",
                "number_of_subjects",
                "number_of_samples"
            ]
        elif metadata in ["subjects", "subject"]:
            fields = [
                "subject_id",
                "pool_id",
                "subject_experimental_group",
                "age",
                "sex",
                "species",
                "strain",
                "rrid_for_strain",
                "age_category",
                "also_in_dataset",
                "member_of",
                "laboratory_internal_id",
                "date_of_birth",
                "age_range_min",
                "age_range_max",
                "body_mass",
                "genotype",
                "phenotype",
                "handedness",
                "reference_atlas",
                "experimental_log_file_path",
                "experiment_date",
                "disease_or_disorder",
                "intervention",
                "disease_model",
                "protocol_title",
                "protocol_url_or_doi"
            ]
        elif metadata in ["samples", "sample"]:
            fields = [
                "sample_id",
                "subject_id",
                "wasDerivedFromSample",
                "pool_id",
                "sample_experimental_group",
                "sample_type",
                "sample_anatomical_location",
                "also_in_dataset",
                "member_of",
                "laboratory_internal_id",
                "date_of_derivation",
                "experimental_log_file_path",
                "reference_atlas",
                "pathology",
                "laterality",
                "cell_type",
                "plane_of_section",
                "protocol_title",
                "protocol_url_or_doi"
            ]
        else:
            raise ValueError(f"Querying for metadata {metadata} is not supported yet".format(metadata=metadata))

        return fields

        # query_string = f"""
        #         {{
        #             __type(name: "{metadata}"){{
        #                 fields{{
        #                     name
        #                 }}
        #             }}
        #         }}
        #
        #         """
        # fields_dict_list = self._querier.graphql_query(query_string=query_string).get("__type").get("fields")
        # fields = list()
        # for fields_dict in fields_dict_list:
        #     name = fields_dict.get("name")
        #     fields.append(name)

