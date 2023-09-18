from digitaltwins import Deleter

from pathlib import Path

if __name__ == '__main__':
    dataset_id = "DATASET_ID"
    config_file = Path(r"/path/to/configs.ini")

    deleter = Deleter(config_file)

    deleter.delete(dataset_id)

    print("done")
