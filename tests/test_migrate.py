"""Tests for the numbered SQL migration runner (digitaltwins.postgres.migrate).

Unit tests need nothing. Integration tests (``-m integration``) need a reachable
Postgres (see conftest.py); each test runs in a throwaway database that is
dropped afterwards. They are skipped if Postgres is unreachable.
"""
import threading
from pathlib import Path

import psycopg2
import pytest

from conftest import load_baseline
from digitaltwins.postgres.migrate import MIGRATIONS_DIR, apply_migrations, discover


def _write(dir_: Path, name: str, sql: str) -> None:
    (dir_ / name).write_text(sql)


# ── Unit: discovery ────────────────────────────────────────────────────


def test_discover_sorts_by_version_and_ignores_other_files(tmp_path):
    _write(tmp_path, "0002_second.sql", "SELECT 1;")
    _write(tmp_path, "0001_first.sql", "SELECT 1;")
    _write(tmp_path, "README.md", "not a migration")
    _write(tmp_path, "draft.sql", "no version prefix")

    assert [v for v, _ in discover(tmp_path)] == ["0001", "0002"]


def test_discover_rejects_duplicate_versions(tmp_path):
    _write(tmp_path, "0001_a.sql", "SELECT 1;")
    _write(tmp_path, "0001_b.sql", "SELECT 1;")

    with pytest.raises(ValueError, match="0001"):
        discover(tmp_path)


def test_shipped_migrations_are_discoverable():
    versions = [v for v, _ in discover(MIGRATIONS_DIR)]
    assert versions[0] == "0001"


# ── Integration: applying ──────────────────────────────────────────────


def _fetch(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.commit()
    return rows


def _applied(conn):
    return [r[0] for r in _fetch(conn, "SELECT version FROM schema_migrations ORDER BY version")]


def _table_exists(conn, table):
    return _fetch(conn, "SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",))[0][0]


@pytest.mark.integration
def test_applies_pending_migrations_in_order(scratch_db, tmp_path):
    _write(tmp_path, "0001_create.sql", "CREATE TABLE t1 (id int);")
    _write(tmp_path, "0002_alter.sql", "ALTER TABLE t1 ADD COLUMN name text;")
    conn = scratch_db()

    assert apply_migrations(conn, tmp_path) == ["0001", "0002"]
    assert _applied(conn) == ["0001", "0002"]
    assert _fetch(conn, "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 't1' ORDER BY ordinal_position") == [("id",), ("name",)]


@pytest.mark.integration
def test_second_run_is_a_noop(scratch_db, tmp_path):
    _write(tmp_path, "0001_create.sql", "CREATE TABLE t1 (id int);")
    conn = scratch_db()
    apply_migrations(conn, tmp_path)

    assert apply_migrations(conn, tmp_path) == []
    assert _applied(conn) == ["0001"]


@pytest.mark.integration
def test_failed_migration_is_rolled_back_and_stops_the_run(scratch_db, tmp_path):
    _write(tmp_path, "0001_ok.sql", "CREATE TABLE t1 (id int);")
    _write(tmp_path, "0002_bad.sql", "CREATE TABLE t2 (id int); SELECT * FROM no_such_table;")
    _write(tmp_path, "0003_later.sql", "CREATE TABLE t3 (id int);")
    conn = scratch_db()

    with pytest.raises(psycopg2.Error):
        apply_migrations(conn, tmp_path)

    check = scratch_db()
    assert _applied(check) == ["0001"]
    assert not _table_exists(check, "t2")  # partial work of 0002 rolled back
    assert not _table_exists(check, "t3")  # later migrations not attempted


@pytest.mark.integration
def test_concurrent_runners_apply_each_migration_once(scratch_db, tmp_path):
    _write(tmp_path, "0001_slow.sql", "SELECT pg_sleep(0.5); CREATE TABLE t1 (id int);")
    _write(tmp_path, "0002_next.sql", "CREATE TABLE t2 (id int);")
    results, errors = [], []

    def run():
        try:
            results.append(apply_migrations(scratch_db(), tmp_path))
        except Exception as exc:  # surfaced by the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert sorted(results) == [[], ["0001", "0002"]]
    assert _applied(scratch_db()) == ["0001", "0002"]


@pytest.mark.integration
def test_shipped_migrations_apply_on_top_of_the_baseline_schema(scratch_db):
    conn = scratch_db()
    load_baseline(conn)
    conn.close()

    conn = scratch_db()
    assert apply_migrations(conn, MIGRATIONS_DIR)[0] == "0001"

    assert _table_exists(conn, "upload_session")
    assert _table_exists(conn, "dataset_fhir_annotation")
    dataset_cols = dict(_fetch(conn, "SELECT column_name, column_default FROM information_schema.columns "
                                     "WHERE table_schema = 'public' AND table_name = 'dataset'"))
    assert "'none'" in dataset_cols["fhir_status"]
    assert "fhir_failure_message" in dataset_cols
    assert "now()" in dataset_cols["created_at"]

    # A new dataset row gets fhir_status 'none'; the status CHECK rejects junk.
    with conn.cursor() as cur:
        cur.execute("INSERT INTO public.dataset (category) VALUES ('measurements') "
                    "RETURNING dataset_uuid, fhir_status")
        dataset_uuid, fhir_status = cur.fetchone()
        assert fhir_status == "none"
        cur.execute("INSERT INTO public.upload_session (category, name, source_kind) "
                    "VALUES ('measurements', 'n', 'folder') RETURNING status, commit_mode, fhir_mode")
        assert cur.fetchone() == ("receiving", "on_finalize", "none")
    conn.commit()
    with pytest.raises(psycopg2.errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute("UPDATE public.dataset SET fhir_status = 'bogus' WHERE dataset_uuid = %s",
                        (dataset_uuid,))
    conn.rollback()
