"""Tests for the DELETE /datasets/{dataset_uuid} endpoint."""

import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `app` can be imported when running directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from app.main import app
from app.routers.auth import validate_credentials

# Bypass authentication for tests
app.dependency_overrides[validate_credentials] = lambda: True

client = TestClient(app)


def test_delete_nonexistent_dataset():
    """DELETEing a UUID that doesn't exist should return 404."""
    response = client.delete("/datasets/00000000-0000-0000-0000-000000000000")
    print("404 Status:", response.status_code)
    print("404 Response:", response.json())
    assert response.status_code == 404


def test_upload_then_delete():
    """Upload a dataset and then delete it; both should succeed."""
    dataset_dir = Path("/home/clin864/Projects/digitaltwins-api/tests/data/example_sds_dataset")
    if not dataset_dir.exists():
        print("SKIP: example dataset not found at", dataset_dir)
        return

    # ── Upload ──
    files = []
    for filepath in dataset_dir.rglob("*"):
        if filepath.is_file():
            rel_path = filepath.relative_to(dataset_dir.parent)
            files.append(
                ("files", (str(rel_path), open(filepath, "rb"), "application/octet-stream"))
            )

    print(f"\nUploading {len(files)} files...")
    upload_resp = client.post("/upload/dataset", files=files, params={"category": "test-category"})
    print("Upload Status:", upload_resp.status_code)
    upload_data = upload_resp.json()
    print("Upload Response:", upload_data)
    assert upload_resp.status_code == 200

    dataset_uuid = upload_data["dataset_uuid"]

    # ── Delete ──
    print(f"\nDeleting dataset {dataset_uuid}...")
    delete_resp = client.delete(f"/datasets/{dataset_uuid}")
    print("Delete Status:", delete_resp.status_code)
    print("Delete Response:", delete_resp.json())
    assert delete_resp.status_code == 200

    # ── Verify gone ──
    delete_again = client.delete(f"/datasets/{dataset_uuid}")
    print("Re-delete Status:", delete_again.status_code)
    assert delete_again.status_code == 404


def test_delete_existing_dataset():
    """Delete a dataset that already exists in the database.

    Set the DATASET_UUID environment variable before running, or enter it
    interactively when prompted::

        DATASET_UUID=<uuid> python tests/faskapi/test_delete_dataset.py
    """
    dataset_uuid = os.getenv("DATASET_UUID") or input("Enter dataset UUID to delete: ").strip()
    if not dataset_uuid:
        print("SKIP: no dataset UUID provided")
        return

    print(f"\nDeleting existing dataset {dataset_uuid}...")
    response = client.delete(f"/datasets/{dataset_uuid}")
    print("Status:", response.status_code)
    print("Response:", response.json())
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


if __name__ == "__main__":
    test_delete_nonexistent_dataset()
    test_delete_existing_dataset()
    # test_upload_then_delete()
