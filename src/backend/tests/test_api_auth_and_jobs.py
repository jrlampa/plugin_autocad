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


def test_geojson_invalid_returns_400(client):
    payload = {"kind": "geojson", "geojson": {"type": "FeatureCollection", "features": []}}
    r = client.post("/api/v1/jobs/prepare", json=payload, headers={"X-SisRua-Token": "test-token-123"})
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    deadline = time.time() + 10
    while time.time() < deadline:
        r2 = client.get(f"/api/v1/jobs/{job_id}", headers={"X-SisRua-Token": "test-token-123"})
        assert r2.status_code == 200
        job = r2.json()
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert job["status"] == "failed"
    assert "GeoJSON inválido" in (job.get("error") or job.get("message") or "")

