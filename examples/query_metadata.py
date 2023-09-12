from digitaltwins import MetadataQuerier
from pathlib import Path
import configparser

if __name__ == '__main__':
    configs = configparser.ConfigParser()
    configs.read(Path(r"../configs/templates/config.ini"))

    querier = MetadataQuerier(Path(r"../configs/templates/config.ini"))

    # # List programs
    programs = querier.get_programs_all()
    print("Programs: " + str(programs))
    #
    # # List projects
    projects = querier.get_projects_by_program(program=configs["gen3"].get("program"))
    print("projects: " + str(projects))

    # List datasets
    datasets = querier.get_datasets()
    print("Datasets: " + str(datasets))

    # # List subjects
    subjects = querier.get_subjects(dataset_id=datasets[0].get("submitter_id"))
    print("Subjects: " + str(subjects))

    # Get dataset descriptions
    dataset_descriptions = querier.get_dataset_descriptions(dataset_id=datasets[0].get("submitter_id"))
    print("Dataset description: " + str(dataset_descriptions))

    print("done")
