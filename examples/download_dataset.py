from dtp.cores.downloader import Downloader

if __name__ == '__main__':
    config_file = "../configs/templates/pacs.json"
    dataset_id = None
    dest = "./"

    downloader = Downloader(config_file)
    downloader.download_dataset(dataset_id=dataset_id, dest=dest)