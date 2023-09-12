import configparser

from pathlib import Path
import shutil

from digitaltwins import MetadataConvertor
from digitaltwins import MetadataUploader
from digitaltwins.irods.irods import IRODS


class Uploader(object):
    def __init__(self, config_file):
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._program = self._configs["gen3"].get("program")
        self._project = self._configs["gen3"].get("project")

        self._tmp_meta_dir = Path(r"./gen3_tmp")
        self._meta_files = ["experiment.json", "dataset_description.json", "manifest.json", "subjects.json"]

    def execute(self, dataset_dir):
        dataset_dir = Path(dataset_dir)
        self._verify_dataset(dataset_dir)

        # Upload metadata to Gen3
        self.upload_metadata(dataset_dir)
        # Upload the actual files to iRODS
        self.upload_dataset(dataset_dir)

        print("Dataset uploaded")

    def upload_metadata(self, dataset_dir):
        meta_dir = dataset_dir.joinpath(self._tmp_meta_dir)
        # convert sds metadata to gen3
        meta_convertor = MetadataConvertor(program=self._program, project=self._project, experiment=dataset_dir.name)
        meta_convertor.execute(source_dir=dataset_dir, dest_dir=meta_dir)

        # upload metadata
        meta_uploader = MetadataUploader(self._configs["gen3"].get("endpoint"), (self._configs["gen3"].get("cred_file")))

        for filename in self._meta_files:
            file = meta_dir.joinpath(filename)
            meta_uploader.execute(program=self._program, project=self._project, file=str(file))

        # delete the temporary metadata dir
        if meta_dir.is_dir:
            shutil.rmtree(meta_dir)

    def upload_dataset(self, dataset_dir):
        irods = IRODS(self._configs)
        irods.upload(dataset_dir)

    def _verify_dataset(self, dataset_dir):
        if dataset_dir.is_dir():
            dataset_name = dataset_dir.name
        else:
            raise NotADirectoryError("Dataset directory not found")

        # check if dataset exists
        # todo
        pass
