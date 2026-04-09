import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from digitaltwins.postgres.uploader import Uploader

def main():
    script_dir = Path(__file__).resolve().parent
    assay_data_path = script_dir / "data" / "assay_data.json"
    
    with open(assay_data_path, "r") as f:
        assay_data = json.load(f)
    
    print("Testing Postgres connection and configure_assay...")
    
    uploader = Uploader()
    try:
        # First upload (insert)
        assay_uuid = uploader.configure_assay(assay_data)
        print(f"✅ Success! Uploaded assay. Generated UUID: {assay_uuid}")
        
        # Test update path using the generated UUID
        assay_data["assay_uuid"] = assay_uuid
        print(f"Testing update path for UUID: {assay_uuid}...")
        updated_uuid = uploader.configure_assay(assay_data)
        print(f"✅ Success! Updated assay. Returned UUID: {updated_uuid}")
        
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    main()
