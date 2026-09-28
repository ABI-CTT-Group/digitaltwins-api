"""examples/upload_measurement_dataset.py: CLI wrapper around digitaltwins.UploadClient."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app
from app.routers import auth, dataset_uploads
from digitaltwins import UploadClient
from digitaltwins.measurements.tree import build_tree

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"
UPLOADER = {"username": "alice", "token": "t", "claims": {"realm_access": {"roles": ["researcher"]}}}

_spec = importlib.util.spec_from_file_location("upload_example", ROOT / "examples" / "upload_measurement_dataset.py")
example = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(example)


@pytest.fixture
def client(platform_db, minio_bucket, hapi, tmp_path, monkeypatch):
    monkeypatch.setenv("DATASET_STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setattr(dataset_uploads, "INGEST_CATEGORIES", {minio_bucket})
    app = create_app()
    app.dependency_overrides[auth.validate_credentials] = lambda: UPLOADER
    http = TestClient(app)
    c = UploadClient("http://testserver", token="t", session=http, poll_interval=0)
    c.bucket, c.http = minio_bucket, http
    return c


@pytest.mark.integration
def test_uploads_a_folder_and_reports_the_dataset(client, capsys):
    code = example.main([str(FIXTURE), "--category", client.bucket, "--fhir", "auto", "--name", "From example"],
                        client=client)

    out = capsys.readouterr().out
    assert code == 0
    assert "FHIR: completed" in out
    assert client.last_upload_id and any(len(w) == 36 for w in out.split())  # dataset UUID printed


@pytest.mark.integration
def test_uses_an_annotation_file(client, tmp_path, capsys):
    descriptions = tmp_path / "annotation.json"
    descriptions.write_text(json.dumps(build_tree(FIXTURE, "example")["descriptions"]))

    code = example.main([str(FIXTURE), "--category", client.bucket, "--descriptions", str(descriptions)],
                        client=client)

    assert code == 0 and "FHIR: completed" in capsys.readouterr().out


@pytest.mark.integration
def test_interrupted_upload_prints_how_to_resume_and_resume_finishes(client, monkeypatch, capsys):
    real_put, sent = client.http.put, []

    def flaky_put(url, **kwargs):
        if len(sent) == 3:
            raise ConnectionError("network dropped")
        sent.append(url)
        return real_put(url, **kwargs)

    monkeypatch.setattr(client.http, "put", flaky_put)
    assert example.main([str(FIXTURE), "--category", client.bucket], client=client) == 1
    err = capsys.readouterr().err
    assert f"--resume {client.last_upload_id}" in err

    monkeypatch.setattr(client.http, "put", real_put)
    assert example.main([str(FIXTURE), "--category", client.bucket, "--resume", client.last_upload_id],
                        client=client) == 0
    assert "Dataset UUID" in capsys.readouterr().out


def test_password_is_never_a_command_line_option():
    with pytest.raises(SystemExit):
        example.parse_args(["dataset", "--password", "secret"])
