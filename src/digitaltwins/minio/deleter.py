"""MinIO deletion operations for datasets."""

import os
import logging

import boto3
from botocore.exceptions import ClientError, ConnectionClosedError, EndpointConnectionError

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

    def delete_bucket(self, bucket_name: str) -> dict:
        """Delete a bucket only when it exists and is empty.

        Returns a structured response with status values:
        ``success``, ``not_found``, ``not_empty``, ``permission_denied``,
        or ``connection_error``.
        """

        def _result(status: str, deleted: bool, message: str, error_code: str | None = None) -> dict:
            payload = {
                "bucket_name": bucket_name,
                "status": status,
                "deleted": deleted,
                "message": message,
            }
            if error_code:
                payload["error_code"] = error_code
            return payload

        if not bucket_name:
            return _result("invalid_request", False, "Bucket name must be provided")

        # 1) Check that the bucket exists and is accessible.
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
        except (EndpointConnectionError, ConnectionClosedError) as e:
            logger.error("Connection error while checking bucket '%s': %s", bucket_name, e)
            return _result("connection_error", False, "Unable to reach MinIO endpoint")
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in {"404", "NoSuchBucket", "NotFound"}:
                return _result("not_found", False, f"Bucket '{bucket_name}' does not exist", code)
            if code in {"403", "AccessDenied", "AllAccessDisabled"}:
                return _result("permission_denied", False, f"Access denied for bucket '{bucket_name}'", code)
            if code in {"RequestTimeout", "RequestTimeoutException", "NetworkingError"}:
                return _result("connection_error", False, "Network issue while checking bucket", code)
            raise RuntimeError(f"Failed to check bucket '{bucket_name}': {e}") from e

        # 2) Ensure bucket is empty before deleting.
        try:
            listing = self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            if listing.get("KeyCount", 0) > 0:
                return _result("not_empty", False, f"Bucket '{bucket_name}' is not empty")
        except (EndpointConnectionError, ConnectionClosedError) as e:
            logger.error("Connection error while listing bucket '%s': %s", bucket_name, e)
            return _result("connection_error", False, "Unable to reach MinIO endpoint")
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in {"403", "AccessDenied", "AllAccessDisabled"}:
                return _result("permission_denied", False, f"Access denied for bucket '{bucket_name}'", code)
            if code in {"404", "NoSuchBucket", "NotFound"}:
                return _result("not_found", False, f"Bucket '{bucket_name}' does not exist", code)
            if code in {"RequestTimeout", "RequestTimeoutException", "NetworkingError"}:
                return _result("connection_error", False, "Network issue while listing bucket", code)
            raise RuntimeError(f"Failed to inspect bucket '{bucket_name}': {e}") from e

        # 3) Delete empty bucket.
        try:
            self.s3_client.delete_bucket(Bucket=bucket_name)
            logger.info("Deleted empty bucket '%s'", bucket_name)
            return _result("success", True, f"Bucket '{bucket_name}' deleted")
        except (EndpointConnectionError, ConnectionClosedError) as e:
            logger.error("Connection error while deleting bucket '%s': %s", bucket_name, e)
            return _result("connection_error", False, "Unable to reach MinIO endpoint")
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in {"BucketNotEmpty"}:
                return _result("not_empty", False, f"Bucket '{bucket_name}' is not empty", code)
            if code in {"404", "NoSuchBucket", "NotFound"}:
                return _result("not_found", False, f"Bucket '{bucket_name}' does not exist", code)
            if code in {"403", "AccessDenied", "AllAccessDisabled"}:
                return _result("permission_denied", False, f"Access denied for bucket '{bucket_name}'", code)
            if code in {"RequestTimeout", "RequestTimeoutException", "NetworkingError"}:
                return _result("connection_error", False, "Network issue while deleting bucket", code)
            raise RuntimeError(f"Failed to delete bucket '{bucket_name}': {e}") from e

