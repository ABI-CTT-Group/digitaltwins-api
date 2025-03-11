import configparser
import os
import shutil

from ..irods.downloader import Downloader as IRODSDownloader

from digitaltwins import Querier


class Downloader(object):
    def __init__(self, config_file):
        self._config_file = config_file
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._irods_downloader = None

        if self._configs.getboolean("irods", "enabled"):
            self._irods_downloader = IRODSDownloader(self._config_file)

    def download_dataset(self, dataset_id, save_dir="./tmp"):
        if self._irods_downloader:
            os.makedirs(str(save_dir), exist_ok=True)

            print("Downloading dataset " + dataset_id)

            self._irods_downloader.download(dataset_id, save_dir)

            print("Dataset successfully downloaded")
        else:
            raise EnvironmentError("Missing Downloader. Please check your configurations for data storage.")

    def download_assay_inputs(self, assay_id, save_dir="./tmp"):
        querier = Querier(self._config_file)
        assay = querier.get_assay(assay_id, get_params=True)

        params = assay.get("params")
        assay_uuid = params.get("assay_uuid")
        inputs = params.get("inputs")

        assay_dir = os.path.join(save_dir, assay_uuid)

        assay_inputs_dir = os.path.join(assay_dir, "inputs")
        for input in inputs:
            self.download_assay_input(input, assay_inputs_dir)

    def download_assay_input(self, assay_input, save_dir="./tmp"):
        querier = Querier(self._config_file)

        name = assay_input.get("name")
        assay_input_dir = os.path.join(save_dir, name)
        os.makedirs(assay_input_dir, exist_ok=True)

        dataset_uuid = assay_input.get("dataset_uuid")
        sample_type = assay_input.get("sample_type")
        category = assay_input.get("category")
        if category == "measurement":
            # get sample uuids by sample_type
            samples = querier.get_dataset_samples(dataset_uuid=dataset_uuid, sample_type=sample_type)
            for sample in samples:
                subject_id = sample.get("subject_id")
                sample_id = sample.get("sample_id")
                sample_uuid = sample.get("sample_uuid")

                sample_path = dataset_uuid + "/primary/" + subject_id + "/" + sample_id

                local_sample_path_tmp = assay_input_dir + "/" + sample_id
                if os.path.exists(local_sample_path_tmp):
                    shutil.rmtree(local_sample_path_tmp)

                self._irods_downloader.download(sample_path, assay_input_dir)

                local_sample_path = assay_input_dir + "/" + sample_uuid
                if os.path.exists(local_sample_path):
                    shutil.rmtree(local_sample_path)

                os.rename(local_sample_path_tmp, local_sample_path)


