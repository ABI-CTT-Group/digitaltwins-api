"""DELETE /datasets/{uuid} removes every trace: Postgres rows (incl. subject/sample), MinIO, HAPI, caches."""
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app
from app.routers import auth
from digitaltwins.measurements import jobs, sessions
from digitaltwins.measurements.staging import dataset_dir, staging_root

FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"
UPLOADER = {"username": "alice", "token": "t", "claims": {"realm_access": {"roles": ["admin"]}}}
VIEWER = {"username": "bob", "token": "t", "claims": {"realm_access": {"roles": []}}}


@pytest.fixture
def env(platform_db, minio_bucket, hapi, tmp_path, monkeypatch):
    monkeypatch.setenv("DATASET_STAGING_DIR", str(tmp_path / "staging"))
    app = create_app()
    app.dependency_overrides[auth.validate_credentials] = lambda: UPLOADER
    return {"db": platform_db, "bucket": minio_bucket, "hapi": hapi, "client": TestClient(app)}


def _committed(env, fhir_mode):
    conn = env["db"]()
    upload_id = sessions.create_session(conn, category=env["bucket"], name="example", description=None,
                                        source_kind="folder", commit_mode="on_finalize", fhir_mode=fhir_mode)
    shutil.copytree(FIXTURE, dataset_dir(upload_id))
    sessions.update_session(conn, upload_id, status="processing")
    jobs.run_commit_job(upload_id)
    return upload_id, sessions.get_session(conn, upload_id)["dataset_uuid"]


def _count(env, table):
    conn = env["db"]()
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table}")
        return cur.fetchone()[0]


def _objects(s3, bucket, prefix):
    return s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get("KeyCount", 0)


@pytest.mark.integration
def test_delete_removes_all_rows_objects_fhir_and_caches(env, s3):
    upload_id, dataset_uuid = _committed(env, fhir_mode="auto")
    jobs.run_fhir_push_job(dataset_uuid)
    downloaded = staging_root() / "downloads" / dataset_uuid
    downloaded.mkdir(parents=True)
    assert _objects(s3, env["bucket"], f"{dataset_uuid}/") > 0

    r = env["client"].delete(f"/datasets/{dataset_uuid}")

    assert r.status_code == 200, r.text
    assert r.json()["fhir_resources_deleted"] == {"Composition": 2, "Consent": 2, "Endpoint": 8, "ImagingStudy": 4, "Patient": 2, "ResearchSubject": 2}
    assert env["hapi"].store == {}
    for table in ("dataset", "dataset_mapping", "subject", "sample", "dataset_description",
                  "manifest", "dataset_fhir_annotation", "upload_session"):
        assert _count(env, table) == 0, table
    assert _objects(s3, env["bucket"], f"{dataset_uuid}/") == 0
    assert not dataset_dir(upload_id).exists() and not downloaded.exists()


@pytest.mark.integration
def test_delete_keeps_subjects_and_samples_of_other_datasets(env):
    _, first = _committed(env, fhir_mode="none")
    _, second = _committed(env, fhir_mode="none")

    assert env["client"].delete(f"/datasets/{first}").status_code == 200

    assert _count(env, "subject") == 2 and _count(env, "sample") == 4  # the second dataset's rows


@pytest.mark.integration
def test_delete_of_a_dataset_without_fhir_does_not_call_hapi(env):
    _, dataset_uuid = _committed(env, fhir_mode="none")

    r = env["client"].delete(f"/datasets/{dataset_uuid}")

    assert r.status_code == 200 and r.json()["fhir_resources_deleted"] == {}
    assert env["hapi"].calls == []


@pytest.mark.integration
def test_delete_requires_an_upload_role(env):
    _, dataset_uuid = _committed(env, fhir_mode="none")
    env["client"].app.dependency_overrides[auth.validate_credentials] = lambda: VIEWER

    assert env["client"].delete(f"/datasets/{dataset_uuid}").status_code == 403
    assert _count(env, "dataset") == 1


@pytest.mark.integration
def test_delete_of_an_unknown_dataset_is_404(env):
    assert env["client"].delete("/datasets/00000000-0000-0000-0000-000000000000").status_code == 404
