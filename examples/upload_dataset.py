from digitaltwins import Uploader
from pathlib import Path

if __name__ == '__main__':
    dataset_dir = Path(r"DATASET_DIR")

    uploader = Uploader(Path(r"config.ini"))

    uploader.execute(dataset_dir=dataset_dir)
    print("done")
