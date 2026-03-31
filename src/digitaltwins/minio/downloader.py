"""MinIO download operations for datasets."""

import os
import logging

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectionClosedError

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Downloader(object):
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
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
            )
            logger.info("Connected to MinIO at %s", self._endpoint)
        except Exception as e:
            logger.error("Failed to initialise MinIO client: %s", e)
            raise

    def list_dataset_objects(self, dataset_uuid: str, bucket_name: str) -> list[str]:
        """List all object keys for a dataset in a specific bucket.

        Args:
            dataset_uuid: The UUID prefix to search for.
            bucket_name: The bucket to search in.

        Returns:
            A list of object key strings.

        Raises:
            FileNotFoundError: If no objects match the prefix.
            RuntimeError: If the bucket does not exist or a connection error occurs.
        """
        prefix = f"{dataset_uuid}/"
        keys = []

        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in {"404", "NoSuchBucket", "NotFound"}:
                raise FileNotFoundError(
                    f"Bucket '{bucket_name}' does not exist"
                ) from e
            raise RuntimeError(
                f"Error listing objects in bucket '{bucket_name}': {e}"
            ) from e
        except (EndpointConnectionError, ConnectionClosedError) as e:
            raise ConnectionError(
                f"Unable to reach MinIO endpoint: {e}"
            ) from e

        if not keys:
            raise FileNotFoundError(
                f"No objects found for dataset '{dataset_uuid}' in bucket '{bucket_name}'"
            )

        return keys

    def download_dataset(self, dataset_uuid: str, save_dir: str) -> int:
        """Download all objects for a dataset across all buckets.

        Searches every bucket for objects prefixed with ``<dataset_uuid>/``
        and downloads them to *save_dir*, preserving the key structure.

        Args:
            dataset_uuid: The dataset UUID to download.
            save_dir: Local directory to save downloaded files into.

        Returns:
            The total number of files downloaded.

        Raises:
            FileNotFoundError: If no objects are found for the dataset in any bucket.
            ConnectionError: If the MinIO endpoint is unreachable.
            RuntimeError: If a download operation fails.
        """
        prefix = f"{dataset_uuid}/"
        total_downloaded = 0

        try:
            buckets = self.s3_client.list_buckets().get("Buckets", [])
        except (EndpointConnectionError, ConnectionClosedError) as e:
            raise ConnectionError(
                f"Unable to reach MinIO endpoint: {e}"
            ) from e
        except ClientError as e:
            raise RuntimeError(f"Failed to list MinIO buckets: {e}") from e

        for bucket in buckets:
            bucket_name = bucket["Name"]
            try:
                paginator = self.s3_client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        local_path = os.path.join(save_dir, key)
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)

                        self.s3_client.download_file(bucket_name, key, local_path)
                        total_downloaded += 1
                        logger.debug("Downloaded %s/%s → %s", bucket_name, key, local_path)

            except (EndpointConnectionError, ConnectionClosedError) as e:
                raise ConnectionError(
                    f"Lost connection to MinIO while downloading from bucket '{bucket_name}': {e}"
                ) from e
            except ClientError as e:
                raise RuntimeError(
                    f"Error downloading from bucket '{bucket_name}': {e}"
                ) from e

        if total_downloaded == 0:
            raise FileNotFoundError(
                f"No objects found for dataset '{dataset_uuid}' in any bucket"
            )

        logger.info(
            "Downloaded %d file(s) for dataset %s to %s",
            total_downloaded, dataset_uuid, save_dir,
        )
        return total_downloaded
