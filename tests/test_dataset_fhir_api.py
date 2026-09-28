"""FHIR push job + /datasets/{uuid}/fhir/* and /files/* on committed datasets.

HAPI FHIR is replaced by an in-memory fake; Postgres and MinIO are real
(scratch database / bucket).
"""
import os
import shutil
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app
from app.routers import auth, dataset_uploads
from digitaltwins.measurements import jobs, pipeline, sessions
from digitaltwins.measurements.fhir_service import compute_endpoint_urls
from digitaltwins.measurements.staging import dataset_dir, staging_root
from digitaltwins.measurements.tree import build_tree

FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"
UPLOADER = {"username": "alice", "token": "t", "claims": {"realm_access": {"roles": ["researcher"]}}}
PUBLIC = "https://platform.example/digitaltwins-api"


@pytest.fixture
def env(platform_db, minio_bucket, tmp_path, monkeypatch, hapi):
    monkeypatch.setenv("DATASET_STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("DIGITALTWINS_API_PUBLIC_URL", PUBLIC)
    monkeypatch.setattr(dataset_uploads, "INGEST_CATEGORIES", {minio_bucket})
    return {"db": platform_db, "bucket": minio_bucket, "hapi": hapi}


def _committed(env, fhir_mode="auto"):
    """A committed dataset via the real session + commit job; returns (upload_id, dataset_uuid)."""
    conn = env["db"]()
    upload_id = sessions.create_session(conn, category=env["bucket"], name="example", description=None,
                                        source_kind="folder", commit_mode="on_finalize", fhir_mode=fhir_mode)
    shutil.copytree(FIXTURE, dataset_dir(upload_id))
    sessions.update_session(conn, upload_id, status="processing")
    jobs.run_commit_job(upload_id)
    return upload_id, sessions.get_session(conn, upload_id)["dataset_uuid"]


def _fhir_status(env, dataset_uuid):
    conn = env["db"]()
    with conn.cursor() as cur:
        cur.execute("SELECT fhir_status, fhir_failure_message FROM dataset WHERE dataset_uuid = %s", (dataset_uuid,))
        return cur.fetchone()


# ── Unit: endpoint URLs ────────────────────────────────────────────────


def test_endpoint_urls_point_at_the_api_file_endpoint(tmp_path):
    ds = tmp_path / "example"
    shutil.copytree(FIXTURE, ds)
    descriptions = build_tree(ds, "example")["descriptions"]
    descriptions["patients"][0]["documentReference"] = [
        {"samplePath": "sub-1/sam-1", "attachments": [{"title": "report.pdf", "url": ""}]}
    ]

    out = compute_endpoint_urls(descriptions, "d-uuid", PUBLIC + "/")

    base = f"{PUBLIC}/datasets/d-uuid/files/primary"
    study = out["patients"][0]["imagingStudy"][0]
    assert study["endpointUrl"] == f"{base}/sub-1"
    assert study["series"][0]["endpointUrl"] == f"{base}/sub-1/sam-1"
    # The file lives in the sample folder (the portal pointed at the patient folder).
    assert out["patients"][0]["documentReference"][0]["attachments"][0]["url"] == f"{base}/sub-1/sam-1/report.pdf"


# ── Integration: push job ──────────────────────────────────────────────


@pytest.mark.integration
def test_push_job_builds_stores_and_pushes_fhir(env, s3):
    upload_id, dataset_uuid = _committed(env)
    assert _fhir_status(env, dataset_uuid) == ("pending", None)

    jobs.run_fhir_push_job(dataset_uuid)

    assert _fhir_status(env, dataset_uuid) == ("completed", None)
    pushed = env["hapi"].pushed
    assert pushed["dataset"]["uuid"] == dataset_uuid
    series = pushed["patients"][0]["imagingStudy"][0]["series"][0]
    assert series["endpointUrl"].startswith(f"{PUBLIC}/datasets/{dataset_uuid}/files/primary/sub-1/")
    assert s3.head_object(Bucket=env["bucket"], Key=f"{dataset_uuid}/fhir.json")["ContentLength"] > 0
    assert not dataset_dir(upload_id).exists()  # cache released after a successful push


@pytest.mark.integration
def test_repush_replaces_the_previous_resources(env):
    # digitaltwins-on-fhir keeps a resource whose identifier already exists, so an
    # edited annotation only reaches FHIR if the previous graph is removed first.
    _, dataset_uuid = _committed(env)
    jobs.run_fhir_push_job(dataset_uuid)
    assert env["hapi"].types() == {"Composition": 2, "Consent": 2, "Endpoint": 8, "ImagingStudy": 4, "Patient": 2, "ResearchSubject": 2}
    conn = env["db"]()
    annotation = pipeline.load_annotation(conn, dataset_uuid)
    annotation["patients"][0]["imagingStudy"][0]["description"] = "edited"
    pipeline.save_annotation(conn, dataset_uuid, annotation)

    jobs.run_fhir_push_job(dataset_uuid)

    assert env["hapi"].types() == {"Composition": 2, "Consent": 2, "Endpoint": 8, "ImagingStudy": 4, "Patient": 2, "ResearchSubject": 2}  # replaced, not duplicated
    descriptions = [r.get("description") for r in env["hapi"].store.values() if r["resourceType"] == "ImagingStudy"]
    assert "edited" in descriptions


@pytest.mark.integration
def test_failed_push_keeps_the_dataset_and_can_be_retried(env):
    upload_id, dataset_uuid = _committed(env)
    env["hapi"].fail_push = True

    jobs.run_fhir_push_job(dataset_uuid)  # never raises

    status, message = _fhir_status(env, dataset_uuid)
    assert status == "failed" and "HAPI FHIR unreachable" in message
    assert dataset_dir(upload_id).is_dir()  # cache kept for the retry

    env["hapi"].fail_push = False
    jobs.run_fhir_push_job(dataset_uuid)
    assert _fhir_status(env, dataset_uuid) == ("completed", None)


@pytest.mark.integration
def test_push_redownloads_the_dataset_when_the_cache_is_gone(env):
    upload_id, dataset_uuid = _committed(env)
    shutil.rmtree(dataset_dir(upload_id))

    jobs.run_fhir_push_job(dataset_uuid)

    assert _fhir_status(env, dataset_uuid) == ("completed", None)
    assert env["hapi"].pushed["patients"][0]["imagingStudy"][0]["series"][0]["uid"]


@pytest.mark.integration
def test_push_without_an_annotation_fails_cleanly(env):
    _, dataset_uuid = _committed(env, fhir_mode="none")

    jobs.run_fhir_push_job(dataset_uuid)

    status, message = _fhir_status(env, dataset_uuid)
    assert status == "failed" and "annotation" in message


@pytest.mark.integration
def test_stale_caches_are_swept_but_staged_datasets_are_kept(env):
    conn = env["db"]()
    committed, _ = _committed(env, fhir_mode="none")
    staged = sessions.create_session(conn, category=env["bucket"], name="s", description=None,
                                     source_kind="folder", commit_mode="on_approve")
    shutil.copytree(FIXTURE, dataset_dir(staged))
    sessions.update_session(conn, staged, status="staged")
    downloaded = staging_root() / "downloads" / "some-uuid"
    downloaded.mkdir(parents=True)
    old = time.time() - 8 * 86400
    for path in (dataset_dir(committed), dataset_dir(staged), downloaded):
        os.utime(path, (old, old))

    jobs.sweep_stale_caches(conn, max_age_days=7)

    assert not dataset_dir(committed).exists()
    assert not downloaded.exists()
    assert dataset_dir(staged).is_dir()


# ── Integration: endpoints ─────────────────────────────────────────────


@pytest.fixture
def client(env):
    app = create_app()
    app.dependency_overrides[auth.validate_credentials] = lambda: UPLOADER
    return TestClient(app)


@pytest.mark.integration
def test_finalize_with_auto_fhir_commits_then_pushes(env, client):
    rel_files = [(f"example/{p.relative_to(FIXTURE).as_posix()}", p.read_bytes())
                 for p in sorted(FIXTURE.rglob("*")) if p.is_file()]
    r = client.post("/datasets/uploads", json={
        "name": "example", "category": env["bucket"], "source_kind": "folder", "fhir": "auto",
        "manifest": [{"rel_path": rel, "size": len(data), "parts": 1} for rel, data in rel_files],
    })
    upload_id = r.json()["upload_id"]
    for rel, data in rel_files:
        client.put(f"/datasets/uploads/{upload_id}/parts/{rel}", params={"n": 0, "of": 1}, content=data)

    assert client.post(f"/datasets/uploads/{upload_id}/finalize").status_code == 202

    dataset_uuid = client.get(f"/datasets/uploads/{upload_id}").json()["dataset_uuid"]
    assert _fhir_status(env, dataset_uuid) == ("completed", None)


@pytest.mark.integration
def test_tree_and_annotation_on_a_committed_dataset_carry_real_uuids(env, client):
    _, dataset_uuid = _committed(env, fhir_mode="none")

    descriptions = client.get(f"/datasets/{dataset_uuid}/fhir/tree").json()["descriptions"]
    assert descriptions["dataset"]["uuid"] == dataset_uuid
    assert all(p["uuid"] for p in descriptions["patients"])
    assert client.get(f"/datasets/{dataset_uuid}/fhir/annotation").status_code == 404

    subject_uuid = descriptions["patients"][0]["uuid"]
    descriptions["patients"][0]["uuid"] = "tampered"
    r = client.put(f"/datasets/{dataset_uuid}/fhir/annotation", json={"descriptions": descriptions})
    assert r.status_code == 200
    stored = client.get(f"/datasets/{dataset_uuid}/fhir/annotation").json()["descriptions"]
    assert stored["patients"][0]["uuid"] == subject_uuid  # server re-stamped it


@pytest.mark.integration
def test_annotation_with_unknown_sample_path_is_rejected(env, client):
    _, dataset_uuid = _committed(env, fhir_mode="none")
    descriptions = client.get(f"/datasets/{dataset_uuid}/fhir/tree").json()["descriptions"]
    descriptions["patients"][0]["imagingStudy"][0]["samplePath"] = "sub-1/sam-9"

    r = client.put(f"/datasets/{dataset_uuid}/fhir/annotation", json={"descriptions": descriptions})

    assert r.status_code == 400 and "sub-1/sam-9" in r.json()["detail"]


@pytest.mark.integration
def test_push_endpoint_queues_the_job_and_preview_serves_the_pushed_bundle(env, client):
    _, dataset_uuid = _committed(env)
    jobs.set_fhir_status(env["db"](), dataset_uuid, "none")  # annotation stored, never pushed

    assert client.post(f"/datasets/{dataset_uuid}/fhir/push").status_code == 202
    assert _fhir_status(env, dataset_uuid) == ("completed", None)
    preview = client.get(f"/datasets/{dataset_uuid}/fhir/preview").json()
    assert preview["patients"][0]["imagingStudy"][0]["series"][0]["endpointUrl"].startswith(PUBLIC)


@pytest.mark.integration
def test_push_endpoint_requires_an_annotation(env, client):
    _, dataset_uuid = _committed(env, fhir_mode="none")

    assert client.post(f"/datasets/{dataset_uuid}/fhir/push").status_code == 400


@pytest.mark.integration
def test_push_endpoint_rejects_a_push_already_in_flight(env, client):
    _, dataset_uuid = _committed(env)
    jobs.set_fhir_status(env["db"](), dataset_uuid, "pushing")

    assert client.post(f"/datasets/{dataset_uuid}/fhir/push").status_code == 409


@pytest.mark.integration
def test_file_endpoint_streams_objects_and_requires_a_token(env, client):
    _, dataset_uuid = _committed(env, fhir_mode="none")
    rel = "primary/sub-1/sam-1/1-001.dcm"

    r = client.get(f"/datasets/{dataset_uuid}/files/{rel}")
    assert r.status_code == 200 and r.content == (FIXTURE / rel).read_bytes()
    assert client.get(f"/datasets/{dataset_uuid}/files/primary/nope.dcm").status_code == 404

    client.app.dependency_overrides.pop(auth.validate_credentials)
    assert client.get(f"/datasets/{dataset_uuid}/files/{rel}").status_code == 401
