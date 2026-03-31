"""MinIO deletion operations for datasets."""

import os
import logging

import boto3
from botocore.exceptions import ClientError

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Deleter(object):
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

    def delete_dataset_objects(self, dataset_uuid: str) -> int:
        """Delete all objects associated with *dataset_uuid* across all buckets.

        Objects are identified by the key prefix ``<dataset_uuid>/``.

        Returns:
            The total number of objects deleted.

        Raises:
            RuntimeError: If any deletion call fails.
        """
        total_deleted = 0
        try:
            buckets = self.s3_client.list_buckets().get("Buckets", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to list MinIO buckets: {e}") from e

        prefix = f"{dataset_uuid}/"

        for bucket in buckets:
            bucket_name = bucket["Name"]
            try:
                objects_to_delete = []
                paginator = self.s3_client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                    for obj in page.get("Contents", []):
                        objects_to_delete.append({"Key": obj["Key"]})

                if not objects_to_delete:
                    continue

                # delete_objects accepts up to 1000 keys per call
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i : i + 1000]
                    resp = self.s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={"Objects": batch, "Quiet": True},
                    )
                    errors = resp.get("Errors", [])
                    if errors:
                        raise RuntimeError(
                            f"Failed to delete objects in bucket '{bucket_name}': {errors}"
                        )
                    total_deleted += len(batch)

                logger.info(
                    "Deleted %d object(s) from bucket '%s' for dataset %s",
                    len(objects_to_delete), bucket_name, dataset_uuid,
                )
            except ClientError as e:
                raise RuntimeError(
                    f"Error processing bucket '{bucket_name}': {e}"
                ) from e

        logger.info("Total objects deleted for dataset %s: %d", dataset_uuid, total_deleted)
        return total_deleted
