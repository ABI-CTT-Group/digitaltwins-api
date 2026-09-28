"""Shared fixtures for integration tests against the local platform services.

Postgres fixtures use POSTGRES_HOST/PORT/USER/PASSWORD and create a throwaway
database per test; MinIO fixtures use MINIO_ENDPOINT/SERVER_ACCESS_KEY/
SERVER_SECRET_KEY and create a throwaway bucket. Tests are skipped when the
service is unreachable.
"""
import os
import uuid
from pathlib import Path

import psycopg2
import pytest

from digitaltwins.postgres.migrate import apply_migrations

BASELINE_SCHEMA = Path(__file__).resolve().parents[3] / "postgres" / "digitaltwins_schema.sql"


def _pg_params(database=None):
    return dict(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        dbname=database or os.getenv("POSTGRES_DB", "postgres"),
    )


@pytest.fixture
def scratch_db():
    """Create an empty throwaway database; yield a connect() factory for it.

    The factory's ``.name`` attribute is the database name.
    """
    try:
        admin = psycopg2.connect(**_pg_params(), connect_timeout=3)
    except psycopg2.OperationalError as exc:
        pytest.skip(f"Postgres unreachable: {exc}")
    admin.autocommit = True
    name = f"dt_test_{uuid.uuid4().hex[:10]}"
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{name}"')

    opened = []

    def connect():
        conn = psycopg2.connect(**_pg_params(name))
        opened.append(conn)
        return conn

    connect.name = name
    try:
        yield connect
    finally:
        for conn in opened:
            conn.close()
        with admin.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        admin.close()


def load_baseline(conn):
    """Load services/postgres/digitaltwins_schema.sql (the init-time baseline)."""
    if not BASELINE_SCHEMA.exists():
        pytest.skip(f"baseline schema not found at {BASELINE_SCHEMA}")
    # pg_dump output contains psql meta-commands (e.g. \restrict) that
    # psycopg2 cannot execute; drop them.
    baseline = "\n".join(
        line for line in BASELINE_SCHEMA.read_text().splitlines() if not line.startswith("\\")
    )
    with conn.cursor() as cur:
        cur.execute(baseline)
    conn.commit()


@pytest.fixture
def platform_db(scratch_db, monkeypatch):
    """A scratch DB with baseline + migrations applied, wired into POSTGRES_* env.

    Yields a connect() factory (each call returns a new connection).
    """
    conn = scratch_db()
    load_baseline(conn)
    conn.close()
    conn = scratch_db()
    apply_migrations(conn)
    conn.close()
    monkeypatch.setenv("POSTGRES_ENABLED", "true")
    monkeypatch.setenv("POSTGRES_DB", scratch_db.name)
    for key, value in _pg_params(scratch_db.name).items():
        if key != "dbname":
            monkeypatch.setenv(f"POSTGRES_{key.upper()}", str(value))
    yield scratch_db


@pytest.fixture
def minio_bucket(monkeypatch):
    """A throwaway MinIO bucket name (created lazily by the code under test); emptied and removed after."""
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    endpoint = os.getenv("MINIO_ENDPOINT")
    if not endpoint:
        pytest.skip("MINIO_ENDPOINT not set")
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("MINIO_SERVER_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("MINIO_SERVER_SECRET_KEY"),
    )
    try:
        s3.list_buckets()
    except (BotoCoreError, ClientError) as exc:
        pytest.skip(f"MinIO unreachable: {exc}")
    monkeypatch.setenv("MINIO_ENABLED", "true")
    bucket = f"dt-test-{uuid.uuid4().hex[:10]}"
    try:
        yield bucket
    finally:
        try:
            for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
                for obj in page.get("Contents", []):
                    s3.delete_object(Bucket=bucket, Key=obj["Key"])
            s3.delete_bucket(Bucket=bucket)
        except ClientError:
            pass  # never created


@pytest.fixture
def s3():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        aws_access_key_id=os.getenv("MINIO_SERVER_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("MINIO_SERVER_SECRET_KEY"),
    )


# ── HAPI FHIR fake ─────────────────────────────────────────────────────


