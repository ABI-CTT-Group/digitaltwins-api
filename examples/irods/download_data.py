from dtp.irods.irods import IRODSAPI

if __name__ == '__main__':
    config_file = "../../configs/templates/irods.json"
    irods = IRODSAPI(config_file)
    save_dir = "./"
    irods.download_data(data="dataset-12L_1-version-1", save_dir=save_dir)
