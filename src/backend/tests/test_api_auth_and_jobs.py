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
    from backend import api as api_mod  # noqa: WPS433 (import local intencional)

    importlib.reload(api_mod)
    return api_mod


@pytest.fixture()
def api_mod(tmp_path, monkeypatch):
    # Evita escrever cache/log em diretórios reais.
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    return _import_api_with_token("test-token-123")


@pytest.fixture()
def client(api_mod):
    return TestClient(api_mod.app)


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
    assert job["status"] in ("queued", "processing", "completed")

    # Polling simples até concluir (job roda em thread daemon)
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
    assert last["result"]["crs_out"].startswith("EPSG:")
    assert isinstance(last["result"]["features"], list)
    assert len(last["result"]["features"]) >= 1
    f0 = last["result"]["features"][0]
    assert f0["layer"] == "V_TEST"
    assert "coords_xy" in f0


def test_jobs_require_token(client):
    r = client.post("/api/v1/jobs/prepare", json={"kind": "geojson", "geojson": {}})
    assert r.status_code == 401


    assert job["status"] == "failed"
    assert "GeoJSON inválido" in (job.get("error") or job.get("message") or "")

def test_create_prepare_job_osm_blocks_completes(client, api_mod):
    # Latitude/Longitude em área que deve conter street_lights/poles
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
    
    deadline = time.time() + 30 # Aumentado o timeout para dados OSM
    last = None
    while time.time() < deadline:
        r2 = client.get(f"/api/v1/jobs/{job_id}", headers={"X-SisRua-Token": "test-token-123"})
        assert r2.status_code == 200
        last = r2.json()
        if last["status"] in ("completed", "failed"):
            break
        time.sleep(0.5)

    assert last is not None
    assert last["status"] == "completed"
    assert last["result"]["crs_out"].startswith("EPSG:")
    assert isinstance(last["result"]["features"], list)
    
    # Verifica se existem features de ponto (blocos)
    point_features = [f for f in last["result"]["features"] if f["feature_type"] == "Point"]
    assert len(point_features) >= 1, "Should find at least one point feature (block)"
    
    # Verifica propriedades de um bloco
    f_point = point_features[0]
    assert f_point["feature_type"] == "Point"
    assert "insertion_point_xy" in f_point
    assert "block_name" in f_point
    assert f_point["block_name"] in ["POSTE", "BANCO"] # Based on current mapping in api.py
    assert "block_filepath" not in f_point # C# will resolve this from config
    assert f_point["layer"] == "SISRUA_OSM_PONTOS"

    # Verifica se ainda existem features de polilinha
    polyline_features = [f for f in last["result"]["features"] if f["feature_type"] == "Polyline"]
    assert len(polyline_features) >= 1, "Should still find polyline features"


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
    assert job["status"] in ("queued", "processing", "completed")

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
    assert last["result"]["crs_out"].startswith("EPSG:")
    assert isinstance(last["result"]["features"], list)
    assert len(last["result"]["features"]) == 2 # One polyline, one point

    # Verify point feature
    f_point = next((f for f in last["result"]["features"] if f["feature_type"] == "Point"), None)
    assert f_point is not None
    assert f_point["layer"] == "SISRUA_TEST_POINTS"
    assert f_point["name"] == "Poste Teste"
    assert f_point["block_name"] == "POSTE"
    assert f_point["block_filepath"] == "POSTE_GENERICO.dxf"
    assert f_point["rotation"] == 45.0
    assert f_point["scale"] == 1.5
    assert len(f_point["insertion_point_xy"]) == 2 # X, Y coordinates

    # Verify polyline feature
    f_polyline = next((f for f in last["result"]["features"] if f["feature_type"] == "Polyline"), None)
    assert f_polyline is not None
    assert f_polyline["layer"] == "V_TEST"
    assert f_polyline["name"] == "Rua Teste"
    assert "coords_xy" in f_polyline

