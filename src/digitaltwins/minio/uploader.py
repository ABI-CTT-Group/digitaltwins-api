import os
import boto3
from botocore.exceptions import ClientError

from dotenv import load_dotenv
load_dotenv(".env")

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class Uploader(object):
    def __init__(self):
        self._endpoint = os.getenv("MINIO_ENDPOINT")
        self._access_key = os.getenv("MINIO_SERVER_ACCESS_KEY")
        self._secret_key = os.getenv("MINIO_SERVER_SECRET_KEY")

        missing_vars = [
            name
            for name, value in [
                ("MINIO_ENDPOINT", self._endpoint),
                ("MINIO_SERVER_ACCESS_KEY", self._access_key),
                ("MINIO_SERVER_SECRET_KEY", self._secret_key),
            ]
            if not value
        ]
        
        if missing_vars:
            raise ValueError(
                "Missing required environment variables for MinIO connection: "
                + ", ".join(missing_vars)
            )

        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self._endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key
            )
            logging.info(f"Connected to MinIO at {self._endpoint}")
        except Exception as e:
            logging.error(f"Failed to initialize MinIO client: {e}")
            raise

    def bucket_exists(self, bucket_name: str = None) -> bool:
        """
        Checks if a specific bucket exists on the MinIO server.

        :param bucket_name: The name of the bucket to check. Defaults to the initialized bucket.
        :return: True if the bucket exists, False otherwise.
        """
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            logging.info(f"Bucket '{bucket_name}' exists.")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == '404':
                logging.info(f"Bucket '{bucket_name}' does not exist.")
                return False
            elif error_code == '403':
                logging.warning(f"Bucket '{bucket_name}' exists, but you do not have permission to access it.")
                return True # It exists, but access is denied
            else:
                logging.error(f"An unexpected error occurred: {e}")
                raise

    def upload_file(self, file_path: str, bucket_name: str, object_name: str = None, overwrite: bool = False) -> bool:
        """
        Uploads a single file to a MinIO bucket.
        """
        if object_name is None:
            object_name = os.path.basename(file_path)

        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            return False

        if not overwrite:
            try:
                self.s3_client.head_object(Bucket=bucket_name, Key=object_name)
                logging.warning(f"File '{object_name}' already exists in bucket '{bucket_name}'. Skipping upload.")
                return False
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    pass  # File does not exist, proceed with upload
                else:
                    logging.error(f"Error checking if object exists: {e}")
                    return False

        try:
            self.s3_client.upload_file(file_path, bucket_name, object_name)
            logging.info(f"Successfully uploaded {file_path} to {bucket_name}/{object_name}")
            return True
        except ClientError as e:
            logging.error(f"Failed to upload {file_path}: {e}")
            return False

    def upload_folder(self, folder_path: str, bucket_name: str, prefix: str = "", overwrite: bool = False) -> bool:
        """
        Uploads a folder to a MinIO bucket.
        """
        if not os.path.isdir(folder_path):
            logging.error(f"Folder not found: {folder_path}")
            return False

        success = True
        for root, _, files in os.walk(folder_path):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, folder_path)
                
                object_name = relative_path.replace(os.path.sep, '/')
                if prefix:
                    object_name = f"{prefix.rstrip('/')}/{object_name}"
                    
                if not self.upload_file(local_path, bucket_name, object_name, overwrite=overwrite):
                    success = False
                    
        return success

        