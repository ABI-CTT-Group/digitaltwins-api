from digitaltwins import MetadataQuerier
from pathlib import Path
import configparser

if __name__ == '__main__':
    config_file = Path(r"/path/to/configs.ini")

    querier = MetadataQuerier(config_file)

    # List programs
    programs = querier.get_programs_all()
    print("Programs: " + str(programs))

    # List projects
    program = "PROGRAM_NAME"
    projects = querier.get_projects_by_program(program=program)
    print("projects: " + str(projects))

    # List datasets
    datasets = querier.get_datasets()
    for dataset in datasets:
        print("Dataset: " + dataset.get_id())

    # Get dataset by id
    dataset_id = "DATASET_ID"
    dataset = querier.get_dataset(dataset_id)
    if dataset:
        print("Dataset: " + dataset.get_id())
    else:
        raise ValueError("Dataset not found")

    # get dataset_description
    metadata = dataset.get_metadata(metadata="dataset_description")
    print("dataset_description: " + str(metadata))

    # get subjects
    metadata = dataset.get_metadata(metadata="subjects")
    print("subjects: " + str(metadata))

    print("done")
