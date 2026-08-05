import os
import sys
import zipfile
import io
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the project root is on sys.path so `app` can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.routers.auth import validate_credentials

# Bypass authentication
app.dependency_overrides[validate_credentials] = lambda: True

client = TestClient(app)

def test_download_workspace_dataset():
    """Test the GET /assays/{assay_id}/workspace/dataset/download endpoint."""
    with patch("digitaltwins.minio.downloader.Downloader") as MockMinioDownloader:
        mock_downloader = MagicMock()
        MockMinioDownloader.return_value = mock_downloader
        
        # Setup mock for get_latest_timestamp_folder
        mock_downloader.get_latest_timestamp_folder.return_value = "20260805_131413"
        
        # Setup mock for download_folder to simulate downloading files
        def mock_download_folder(bucket, prefix, save_dir):
            # Create a dummy file in the save_dir to be zipped
            dummy_file = os.path.join(save_dir, "test.txt")
            os.makedirs(os.path.dirname(dummy_file), exist_ok=True)
            with open(dummy_file, "w") as f:
                f.write("dummy content")
            return 1
            
        mock_downloader.download_folder.side_effect = mock_download_folder
        
        response = client.get("/assays/1/workspace/dataset/download")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "assay_1_20260805_131413.zip" in response.headers["content-disposition"]
        
        # Verify the ZIP contains the dummy file
        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data, "r") as zf:
            assert "test.txt" in zf.namelist()
            with zf.open("test.txt") as f:
                assert f.read() == b"dummy content"
                
        mock_downloader.get_latest_timestamp_folder.assert_called_once_with("airflow-workspace", "assay_1/")
        mock_downloader.download_folder.assert_called_once()
