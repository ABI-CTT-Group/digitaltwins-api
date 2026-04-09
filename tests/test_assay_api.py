import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure the root directory is in sys.path so we can import 'app' and 'src' modules directly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

load_dotenv()

from fastapi.testclient import TestClient

# Must be imported after load_dotenv to get the DB connection string right
# and the app right.
from app.main import app

# To bypass the validate_credentials dependency.
# In `app/routers/auth.py`, let's see what it requires, or we can just override it using app.dependency_overrides
from app.routers.auth import validate_credentials

# Override the validate_credentials dependency to always return True for tests
app.dependency_overrides[validate_credentials] = lambda: True

client = TestClient(app)

def test_configure_assay():
    script_dir = Path(__file__).resolve().parent
    assay_data_path = script_dir / "data" / "assay_data.json"
    
    with open(assay_data_path, "r") as f:
        assay_data = json.load(f)
        
    print("Testing POST /assay endpoint...")
    
    # Send the first request (INSERT or UPDATE if it already exists)
    response = client.post("/assay", json=assay_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Response: {data}")
        assay_uuid = data.get("assay_uuid")
        
        if assay_uuid:
            # Let's perform a subsequent request (explicit UPDATE) to test the branch
            assay_data["assay_uuid"] = assay_uuid
            print(f"\nTesting implicit update branch with assay_uuid {assay_uuid}...")
            response_update = client.post("/assay", json=assay_data)
            
            if response_update.status_code == 200:
                print(f"✅ Update Success! Response: {response_update.json()}")
            else:
                print(f"❌ Update Failed: {response_update.status_code} - {response_update.text}")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_configure_assay()
