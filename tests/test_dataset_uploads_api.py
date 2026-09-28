"""/datasets/uploads: chunked upload sessions, staged annotation, approval, cancel."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app
from app.routers import auth, dataset_uploads
from digitaltwins.measurements import chunk_store as chunk_store_mod
from digitaltwins.measurements.staging import dataset_dir

FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"
FIXTURE_ZIP = Path(__file__).parent / "data" / "example_sds_dataset.zip"
UPLOADER = {"username": "alice", "token": "t", "claims": {"realm_access": {"roles": ["researcher"]}}}
VIEWER = {"username": "bob", "token": "t", "claims": {"realm_access": {"roles": ["viewer"]}}}


@pytest.fixture
def client(platform_db, minio_bucket, tmp_path, monkeypatch):
    monkeypatch.setenv("DATASET_STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setattr(dataset_uploads, "INGEST_CATEGORIES", {minio_bucket})
    app = create_app()
    app.dependency_overrides[auth.validate_credentials] = lambda: UPLOADER
    c = TestClient(app)
    c.bucket = minio_bucket
    c.db = platform_db
    return c


def _folder_manifest(root, prefix="example"):
    files = sorted(p for p in root.rglob("*") if p.is_file())
    return [(f"{prefix}/{p.relative_to(root).as_posix()}", p.read_bytes()) for p in files]


def _upload(client, files, source_kind="folder", **body):
    manifest = [{"rel_path": rel, "size": len(data), "parts": 1} for rel, data in files]
    r = client.post("/datasets/uploads", json={
        "name": "My dataset", "category": client.bucket, "source_kind": source_kind,
        "manifest": manifest, **body,
    })
    assert r.status_code == 200, r.text
    upload_id = r.json()["upload_id"]
    for rel, data in files:
        r = client.put(f"/datasets/uploads/{upload_id}/parts/{rel}", params={"n": 0, "of": 1}, content=data,
                       headers={"Content-Type": "application/octet-stream"})
        assert r.status_code == 200, r.text
    return upload_id


def _db_one(client, sql, params):
    conn = client.db()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


@pytest.mark.integration
def test_on_finalize_upload_commits_in_the_background(client):
    upload_id = _upload(client, _folder_manifest(FIXTURE))
    assert client.get(f"/datasets/uploads/{upload_id}").json()["upload"]["complete"] is True

    r = client.post(f"/datasets/uploads/{upload_id}/finalize")

    assert r.status_code == 202, r.text
    session = client.get(f"/datasets/uploads/{upload_id}").json()  # TestClient ran the background job
    assert session["status"] == "completed"
    assert _db_one(client, "SELECT dataset_name, fhir_status FROM dataset WHERE dataset_uuid = %s",
                   (session["dataset_uuid"],)) == ("My dataset", "none")


@pytest.mark.integration
def test_zip_upload_is_extracted_and_committed(client):
    upload_id = _upload(client, [("source.zip", FIXTURE_ZIP.read_bytes())], source_kind="zip")

    assert client.post(f"/datasets/uploads/{upload_id}/finalize").status_code == 202
    assert client.get(f"/datasets/uploads/{upload_id}").json()["status"] == "completed"


@pytest.mark.integration
def test_status_reports_missing_parts_and_finalize_refuses(client):
    data = b"x" * 10
    r = client.post("/datasets/uploads", json={
        "name": "n", "category": client.bucket, "source_kind": "folder",
        "manifest": [{"rel_path": "a.bin", "size": 10, "parts": 2}],
    })
    upload_id = r.json()["upload_id"]
    client.put(f"/datasets/uploads/{upload_id}/parts/a.bin", params={"n": 0, "of": 2}, content=data[:5])

    status = client.get(f"/datasets/uploads/{upload_id}").json()["upload"]
    assert status["files"][0]["received_parts"] == [0] and status["complete"] is False
    assert client.post(f"/datasets/uploads/{upload_id}/finalize").status_code == 400


@pytest.mark.integration
def test_invalid_dataset_fails_finalize_and_keeps_the_session_receiving(client):
    files = [("example/dataset_description.xlsx", (FIXTURE / "dataset_description.xlsx").read_bytes())]
    upload_id = _upload(client, files)

    r = client.post(f"/datasets/uploads/{upload_id}/finalize")

    assert r.status_code == 400 and "primary/" in r.json()["detail"]
    assert client.get(f"/datasets/uploads/{upload_id}").json()["status"] == "receiving"


@pytest.mark.integration
def test_on_approve_upload_stages_then_commits_with_the_draft(client):
    upload_id = _upload(client, _folder_manifest(FIXTURE), commit_mode="on_approve")

    r = client.post(f"/datasets/uploads/{upload_id}/finalize")
    assert r.status_code == 200 and r.json()["status"] == "staged"
    assert r.json()["warnings"] == []

    tree = client.get(f"/datasets/uploads/{upload_id}/fhir/tree").json()
    draft = tree["descriptions"]
    assert client.put(f"/datasets/uploads/{upload_id}/fhir/annotation", json={"descriptions": draft}).status_code == 200
    assert client.get(f"/datasets/uploads/{upload_id}/fhir/annotation").json()["descriptions"] == draft
    assert client.get(f"/datasets/uploads/{upload_id}/fhir/preview").status_code == 200
    assert not (dataset_dir(upload_id) / "fhir.json").exists()  # preview never writes into the dataset

    assert client.post(f"/datasets/uploads/{upload_id}/approve").status_code == 202
    session = client.get(f"/datasets/uploads/{upload_id}").json()
    assert session["status"] == "completed"
    [stored] = _db_one(client, "SELECT descriptions FROM dataset_fhir_annotation WHERE dataset_uuid = %s",
                       (session["dataset_uuid"],))
    assert stored["dataset"]["uuid"] == session["dataset_uuid"]
    assert all(p["uuid"] for p in stored["patients"])


@pytest.mark.integration
def test_annotation_with_unknown_sample_path_is_rejected(client):
    upload_id = _upload(client, _folder_manifest(FIXTURE), commit_mode="on_approve")
    client.post(f"/datasets/uploads/{upload_id}/finalize")
    draft = client.get(f"/datasets/uploads/{upload_id}/fhir/tree").json()["descriptions"]
    draft["patients"][0]["imagingStudy"][0]["samplePath"] = "sub-1/sam-9"

    r = client.put(f"/datasets/uploads/{upload_id}/fhir/annotation", json={"descriptions": draft})

    assert r.status_code == 400 and "sub-1/sam-9" in r.json()["detail"]


@pytest.mark.integration
def test_inline_descriptions_are_validated_at_finalize(client):
    draft = {"dataset": {"name": "x"}, "patients": [{"name": "sub-9", "observations": [],
                                                     "imagingStudy": [], "documentReference": []}]}
    upload_id = _upload(client, _folder_manifest(FIXTURE), fhir_descriptions=draft)

    r = client.post(f"/datasets/uploads/{upload_id}/finalize")

    assert r.status_code == 400 and "sub-9" in r.json()["detail"]


@pytest.mark.integration
def test_approve_requires_a_staged_or_failed_session(client):
    upload_id = _upload(client, _folder_manifest(FIXTURE), commit_mode="on_approve")

    assert client.post(f"/datasets/uploads/{upload_id}/approve").status_code == 409


@pytest.mark.integration
def test_cancel_removes_a_staged_session_and_its_files(client):
    upload_id = _upload(client, _folder_manifest(FIXTURE), commit_mode="on_approve")
    client.post(f"/datasets/uploads/{upload_id}/finalize")
    assert dataset_dir(upload_id).is_dir()

    assert client.delete(f"/datasets/uploads/{upload_id}").status_code == 200
    assert client.get(f"/datasets/uploads/{upload_id}").status_code == 404
    assert not dataset_dir(upload_id).exists()


@pytest.mark.integration
def test_list_shows_sessions_that_are_not_committed(client):
    staged = _upload(client, _folder_manifest(FIXTURE), commit_mode="on_approve")
    client.post(f"/datasets/uploads/{staged}/finalize")
    done = _upload(client, _folder_manifest(FIXTURE))
    client.post(f"/datasets/uploads/{done}/finalize")

    listed = {s["upload_id"]: s["status"] for s in client.get("/datasets/uploads").json()["uploads"]}

    assert listed == {staged: "staged"}


@pytest.mark.integration
def test_config_reports_part_size(client):
    assert client.get("/datasets/uploads/config").json()["max_part_size"] == chunk_store_mod.PART_SIZE


@pytest.mark.integration
def test_other_categories_are_rejected(client):
    r = client.post("/datasets/uploads", json={
        "name": "n", "category": "workflows", "source_kind": "folder",
        "manifest": [{"rel_path": "a", "size": 1, "parts": 1}],
    })
    assert r.status_code == 400


@pytest.mark.integration
def test_writes_require_an_upload_role(client):
    client.app.dependency_overrides[auth.validate_credentials] = lambda: VIEWER

    r = client.post("/datasets/uploads", json={
        "name": "n", "category": client.bucket, "source_kind": "folder",
        "manifest": [{"rel_path": "a", "size": 1, "parts": 1}],
    })

    assert r.status_code == 403
    assert client.get("/datasets/uploads").status_code == 200  # reads need only authentication
