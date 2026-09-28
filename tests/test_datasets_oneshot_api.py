"""One-shot POST /datasets: streamed to disk, safe paths, measurements via the ingest pipeline."""
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app
from app.routers import auth, dataset_uploads

FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"
FIXTURE_ZIP = Path(__file__).parent / "data" / "example_sds_dataset.zip"
UPLOADER = {"username": "alice", "token": "t", "claims": {"realm_access": {"roles": ["admin"]}}}
VIEWER = {"username": "bob", "token": "t", "claims": {"realm_access": {"roles": []}}}


@pytest.fixture
def client(platform_db, minio_bucket, tmp_path, monkeypatch):
    monkeypatch.setenv("DATASET_STAGING_DIR", str(tmp_path / "staging"))
    app = create_app()
    app.dependency_overrides[auth.validate_credentials] = lambda: UPLOADER
    c = TestClient(app)
    c.bucket = minio_bucket
    c.db = platform_db
    c.monkeypatch = monkeypatch
    return c


def _as_measurements(client):
    client.monkeypatch.setattr(dataset_uploads, "INGEST_CATEGORIES", {client.bucket})


def _folder_parts(root=FIXTURE, prefix="example"):
    return [("files", (f"{prefix}/{p.relative_to(root).as_posix()}", p.read_bytes(), "application/octet-stream"))
            for p in sorted(root.rglob("*")) if p.is_file()]


def _post(client, files, **params):
    data = {}
    if "fhir_descriptions" in params:
        data["fhir_descriptions"] = json.dumps(params.pop("fhir_descriptions"))
    return client.post("/datasets", params={"category": client.bucket, **params}, files=files, data=data)


def _db_one(client, sql, params):
    conn = client.db()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


@pytest.mark.integration
def test_measurements_folder_upload_is_committed_through_the_pipeline(client):
    _as_measurements(client)

    r = _post(client, _folder_parts())

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fhir_status"] == "none"
    assert _db_one(client, "SELECT dataset_name FROM dataset WHERE dataset_uuid = %s",
                   (body["dataset_uuid"],)) == ("example",)
    assert _db_one(client, "SELECT status FROM upload_session WHERE dataset_uuid = %s",
                   (body["dataset_uuid"],)) == ("completed",)
    # Folder-derived + spreadsheet subjects: all four samples mapped.
    assert _db_one(client, "SELECT count(*) FROM dataset_mapping WHERE dataset_uuid = %s",
                   (body["dataset_uuid"],)) == (4,)


@pytest.mark.integration
def test_measurements_zip_upload(client):
    _as_measurements(client)

    r = _post(client, [("files", ("example_sds_dataset.zip", FIXTURE_ZIP.read_bytes(), "application/zip"))])

    assert r.status_code == 200, r.text
    assert _db_one(client, "SELECT dataset_name FROM dataset WHERE dataset_uuid = %s",
                   (r.json()["dataset_uuid"],)) == ("example_sds_dataset",)


@pytest.mark.integration
def test_inline_auto_fhir_stores_the_annotation_and_marks_fhir_pending(client, monkeypatch):
    _as_measurements(client)
    monkeypatch.setattr("digitaltwins.measurements.jobs.run_fhir_push_job", lambda *a: None, raising=False)

    r = _post(client, _folder_parts(), fhir="auto")

    assert r.status_code == 200, r.text
    assert r.json()["fhir_status"] == "pending"
    [descriptions] = _db_one(client, "SELECT descriptions FROM dataset_fhir_annotation WHERE dataset_uuid = %s",
                             (r.json()["dataset_uuid"],))
    assert descriptions["dataset"]["uuid"] == r.json()["dataset_uuid"]


@pytest.mark.integration
def test_inline_descriptions_that_do_not_match_folders_are_rejected(client):
    _as_measurements(client)
    bad = {"dataset": {}, "patients": [{"name": "sub-9"}]}

    r = _post(client, _folder_parts(), fhir_descriptions=bad)

    assert r.status_code == 400 and "sub-9" in r.json()["detail"]


@pytest.mark.integration
def test_measurements_without_primary_are_rejected(client):
    _as_measurements(client)
    parts = [("files", ("example/dataset_description.xlsx",
                        (FIXTURE / "dataset_description.xlsx").read_bytes(), "application/octet-stream"))]

    r = _post(client, parts)

    assert r.status_code == 400 and "primary/" in r.json()["detail"]


@pytest.mark.integration
def test_path_traversal_in_part_filenames_is_rejected(client, tmp_path):
    r = _post(client, [("files", ("../../escaped.txt", b"x", "text/plain"))])

    assert r.status_code == 400
    assert not (tmp_path / "escaped.txt").exists()


@pytest.mark.integration
def test_zip_slip_archives_are_rejected(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.txt", "x")

    r = _post(client, [("files", ("evil.zip", buf.getvalue(), "application/zip"))])

    assert r.status_code == 400


@pytest.mark.integration
def test_other_categories_keep_the_plain_uploader_path(client):
    # Not in INGEST_CATEGORIES: no SPARC validation, no upload session.
    r = _post(client, [("files", ("tool/readme.txt", b"hello", "text/plain"))])

    assert r.status_code == 200, r.text
    assert _db_one(client, "SELECT count(*) FROM upload_session", None) == (0,)
    assert _db_one(client, "SELECT category FROM dataset WHERE dataset_uuid = %s",
                   (r.json()["dataset_uuid"],)) == (client.bucket,)


@pytest.mark.integration
def test_upload_requires_an_upload_role(client):
    client.app.dependency_overrides[auth.validate_credentials] = lambda: VIEWER

    assert _post(client, _folder_parts()).status_code == 403
