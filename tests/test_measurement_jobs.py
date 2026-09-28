"""Upload-session state, the commit background job, and the startup sweep."""
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitaltwins.measurements import jobs, pipeline, sessions
from digitaltwins.measurements.staging import dataset_dir

FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"


@pytest.fixture
def staging(tmp_path, monkeypatch):
    monkeypatch.setenv("DATASET_STAGING_DIR", str(tmp_path / "staging"))
    return tmp_path / "staging"


def _staged_session(conn, bucket, fhir_mode="none", fhir_descriptions=None, name="My dataset"):
    upload_id = sessions.create_session(
        conn, category=bucket, name=name, description="d", source_kind="folder",
        commit_mode="on_finalize", fhir_mode=fhir_mode, fhir_descriptions=fhir_descriptions,
    )
    shutil.copytree(FIXTURE, dataset_dir(upload_id))
    sessions.update_session(conn, upload_id, status="processing")
    return upload_id


def _fetch_one(conn, sql, params):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


@pytest.mark.integration
def test_commit_job_completes_the_session_and_links_the_dataset(platform_db, minio_bucket, staging):
    conn = platform_db()
    upload_id = _staged_session(conn, minio_bucket)

    jobs.run_commit_job(upload_id)

    session = sessions.get_session(platform_db(), upload_id)
    assert session["status"] == "completed"
    assert session["failure_stage"] is None
    assert _fetch_one(conn, "SELECT dataset_name, category, fhir_status FROM dataset WHERE dataset_uuid = %s",
                      (session["dataset_uuid"],)) == ("My dataset", minio_bucket, "none")
    assert dataset_dir(upload_id).is_dir()  # kept as the local cache for FHIR build


@pytest.mark.integration
def test_commit_job_with_auto_fhir_stores_annotation_and_marks_fhir_pending(platform_db, minio_bucket, staging):
    conn = platform_db()
    upload_id = _staged_session(conn, minio_bucket, fhir_mode="auto")

    jobs.run_commit_job(upload_id)

    dataset_uuid = sessions.get_session(conn, upload_id)["dataset_uuid"]
    [descriptions] = _fetch_one(conn, "SELECT descriptions FROM dataset_fhir_annotation WHERE dataset_uuid = %s",
                                (dataset_uuid,))
    assert descriptions["dataset"]["uuid"] == dataset_uuid
    assert [p["name"] for p in descriptions["patients"]] == ["sub-1", "sub-2"]
    assert _fetch_one(conn, "SELECT fhir_status FROM dataset WHERE dataset_uuid = %s", (dataset_uuid,)) == ("pending",)


@pytest.mark.integration
def test_commit_job_that_raises_marks_the_session_failed(platform_db, staging, monkeypatch):
    conn = platform_db()
    upload_id = _staged_session(conn, "unused")

    def boom(*a, **k):
        raise RuntimeError("MinIO upload failed for dataset x")

    monkeypatch.setattr(pipeline, "commit_dataset", boom)
    jobs.run_commit_job(upload_id)  # must not raise: it runs as a background task

    session = sessions.get_session(conn, upload_id)
    assert (session["status"], session["failure_stage"]) == ("failed", "commit")
    assert "MinIO upload failed" in session["failure_message"]
    assert dataset_dir(upload_id).is_dir()  # kept so the session can be retried


@pytest.mark.integration
def test_sweep_fails_interrupted_jobs(platform_db):
    conn = platform_db()
    processing = sessions.create_session(conn, category="measurements", name="p", description=None,
                                         source_kind="folder", commit_mode="on_finalize")
    sessions.update_session(conn, processing, status="processing")
    staged = sessions.create_session(conn, category="measurements", name="s", description=None,
                                     source_kind="folder", commit_mode="on_approve")
    sessions.update_session(conn, staged, status="staged")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO dataset (category, fhir_status) VALUES ('measurements', 'pushing'), "
                    "('measurements', 'pending'), ('measurements', 'completed')")
    conn.commit()

    jobs.sweep_interrupted_jobs(conn)

    assert sessions.get_session(conn, processing)["status"] == "failed"
    assert sessions.get_session(conn, processing)["failure_message"] == "Interrupted by an API restart; retry."
    assert sessions.get_session(conn, staged)["status"] == "staged"
    with conn.cursor() as cur:
        cur.execute("SELECT fhir_status, count(*) FROM dataset GROUP BY 1 ORDER BY 1")
        assert cur.fetchall() == [("completed", 1), ("failed", 2)]


def test_startup_runs_the_sweep_after_migrations(monkeypatch):
    from app.main import create_app
    from digitaltwins.postgres import migrate

    calls = []
    monkeypatch.setenv("POSTGRES_ENABLED", "true")
    monkeypatch.setattr(migrate, "run", lambda: calls.append("migrate"))
    monkeypatch.setattr(jobs, "sweep_on_startup", lambda: calls.append("sweep"))
    with TestClient(create_app()):
        pass

    assert calls == ["migrate", "sweep"]
