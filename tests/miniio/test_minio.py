from pathlib import Path
from digitaltwins import MinIOUploader

if __name__ == "__main__":
    bucket_name = "measurements"
    test_file = Path("./tests/miniio/data/test.txt")

    uploader = MinIOUploader()
    uploader.bucket_exists(bucket_name)

    # Upload a file
    uploader.upload_file(str(test_file), bucket_name, test_file.name, overwrite=False)
    
    # Upload a folder
    test_folder = Path("./tests/miniio/data")
    uploader.upload_folder(str(test_folder), bucket_name, "test_folder", overwrite=False)
