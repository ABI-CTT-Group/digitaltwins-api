from ctp.irods_api.irods_api import IRODSAPI

if __name__ == '__main__':
    irods = IRODSAPI()
    save_dir = "./"
    irods.download_dataset(dataset="dataset-12L_1-version-1", save_dir=save_dir)
