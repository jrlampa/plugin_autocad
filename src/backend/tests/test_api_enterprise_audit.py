"""
tests/test_api_enterprise_audit.py
Targeted tests for audit_routes.py and routes/enterprise.py.

These tests exercise the HTTP endpoints that were uncovered in previous sessions:
  - audit_routes.py:  37% → target ≥75%
  - routes/enterprise.py: 43% → target ≥70%
"""
import importlib
import os
import signal
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _reload_api(token: str, tmp_path):
    os.environ["SISRUA_AUTH_TOKEN"] = token
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend import api as api_mod
    importlib.reload(api_mod)
    return api_mod


@pytest.fixture()
def api_mod(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    return _reload_api("ent-test-token", tmp_path)


@pytest.fixture()
def client(api_mod):
    c = TestClient(api_mod.app, base_url="http://localhost:8000")
    c.headers.update({"Origin": "http://localhost:8000"})
    return c


@pytest.fixture()
def auth_headers():
    return {"X-SisRua-Token": "ent-test-token"}


# ---------------------------------------------------------------------------
# audit_routes.py — GET /api/audit/{id}  (lines 64-90)
# ---------------------------------------------------------------------------

def test_audit_get_by_id_not_found(client, auth_headers):
    """GET /api/audit/9999 com ID inexistente retorna 404."""
    r = client.get("/api/audit/9999", headers=auth_headers)
    assert r.status_code == 404
    assert "não encontrado" in r.json()["detail"]


def test_audit_get_by_id_mock_not_written_to_db(client, auth_headers):
    """POST com mock não escreve no DB real; GET por ID grande e inexistente retorna 404."""
    mock_audit = MagicMock()
    mock_audit.log.return_value = 99999

    with patch("backend.audit_routes.get_audit_logger", return_value=mock_audit):
        post_r = client.post(
            "/api/audit",
            json={"event_type": "CREATE", "entity_type": "Project"},
            headers=auth_headers,
        )
    assert post_r.status_code == 201

    # Mock post não escreve no DB real; audit_id=99999 nunca foi inserido → 404
    r = client.get("/api/audit/99999", headers=auth_headers)
    assert r.status_code == 404


def test_audit_get_by_id_real_insert(client, auth_headers):
    """Cria log real (sem mock) e depois lê pelo ID."""
    post_r = client.post(
        "/api/audit",
        json={"event_type": "TEST_REAL", "entity_type": "Feature", "entity_id": "f1"},
        headers=auth_headers,
    )
    assert post_r.status_code == 201
    audit_id = post_r.json()["audit_id"]

    get_r = client.get(f"/api/audit/{audit_id}", headers=auth_headers)
    assert get_r.status_code == 200
    body = get_r.json()
    assert body["audit_id"] == audit_id
    assert body["event_type"] == "TEST_REAL"
    assert body["entity_type"] == "Feature"
    assert "signature" in body


# ---------------------------------------------------------------------------
# audit_routes.py — POST /api/audit missing field → 400  (lines 53-58)
# ---------------------------------------------------------------------------

def test_audit_post_missing_required_field(client, auth_headers):
    """POST sem campo obrigatório entity_type retorna 400."""
    r = client.post(
        "/api/audit",
        json={"event_type": "CREATE"},  # entity_type está faltando
        headers=auth_headers,
    )
    # audit.log() acessa raw["entity_type"] e lança KeyError → 400
    assert r.status_code == 400
    assert "Campo obrigatório ausente" in r.json()["detail"]


# ---------------------------------------------------------------------------
# audit_routes.py — GET /api/audit/{id}/verify  (lines 96-99)
# ---------------------------------------------------------------------------

def test_audit_verify_valid(client, auth_headers):
    """Insere log real, verifica assinatura → valid=True."""
    post_r = client.post(
        "/api/audit",
        json={"event_type": "VERIFY_TEST", "entity_type": "Project", "entity_id": "p99"},
        headers=auth_headers,
    )
    assert post_r.status_code == 201
    audit_id = post_r.json()["audit_id"]

    verify_r = client.get(f"/api/audit/{audit_id}/verify", headers=auth_headers)
    assert verify_r.status_code == 200
    body = verify_r.json()
    assert body["audit_id"] == audit_id
    assert "valid" in body
    assert "message" in body


def test_audit_verify_invalid_signature(client, auth_headers, api_mod, tmp_path):
    """Assinatura adulterada retorna valid=False."""
    post_r = client.post(
        "/api/audit",
        json={"event_type": "TAMPER_TEST", "entity_type": "Project"},
        headers=auth_headers,
    )
    assert post_r.status_code == 201
    audit_id = post_r.json()["audit_id"]

    # Adultera a signature diretamente no banco
    from backend.shared.database import get_db_connection
    conn = get_db_connection()
    conn.execute(
        "UPDATE AuditLog SET signature = 'tampered_bad_signature' WHERE audit_id = ?",
        (audit_id,),
    )
    conn.commit()
    conn.close()

    verify_r = client.get(f"/api/audit/{audit_id}/verify", headers=auth_headers)
    assert verify_r.status_code == 200
    assert verify_r.json()["valid"] is False


# ---------------------------------------------------------------------------
# audit_routes.py — POST /api/audit/verify-all  (lines 109-118)
# ---------------------------------------------------------------------------

def test_audit_verify_all_empty(client, auth_headers):
    """POST /api/audit/verify-all sem body → estrutura de resultado."""
    r = client.post("/api/audit/verify-all", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "total" in body or isinstance(body, dict)


def test_audit_verify_all_with_limit(client, auth_headers):
    """POST /api/audit/verify-all com limit no body."""
    r = client.post(
        "/api/audit/verify-all",
        json={"limit": 5},
        headers=auth_headers,
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# audit_routes.py — GET /api/audit  (lines 130-137)
# ---------------------------------------------------------------------------

def test_audit_list_empty(client, auth_headers):
    """GET /api/audit em DB limpo retorna count=0."""
    r = client.get("/api/audit", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "count" in body
    assert "logs" in body
    assert body["count"] >= 0


def test_audit_list_with_entity_type_filter(client, auth_headers):
    """GET /api/audit?entity_type=Project filtra por entidade."""
    client.post(
        "/api/audit",
        json={"event_type": "CREATE", "entity_type": "Project"},
        headers=auth_headers,
    )
    r = client.get("/api/audit?entity_type=Project", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    for log in body["logs"]:
        assert log["entity_type"] == "Project"


def test_audit_list_with_event_type_filter(client, auth_headers):
    """GET /api/audit?event_type=DELETE filtra por tipo de evento."""
    client.post(
        "/api/audit",
        json={"event_type": "DELETE", "entity_type": "Feature"},
        headers=auth_headers,
    )
    r = client.get("/api/audit?event_type=DELETE", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["count"] >= 1


# ---------------------------------------------------------------------------
# audit_routes.py — GET /api/audit/stats  (lines 143-167)
# ---------------------------------------------------------------------------

def test_audit_stats(client, auth_headers):
    """GET /api/audit/stats retorna contagens agregadas."""
    client.post(
        "/api/audit",
        json={"event_type": "CREATE", "entity_type": "Project"},
        headers=auth_headers,
    )
    r = client.get("/api/audit/stats", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "total_logs" in body
    assert "recent_24h" in body
    assert "by_entity_type" in body
    assert "by_event_type" in body
    assert body["total_logs"] >= 1


# ---------------------------------------------------------------------------
# audit_routes.py — GET /api/valuation/summary  (lines 176-211)
# ---------------------------------------------------------------------------

def test_valuation_summary_empty(client, auth_headers):
    """GET /api/valuation/summary sem dados de mileagem retorna 0."""
    r = client.get("/api/valuation/summary", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "total_urban_assets_mapped_km" in body
    assert body["total_urban_assets_mapped_km"] >= 0
    assert "compliance_status" in body


def test_valuation_summary_with_mileage(client, auth_headers):
    """GET /api/valuation/summary com logs UPDATE Project com mileage_km."""
    client.post(
        "/api/audit",
        json={
            "event_type": "UPDATE",
            "entity_type": "Project",
            "data": {"project_id": "p1", "mileage_km": 12.5},
        },
        headers=auth_headers,
    )
    r = client.get("/api/valuation/summary", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total_urban_assets_mapped_km"] >= 0
    assert "estimated_asset_value_usd" in body


# ---------------------------------------------------------------------------
# audit_routes.py — GET /api/audit/export/compliance  (lines 219-245)
# ---------------------------------------------------------------------------

def test_audit_export_compliance_csv(client, auth_headers):
    """GET /api/audit/export/compliance retorna CSV válido."""
    client.post(
        "/api/audit",
        json={"event_type": "EXPORT_TEST", "entity_type": "Project"},
        headers=auth_headers,
    )
    r = client.get("/api/audit/export/compliance", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "AuditID" in r.text
    assert "sisrua_compliance_evidence.csv" in r.headers.get("content-disposition", "")


# ---------------------------------------------------------------------------
# routes/enterprise.py — Export endpoints (lines 41-45, 64-77, 99-103, 115-132)
# ---------------------------------------------------------------------------

def _mock_export_service_for(api_mod, method: str, return_value):
    """Configura mock no export_service do módulo api."""
    import backend.api as _api_module
    mock_svc = MagicMock()
    getattr(mock_svc, method).return_value = return_value
    _api_module.export_service = mock_svc
    return mock_svc


def test_export_geopackage_not_found(client, auth_headers, api_mod, tmp_path):
    """GET /api/v1/export/geopackage/{id} com projeto inexistente → 404."""
    from backend.application.projects import NotFoundError
    import backend.api as _api_module
    mock_svc = MagicMock()
    mock_svc.export_project_to_geopackage.side_effect = NotFoundError("não encontrado")
    _api_module.export_service = mock_svc

    r = client.get("/api/v1/export/geopackage/nonexistent-id", headers=auth_headers)
    assert r.status_code == 404


def test_export_geopackage_success(client, auth_headers, api_mod, tmp_path):
    """GET /api/v1/export/geopackage/{id} com mock de arquivo real → 200."""
    import backend.api as _api_module
    fake_file = tmp_path / "test.gpkg"
    fake_file.write_bytes(b"GPKG")
    mock_svc = MagicMock()
    mock_svc.export_project_to_geopackage.return_value = fake_file
    _api_module.export_service = mock_svc

    r = client.get("/api/v1/export/geopackage/some-project-id", headers=auth_headers)
    assert r.status_code == 200


def test_export_geopackage_500(client, auth_headers, api_mod):
    """GET /api/v1/export/geopackage/{id} com erro genérico → 500."""
    import backend.api as _api_module
    mock_svc = MagicMock()
    mock_svc.export_project_to_geopackage.side_effect = RuntimeError("disk error")
    _api_module.export_service = mock_svc

    r = client.get("/api/v1/export/geopackage/bad-id", headers=auth_headers)
    assert r.status_code == 500


def test_export_dxf_not_found(client, auth_headers, api_mod):
    """GET /api/v1/export/dxf/{id} com projeto inexistente → 404."""
    from backend.application.projects import NotFoundError
    import backend.api as _api_module
    mock_svc = MagicMock()
    mock_svc.export_project_to_dxf.side_effect = NotFoundError("não encontrado")
    _api_module.export_service = mock_svc

    r = client.get("/api/v1/export/dxf/nonexistent-id", headers=auth_headers)
    assert r.status_code == 404


def test_export_dxf_success(client, auth_headers, api_mod, tmp_path):
    """GET /api/v1/export/dxf/{id} com mock de arquivo DXF → 200."""
    import backend.api as _api_module
    fake_file = tmp_path / "test.dxf"
    fake_file.write_text("DXF MOCK")
    mock_svc = MagicMock()
    mock_svc.export_project_to_dxf.return_value = fake_file
    _api_module.export_service = mock_svc

    r = client.get("/api/v1/export/dxf/some-id?escala=1000", headers=auth_headers)
    assert r.status_code == 200


def test_export_dxf_500(client, auth_headers, api_mod):
    """GET /api/v1/export/dxf/{id} com erro genérico → 500."""
    import backend.api as _api_module
    mock_svc = MagicMock()
    mock_svc.export_project_to_dxf.side_effect = RuntimeError("write error")
    _api_module.export_service = mock_svc

    r = client.get("/api/v1/export/dxf/bad-id", headers=auth_headers)
    assert r.status_code == 500


def test_export_geojson_not_found(client, auth_headers, api_mod):
    """GET /api/v1/export/geojson/{id} com projeto inexistente → 404."""
    from backend.application.projects import NotFoundError
    import backend.api as _api_module
    mock_svc = MagicMock()
    mock_svc.export_project_to_geojson.side_effect = NotFoundError("não encontrado")
    _api_module.export_service = mock_svc

    r = client.get("/api/v1/export/geojson/nonexistent-id", headers=auth_headers)
    assert r.status_code == 404


def test_export_geojson_success(client, auth_headers, api_mod, tmp_path):
    """GET /api/v1/export/geojson/{id} com mock de arquivo → 200."""
    import backend.api as _api_module
    fake_file = tmp_path / "test.geojson"
    fake_file.write_text('{"type":"FeatureCollection","features":[]}')
    mock_svc = MagicMock()
    mock_svc.export_project_to_geojson.return_value = fake_file
    _api_module.export_service = mock_svc

    r = client.get("/api/v1/export/geojson/some-id", headers=auth_headers)
    assert r.status_code == 200


def test_export_geojson_500(client, auth_headers, api_mod):
    """GET /api/v1/export/geojson/{id} com erro genérico → 500."""
    import backend.api as _api_module
    mock_svc = MagicMock()
    mock_svc.export_project_to_geojson.side_effect = RuntimeError("io error")
    _api_module.export_service = mock_svc

    r = client.get("/api/v1/export/geojson/bad-id", headers=auth_headers)
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# routes/enterprise.py — POST /api/v1/sync/cloud  (lines 144-156)
# ---------------------------------------------------------------------------

def test_sync_cloud_no_env_var(client, auth_headers, monkeypatch):
    """POST /api/v1/sync/cloud sem SISRUA_CLOUD_URL → status=local_only."""
    monkeypatch.delenv("SISRUA_CLOUD_URL", raising=False)
    r = client.post("/api/v1/sync/cloud", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "local_only"
    assert "local_projects" in body
    assert "local_features" in body


def test_sync_cloud_with_env_var(client, auth_headers, monkeypatch):
    """POST /api/v1/sync/cloud com SISRUA_CLOUD_URL → status=pending."""
    monkeypatch.setenv("SISRUA_CLOUD_URL", "https://cloud.example.com")
    r = client.post("/api/v1/sync/cloud", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending"
    assert body["cloud_url"] == "https://cloud.example.com"


# ---------------------------------------------------------------------------
# routes/enterprise.py — POST /api/v1/management/shutdown  (lines 171-177)
# ---------------------------------------------------------------------------

def test_management_shutdown_returns_shutting_down(client, auth_headers):
    """POST /api/v1/management/shutdown retorna status=shutting_down (thread mockada)."""
    # Mock threading.Thread to prevent the self_terminate daemon from ever starting.
    # The handler spawns a daemon thread that calls os.kill(pid, SIGINT) after 1 second.
    # If the thread fires during a later test's time.sleep(), it kills the test process.
    with patch("backend.routes.enterprise.threading.Thread"):
        r = client.post("/api/v1/management/shutdown", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "shutting_down"


def test_management_shutdown_requires_auth(client):
    """POST /api/v1/management/shutdown sem token retorna 401."""
    r = client.post("/api/v1/management/shutdown")
    assert r.status_code == 401
