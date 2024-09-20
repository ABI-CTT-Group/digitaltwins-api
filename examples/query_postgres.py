from pathlib import Path

from digitaltwins import QuerierFactory

if __name__ == '__main__':
    config_file = Path(r"/path/to/configs.ini")

    querier = QuerierFactory().create(config_file)

    programs = querier.get_programs()
    print("programs: " + str(programs))

    projects = querier.get_projects()
    print("projects: " + str(projects))

    datasets = querier.get_datasets()
    print("All datasets: " + str(datasets))

    print("--------Query by category--------")
    datasets = querier.get_datasets(categories=["measurement"])
    print("measurement datasets: " + str(datasets))

    datasets = querier.get_datasets(categories=["workflow"])
    print("workflow datasets: " + str(datasets))

    datasets = querier.get_datasets(categories=["tool"])
    print("tool datasets: " + str(datasets))

    datasets = querier.get_datasets(categories=["model"])
    print("model datasets: " + str(datasets))

    datasets = querier.get_datasets(categories=["measurement", "workflow"])
    print("measurement & workflow datasets: " + str(datasets))
