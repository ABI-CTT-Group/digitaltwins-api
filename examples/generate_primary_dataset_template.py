"""
Example for generating a SDS primary dataset
"""
import os.path
import warnings

from sparc_me import Dataset


warnings.filterwarnings('ignore', category=DeprecationWarning)


def add_dataset_description(dataset, save_dir):
    """
    the values can be filled in by 2 methods, set_field() or set_field_using_row_name().

    This example will use Dataset.set_field()
    # You can get the row_index by looking at
    #   1. the saved metadata file dataset_description.xlsx. Excel index starts from 1 where index 1 is the header row. so actual data index starts from 2.
    #   2. or the DataFrame object in the python code. dataset._dataset.dataset_description.metadata
    """

    metadata = dataset.get_metadata(metadata_file='dataset_description')
    metadata.add_values(
        element='Type',
        values='Experimental')
    metadata.add_values(
        element='Title',
        values='')
    metadata.add_values(
        element='Subtitle',
        values='')
    metadata.add_values(
        element='Keywords',
        values=['', ''])
    metadata.add_values(
        element='Study purpose',
        values='')
    metadata.add_values(
        element='Study data Collection',
        values='')
    metadata.add_values(
        element='Study primary conclusion',
        values='')
    metadata.add_values(
        element='Study organ system',
        values='')
    metadata.add_values(
        element='Study approach',
        values='')
    metadata.add_values(
        element='Study technique',
        values='')
    metadata.add_values(
        element='Contributorname',
        values=['', '', ''])
    metadata.add_values(
        element='Contributor orcid',
        values=['', '', ''])
    metadata.add_values(
        element='Identifier',
        values='')
    metadata.add_values(
        element='Identifier description',
        values='')
    metadata.add_values(
        element='Relation type',
        values='')
    metadata.add_values(
        element='Identifier type',
        values='')
    metadata.add_values(
        element='Contributor affiliation',
        values=['', '', ''])
    metadata.add_values(
        element='Contributor role',
        values=['', '', ''])

    dataset.save_metadata(save_dir)
    return dataset


def set_subject_metadata(subject):
    subject_metadata = {
        "subject id": subject,
        "subject experimental group": "experimental",
        "age": "",
        "sex": "",
        "species": "",
        "strain": "",
        "age category": ""
    }

    return subject_metadata


def set_sample_metadata(subject, sample):
    sample_metadata = {
        "sample id": sample,
        "subject id": subject,
        "sample experimental group": "experimental",
        "sample type": "",
        "sample anatomical location": "",
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


if __name__ == '__main__':
    save_dir = "/path/to/your/output/directory"

    # Creating a SDS dataset from template
    dataset = Dataset()
    dataset.load_from_template(version="2.0.0")

    # Filling dataset. Please modify this function according to your dataset description
    add_dataset_description(dataset, save_dir=save_dir)
    subject = "sub-"
    sample = "sam-"
    add_data(dataset, source_path= os.path.join("../resources", subject, sample), subject=subject, sample=sample, save_dir=save_dir)
