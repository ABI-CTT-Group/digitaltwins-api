from dtp.core.downloader import Downloader

if __name__ == '__main__':
    data_storage_config = "../configs/templates/pacs.json"
    gen3_config = "../configs/templates/gen3.json"
    dataset_id = None
    dest = "./"

    downloader = Downloader(data_storage_config=data_storage_config)
    downloader.download_dataset(dataset_id=dataset_id, dest=dest)