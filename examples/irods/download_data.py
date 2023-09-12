from digitaltwins.irods.irods import IRODS

if __name__ == '__main__':
    config_file = "../../configs/templates/irods.json"
    irods = IRODS(config_file)
    save_dir = "./"
    irods.download(collection_name="dataset-12L_1-version-1", save_dir=save_dir)
