import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure the project root is on sys.path so `app` can be imported when running directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.main import app
from app.routers.auth import validate_credentials

app.dependency_overrides[validate_credentials] = lambda: True

client = TestClient(app)

SCRIPT_DIR = Path(__file__).resolve().parent

def test_upload(bucket_name, dataset_path):
    files = []
    for filepath in dataset_path.rglob("*"):
        if filepath.is_file():
            rel_path = filepath.relative_to(dataset_path.parent)
            files.append(
                ("files", (str(rel_path), open(filepath, "rb"), "application/octet-stream"))
            )
    
    print(f"Uploading {len(files)} files...")
    response = client.post("/dataset", files=files, params={"category": bucket_name})
    print("RAW Status:", response.status_code)
    try:
        print("RAW Response:", response.json())
    except Exception as e:
        print("RAW Response decode failed:", e, response.text)

def test_upload_zip(bucket_name, dataset_path):
    files = [
        ("files", (dataset_path.name, open(dataset_path, "rb"), "application/zip"))
    ]
    
    print(f"\nUploading zip file...")
    response = client.post("/dataset", files=files, params={"category": bucket_name})
    print("ZIP Status:", response.status_code)
    try:
        print("ZIP Response:", response.json())
    except Exception as e:
        print("ZIP Response decode failed:", e, response.text)

if __name__ == "__main__":
    dataset_path = SCRIPT_DIR / "tests/data/example_sds_dataset"
    test_upload(bucket_name="measurement", dataset_path=dataset_path)
    test_upload_zip(bucket_name="test", dataset_path=dataset_path)
