from pathlib import Path
from digitaltwins.minio.uploader import Uploader
from digitaltwins.minio.deleter import Deleter
from digitaltwins.minio.downloader import Downloader

SCRIPT_DIR = Path(__file__).resolve().parent

def test_upload():
    bucket_name="measurement"
    prefix = None

    uploader = Uploader()
    uploader.bucket_exists(bucket_name)

    # Upload a file
    # test_file = SCRIPT_DIR / "data/test.txt"
    # uploader.upload_file(str(test_file), bucket_name, test_file.name, overwrite=False)

    # Upload a folder
    test_folder = SCRIPT_DIR / "./data/example_duke_sds"
    if prefix:
        prefix = prefix + "/" + test_folder.name
    else:
        prefix = test_folder.name
    uploader.upload_folder(str(test_folder), bucket_name, prefix, overwrite=False)


def test_delete_bucket():
    bucket_name=""
    deleter = Deleter()
    resp = deleter.delete_bucket(bucket_name)
    print(resp)


def test_download():
    # Use "test_folder" as the dataset_uuid since test_upload uploads it with that prefix
    dataset_uuid = "87073f22-2ce1-11f1-b23b-4683f1ffa86d"
    save_dir = str(SCRIPT_DIR / "data/download_test")

    downloader = Downloader()
    print(f"testing download for dataset '{dataset_uuid}'...")
    try:
        count = downloader.download_dataset(dataset_uuid, save_dir)
        print(f"Successfully downloaded {count} files to {save_dir}")
    except Exception as e:
        print(f"Download failed: {e}")




if __name__ == "__main__":
    test_upload()
    test_download()
    test_delete_bucket()
