from digitaltwins.gen3.auth import Auth
from digitaltwins.gen3.metadata_exporter import MetadataExporter
from digitaltwins.utils.config_loader import ConfigLoader

if __name__ == '__main__':
    config_file = "../configs/templates/gen3.json"
    program = None
    project = None
    node_type = "experiment"
    uuid = None

    config_loader = ConfigLoader()
    configs = config_loader.load_from_json(config_file)
    endpoint = configs.get("gen3_endpoint")
    cred_file = configs.get("gen3_cred_file")
    auth = Auth(endpoint, cred_file)

    exporter = MetadataExporter(auth)

    experiments = exporter.export_node(program=program, project=project, node_type=node_type, fileformat="json", filename="metadata_node.json")
    print(experiments)

    output = exporter.export_record(program=program, project=project, uuid=uuid, fileformat="json", filename="metadata_uuid.json")
    print(output)
