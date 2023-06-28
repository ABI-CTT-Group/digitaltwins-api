from pathlib import Path
from dtp.gen3.convertor import Gen3Convertor

if __name__ == '__main__':
    project = "gen3_project_name"
    experiment = "experiment_name"
    source_dir = Path(r"/path/to/dataset_dir")
    dest_dir = Path(r"/path/to/output/ge3/metadata/folder")
    sds_schema_dir = Path(r"/path/to/sds/dictionary/folder")

    convertor = Gen3Convertor(project=project, experiment=experiment, version="2.0.0")
    convertor.set_schema_dir(sds_schema_dir)
    convertor.execute(source_dir=source_dir, dest_dir=dest_dir,)
