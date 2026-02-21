# BIM_LITE_TEST_V1: NO OSMNX
import importlib
import os
import time
import pytest
from fastapi.testclient import TestClient

def _import_api_with_token(token: str):
    """
    backend.api lê AUTH_TOKEN no import. Para testes, precisamos setar env antes e recarregar o módulo.
    """
    os.environ["SISRUA_AUTH_TOKEN"] = token
    # BIM-LITE: No osmnx imports here or in backend.api
    from backend import api as api_mod
    importlib.reload(api_mod)
    return api_mod

@pytest.fixture()
def api_mod(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    return _import_api_with_token("test-token-123")

@pytest.fixture()
def client(api_mod):
    c = TestClient(api_mod.app, base_url="http://localhost:8000")
    c.headers.update({"Origin": "http://localhost:8000"})
    return c

def test_health_is_public(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_auth_check_requires_token(client):
    r = client.get("/api/v1/auth/check")
    assert r.status_code == 401

def test_auth_check_ok_with_token(client):
    r = client.get("/api/v1/auth/check", headers={"X-SisRua-Token": "test-token-123"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_prepare_job_geojson_completes(client, api_mod):
    payload = {
        "kind": "geojson",
        "geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"layer": "V_TEST", "name": "Rua Teste", "highway": "residential"},
                    "geometry": {"type": "LineString", "coordinates": [[-41.3235, -21.7634], [-41.3234, -21.7633]]},
                }
            ],
        },
    }
    r = client.post("/api/v1/jobs/prepare", json=payload, headers={"X-SisRua-Token": "test-token-123"})
    assert r.status_code == 200
    job = r.json()
    job_id = job["job_id"]
    
    deadline = time.time() + 10
    last = None
    while time.time() < deadline:
        r2 = client.get(f"/api/v1/jobs/{job_id}", headers={"X-SisRua-Token": "test-token-123"})
        assert r2.status_code == 200
        last = r2.json()
        if last["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert last is not None
    assert last["status"] == "completed"

def test_jobs_require_token(client):
    r = client.post("/api/v1/jobs/prepare", json={"kind": "geojson", "geojson": {}})
    assert r.status_code == 401

def test_create_prepare_job_osm_blocks_completes(client, api_mod, monkeypatch):
    import backend.gis_core.osm as osm_core
    
    class MockElevation:
        def get_elevation_profile(self, latlons): return [10.0] * len(latlons)
        def get_contours(self, *args): return []
        def get_elevation_at_point(self, lat, lon): return 10.0

    mock_raw_data = {
        "elements": [
            {"type": "node", "id": 1, "lat": -21.7634, "lon": -41.3235, "tags": {"highway": "street_light", "name": "Poste A"}},
            {"type": "node", "id": 2, "lat": -21.7630, "lon": -41.3230, "tags": {"power": "pole", "name": "Poste B"}},
            {"type": "node", "id": 3, "lat": -21.7632, "lon": -41.3232, "tags": {"amenity": "bench", "name": "Banco C"}},
            {"type": "way", "id": 4, "nodes": [1, 2], "tags": {"highway": "residential", "name": "Rua D"}}
        ]
    }
    
    monkeypatch.setattr(osm_core, "_fetch_overpass_data", lambda *args, **kwargs: mock_raw_data)
    
    import backend.services.executor as executor_mod
    monkeypatch.setattr(executor_mod, "ElevationService", lambda *args, **kwargs: MockElevation())
    
    payload = {
        "kind": "osm",
        "latitude": -21.7634,
        "longitude": -41.3235,
        "radius": 100
    }

    r = client.post("/api/v1/jobs/prepare", json=payload, headers={"X-SisRua-Token": "test-token-123"})
    assert r.status_code == 200
    job = r.json()
    job_id = job["job_id"]
    
    deadline = time.time() + 10
    last = None
    while time.time() < deadline:
        r2 = client.get(f"/api/v1/jobs/{job_id}", headers={"X-SisRua-Token": "test-token-123"})
        assert r2.status_code == 200
        last = r2.json()
        if last["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert last is not None
    assert last["status"] == "completed"

def test_create_prepare_job_geojson_blocks_completes(client, api_mod):
    payload = {
        "kind": "geojson",
        "geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"layer": "SISRUA_TEST_POINTS", "name": "Poste Teste", "block_name": "POSTE", "block_filepath": "POSTE_GENERICO.dxf", "rotation": 45.0, "scale": 1.5},
                    "geometry": {"type": "Point", "coordinates": [-41.3235, -21.7634]},
                },
                {
                    "type": "Feature",
                    "properties": {"layer": "V_TEST", "name": "Rua Teste", "highway": "residential"},
                    "geometry": {"type": "LineString", "coordinates": [[-41.3236, -21.7635], [-41.3234, -21.7633]]},
                }
            ],
        },
    }
    r = client.post("/api/v1/jobs/prepare", json=payload, headers={"X-SisRua-Token": "test-token-123"})
    assert r.status_code == 200
    job = r.json()
    job_id = job["job_id"]
    
    deadline = time.time() + 10
    last = None
    while time.time() < deadline:
        r2 = client.get(f"/api/v1/jobs/{job_id}", headers={"X-SisRua-Token": "test-token-123"})
        assert r2.status_code == 200
        last = r2.json()
        if last["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert last is not None
    assert last["status"] == "completed"


# --- Projects endpoint tests ---

def test_get_project_not_found(client):
    """GET /api/v1/projects/{id} deve retornar 404 para projeto inexistente."""
    from unittest.mock import patch
    import backend.routes.deps as deps

    with patch.object(deps.project_service, "get_project", return_value=None):
        r = client.get(
            "/api/v1/projects/nao-existe",
            headers={"X-SisRua-Token": "test-token-123"},
        )
    assert r.status_code == 404
    assert "não encontrado" in r.json()["detail"]


def test_get_project_requires_auth(client):
    """GET /api/v1/projects/{id} deve exigir token de autenticação."""
    r = client.get("/api/v1/projects/qualquer-id")
    assert r.status_code == 401


def test_get_project_success(client):
    """GET /api/v1/projects/{id} deve retornar o projeto quando encontrado."""
    from unittest.mock import patch
    import backend.routes.deps as deps

    fake_project = {
        "project_id": "proj-001",
        "project_name": "Rua Referência",
        "crs_out": "EPSG:31983",
        "version": 1,
        "creation_date": "2026-02-21T00:00:00",
    }

    with patch.object(deps.project_service, "get_project", return_value=fake_project):
        r = client.get(
            "/api/v1/projects/proj-001",
            headers={"X-SisRua-Token": "test-token-123"},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["project_id"] == "proj-001"
    assert body["project_name"] == "Rua Referência"
    assert body["crs_out"] == "EPSG:31983"
    assert body["version"] == 1
