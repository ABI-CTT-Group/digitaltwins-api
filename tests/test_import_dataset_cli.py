"""python -m digitaltwins.cli.import_dataset: login + role gate, then the in-process pipeline."""
import shutil
from pathlib import Path

import pytest

from digitaltwins.cli import import_dataset, keycloak_login
from digitaltwins.measurements import sessions

FIXTURE = Path(__file__).parent / "data" / "example_sds_dataset"
FIXTURE_ZIP = Path(__file__).parent / "data" / "example_sds_dataset.zip"


# ── Unit: role gate + device flow ──────────────────────────────────────


@pytest.mark.parametrize("roles", [["admin"], ["offline_access", "researcher"]])
def test_role_gate_accepts_upload_roles(roles):
    claims = {"preferred_username": "alice", "realm_access": {"roles": roles}}
    assert keycloak_login.require_upload_role(claims) == "alice"


def test_role_gate_rejects_other_users():
    claims = {"preferred_username": "bob", "realm_access": {"roles": ["viewer"]}}
    with pytest.raises(PermissionError, match="bob"):
        keycloak_login.require_upload_role(claims)


def test_device_login_polls_until_the_user_signs_in(monkeypatch, capsys):
    responses = iter([
        (200, {"device_code": "dc", "verification_uri_complete": "https://kc/device?code=X", "interval": 0}),
        (400, {"error": "authorization_pending"}),
        (200, {"access_token": "tok"}),
    ])
    monkeypatch.setattr(keycloak_login, "_post_form", lambda url, data: next(responses))
    monkeypatch.setattr(keycloak_login, "verify_token", lambda token: {"token": token})

    assert keycloak_login.device_login() == {"token": "tok"}
    assert "https://kc/device?code=X" in capsys.readouterr().out


def test_login_falls_back_to_password_when_device_flow_is_unavailable(monkeypatch):
    monkeypatch.setattr(keycloak_login, "device_login", lambda: (_ for _ in ()).throw(RuntimeError("off")))
    monkeypatch.setattr(keycloak_login, "password_login", lambda username=None: {
        "preferred_username": "alice", "realm_access": {"roles": ["admin"]}})

    assert keycloak_login.login() == "alice"


# ── Integration: import ────────────────────────────────────────────────


@pytest.fixture
def cli_env(platform_db, minio_bucket, hapi, tmp_path, monkeypatch):
    monkeypatch.setenv("DATASET_STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setattr(import_dataset, "login", lambda **kw: "alice")
    return {"db": platform_db, "bucket": minio_bucket, "tmp": tmp_path}


def _dataset(env, dataset_uuid):
    with env["db"]().cursor() as cur:
        cur.execute("SELECT dataset_name, fhir_status FROM dataset WHERE dataset_uuid = %s", (dataset_uuid,))
        return cur.fetchone()


def _only_session(env):
    with env["db"]().cursor() as cur:
        cur.execute("SELECT upload_id FROM upload_session")
        [(upload_id,)] = cur.fetchall()
    return sessions.get_session(env["db"](), upload_id)


@pytest.mark.integration
def test_imports_a_folder_with_auto_fhir(cli_env, capsys):
    code = import_dataset.main([str(FIXTURE), "--name", "CLI import", "--fhir", "auto",
                                "--category", cli_env["bucket"]])

    assert code == 0
    session = _only_session(cli_env)
    assert _dataset(cli_env, session["dataset_uuid"]) == ("CLI import", "completed")
    assert session["dataset_uuid"] in capsys.readouterr().out
    assert FIXTURE.is_dir()  # copied, not moved, by default


@pytest.mark.integration
def test_imports_a_zip(cli_env):
    assert import_dataset.main([str(FIXTURE_ZIP), "--category", cli_env["bucket"]]) == 0
    assert _dataset(cli_env, _only_session(cli_env)["dataset_uuid"]) == ("example_sds_dataset", "none")


@pytest.mark.integration
def test_move_consumes_the_staged_copy(cli_env):
    staged = cli_env["tmp"] / "import-staging" / "example"
    shutil.copytree(FIXTURE, staged)

    assert import_dataset.main([str(staged), "--move", "--category", cli_env["bucket"]]) == 0
    assert not staged.exists()


@pytest.mark.integration
def test_invalid_dataset_exits_2_without_a_session(cli_env, capsys):
    broken = cli_env["tmp"] / "broken"
    broken.mkdir()
    (broken / "dataset_description.xlsx").write_bytes(b"")

    assert import_dataset.main([str(broken), "--category", cli_env["bucket"]]) == 2
    assert "primary/" in capsys.readouterr().err
    with cli_env["db"]().cursor() as cur:
        cur.execute("SELECT count(*) FROM upload_session")
        assert cur.fetchone() == (0,)


@pytest.mark.integration
def test_user_without_an_upload_role_exits_3(cli_env, monkeypatch, capsys):
    def denied(**kw):
        raise PermissionError("User 'bob' lacks an upload role")

    monkeypatch.setattr(import_dataset, "login", denied)

    assert import_dataset.main([str(FIXTURE), "--category", cli_env["bucket"]]) == 3
    assert "bob" in capsys.readouterr().err
