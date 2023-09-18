from digitaltwins import Uploader
from pathlib import Path

if __name__ == '__main__':
    dataset_dir = Path(r"/path/to/dataset_dir")

    uploader = Uploader(Path(r"/path/to/configs.ini"))

    uploader.upload(dataset_dir=dataset_dir)
    print("done")
