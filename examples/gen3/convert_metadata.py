from pathlib import Path
from digitaltwins.gen3.metadata_convertor import MetadataConvertor

if __name__ == '__main__':
    project = "gen3_project_name"
    experiment = "experiment_name"
    source_dir = Path(r"/path/to/dataset_dir")
    dest_dir = Path(r"/path/to/output/ge3/metadata/folder")
    sds_schema_dir = Path(r"/path/to/sds/dictionary/folder")

    convertor = MetadataConvertor(project=project, experiment=experiment, schema_dir=sds_schema_dir, version="2.0.0")
    convertor.execute(source_dir=source_dir, dest_dir=dest_dir)
