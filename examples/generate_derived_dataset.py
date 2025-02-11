"""
Example for generating a SDS derived dataset
"""
import os
from pathlib import Path
from sparc_me import Dataset

import dicom2nifti


def convert_DICOM_to_Nifti(dicom_folder, nii_file):
    """
    Convert a dicom folder to a single nifti file
    """

    print("Processing study {}".format(dicom_folder))
    nii_file.parent.mkdir(parents=True, exist_ok=True)
    dicom2nifti.convert_directory(dicom_folder, nii_file.parent, compression=True, reorient=False)


def add_dataset_description(dataset, save_dir):
    dataset.set_field(category="dataset_description", row_index=2, header="Value", value="2.0.0")
    dataset.set_field(category="dataset_description", row_index=3, header="Value", value="experimental")
    dataset.set_field(category="dataset_description", row_index=5, header="Value",
                      value="Duke breast cancer MRI preprocessing")
    dataset.set_field(category="dataset_description", row_index=6, header="Value", value="""Preprocessing the breast cancer MRI images and saving in Nifti format""")
    dataset.set_field(category="dataset_description", row_index=7, header="Value", value="Breast cancer")
    dataset.set_field(category="dataset_description", row_index=7, header="Value 2", value="image processing")
    dataset.set_field(category="dataset_description", row_index=11, header="Value",
                      value="""Preprocessing the breast cancer MRI images and saving in Nifti format""")
    dataset.set_field(category="dataset_description", row_index=12, header="Value", value="""derived from Duke Breast Cancer MRI dataset""")
    dataset.set_field(category="dataset_description", row_index=13, header="Value",
                      value="NA")
    dataset.set_field(category="dataset_description", row_index=14, header="Value", value="breast")
    dataset.set_field(category="dataset_description", row_index=15, header="Value", value="image processing")
    dataset.set_field(category="dataset_description", row_index=16, header="Value",
                      value="""dicom2nifti""")
    dataset.set_field(category="dataset_description", row_index=19, header="Value", value="Lin, Chinchien")
    dataset.set_field(category="dataset_description", row_index=20, header="Value",
                      value="https://orcid.org/0000-0001-8170-199X")
    dataset.set_field(category="dataset_description", row_index=21, header="Value", value="University of Auckland")
    dataset.set_field(category="dataset_description", row_index=22, header="Value", value="Researcher")
    dataset.set_field(category="dataset_description", row_index=24, header="Value", value="source")
    dataset.set_field(category="dataset_description", row_index=25, header="Value", value="WasDerivedFrom")
    dataset.set_field(category="dataset_description", row_index=26, header="Value",
                      value="DTP-UUID")
    dataset.set_field(category="dataset_description", row_index=27, header="Value", value="12L digital twin UUID")
    dataset.set_field(category="dataset_description", row_index=29, header="Value", value="1")
    dataset.set_field(category="dataset_description", row_index=30, header="Value", value="1")

    dataset.save_metadata(save_dir)
    return dataset

def set_subject_metadata(subject):
    subject_metadata = {
        "subject id": subject,
        "subject experimental group": "experimental",
        "age": "041Y",
        "sex": "F",
        "species": "human",
        "strain": "tissue",
        "age category": "middle adulthood"
    }

    return subject_metadata


def set_sample_metadata(subject, sample):
    sample_metadata = {
        "sample id": sample,
        "subject id": subject,
        "sample experimental group": "experimental",
        "sample type": "tissue",
        "sample anatomical location": "breast tissue",
    }
    return sample_metadata

def add_data(dataset, source_path, subject, sample, save_dir):
    subject_metadata = set_subject_metadata(subject)
    sample_metadata = set_sample_metadata(subject, sample)
    dataset.add_primary_data(source_path=source_path, subject=subject, sample=sample, sds_parent_dir=save_dir,
                             overwrite=True,
                             sample_metadata=sample_metadata,
                             subject_metadata=subject_metadata)
    return dataset


def run_dicom_to_nifti(source_dataset_path, subject, sample, save_dataset_path):
    save_dataset = Dataset()
    save_dataset.load_from_template(version="2.0.0")

    add_dataset_description(save_dataset, save_dir=save_dataset_path)

    dicom_dir = source_dataset_path.joinpath("primary", subject, sample)

    temp_nii_dir = Path(r"./logs/temp_nii_dir")
    nii_file = temp_nii_dir.joinpath("results.nii.gz")

    convert_DICOM_to_Nifti(dicom_dir, nii_file)

    add_data(save_dataset, source_path=temp_nii_dir, subject=subject, sample=sample, save_dir=save_dataset_path)

    rm_tree(temp_nii_dir)


def rm_tree(pth):
    pth = Path(pth)
    for child in pth.glob('*'):
        if child.is_file():
            child.unlink()
        else:
            rm_tree(child)
    pth.rmdir()


if __name__ == '__main__':
    source_dataset_path = Path(r"./logs/primary_dataset")
    save_dataset_path = Path(r"./logs/derived_dataset")

    subject = "sub-1.3.6.1.4.1.14519.5.2.1.186051521067863971269584893740842397538"
    sample = "sam-1.3.6.1.4.1.14519.5.2.1.175414966301645518238419021688341658582"

    run_dicom_to_nifti(source_dataset_path, subject, sample, save_dataset_path)
