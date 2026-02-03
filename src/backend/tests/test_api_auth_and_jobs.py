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
    import osmnx # Explicitly import osmnx to ensure it's loaded in the test environment
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
    # Set base_url and default Origin for ISO 27001 compliance tests
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


def test_create_prepare_job_osm_blocks_completes(client, api_mod, monkeypatch):
    # Mock osmnx calls since it's not installed in CI
    # Need to set up mocks before any osmnx calls
    from shapely.geometry import Point, LineString
    
    class MockNode:
        def __init__(self, osmid, x, y, tags):
            self.osmid = osmid
            self.x = x
            self.y = y
            self.geometry = Point(x, y)
            self.tags = tags

        def to_dict(self):
            return self.tags

    class MockEdge:
        def __init__(self, u, v, key, geometry, tags):
            self.u = u
            self.v = v
            self.key = key
            self.geometry = geometry
            self.tags = tags

        def to_dict(self):
            return self.tags

    class MockRow:
        """Mock para uma linha retornada por iterrows()"""
        def __init__(self, item):
            self._item = item
            self.geometry = item.geometry if hasattr(item, 'geometry') else None
            # Make tags accessible as attributes for get() method
            if hasattr(item, 'tags'):
                self._tags = item.tags
                for key, value in item.tags.items():
                    setattr(self, key, value)
            else:
                self._tags = {}
        
        def get(self, key, default=None):
            # First try as attribute
            if hasattr(self, key) and not key.startswith('_'):
                return getattr(self, key)
            # Then try tags
            if hasattr(self, '_tags'):
                return self._tags.get(key, default)
            return default
        
        def to_dict(self):
            # Return tags dictionary directly
            if hasattr(self, '_tags'):
                return self._tags.copy()
            if hasattr(self._item, 'to_dict'):
                return self._item.to_dict()
            return {}
    
    class MockGeometrySeries:
        """Mock para edges.geometry que retorna uma série com notna()"""
        def __init__(self, gdf):
            self._gdf = gdf
        
        def notna(self):
            # Retorna uma lista booleana que pode ser usada para indexação
            return [True] * len(self._gdf._data)
    
    class MockGDF:
        def __init__(self, data):
            self._data = data
            self._geometry_series = MockGeometrySeries(self)

        def iterrows(self):
            for item in self._data:
                yield None, MockRow(item) # row_idx, row_series

        def itertuples(self, index=True, name='Pandas'):
            for item in self._data:
                yield MockRow(item)

        @property
        def geometry(self):
            return self._geometry_series
        
        def __getitem__(self, key):
            # Quando indexado com lista booleana (resultado de notna()), retorna o próprio objeto
            # Isso simula edges[edges.geometry.notna()] retornando edges (todos passam)
            if isinstance(key, list) and len(key) == len(self._data) and all(isinstance(x, bool) for x in key):
                return self
            return self

    mock_nodes_data = [
        MockNode(1, -41.3235, -21.7634, {"highway": "street_light", "name": "Poste A"}),
        MockNode(2, -41.3230, -21.7630, {"power": "pole", "name": "Poste B"}),
        MockNode(3, -41.3232, -21.7632, {"amenity": "bench", "name": "Banco C"}),
    ]
    mock_edges_data = [
        MockEdge(1, 2, 0, LineString([[-41.3235, -21.7634], [-41.3230, -21.7630]]), {"highway": "residential", "name": "Rua D"}),
    ]

    mock_nodes_gdf = MockGDF(mock_nodes_data)
    mock_edges_gdf = MockGDF(mock_edges_data)

    # Create a mock graph object that can be passed to graph_to_gdfs
    class MockGraph:
        pass
    
    mock_graph = MockGraph()

    def mock_graph_from_point(point, dist, network_type):
        return mock_graph

    def mock_graph_to_gdfs(graph):
        return mock_nodes_gdf, mock_edges_gdf

    # Mock osmnx module - it's already imported in _import_api_with_token, so we patch it
    import osmnx
    monkeypatch.setattr(osmnx, "graph_from_point", mock_graph_from_point)
    monkeypatch.setattr(osmnx, "graph_to_gdfs", mock_graph_to_gdfs)
    monkeypatch.setattr(osmnx, "project_graph", lambda g, to_crs: g) 

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
    
    deadline = time.time() + 30 # Increased timeout for mock/slow disk
    last = None
    while time.time() < deadline:
        r2 = client.get(f"/api/v1/jobs/{job_id}", headers={"X-SisRua-Token": "test-token-123"})
        assert r2.status_code == 200
        last = r2.json()
        if last["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert last is not None
    if last["status"] == "failed":
        error_msg = last.get("error", "Unknown error")
        message = last.get("message", "No message")
        pytest.fail(f"OSM Job Failed. Error: {error_msg}, Message: {message}")
    assert last["status"] == "completed"
    assert last["result"]["crs_out"].startswith("EPSG:")
    assert isinstance(last["result"]["features"], list)
    
    # Verifica se existem features de ponto (blocos)
    point_features = [f for f in last["result"]["features"] if f["feature_type"] == "Point"]
    assert len(point_features) >= 3, "Should find 3 point features (blocks)"
    
    # Verifica propriedades de um bloco
    f_point_poste_a = next((f for f in point_features if f["name"] == "Poste A"), None)
    assert f_point_poste_a is not None
    assert f_point_poste_a["feature_type"] == "Point"
    assert "insertion_point_xy" in f_point_poste_a
    assert f_point_poste_a["block_name"] == "POSTE"
    assert f_point_poste_a["layer"] == "SISRUA_OSM_PONTOS"

    f_point_poste_b = next((f for f in point_features if f["name"] == "Poste B"), None)
    assert f_point_poste_b is not None
    assert f_point_poste_b["block_name"] == "POSTE"

    f_point_banco_c = next((f for f in point_features if f["name"] == "Banco C"), None)
    assert f_point_banco_c is not None
    assert f_point_banco_c["block_name"] == "BANCO"


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

