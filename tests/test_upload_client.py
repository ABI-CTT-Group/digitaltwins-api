"""digitaltwins.UploadClient: chunked upload with resume, polling, one-time login."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app
from app.routers import auth, dataset_uploads
from digitaltwins import UploadClient
from digitaltwins.client import UploadError
from digitaltwins.measurements import pipeline

FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"
FIXTURE_ZIP = Path(__file__).parent / "data" / "example_sds_dataset.zip"
UPLOADER = {"username": "alice", "token": "t", "claims": {"realm_access": {"roles": ["researcher"]}}}


@pytest.fixture
def http(platform_db, minio_bucket, hapi, tmp_path, monkeypatch):
    monkeypatch.setenv("DATASET_STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setattr(dataset_uploads, "INGEST_CATEGORIES", {minio_bucket})
    app = create_app()
    app.dependency_overrides[auth.validate_credentials] = lambda: UPLOADER
    session = TestClient(app)
    session.bucket, session.db = minio_bucket, platform_db
    return session


def _client(http):
    return UploadClient("http://testserver", token="t", session=http, poll_interval=0)


def _dataset_name(http, dataset_uuid):
    with http.db().cursor() as cur:
        cur.execute("SELECT dataset_name FROM dataset WHERE dataset_uuid = %s", (dataset_uuid,))
        return cur.fetchone()[0]


@pytest.mark.integration
def test_uploads_a_folder_and_waits_for_the_commit(http):
    session = _client(http).upload_dataset(FIXTURE, category=http.bucket, name="From script")

    assert session["status"] == "completed"
    assert _dataset_name(http, session["dataset_uuid"]) == "From script"


@pytest.mark.integration
def test_uploads_a_zip(http):
    session = _client(http).upload_dataset(FIXTURE_ZIP, category=http.bucket)

    assert session["status"] == "completed"
    assert _dataset_name(http, session["dataset_uuid"]) == "example_sds_dataset"


@pytest.mark.integration
def test_auto_fhir_waits_for_the_push(http):
    session = _client(http).upload_dataset(FIXTURE, category=http.bucket, fhir="auto")

    assert session["fhir_status"] == "completed"


@pytest.mark.integration
def test_resume_sends_only_the_missing_parts(http, monkeypatch):
    client = _client(http)
    sent = []
    real_put = http.put

    def flaky_put(url, **kwargs):
        if len(sent) == 5:
            raise ConnectionError("network dropped")
        sent.append(url)
        return real_put(url, **kwargs)

    monkeypatch.setattr(http, "put", flaky_put)
    with pytest.raises(ConnectionError):
        client.upload_dataset(FIXTURE, category=http.bucket)
    upload_id = client.last_upload_id  # kept so an interrupted upload can be resumed
    assert upload_id == sent[0].split("/datasets/uploads/")[1].split("/")[0]
    monkeypatch.setattr(http, "put", lambda url, **kw: (sent.append(url), real_put(url, **kw))[1])

    session = client.resume(upload_id, FIXTURE)

    total_files = sum(1 for p in FIXTURE.rglob("*") if p.is_file())
    assert len(sent) == total_files  # 5 before the drop + only the rest after
    assert session["status"] == "completed"


@pytest.mark.integration
def test_a_failed_commit_raises_with_the_server_message(http, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("MinIO upload failed")

    monkeypatch.setattr(pipeline, "commit_dataset", boom)

    with pytest.raises(UploadError, match="MinIO upload failed"):
        _client(http).upload_dataset(FIXTURE, category=http.bucket)


class _RecordingSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))

        class _R:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"access_token": "issued-token", "token_type": "Bearer"}

        return _R()


def test_login_exchanges_credentials_once_and_uses_bearer_afterwards():
    session = _RecordingSession()

    client = UploadClient.login("https://platform.example/digitaltwins-api/", "alice", "<REDACTED>", session=session)

    [(method, url, kwargs)] = session.calls
    assert url == "https://platform.example/digitaltwins-api/login"
    assert kwargs["auth"] == ("alice", "<REDACTED>")
    assert client.headers == {"Authorization": "Bearer issued-token"}
