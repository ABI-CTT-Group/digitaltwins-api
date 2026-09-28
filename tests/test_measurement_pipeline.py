"""Commit pipeline: folder-derived subjects/samples, UUID stamping, dataset commit."""
import shutil
import uuid
from pathlib import Path

import psycopg2
import pytest

from digitaltwins.core import uploader as uploader_mod
from digitaltwins.core.uploader import Uploader
from digitaltwins.measurements.pipeline import (
    check_descriptions_match,
    commit_dataset,
    fetch_mapping,
    stamp_uuids,
)
from digitaltwins.measurements.tree import build_tree

FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"
PAIRS = [("sub-1", "sam-1"), ("sub-1", "sam-2"), ("sub-2", "sam-1"), ("sub-2", "sam-2")]


@pytest.fixture
def dataset(tmp_path):
    ds = tmp_path / "example"
    shutil.copytree(FIXTURE, ds)
    return ds


def _mapping():
    subjects = {"sub-1": str(uuid.uuid4()), "sub-2": str(uuid.uuid4())}
    return {(sub, sam): (subjects[sub], str(uuid.uuid4())) for sub, sam in PAIRS}


# ── Unit: UUID stamping ────────────────────────────────────────────────


def test_stamp_uuids_uses_platform_uuids_and_overwrites_client_values(dataset):
    descriptions = build_tree(dataset, "example")["descriptions"]
    descriptions["patients"][0]["uuid"] = "client-supplied"
    descriptions["patients"][0]["imagingStudy"][0]["uuid"] = "client-supplied"
    mapping = _mapping()

    stamped = stamp_uuids(descriptions, "d-uuid", mapping)

    assert stamped["dataset"]["uuid"] == "d-uuid"
    for p in stamped["patients"]:
        assert p["uuid"] == mapping[(p["name"], "sam-1")][0]
        for s in p["imagingStudy"]:
            sub, sam = s["samplePath"].split("/")
            sample_uuid = mapping[(sub, sam)][1]
            assert s["uuid"] == sample_uuid
            assert s["series"][0]["endpointUuid"] == str(uuid.uuid5(uuid.UUID(sample_uuid), "endpoint"))
    assert descriptions["patients"][0]["uuid"] == "client-supplied"  # input not mutated


def test_stamp_uuids_is_deterministic(dataset):
    descriptions = build_tree(dataset, "example")["descriptions"]
    mapping = _mapping()

    assert stamp_uuids(descriptions, "d", mapping) == stamp_uuids(descriptions, "d", mapping)


def test_stamp_uuids_rejects_unknown_sample_path(dataset):
    descriptions = build_tree(dataset, "example")["descriptions"]
    descriptions["patients"][0]["imagingStudy"][0]["samplePath"] = "sub-1/sam-9"

    with pytest.raises(ValueError, match="sub-1/sam-9"):
        stamp_uuids(descriptions, "d", _mapping())


def test_check_descriptions_match_accepts_the_auto_tree(dataset):
    check_descriptions_match(build_tree(dataset, "example")["descriptions"], dataset)


@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda d: d["patients"][0].update(name="sub-9"), "sub-9"),
        (lambda d: d["patients"][0]["imagingStudy"][0].update(samplePath="sub-1/sam-9"), "sub-1/sam-9"),
        (lambda d: d["patients"][0]["imagingStudy"][0].update(samplePath="sub-2/sam-1"), "sub-2/sam-1"),
    ],
)
def test_check_descriptions_match_rejects_entries_without_folders(dataset, mutate, needle):
    descriptions = build_tree(dataset, "example")["descriptions"]
    mutate(descriptions)

    with pytest.raises(ValueError, match=needle):
        check_descriptions_match(descriptions, dataset)


# ── Unit: Uploader error handling (defect 2) ───────────────────────────


class _FakeMinio:
    def __init__(self):
        self.prefixes = []

    def bucket_exists(self, bucket_name):
        return True

    def upload_folder(self, folder_path, bucket_name, prefix):
        self.prefixes.append(prefix)
        return True


def test_minio_only_upload_gets_a_generated_uuid_prefix(dataset, monkeypatch):
    monkeypatch.setenv("POSTGRES_ENABLED", "false")
    monkeypatch.setenv("MINIO_ENABLED", "false")
    up = Uploader()
    fake = _FakeMinio()
    up._minio_enabled, up._minio_uploader = True, fake

    dataset_uuid = up.upload_dataset(str(dataset), category="measurements")

    assert fake.prefixes == [dataset_uuid]
    uuid.UUID(dataset_uuid)


def test_failed_dataset_insert_surfaces_the_original_error(dataset, monkeypatch):
    class _Cur:
        def execute(self, *a, **k):
            raise psycopg2.errors.UndefinedTable("relation dataset does not exist")

    class _Conn:
        autocommit = True

        def cursor(self):
            return _Cur()

        def rollback(self):
            pass

        def close(self):
            pass

    for key in ("HOST", "PORT", "DB", "USER", "PASSWORD"):
        monkeypatch.setenv(f"POSTGRES_{key}", "x")
    monkeypatch.setenv("POSTGRES_ENABLED", "true")
    monkeypatch.setenv("MINIO_ENABLED", "false")
    monkeypatch.setattr(uploader_mod.psycopg2, "connect", lambda **k: _Conn())

    with pytest.raises(psycopg2.errors.UndefinedTable):
        Uploader().upload_dataset(str(dataset), category="measurements")


