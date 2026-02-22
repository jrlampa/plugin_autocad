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


# ---------------------------------------------------------------------------
# ElevationService.get_elevation_profile — null guard (tif_path is None)
# ---------------------------------------------------------------------------

def test_elevation_profile_returns_nones_when_no_dem():
    """
    get_elevation_profile deve retornar lista de None quando nenhum DEM
    estiver disponível (tif_path is None), sem lançar exceção.
    """
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    svc = ElevationService(cache=mock_cache)
    # Simula ausência total de DEM (offline, sem cache local)
    with patch.object(svc, "get_elevation_grid", return_value=None):
        coords = [(-22.15018, -42.92185), (-22.15118, -42.92285)]
        result = svc.get_elevation_profile(coords)

    assert result == [None, None], (
        f"Esperava [None, None] quando DEM indisponível, obteve {result}"
    )


def test_elevation_contours_returns_empty_when_no_dem():
    """
    get_contours deve retornar lista vazia quando nenhum DEM estiver
    disponível (tif_path is None), sem lançar exceção.
    """
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    svc = ElevationService(cache=mock_cache)
    with patch.object(svc, "get_elevation_grid", return_value=None):
        result = svc.get_contours(-22.18, -42.95, -22.12, -42.89)

    assert result == [], (
        f"Esperava [] quando DEM indisponível, obteve {result}"
    )


# ---------------------------------------------------------------------------
# ExportService.export_project_to_dxf
# ---------------------------------------------------------------------------

def test_export_service_dxf_not_found():
    """export_project_to_dxf deve lançar NotFoundError para projeto inexistente."""
    import sqlite3
    import tempfile
    from pathlib import Path
    from backend.services.export_service import ExportService
    from backend.services.projects import NotFoundError

    tmp_db = Path(tempfile.mkdtemp()) / "test.db"
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        "CREATE TABLE Projects (project_id TEXT, project_name TEXT, crs_out TEXT)"
    )
    conn.execute(
        "CREATE TABLE CadFeatures (project_id TEXT, feature_type TEXT, layer TEXT,"
        " name TEXT, highway TEXT, width_m REAL, color TEXT, elevation REAL,"
        " slope REAL, original_geojson_properties TEXT, coords_xy TEXT,"
        " insertion_point_xy TEXT, block_name TEXT, rotation REAL, scale REAL)"
    )
    conn.commit()
    conn.close()

    svc = ExportService(db_path=tmp_db)
    with pytest.raises(NotFoundError):
        svc.export_project_to_dxf("projeto-inexistente")


def test_export_service_dxf_creates_valid_file():
    """export_project_to_dxf deve gerar um arquivo DXF válido para projeto real."""
    import sqlite3
    import tempfile
    import json
    from pathlib import Path
    import ezdxf
    from backend.services.export_service import ExportService

    tmp_db = Path(tempfile.mkdtemp()) / "test.db"
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        "CREATE TABLE Projects (project_id TEXT, project_name TEXT, crs_out TEXT)"
    )
    conn.execute(
        "CREATE TABLE CadFeatures (project_id TEXT, feature_type TEXT, layer TEXT,"
        " name TEXT, highway TEXT, width_m REAL, color TEXT, elevation REAL,"
        " slope REAL, original_geojson_properties TEXT, coords_xy TEXT,"
        " insertion_point_xy TEXT, block_name TEXT, rotation REAL, scale REAL)"
    )
    conn.execute(
        "INSERT INTO Projects VALUES (?, ?, ?)",
        ("proj-dxf-01", "Via Referência", "EPSG:31983"),
    )
    # One polyline feature (UTM REF_2: E≈714316, N≈7549084 + 100m)
    coords = [[714316.0, 7549084.0], [714416.0, 7549084.0]]
    conn.execute(
        "INSERT INTO CadFeatures VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "proj-dxf-01", "Polyline", "SISRUA_OSM_HIGHWAY",
            "Via Teste", "residential", 6.0, None, 850.0, None,
            json.dumps({}), json.dumps(coords), json.dumps([]), None, 0.0, 1.0,
        ),
    )
    conn.commit()
    conn.close()

    svc = ExportService(db_path=tmp_db)
    dxf_path = svc.export_project_to_dxf("proj-dxf-01", escala=1_000)

    assert dxf_path.exists(), "Arquivo DXF não foi criado"
    assert dxf_path.stat().st_size > 0, "Arquivo DXF está vazio"

    doc = ezdxf.readfile(str(dxf_path))
    assert doc.dxfversion >= "AC1024", "Versão DXF deve ser R2010+"
    msp = doc.modelspace()
    plines = list(msp.query("LWPOLYLINE"))
    assert len(plines) == 1, f"Esperava 1 polilinha, obteve {len(plines)}"


# ---------------------------------------------------------------------------
# OSM module-level classes (_OsmWayRow / _OsmNodeRow)
# ---------------------------------------------------------------------------

def test_osm_way_row_module_level():
    """_OsmWayRow deve ser uma classe de módulo (não definida inline em loop)."""
    from backend.gis_core.osm import _OsmWayRow

    way = {"tags": {"highway": "residential", "name": "Rua Teste"}}

    class _FakeGeom:
        pass

    row = _OsmWayRow(way, _FakeGeom())
    assert row.highway == "residential"
    assert row.name == "Rua Teste"
    assert row._asdict() == {"highway": "residential", "name": "Rua Teste"}


def test_osm_node_row_module_level():
    """_OsmNodeRow deve ser uma classe de módulo com atributos corretos."""
    from backend.gis_core.osm import _OsmNodeRow

    node = {"tags": {"power": "pole", "name": "Poste"}}
    row = _OsmNodeRow(node, 714316.0, 7549084.0)

    assert row.power == "pole"
    assert row.name == "Poste"
    assert row.highway is None
    assert row._asdict() == {"power": "pole", "name": "Poste"}
    # Verifica que o ponto foi criado com as coordenadas corretas
    assert abs(row.geometry.x - 714316.0) < 0.01
    assert abs(row.geometry.y - 7549084.0) < 0.01
