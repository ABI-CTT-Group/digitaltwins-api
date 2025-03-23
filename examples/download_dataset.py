from digitaltwins import Downloader

from pathlib import Path

if __name__ == '__main__':
    dataset_id = None
    config_file = Path(r"/path/to/configs.ini")

    downloader = Downloader(config_file)

    downloader.download_dataset(dataset_id, save_dir="./logs")

    print("done")
