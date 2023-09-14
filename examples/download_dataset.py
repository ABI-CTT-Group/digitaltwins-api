from digitaltwins import Downloader

from pathlib import Path

if __name__ == '__main__':
    dataset_name = None
    config_file = Path(r"/path/to/configs.ini")

    downloader = Downloader(config_file)

    downloader.execute(dataset_name, save_dir="./tmp")

    print("done")
