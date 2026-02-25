import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import os
import time
import importlib
from pathlib import Path
from typing import Optional, Any, Dict, List

def _import_api_mod(token: str):
    os.environ["SISRUA_AUTH_TOKEN"] = token
    from backend.infrastructure import api
    import importlib
    importlib.reload(api)
    return api

@pytest.fixture()
def api_mod(monkeypatch):
    return _import_api_mod("iso-master-token")

@pytest.fixture()
def client(api_mod):
    # Set default Origin for ISO 27001 compliance tests
    from fastapi.testclient import TestClient
    c = TestClient(api_mod.app)
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


# --- Audit Routes: ISO 27001 Authentication ---

def test_audit_post_requires_auth(client):
    """ISO 27001: POST /api/audit sem token deve retornar 401."""
    r = client.post(
        "/api/audit",
        json={"event_type": "TEST", "entity_type": "Project"},
    )
    assert r.status_code == 401


def test_audit_get_requires_auth(client):
    """ISO 27001: GET /api/audit sem token deve retornar 401."""
    r = client.get("/api/audit")
    assert r.status_code == 401


def test_audit_stats_requires_auth(client):
    """ISO 27001: GET /api/audit/stats sem token deve retornar 401."""
    r = client.get("/api/audit/stats")
    assert r.status_code == 401


def test_audit_export_requires_auth(client):
    """ISO 27001: GET /api/audit/export/compliance sem token deve retornar 401."""
    r = client.get("/api/audit/export/compliance")
    assert r.status_code == 401


def test_valuation_requires_auth(client):
    """ISO 27001: GET /api/valuation/summary sem token deve retornar 401."""
    r = client.get("/api/valuation/summary")
    assert r.status_code == 401


def test_audit_post_with_valid_token(client):
    """Criação de log de auditoria deve funcionar com token válido."""
    mock_audit = MagicMock()
    mock_audit.log.return_value = 42

    with patch("backend.infrastructure.audit_routes.get_audit_logger", return_value=mock_audit):
        r = client.post(
            "/api/audit",
            json={"event_type": "TEST_EVENT", "entity_type": "Project", "entity_id": "p1"},
            headers={"X-SisRua-Token": "iso-master-token"},
        )
    assert r.status_code == 201
    assert r.json()["audit_id"] == 42


def test_audit_sanitizes_oversized_fields(client):
    """Campos de texto excessivamente longos devem ser truncados (proteção DoS)."""
    mock_audit = MagicMock()
    mock_audit.log.return_value = 99
    long_str = "A" * 1000

    with patch("backend.infrastructure.audit_routes.get_audit_logger", return_value=mock_audit):
        r = client.post(
            "/api/audit",
            json={"event_type": long_str, "entity_type": "Project"},
            headers={"X-SisRua-Token": "iso-master-token"},
        )
    assert r.status_code == 201
    # Verifica que o campo foi truncado para no máximo 256 caracteres
    call_args = mock_audit.log.call_args
    assert len(call_args.kwargs["event_type"]) <= 256