# ── Integration: derived subjects/samples + commit ─────────────────────


def _rows(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _upload(dataset, bucket):
    return Uploader().upload_dataset(str(dataset), category=bucket, derive_from_primary=True)


@pytest.mark.integration
def test_dataset_without_spreadsheets_gets_one_row_per_folder(platform_db, minio_bucket, dataset):
    (dataset / "subjects.xlsx").unlink()
    (dataset / "samples.xlsx").unlink()

    dataset_uuid = _upload(dataset, minio_bucket)

    conn = platform_db()
    mapping = fetch_mapping(conn, dataset_uuid)
    assert sorted(mapping) == PAIRS
    names = _rows(conn, "SELECT s.subject_name, sa.sample_name FROM dataset_mapping m "
                        "JOIN subject s USING (subject_uuid) JOIN sample sa USING (sample_uuid) "
                        "WHERE m.dataset_uuid = %s ORDER BY 1, 2", (dataset_uuid,))
    assert names == PAIRS
    assert _rows(conn, "SELECT count(DISTINCT subject_uuid) FROM dataset_mapping "
                       "WHERE dataset_uuid = %s", (dataset_uuid,)) == [(2,)]


@pytest.mark.integration
def test_spreadsheet_rows_are_reused_and_not_duplicated(platform_db, minio_bucket, dataset):
    dataset_uuid = _upload(dataset, minio_bucket)

    conn = platform_db()
    assert sorted(fetch_mapping(conn, dataset_uuid)) == PAIRS
    # Subjects/samples come from the spreadsheets (sex, sample_type populated), none derived.
    assert _rows(conn, "SELECT count(*) FROM subject") == [(2,)]
    assert _rows(conn, "SELECT count(*) FROM sample") == [(4,)]
    assert _rows(conn, "SELECT DISTINCT s.sex FROM dataset_mapping m JOIN subject s USING (subject_uuid) "
                       "WHERE m.dataset_uuid = %s", (dataset_uuid,)) == [("Female",)]


@pytest.mark.integration
def test_partial_spreadsheets_only_derive_the_missing_rows(platform_db, minio_bucket, dataset):
    (dataset / "samples.xlsx").unlink()  # subjects.xlsx still lists sub-1, sub-2

    dataset_uuid = _upload(dataset, minio_bucket)

    conn = platform_db()
    assert sorted(fetch_mapping(conn, dataset_uuid)) == PAIRS
    assert _rows(conn, "SELECT count(*) FROM subject") == [(2,)]  # reused, not re-derived
    assert _rows(conn, "SELECT count(*) FROM sample") == [(4,)]


@pytest.mark.integration
def test_commit_dataset_stores_files_and_stamped_annotation(platform_db, minio_bucket, s3, dataset):
    descriptions = build_tree(dataset, "example")["descriptions"]

    result = commit_dataset(dataset, category=minio_bucket, descriptions=descriptions)

    conn = platform_db()
    mapping = fetch_mapping(conn, result.dataset_uuid)
    [(stored,)] = _rows(conn, "SELECT descriptions FROM dataset_fhir_annotation WHERE dataset_uuid = %s",
                        (result.dataset_uuid,))
    assert stored == result.descriptions
    assert stored["dataset"]["uuid"] == result.dataset_uuid
    assert stored["patients"][0]["uuid"] == mapping[("sub-1", "sam-1")][0]
    key = f"{result.dataset_uuid}/primary/sub-1/sam-1/1-001.dcm"
    assert s3.head_object(Bucket=minio_bucket, Key=key)["ContentLength"] > 0


@pytest.mark.integration
def test_commit_dataset_without_descriptions_stores_no_annotation(platform_db, minio_bucket, dataset):
    result = commit_dataset(dataset, category=minio_bucket)

    assert result.descriptions is None
    assert _rows(platform_db(), "SELECT count(*) FROM dataset_fhir_annotation") == [(0,)]


# ── Unit: subject-level resources (added by hand, no sample folder) ────


def _manual_observation(uuid_value=""):
    return {"resourceType": "Observation", "uuid": uuid_value, "value": "28.5", "valueType": "Quantity",
            "code": "", "codeSystem": "http://loinc.org", "unit": "kg", "display": ""}


def test_subject_level_resources_get_stable_uuids_from_their_subject(dataset):
    descriptions = build_tree(dataset, "example")["descriptions"]
    descriptions["patients"][0]["observations"] = [_manual_observation("MOCK-obs-1"), _manual_observation()]
    mapping = _mapping()
    subject_uuid = uuid.UUID(mapping[("sub-1", "sam-1")][0])

    stamped = stamp_uuids(descriptions, "d", mapping)

    obs = stamped["patients"][0]["observations"]
    assert [o["uuid"] for o in obs] == [str(uuid.uuid5(subject_uuid, "observations:0")),
                                        str(uuid.uuid5(subject_uuid, "observations:1"))]
    # Re-stamping an already-stamped draft (a later save) keeps the same UUIDs.
    assert stamp_uuids(stamped, "d", mapping) == stamped


def test_check_descriptions_match_accepts_subject_level_resources(dataset):
    descriptions = build_tree(dataset, "example")["descriptions"]
    descriptions["patients"][0]["observations"] = [_manual_observation()]

    check_descriptions_match(descriptions, dataset)
