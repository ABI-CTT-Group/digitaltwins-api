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
from app.routers.dependencies import get_querier

# Bypass authentication
app.dependency_overrides[validate_credentials] = lambda: {"username": "testuser"}

client = TestClient(app)

def test_download_workspace_dataset_airflow():
    """Test the GET /assays/{assay_id}/workspace/dataset/download endpoint for airflow."""
    mock_querier = MagicMock()
    mock_querier.get_assay.return_value = {"attributes": {"tags": ["script"]}}
    app.dependency_overrides[get_querier] = lambda: mock_querier

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
        assert 'filename="assay_1_results_20260805_131413.zip"' in response.headers["content-disposition"]
        
        # Verify the ZIP contains the dummy file
        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data, "r") as zf:
            assert "test.txt" in zf.namelist()
            with zf.open("test.txt") as f:
                assert f.read() == b"dummy content"
                
        mock_downloader.get_latest_timestamp_folder.assert_called_once_with("airflow-workspace", "assay_1/")
        mock_downloader.download_folder.assert_called_once()
        mock_querier.get_assay.assert_called_once_with(1, get_configs=False)

def test_download_workspace_dataset_jupyter():
    """Test the GET /assays/{assay_id}/workspace/dataset/download endpoint for jupyter."""
    mock_querier = MagicMock()
    mock_querier.get_assay.return_value = {"attributes": {"tags": ["notebook"]}}
    app.dependency_overrides[get_querier] = lambda: mock_querier

    with patch("app.routers.assays._download_jupyter_folder") as mock_download_jupyter_folder:
        # Setup mock for download_folder to simulate downloading files
        def mock_download_jupyter(username, remote_path, save_dir):
            # Create a dummy file in the save_dir to be zipped
            dummy_file = os.path.join(save_dir, "test_jupyter.txt")
            os.makedirs(os.path.dirname(dummy_file), exist_ok=True)
            with open(dummy_file, "w") as f:
                f.write("dummy jupyter content")
            
        mock_download_jupyter_folder.side_effect = mock_download_jupyter
        
        response = client.get("/assays/2/workspace/dataset/download")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert 'filename="assay_2_results.zip"' in response.headers["content-disposition"]
        
        # Verify the ZIP contains the dummy file
        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data, "r") as zf:
            assert "test_jupyter.txt" in zf.namelist()
            with zf.open("test_jupyter.txt") as f:
                assert f.read() == b"dummy jupyter content"
                
        mock_download_jupyter_folder.assert_called_once_with("testuser", "assay_2/outputs/datasets", mock_download_jupyter_folder.call_args[0][2])
        mock_querier.get_assay.assert_called_once_with(2, get_configs=False)
