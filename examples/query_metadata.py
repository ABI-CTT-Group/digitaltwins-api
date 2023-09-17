from digitaltwins import MetadataQuerier
from pathlib import Path
import configparser

if __name__ == '__main__':
    config_file = Path(r"/path/to/configs_ctt.ini")

    querier = MetadataQuerier(config_file)

    # # List programs
    programs = querier.get_programs_all()
    print("Programs: " + str(programs))
    #
    # # List projects
    configs = configparser.ConfigParser()
    configs.read(config_file)
    projects = querier.get_projects_by_program(program=configs["gen3"].get("program"))
    print("projects: " + str(projects))

    # List datasets
    datasets = querier.get_datasets()
    print("Datasets: " + str(datasets))

    # # List subjects
    dataset_id = ""
    subjects = querier.get_subjects(dataset_id=dataset_id)
    print("Subjects: " + str(subjects))

    # Get dataset descriptions
    dataset_id = ""
    dataset_descriptions = querier.get_dataset_descriptions(dataset_id=dataset_id)
    print("Dataset description: " + str(dataset_descriptions))

    print("done")
