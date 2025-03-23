from pathlib import Path

from digitaltwins import Uploader

if __name__ == '__main__':
    config_file = Path(r"/path/to/configs.ini")

    uploader = Uploader(config_file)
    assay_data = {
        "assay_seek_id": 1,
        "workflow_seek_id": 1,
        "cohort": 2,
        "ready": True,
        "inputs": [
            {"name": "",
             "category": "",
             "dataset_uuid": "",
             "sample_type": ""},
            {"name": "",
             "category": "",
             "dataset_uuid": "",
             "sample_type": ""},
            {"name": "",
             "category": "model",
             "dataset_uuid": "",
             "sample_type": ""},
            {"name": "",
             "category": "",
             "dataset_uuid": "",
             "sample_type": ""}
        ],
        "outputs": [
            {"name": "",
             "category": "",
             "dataset_name": "",
             "sample_name": ""},
            {"name": "",
             "category": "",
             "dataset_name": "",
             "sample_name": ""},
            {"name": "",
             "category": "",
             "dataset_name": "",
             "sample_name": ""},
            {"name": "",
             "category": "",
             "dataset_name": "",
             "sample_name": ""},
            {"name": "",
             "category": "",
             "dataset_name": "",
             "sample_name": ""}
        ]
    }

    uploader.upload_assay(assay_data)


