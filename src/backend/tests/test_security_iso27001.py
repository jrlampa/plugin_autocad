import pytest
from fastapi.testclient import TestClient
import os
import time
import importlib

def _import_api_with_token(token: str):
    os.environ["SISRUA_AUTH_TOKEN"] = token
    from backend import api as api_mod
    importlib.reload(api_mod)
    return api_mod

@pytest.fixture()
def api_mod(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    return _import_api_with_token("iso-master-token")

@pytest.fixture()
def client(api_mod):
    # Set base_url and default Origin for ISO 27001 compliance tests
    c = TestClient(api_mod.app, base_url="http://localhost:8000")
    c.headers.update({"Origin": "http://localhost:8000"})
    return c

def test_origin_validation_blocks_unknown(client):
    """ISO 27001: Verify that requests from unknown origins are blocked."""
    r = client.get("/api/v1/auth/check", headers={
        "X-SisRua-Token": "iso-master-token",
        "Origin": "http://evil-attacker.com"
    })
    assert r.status_code == 403
    assert "Invalid Origin" in r.text

def test_origin_validation_allows_whitelisted(client):
    """ISO 27001: Verify that whitelisted origins are allowed."""
    r = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200

def test_session_token_exchange(client):
    """ISO 27001: Verify Master Token -> Session Token exchange."""
    # 1. Exchange
    r = client.post("/api/v1/auth/session", headers={
        "X-SisRua-Token": "iso-master-token",
        "Origin": "http://localhost:5173"
    })
    assert r.status_code == 200
    data = r.json()
    session_token = data["session_token"]
    assert session_token.startswith("sess_")
    
    # 2. Use session token
    r2 = client.get("/api/v1/auth/check", headers={
        "X-SisRua-Token": session_token,
        "Origin": "http://localhost:5173"
    })
    assert r2.status_code == 200
    assert r2.json()["status"] == "ok"

def test_master_token_still_works_for_bootstrap(client):
    """Ensure master token still works (e.g., for the C# plugin backend-to-backend calls)."""
    r = client.get("/api/v1/auth/check", headers={
        "X-SisRua-Token": "iso-master-token",
        "Origin": "http://localhost:5173"
    })
    assert r.status_code == 200

def test_expired_session_token_fails(client, api_mod, monkeypatch):
    """ISO 27001: Verify session expiration."""
    # 1. Exchange
    r = client.post("/api/v1/auth/session", headers={
        "X-SisRua-Token": "iso-master-token",
        "Origin": "http://localhost:5173"
    })
    session_token = r.json()["session_token"]
    
    # 2. Fast-forward time
    future_time = time.time() + 4000 # > 30 mins
    monkeypatch.setattr(time, "time", lambda: future_time)
    
    # 3. Use (should fail)
    r2 = client.get("/api/v1/auth/check", headers={
        "X-SisRua-Token": session_token,
        "Origin": "http://localhost:5173"
    })
    assert r2.status_code == 401
    assert "Invalid or Expired Token" in r2.json()["detail"]
