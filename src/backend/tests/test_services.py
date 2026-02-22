import pytest
from unittest.mock import MagicMock, patch
from backend.services.projects import ProjectService, NotFoundError, ConflictError
from backend.services.health import HealthService
from backend.services.elevation import ElevationService

# --- Project Service Tests ---
def test_project_service_get_not_found():
    # Mock DB connection
    with patch('backend.services.projects.get_db_connection') as mock_db:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_db.return_value = mock_conn
        
        svc = ProjectService()
        assert svc.get_project("p1") is None

def test_project_service_get_success():
    with patch('backend.services.projects.get_db_connection') as mock_db:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("p1", "Project 1", "EPSG:31983", 1, "2023-01-01")
        mock_db.return_value = mock_conn
        
        svc = ProjectService()
        p = svc.get_project("p1")
        assert p["project_name"] == "Project 1"
        assert p["version"] == 1

def test_project_service_update_conflict():
    with patch('backend.services.projects.get_db_connection') as mock_db:
        mock_conn = MagicMock()
        # Mock cursor for UPDATE
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.execute.return_value = mock_cursor
        
        # Mock check if exists
        mock_conn.execute.side_effect = [
            mock_cursor, # UPDATE
            MagicMock(fetchone=MagicMock(return_value=(2,))) # SELECT version
        ]
        
        mock_db.return_value = mock_conn
        
        svc = ProjectService()
        with pytest.raises(ConflictError):
            svc.update_project("p1", {"project_name": "New"}, expected_version=1)

# --- Health Service Tests ---
def test_health_service_check():
    with patch('backend.services.health.get_db_connection') as mock_db, \
         patch('backend.services.health.cache_service') as mock_cache, \
         patch('pyproj.Proj', return_value=MagicMock()):
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn 
        
        mock_cache.get.return_value = {"ts": 1234.5}
        
        # Mock sys.modules for osgeo/gdal if missing
        import sys
        mock_gdal = MagicMock()
        with patch.dict(sys.modules, {'osgeo': mock_gdal, 'osgeo.gdal': mock_gdal}):
            svc = HealthService()
            resp = svc.check_health()
            # It might still be degraded if env vars are missing, which is fine
            assert resp.status in ("up", "degraded")

# --- Elevation Service Tests (Partial Mocks) ---
def test_elevation_service_caching():
    mock_cache = MagicMock()
    mock_cache.get.return_value = {"z": 123.45} # Cached value as dict
    
    svc = ElevationService(cache=mock_cache)
    z = svc.get_elevation_at_point(-23.55, -46.63)
    
    assert z == 123.45
    assert not mock_cache.set.called # Should not set if hit cache


def test_elevation_service_requires_cache():
    """ElevationService.__init__ deve exigir o parâmetro cache (não pode ser instanciado sem)."""
    import inspect
    sig = inspect.signature(ElevationService.__init__)
    params = sig.parameters
    assert "cache" in params, "ElevationService deve ter parâmetro 'cache'"
    # cache não tem valor default → é obrigatório
    assert params["cache"].default is inspect.Parameter.empty, "cache deve ser obrigatório"


def test_geojson_elevation_injection_uses_cache():
    """
    Verifica que prepare_geojson_compute instancia ElevationService com cache
    ao injetar elevação — garante que o bug 'ElevationService()' sem cache está corrigido.
    """
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"highway": "residential", "name": "Rua Teste"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-42.92185, -22.15018],
                        [-42.92085, -22.15018],
                    ],
                },
            }
        ],
    }

    captured_args = []

    original_init = ElevationService.__init__

    def spy_init(self, cache, cache_dir=None):
        captured_args.append(cache)
        self.base_url = ""
        self.api_key = None
        self.cache = cache
        self.cache_dir = Path(tempfile.mkdtemp())

    with patch.object(ElevationService, "__init__", spy_init), \
         patch.object(ElevationService, "get_elevation_profile", return_value=[850.0]):
        from backend.services.geojson import prepare_geojson_compute
        result = prepare_geojson_compute(geojson)

    assert result is not None
    # Garante que ElevationService foi instanciado com um cache (não None)
    assert len(captured_args) > 0, "ElevationService não foi instanciado durante injeção de elevação"
    assert captured_args[0] is not None, "ElevationService instanciado sem cache (bug regressão)"
