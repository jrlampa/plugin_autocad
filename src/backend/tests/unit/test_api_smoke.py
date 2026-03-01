import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app(monkeypatch):
    # Ensure no IPC server is started during tests
    monkeypatch.setenv("SISRUA_TESTING", "true")
    # Make auth deterministic
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "test-token")

    # Import after env is set
    api_mod = importlib.import_module("backend.infrastructure.api")
    importlib.reload(api_mod)
    return api_mod.app


def test_health_public_ok(app):
    c = TestClient(app)
    r = c.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_telemetry_endpoint_ok(app):
    c = TestClient(app)
    r = c.post("/api/v1/audit/telemetry", json={"event": "ping", "v": 1})
    assert r.status_code == 200
    assert r.json()["status"] == "received"


def test_auth_check_requires_token(app):
    c = TestClient(app)
    r = c.get("/api/v1/auth/check")
    assert r.status_code in (401, 403)


def test_auth_check_with_master_token_ok(app):
    c = TestClient(app)
    r = c.get("/api/v1/auth/check", headers={"X-SisRua-Token": "test-token"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_session_exchange(app):
    c = TestClient(app)
    r = c.post("/api/v1/auth/session", headers={"X-SisRua-Token": "test-token"})
    assert r.status_code == 200
    payload = r.json()
    assert payload["session_token"].startswith("sess_")
    assert payload["expires_in"] > 0

    # session token should now work
    r2 = c.get("/api/v1/auth/check", headers={"X-SisRua-Token": payload["session_token"]})
    assert r2.status_code == 200
