import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the project root is on sys.path so `app` can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.routers.auth import validate_credentials
from app.routers.upload import get_uploader

# Bypass authentication
app.dependency_overrides[validate_credentials] = lambda: True

client = TestClient(app)

def test_upload_workspace_datasets():
    """Test the POST /assays/{assay_id}/workspace/dataset/upload endpoint."""
    mock_uploader = MagicMock()
    mock_uploader.upload_dataset.return_value = "mocked-uuid-1234"
    
    app.dependency_overrides[get_uploader] = lambda: mock_uploader
    
    with patch("app.routers.upload.querier") as mock_querier, \
         patch("digitaltwins.minio.downloader.Downloader") as MockMinioDownloader:
         
        # Mock querier to return some outputs
        mock_querier.get_assay.return_value = {
            "configs": {
                "outputs": [
                    {"dataset_name": "converted_dataset", "category": "models"}
                ]
            }
        }
        
        # Mock MinioDownloader
        mock_downloader = MagicMock()
        MockMinioDownloader.return_value = mock_downloader
        mock_downloader.get_latest_timestamp_folder.return_value = "20260805_131413"
        
        # Setup mock for download_folder to simulate creating folders to upload
        def mock_download_folder(bucket, prefix, save_dir):
            # The endpoint expects save_dir to contain dataset folders
            dataset_folder = os.path.join(save_dir, "converted_dataset")
            os.makedirs(dataset_folder, exist_ok=True)
            with open(os.path.join(dataset_folder, "test.txt"), "w") as f:
                f.write("dummy")
            
            # Add a second unmapped folder
            other_folder = os.path.join(save_dir, "other_data")
            os.makedirs(other_folder, exist_ok=True)
            return 2
            
        mock_downloader.download_folder.side_effect = mock_download_folder
        
        response = client.post("/assays/1/workspace/dataset/upload")
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully uploaded 2 datasets." in data["message"]
        assert len(data["datasets"]) == 2
        
        # Find the specific dataset in the response
        converted_ds = next(d for d in data["datasets"] if d["dataset_name"] == "converted_dataset")
        assert converted_ds["category"] == "models"
        assert converted_ds["dataset_uuid"] == "mocked-uuid-1234"
        
        other_ds = next(d for d in data["datasets"] if d["dataset_name"] == "other_data")
        assert other_ds["category"] == "workflows"  # Default category
        
        mock_querier.get_assay.assert_called_once_with(1, get_configs=True)
        assert mock_uploader.upload_dataset.call_count == 2
