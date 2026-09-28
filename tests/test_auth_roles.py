"""require_upload_role: realm role admin|researcher required, via Bearer or Basic."""
import base64
import sys
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers import auth

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _KEY.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
_PUBLIC_PEM = _KEY.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
).decode()


def _token(roles, expires_in=300):
    claims = {
        "preferred_username": "alice",
        "realm_access": {"roles": roles},
        "exp": int(time.time()) + expires_in,
    }
    return jwt.encode(claims, _PRIVATE_PEM, algorithm="RS256")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth, "KEYCLOAK_ALGORITHM", "RS256")
    monkeypatch.setattr(auth, "get_keycloak_public_key", lambda: _PUBLIC_PEM)

    app = FastAPI()

    @app.get("/protected")
    def protected(creds=Depends(auth.require_upload_role)):
        return {"username": creds["username"]}

    return TestClient(app)


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("role", ["admin", "researcher"])
def test_bearer_with_upload_role_is_allowed(client, role):
    r = client.get("/protected", headers=_bearer(_token(["offline_access", role])))
    assert r.status_code == 200
    assert r.json() == {"username": "alice"}


def test_bearer_without_upload_role_is_forbidden(client):
    r = client.get("/protected", headers=_bearer(_token(["offline_access", "viewer"])))
    assert r.status_code == 403


def test_token_without_realm_access_is_forbidden(client):
    token = jwt.encode({"preferred_username": "bob", "exp": int(time.time()) + 300},
                       _PRIVATE_PEM, algorithm="RS256")
    assert client.get("/protected", headers=_bearer(token)).status_code == 403


def test_expired_token_is_unauthorized(client):
    r = client.get("/protected", headers=_bearer(_token(["admin"], expires_in=-60)))
    assert r.status_code == 401


def test_missing_credentials_is_unauthorized(client):
    assert client.get("/protected").status_code == 401


def _basic(user="alice", password="<REDACTED>"):
    raw = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {raw}"}


def test_basic_auth_uses_roles_from_the_issued_token(client, monkeypatch):
    monkeypatch.setattr(auth, "get_token", lambda *a, **k: {"access_token": _token(["researcher"])})
    assert client.get("/protected", headers=_basic()).status_code == 200


def test_basic_auth_without_upload_role_is_forbidden(client, monkeypatch):
    monkeypatch.setattr(auth, "get_token", lambda *a, **k: {"access_token": _token(["viewer"])})
    assert client.get("/protected", headers=_basic()).status_code == 403
