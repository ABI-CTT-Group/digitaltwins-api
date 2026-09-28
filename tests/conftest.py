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
