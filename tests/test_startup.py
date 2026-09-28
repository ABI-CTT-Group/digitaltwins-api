"""The API applies platform schema migrations on startup when Postgres is enabled."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app
from digitaltwins.measurements import jobs
from digitaltwins.postgres import migrate


def _start(monkeypatch, postgres_enabled):
    calls = []
    monkeypatch.setenv("POSTGRES_ENABLED", postgres_enabled)
    monkeypatch.setattr(migrate, "run", lambda: calls.append("run") or [])
    monkeypatch.setattr(jobs, "sweep_on_startup", lambda: None)
    with TestClient(create_app()):  # entering the client runs the lifespan
        pass
    return calls


def test_startup_applies_migrations_when_postgres_enabled(monkeypatch):
    assert _start(monkeypatch, "true") == ["run"]


def test_startup_skips_migrations_when_postgres_disabled(monkeypatch):
    assert _start(monkeypatch, "false") == []
