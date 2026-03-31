from pathlib import Path
from fastapi.testclient import TestClient

# Ensure the project root is on sys.path so `app` can be imported when running directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.main import app
from app.routers.auth import validate_credentials

app.dependency_overrides[validate_credentials] = lambda: True

client = TestClient(app)

def test_upload_raw():
    dataset_dir = Path("/home/clin864/Projects/digitaltwins-api/resources/example_sds_dataset")
    
    files = []
    for filepath in dataset_dir.rglob("*"):
        if filepath.is_file():
            rel_path = filepath.relative_to(dataset_dir.parent)
            files.append(
                ("files", (str(rel_path), open(filepath, "rb"), "application/octet-stream"))
            )
    
    print(f"Uploading {len(files)} files...")
    response = client.post("/upload/dataset", files=files, params={"category": "test-category"})
    print("RAW Status:", response.status_code)
    try:
        print("RAW Response:", response.json())
    except Exception as e:
        print("RAW Response decode failed:", e, response.text)

def test_upload_zip():
    dataset_zip = Path("/home/clin864/Projects/digitaltwins-api/resources/example_sds_dataset.zip")
    
    files = [
        ("files", (dataset_zip.name, open(dataset_zip, "rb"), "application/zip"))
    ]
    
    print(f"\nUploading zip file...")
    response = client.post("/upload/dataset", files=files, params={"category": "test-category"})
    print("ZIP Status:", response.status_code)
    try:
        print("ZIP Response:", response.json())
    except Exception as e:
        print("ZIP Response decode failed:", e, response.text)

if __name__ == "__main__":
    test_upload_raw()
    test_upload_zip()
