import os
from pathlib import Path
import pandas as pd
from xlrd import XLRDError
import json
import yaml
import re
from datetime import datetime


class MetadataConvertor(object):
    """
    Converting the metadata from SPARC dataset structure (SDS) to Gen3 submittable structure in json format
    """
    def __init__(self, program, project, experiment, schema_dir=None, version="2.0.0"):
        """
        Constructor

        :param program: Program name
        :type program: str
        :param project: Project name
        :type project: str
        :param experiment: Experiment/dataset name
        :type experiment: str
        :param version: SDS schema version
        :type version: str
        """
        self._version = version
        self._program = program
        self._project = project
        self._experiment = experiment

        self._current_dir = Path(__file__).parent.resolve()

        self._resources_dir = self._current_dir.joinpath("../resources")

        if schema_dir:
            self._schema_dir = schema_dir
        else:
            version_dirname = "version_" + version.replace('.', '_')
            self._schema_dir = self._resources_dir.joinpath(version_dirname, "sds_dictionary")

        self._supported_versions = ["1.2.3", "2.0.0"]

        self._special_chars = ['/', '_']

        self._categories = ["experiment", "dataset_description", "subjects", "manifest"]
        # self._categories = ["experiment", "dataset_description", "subjects", "manifest", "samples"]
        self._row_based = ["subjects", "manifest"]
        # self._row_based = ["subjects", "manifest", "samples"]
        self._col_based = ["dataset_description"]

        self._validate_version(version)

    def set_schema_dir(self, path):
        """
        Setting the SDS schema directory

        :param path: Path to the SDS schema directory
        :type path: str
        :return:
        :rtype:
        """
        self._schema_dir = Path(path)

    def _validate_version(self, version):
        """
        Checking if the SDS version is supported

        :param version: SDS version
        :type version: str
        :return:
        :rtype:
        """
        if version not in self._supported_versions:
            raise Exception("Dataset version not supported")

    def _init_data(self, category):
        """
        Initialising the Gen3 data structure

        :param category: SDS metadata category
        :type category: str
        :return: Gen3 data structure
        :rtype: dict
        """
        if category == "subjects":
            type = "case"
        elif category == "samples":
            type = "sample"
        else:
            type = category

        if category == "experiment":
            data = {
                "type": type,
                "submitter_id": self._experiment,
                "projects": [{
                    "code": self._project
                }],
            }
        else:
            if category == "samples":
                data = {
                    "type": type,
                    "cases": [{"submitter_id": self._experiment}],
                    "submitter_id": self._experiment + '-' + category
                }
            else:
                data = {
                    "type": type,
                    "experiments": [{"submitter_id": self._experiment}],
                    "submitter_id": self._experiment + '-' + category
                }

        return data

    def execute(self, source_dir, dest_dir):
        """
        Converting metadata

        :param source_dir: Path to the source (SDS) directory
        :type source_dir: str or  pathlib.Path object
        :param dest_dir: Path to the destination (Gen3) directory
        :type dest_dir: str or pathlib.Path object
        :return:
        :rtype:
        """
        source_dir = Path(source_dir)
        dest_dir = Path(dest_dir)
        for category in self._categories:
            data = self._init_data(category)
            if category == "experiment":
                data = self._init_data(category)
                filename = category + ".json"
                dest = dest_dir.joinpath(filename)
                self._save(data, dest)
                continue

            mappings = self._get_mappings(self._version, category)

            if category == "manifest":
                sources = self._get_files(source_dir, category)
                metadata_pd_composite = None
                for source in sources:
                    metadata_pd = self._get_sparc_metadata(source)
                    metadata_pd = self._map_fields(category, metadata_pd, mappings, target_version="2.0.0")

                    if metadata_pd_composite is not None:
                        metadata_pd_composite = pd.concat([metadata_pd_composite, metadata_pd], ignore_index=True)
                    else:
                        metadata_pd_composite = metadata_pd
                metadata_pd = metadata_pd_composite
            else:
                source = source_dir.joinpath(category + ".xlsx")
                metadata_pd = self._get_sparc_metadata(source)
                metadata_pd = self._map_fields(category, metadata_pd, mappings, target_version="2.0.0")
            records = metadata_pd.to_dict('records')

            if category in self._row_based:
                schema = self._get_schema(category)
                properties = schema.get("properties")
                system_properties = schema.get("systemProperties")
                required = schema.get("required")

                data_list = list()
                data_init = data.copy()
                for metadata_dict in records:
                    data = data_init.copy()
                    for property in properties.items():
                        key = property[0]

                        if key in system_properties:
                            continue
                        try:
                            if data.get(key):
                                continue
                        except:
                            print("test")

                        value = metadata_dict.get(key)

                        # Update submitter_id
                        if key in ["subject_id", "filename"]:
                            data["submitter_id"] = data["submitter_id"] + '-' + value
                            data["submitter_id"] = data["submitter_id"].replace('./', '')
                            data["submitter_id"] = re.sub(str(self._special_chars), '-', data["submitter_id"])

                        # check if value exists and if value equals to nan (nan variable does not equal to itself)
                        if value and value == value:
                            if isinstance(value, datetime):
                                value = str(value)

                            if isinstance(value, list) and len(value) == 1:
                                value = value[0]

                            # handle special values
                            if isinstance(value, str):
                                value = value.replace("\"", "\'")

                                # separate string by new line "\n" and saved in a list if the list > 1
                                value_list = value.split("\n")
                                if len(value_list) > 1:
                                    value = value_list

                            data[key] = value
                        else:
                            if key in required:
                                data[key] = "NA"

                    data_list.append(data)
                    del data
                data = data_list
            elif category in self._col_based:
                data = self._convert(category, records, data)

            filename = category + ".json"
            dest = dest_dir.joinpath(filename)
            self._save(data, dest)

    def _get_files(self, source, category):
        """
        Getting all files from a directory filtered by Gen3 category. e.g. manifest

        :param source: path to the source directory
        :type source: str or pathlib.Path object
        :param category: SDS category
        :type category: str
        :return: List of files
        :rtype: list
        """
        files = list()
        if source.is_file():
            files.append(source)
        elif source.is_dir():
            filename = category + ".xlsx"
            for file in source.rglob(filename):
                files.append(file)
        else:
            raise FileNotFoundError("File not found")
        return files

    @staticmethod
    def read_excel(path, sheet_name=None):
        """
        Reading Excel data as a python dataframe object

        :param path: Path to the Excel file
        :type path: str or pathlib.Path object
        :param sheet_name: Excel sheet name
        :type sheet_name: str
        :return: Data in dataframe object format
        :rtype: object
        """
        try:
            # the read_excel method return dict when sheet name is passed. otherwise a dataframe will be returned
            if sheet_name:
                metadata = pd.read_excel(path, sheet_name=sheet_name)
            else:
                metadata = pd.read_excel(path)
        except XLRDError:
            if sheet_name:
                metadata = pd.read_excel(path, sheet_name=sheet_name, engine='openpyxl')
            else:
                metadata = pd.read_excel(path, engine='openpyxl')

        return metadata

    def _get_mappings(self, version, category):
        """
        Getting the mapping between SDS and Gen3 variables

        :param version: SDS version
        :type version: str
        :param category: SDS category
        :type category: str
        :return: The mapping between SDS and Gen3 variables in dataframe
        :rtype: object
        """
        version = version.replace(".", "_")
        version = "version_" + version
        version_dir = self._resources_dir / version
        mapping_file = version_dir / "element_mapping.xlsx"

        mappings = self.read_excel(mapping_file, category)

        return mappings

    def _save(self, data, dest):
        """
        Saving the converted Gen3 submission file

        :param data: Converted data in Gen3 submission structure
        :type data: dict
        :param dest: Path to the save file
        :type dest: str or pathlib.Path object
        :return:
        :rtype:
        """
        os.makedirs(dest.parent, exist_ok=True)
        with open(dest, 'w') as f:
            json.dump(data, f, indent=4)

    def _get_schema(self, category):
        """
        Getting the SDS schema

        :param category: SDS category
        :type category: str
        :return: SDS schema
        :rtype: dict
        """
        if category == "subjects":
            category = "case"
        if category == "samples":
            category = "sample"
        schema_file = category + ".yaml"
        schema_file = self._schema_dir / schema_file

        try:
            # Linux
            with open(schema_file, 'r') as yml:
                schema = yaml.safe_load(yml)
        except Exception as e:
            # Windows
            with open(schema_file, 'rt', encoding='utf8') as yml:
                schema = yaml.safe_load(yml)

        return schema

    def _get_sparc_metadata(self, source):
        """
        Getting the SDS metadata from a file (Excel)

        :param source: Path to the metadata file
        :type source: str
        :return:
        :rtype:
        """
        metadata_sparc = self.read_excel(source)
        if source.stem == "dataset_description":
            # combine values
            metadata_sparc["values"] = metadata_sparc.iloc[:, 3:].values.tolist()
            metadata_sparc["values"] = metadata_sparc["values"].apply(lambda x: [i for i in x if str(i) != "nan"])

            # Extract columns
            # Element name: 1st column
            # Values: last column
            metadata_sparc = metadata_sparc[[metadata_sparc.columns[0], metadata_sparc.columns[-1]]]

        return metadata_sparc

    def _map_fields(self, category, metadata_sparc, mappings, target_version):
        """
        Mapping/changing the SDS fields' names to Gen3 fields' names

        :param category: SDS category
        :type category: str
        :param metadata_sparc: SDS metadata in Dataframe
        :type metadata_sparc: object
        :param mappings: Mapping in Dataframe
        :type mappings: object
        :param target_version: SDS version
        :type target_version: str
        :return: New SDS metadata in Dataframe
        :rtype: object
        """
        if category == "dataset_description":
            nums_of_records = len(metadata_sparc)
            column_idx = 0
            elements = metadata_sparc.iloc[:, column_idx].tolist()

            for idx in range(nums_of_records):
                element = elements[idx]
                try:
                    record = mappings[mappings['element'] == element]
                    metadata_sparc.loc[idx, metadata_sparc.columns[0]] = record.iloc[0]["gen3_element_" + target_version]
                except:
                    continue

            metadata_sparc = metadata_sparc.dropna()
        else:
            column_headers = list(metadata_sparc.columns)
            for idx, column_header in enumerate(column_headers):
                record = mappings[mappings['element'].str.lower() == column_header.lower()]
                if record.empty:
                    continue
                new_name = record.iloc[0]["gen3_element_" + target_version]

                metadata_sparc = metadata_sparc.rename(columns={column_header: new_name})

            metadata_sparc = metadata_sparc.loc[:, metadata_sparc.columns.notna()]

        return metadata_sparc

    def _convert(self, category, records, data):
        """
        Converting SDS data to Gen3 submission structure

        :param category: SDS category
        :type category: str
        :param records: SDS data. List of dictionary
        :type records: list
        :param data: Initial data in Gen3 structure
        :type data: dict
        :return: New data in Gen3 structure
        :rtype: dict
        """
        metadata_dict = dict()

        if category == "dataset_description":
            for record in records:
                element = record.get("Metadata element")
                values = record.get("values")
                metadata_dict[element] = values

        schema = self._get_schema(category)
        properties = schema.get("properties")
        system_properties = schema.get("systemProperties")
        required = schema.get("required")

        for property in properties.items():
            key = property[0]

            if key in system_properties:
                continue
            if data.get(key):
                continue

            value = metadata_dict.get(key)

            if value:
                if category in self._row_based and len(value) == 1:
                    value = value[0]

                data[key] = value
            else:
                if key in required:
                    if category in self._col_based:
                        data[key] = []
                    else:
                        data[key] = "NA"
        return data
