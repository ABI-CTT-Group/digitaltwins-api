import sys
import io
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure the project root is on sys.path so `app` can be imported when running directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.main import app
from app.routers.auth import validate_credentials

app.dependency_overrides[validate_credentials] = lambda: True

client = TestClient(app)

def test_download_dataset():
    dataset_uuid = "87073f22-2ce1-11f1-b23b-4683f1ffa86d"
    
    print(f"\nDownloading dataset {dataset_uuid}...")
    
    response = client.get(f"/datasets/{dataset_uuid}/download")
    
    print("Download Status:", response.status_code)
    
    if response.status_code == 200:
        # Check if it's a valid ZIP file
        try:
            zip_data = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_data, 'r') as zf:
                files = zf.namelist()
                print(f"Successfully downloaded and decoded ZIP archive.")
                print(f"Archive contains {len(files)} files.")
        except zipfile.BadZipFile:
            print("Error: The downloaded content is not a valid ZIP file.")
    else:
        try:
            print("Response:", response.json())
        except Exception:
            print("Response text:", response.text)
    
    if response.status_code == 200:
        # Save the file to disk
        output_file = Path(__file__).resolve().parents[1] / "data" / f"{dataset_uuid}.zip"
        
        # Ensure the parent directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "wb") as f:
            f.write(response.content)
            
        print(f"File successfully saved to: {output_file}")

        

if __name__ == "__main__":
    test_download_dataset()
