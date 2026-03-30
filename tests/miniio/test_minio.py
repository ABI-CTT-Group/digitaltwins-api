from pathlib import Path
from digitaltwins.minio.uploader import Uploader

if __name__ == "__main__":
    bucket_name = "measurements"
    script_dir = Path(__file__).resolve().parent

    uploader = Uploader()
    uploader.bucket_exists(bucket_name)

    # Upload a file
    test_file = script_dir / "data/test.txt"
    uploader.upload_file(str(test_file), bucket_name, test_file.name, overwrite=False)

    # Upload a folder
    test_folder = script_dir / "data/test_folder"
    uploader.upload_folder(str(test_folder), bucket_name, test_folder.name, overwrite=False)