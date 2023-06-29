from dtp.gen3.auth import Auth
from dtp.gen3.queryer import Queryer
from dtp.gen3.exporter import Exporter

from dtp.utils.config_loader import ConfigLoader

if __name__ == '__main__':
    config_file = "../configs/templates/gen3.json"
    dataset_id = None
    save_path = "./metadata.json"

    config_loader = ConfigLoader()
    configs = config_loader.load_from_json(config_file)
    endpoint = configs.get("gen3_endpoint")
    cred_file = config_file.get("gen3_cred_file")

    auth = Auth(endpoint, cred_file)
    queryer = Queryer(auth)

    programs = queryer.get_programs()
    print("Programs:" + str(programs))

    projects = queryer.get_projects(programs[0])
    print("Projects:" + str(projects))

    experiments = queryer.get_node_records("experiment", programs[0], projects[0])
    print(experiments)

    subjects = queryer.get_node_records("case", programs[0], projects[0])
    print(subjects)

    print("GraphQL")
    # query_string = """
    #         { project(first:0) { code } }
    #     """
    # query_string = """
    #         { project{ name } }
    #     """
    query_string = """
        { 
            experiment (submitter_id: "%s")
                { 
                    submitter_id 
                }
        }
    """ % dataset_id

    results = queryer.graphql_query(query_string)
    print(results)

    # Save
    exporter = Exporter(auth)
    exporter.save(results, "json", path=save_path)