class FakeHapi:
    """In-memory HAPI FHIR standing in for both FHIR clients the API uses.

    - Push (digitaltwins-on-fhir Adapter): ``digital_twin().measurements()
      .add_measurements_description(d)`` + ``await generate_resources()`` builds
      the graph the real library creates: per patient a Patient, Consent,
      ResearchSubject and Composition; per ImagingStudy two Endpoints; per
      Observation / DocumentReference one resource, all referencing the Patient.
      Like the library's ``save()``, a resource whose identifier already exists
      is kept as it is (not updated) — except Compositions, which the library
      creates every time (one per patient, all tagged with the dataset UUID).
    - Cleanup (``fhir_service.HapiRest`` surface): ``search``, ``read`` and
      ``delete``. Delete refuses a resource another resource still references
      (HAPI's referential integrity on delete).
    """

    def __init__(self):
        self.store = {}  # "Type/id" -> resource
        self.calls = []  # REST calls made through the cleanup client
        self.fail_push = False
        self._next = 1

    # -- push -------------------------------------------------------------
    def digital_twin(self):
        return self

    def measurements(self):
        return self

    def add_measurements_description(self, description):
        self.pushed = description
        return self

    def _save(self, resource_type, identifier, **fields):
        for ref, r in self.store.items():
            if (resource_type != "Composition" and ref.startswith(resource_type + "/")
                    and r["identifier"][0]["value"] == identifier):
                return ref
        ref = f"{resource_type}/{self._next}"
        self._next += 1
        self.store[ref] = {"resourceType": resource_type, "id": ref.split("/")[1],
                           "identifier": [{"value": identifier}], **fields}
        return ref

    async def generate_resources(self):
        if self.fail_push:
            raise ConnectionError("HAPI FHIR unreachable")
        d = self.pushed["dataset"]["uuid"]
        for p in self.pushed["patients"]:
            patient = self._save("Patient", p["uuid"])
            consent = self._save("Consent", f"{d}_{p['uuid']}_ResearchSubject_Consent", patient={"reference": patient})
            rs = self._save("ResearchSubject", f"{d}_{p['uuid']}_ResearchSubject",
                            individual={"reference": patient}, consent={"reference": consent})
            entries = []
            for i, study in enumerate(p.get("imagingStudy", [])):
                eps = [self._save("Endpoint", f"{d}_{p['uuid']}_Endpoint_{i}_{n}") for n in range(2)]
                entries.append(self._save("ImagingStudy", study["uuid"], subject={"reference": patient},
                                          endpoint=[{"reference": e} for e in eps], description=study.get("description")))
            for key in ("observations", "documentReference"):
                for res in p.get(key, []):
                    entries.append(self._save("Observation" if key == "observations" else "DocumentReference",
                                              res["uuid"], subject={"reference": patient}, value=res.get("value")))
            self._save("Composition", d, subject={"reference": rs}, author=[{"reference": patient}],
                       section=[{"entry": [{"reference": e} for e in entries]}])

    # -- cleanup REST ------------------------------------------------------
    def search(self, resource_type, **params):
        self.calls.append(("search", resource_type, params))
        (param, value), = params.items()
        out = []
        for ref, r in self.store.items():
            if not ref.startswith(resource_type + "/"):
                continue
            if param == "identifier" and r["identifier"][0]["value"] == value:
                out.append(r)
            elif param != "identifier" and (r.get(param) or {}).get("reference") == value:
                out.append(r)
        return out

    def read(self, reference):
        self.calls.append(("read", reference))
        return self.store.get(reference)

    def delete(self, reference):
        self.calls.append(("delete", reference))
        referrers = [ref for ref, r in self.store.items() if ref != reference and reference in _all_refs(r)]
        if referrers:
            raise RuntimeError(f"HAPI-0550: {reference} is referenced by {referrers}")
        self.store.pop(reference, None)

    def types(self):
        from collections import Counter

        return dict(Counter(ref.split("/")[0] for ref in self.store))


def _all_refs(obj):
    if isinstance(obj, dict):
        own = [obj["reference"]] if isinstance(obj.get("reference"), str) else []
        return own + [x for v in obj.values() for x in _all_refs(v)]
    if isinstance(obj, list):
        return [x for v in obj for x in _all_refs(v)]
    return []


@pytest.fixture
def hapi(monkeypatch):
    from digitaltwins.measurements import fhir_service

    fake = FakeHapi()
    monkeypatch.setattr(fhir_service, "get_fhir_adapter", lambda: fake)
    monkeypatch.setattr(fhir_service, "get_fhir_rest", lambda: fake)
    return fake
