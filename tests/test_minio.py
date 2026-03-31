from pathlib import Path
from digitaltwins.minio.uploader import Uploader
from digitaltwins.minio.deleter import Deleter

SCRIPT_DIR = Path(__file__).resolve().parent

def test_upload():
    bucket_name = "measurements"

    uploader = Uploader()
    uploader.bucket_exists(bucket_name)

    # Upload a file
    test_file = SCRIPT_DIR / "data/test.txt"
    uploader.upload_file(str(test_file), bucket_name, test_file.name, overwrite=False)

    # Upload a folder
    test_folder = SCRIPT_DIR / "data/test_folder"
    uploader.upload_folder(str(test_folder), bucket_name, test_folder.name, overwrite=False)


def test_delete_bucket():
    bucket_name = "test"

    deleter = Deleter()
    resp = deleter.delete_bucket(bucket_name)
    print(resp)


if __name__ == "__main__":
    test_upload()
    test_delete_bucket()
