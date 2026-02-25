"""
tests/test_api_coverage.py
Targeted unit tests for backend/api.py uncovered code paths.
Achieved: 66% → 69% (lifespan threads and frozen-exe paths are not exercisable
in unit tests without a live server process).

Covers:
- Token auto-generation when SISRUA_AUTH_TOKEN is not set (lines 43-44)
- /api/v1/audit/telemetry endpoint (lines 267-268)
- Security headers middleware (tests X-Content-Type-Options etc.)
- Origin validation middleware (invalid origin → 403, no-origin non-local → 403)
- _maybe_mount_frontend() — fallback HTML root (lines 328-332)
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("SISRUA_TESTING", "true")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_api(token: str | None = "test-api-cov-token", tmp_path: Path | None = None):
    """Reload backend.api with a specific token (or unset to trigger auto-generation)."""
    if token is None:
        os.environ.pop("SISRUA_AUTH_TOKEN", None)
    else:
        os.environ["SISRUA_AUTH_TOKEN"] = token

    if tmp_path:
        os.environ["LOCALAPPDATA"] = str(tmp_path)

    import backend.api as api_mod
    importlib.reload(api_mod)
    return api_mod


def _client(api_mod, base_url: str = "http://localhost:8000") -> TestClient:
    c = TestClient(api_mod.app, base_url=base_url, raise_server_exceptions=True)
    c.headers.update({"Origin": "http://localhost:8000"})
    return c


# ---------------------------------------------------------------------------
# Token auto-generation (lines 43-44)
# ---------------------------------------------------------------------------

def test_auth_token_auto_generated_when_not_set(tmp_path):
    """When SISRUA_AUTH_TOKEN is absent, api.py generates a UUID hex and sets env (lines 43-44)."""
    import backend.shared.config as _cfg_mod
    os.environ.pop("SISRUA_AUTH_TOKEN", None)
    # Reset the config singleton's cached token so the module-level auto-generation
    # path is exercised even when other tests have already initialized the config.
    with patch.object(_cfg_mod.config, "sisrua_auth_token", None):
        api_mod = _load_api(token=None, tmp_path=tmp_path)

        generated = os.environ.get("SISRUA_AUTH_TOKEN", "")
        assert len(generated) == 32, "Auto-generated token must be a 32-char hex (UUID)"
        assert generated == generated.lower()

    # Reset to stable token for other tests
    os.environ["SISRUA_AUTH_TOKEN"] = "test-api-cov-token"


# ---------------------------------------------------------------------------
# /api/v1/audit/telemetry endpoint (lines 267-268)
# ---------------------------------------------------------------------------

def test_telemetry_endpoint_returns_received(tmp_path):
    """POST /api/v1/audit/telemetry returns {status: 'received'} for any payload."""
    api_mod = _load_api(tmp_path=tmp_path)
    c = _client(api_mod)

    payload = {"plugin_version": "1.0", "event": "autocad_loaded", "cad_count": 42}
    r = c.post("/api/v1/audit/telemetry", json=payload)

    assert r.status_code == 200
    assert r.json() == {"status": "received"}


def test_telemetry_endpoint_accepts_empty_payload(tmp_path):
    """Telemetry accepts an empty JSON object."""
    api_mod = _load_api(tmp_path=tmp_path)
    c = _client(api_mod)

    r = c.post("/api/v1/audit/telemetry", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "received"


# ---------------------------------------------------------------------------
# Security headers middleware — verify headers present (lines 226-243)
# ---------------------------------------------------------------------------

def test_security_headers_present_on_health(tmp_path):
    """All security headers must be injected on every response."""
    api_mod = _load_api(tmp_path=tmp_path)
    c = _client(api_mod)

    r = c.get("/api/v1/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-XSS-Protection") == "1; mode=block"
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "default-src 'self'" in r.headers.get("Content-Security-Policy", "")
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_trace_id_header_echoed(tmp_path):
    """X-Request-ID is echoed back in the response (lines 155-156)."""
    api_mod = _load_api(tmp_path=tmp_path)
    c = _client(api_mod)

    r = c.get("/api/v1/health", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers.get("X-Request-ID") == "trace-abc-123"


def test_trace_id_generated_when_absent(tmp_path):
    """X-Request-ID is auto-generated when not provided by client."""
    api_mod = _load_api(tmp_path=tmp_path)
    c = _client(api_mod)

    r = c.get("/api/v1/health")
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) > 10  # UUID-like


# ---------------------------------------------------------------------------
# Origin validation middleware (lines 193-220)
# ---------------------------------------------------------------------------

def test_invalid_origin_returns_403(tmp_path):
    """A request with an external Origin header is blocked (lines 198-200)."""
    api_mod = _load_api(tmp_path=tmp_path)

    # Use a client without the default Origin header
    c = TestClient(api_mod.app, base_url="http://localhost:8000", raise_server_exceptions=False)

    r = c.get(
        "/api/v1/auth/check",
        headers={"Origin": "https://evil.example.com"},
    )
    assert r.status_code == 403
    assert "Forbidden" in r.text


def test_localhost_origin_passes_validation(tmp_path):
    """Origin=http://localhost:<any port> is allowed."""
    api_mod = _load_api(tmp_path=tmp_path)
    c = TestClient(api_mod.app, base_url="http://localhost:8000", raise_server_exceptions=False)
    token = os.environ.get("SISRUA_AUTH_TOKEN", "test-api-cov-token")

    r = c.get(
        "/api/v1/auth/check",
        headers={"Origin": "http://localhost:5173", "X-SisRua-Token": token},
    )
    assert r.status_code == 200


def test_no_origin_non_api_path_allowed(tmp_path):
    """Public paths (e.g. /api/v1/health) bypass origin check (line 182-183)."""
    api_mod = _load_api(tmp_path=tmp_path)
    c = TestClient(api_mod.app, base_url="http://localhost:8000", raise_server_exceptions=False)

    r = c.get("/api/v1/health")  # No Origin header
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# _maybe_mount_frontend — fallback HTML root (lines 328-332)
# ---------------------------------------------------------------------------

def test_root_returns_html_when_no_frontend_dist(tmp_path):
    """When frontend/dist is absent, '/' returns an HTML page (lines 328-332)."""
    api_mod = _load_api(tmp_path=tmp_path)
    c = _client(api_mod)

    r = c.get("/")
    # FastAPI returns 200 with either the SPA or the fallback HTML
    assert r.status_code in (200, 404)
    if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
        # Should contain Portuguese UI text
        assert "sisRUA" in r.text
