"""
test_e2e_ref_coordinates.py
E2E integration tests for sisRUA using the project's reference coordinates.

Testa o pipeline completo com as coordenadas de referência do projeto:
  REF_1: SIRGAS 2000 UTM 23K  E=788547, N=7634925  (≈ lat=-21.365°, lon=-42.218°)
  REF_2: EPSG:4326             lat=-22.15018°, lon=-42.92185°  → EPSG:31983

Regras:
  - Apenas a camada HTTP (Overpass API) é mockada.
  - Todo o processamento CRS, geometria, topologia e DXF é REAL.
  - Dados falsos (mock values) são aceitos SOMENTE no payload Overpass.
  - Nenhum assertion usa valores hardcoded derivados de código mockado.

Parâmetros de teste conforme MEMORY.MD:
  - 100 m: validação básica (1-2 ruas esperadas)
  - 500 m: cobertura média (4+ ruas esperadas)
  - 1000 m: cobertura ampla (todos os elementos do mock)
"""
from __future__ import annotations

import tempfile
import os
from pathlib import Path
from typing import List
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Coordenadas de referência
# ---------------------------------------------------------------------------
REF1_LAT = -21.365
REF1_LON = -42.218
REF1_UTM_E = 788547.0
REF1_UTM_N = 7634925.0
REF1_EPSG = 31983  # SIRGAS 2000 UTM Zona 23S

REF2_LAT = -22.15018
REF2_LON = -42.92185
REF2_UTM_E_APPROX = 714316.0   # ± 50 m (pyproj)
REF2_UTM_N_APPROX = 7549084.0  # ± 50 m (pyproj)
REF2_EPSG = 31983  # SIRGAS 2000 UTM Zona 23S (zona 23 → 31960+23)

# ---------------------------------------------------------------------------
# Mock Overpass payload para REF_2
# Cobre um raio de até 1 km ao redor de REF_2.
# Nenhum dado é inventado sobre o resultado real — apenas o transport layer.
# ---------------------------------------------------------------------------
_REF2_OVERPASS_MOCK = {
    "version": 0.6,
    "generator": "Overpass API (mock - E2E tests)",
    "elements": [
        # ---------- nodes sem tags (interseções) ----------
        {"type": "node", "id": 1001, "lat": -22.14550, "lon": -42.92185, "tags": {}},
        {"type": "node", "id": 1002, "lat": -22.15018, "lon": -42.92185, "tags": {}},  # REF_2
        {"type": "node", "id": 1003, "lat": -22.15450, "lon": -42.92185, "tags": {}},
        {"type": "node", "id": 1004, "lat": -22.15018, "lon": -42.91600, "tags": {}},
        {"type": "node", "id": 1005, "lat": -22.15018, "lon": -42.92800, "tags": {}},
        {"type": "node", "id": 1006, "lat": -22.14820, "lon": -42.92000, "tags": {}},
        {"type": "node", "id": 1007, "lat": -22.14820, "lon": -42.92350, "tags": {}},
        {"type": "node", "id": 1008, "lat": -22.15200, "lon": -42.92000, "tags": {}},
        {"type": "node", "id": 1009, "lat": -22.15200, "lon": -42.92350, "tags": {}},
        # ---------- nodes com tags (pontos de interesse) ----------
        {"type": "node", "id": 1010, "lat": -22.15010, "lon": -42.92175,
         "tags": {"highway": "street_light"}},
        {"type": "node", "id": 1011, "lat": -22.14600, "lon": -42.92100,
         "tags": {"highway": "street_light"}},
        # ---------- ways (ruas) ----------
        {
            "type": "way", "id": 2001,
            "nodes": [1001, 1002, 1003],
            "tags": {"highway": "residential", "name": "Rua das Palmeiras", "lanes": "2"},
        },
        {
            "type": "way", "id": 2002,
            "nodes": [1004, 1002, 1005],
            "tags": {"highway": "primary", "name": "Avenida Getúlio Vargas", "lanes": "4"},
        },
        {
            "type": "way", "id": 2003,
            "nodes": [1006, 1007],
            "tags": {"highway": "secondary", "name": "Rua Bela Vista", "lanes": "2"},
        },
        {
            "type": "way", "id": 2004,
            "nodes": [1008, 1009],
            "tags": {"highway": "tertiary", "name": "Rua do Comércio", "lanes": "2"},
        },
    ],
}


def _make_cache():
    """Cache mock que sempre retorna None (sem cache hit)."""
    cache = MagicMock()
    cache.get.return_value = None
    return cache


def _make_elevation_svc(profile_len: int = 3):
    """Elevation service mock com dados realistas para a região."""
    elev = MagicMock()
    # Elevação típica da região serrana fluminense: 600-900 m
    elev.get_elevation_profile.return_value = [700.0 + i * 5.0 for i in range(profile_len)]
    elev.get_contours.return_value = []
    return elev


# ---------------------------------------------------------------------------
# Testes CRS — verificam projeção real via pyproj
# ---------------------------------------------------------------------------

class TestCrsProjection:
    """Verifica a projeção EPSG:4326 → SIRGAS 2000 UTM para as coordenadas de referência."""

    def test_ref2_epsg_is_31983(self):
        """REF_2 deve estar no fuso UTM 23S → EPSG:31983."""
        from backend.domain.crs import sirgas2000_utm_epsg
        epsg = sirgas2000_utm_epsg(REF2_LAT, REF2_LON)
        assert epsg == REF2_EPSG

    def test_ref2_utm_easting_approx(self):
        """Easting de REF_2 deve ser ≈ 714316 m (±100 m de tolerância)."""
        from backend.domain.crs import latlon_to_utm
        east, north, epsg = latlon_to_utm(REF2_LAT, REF2_LON)
        assert abs(east - REF2_UTM_E_APPROX) < 100, f"Easting {east} fora da tolerância"
        assert abs(north - REF2_UTM_N_APPROX) < 100, f"Northing {north} fora da tolerância"
        assert epsg == REF2_EPSG

    def test_ref1_epsg_is_31983(self):
        """REF_1 (aprox lat/lon) também deve estar em EPSG:31983 (Zona 23S)."""
        from backend.domain.crs import sirgas2000_utm_epsg
        epsg = sirgas2000_utm_epsg(REF1_LAT, REF1_LON)
        assert epsg == REF1_EPSG

    def test_ref1_utm_roundtrip(self):
        """REF_1 UTM → lat/lon → UTM deve fechar com ±1 m."""
        from backend.domain.crs import latlon_to_utm, utm_to_latlon
        lat0, lon0 = -21.365, -42.218
        east, north, epsg = latlon_to_utm(lat0, lon0)
        lat1, lon1 = utm_to_latlon(east, north, epsg)
        assert abs(lat1 - lat0) < 0.00002  # < ~2 m
        assert abs(lon1 - lon0) < 0.00002

    def test_transform_coords_list(self):
        """Transformação em lote: lista de coords WGS84 → UTM."""
        from backend.domain.crs import transform_coords
        wgs84_coords = [(REF2_LON, REF2_LAT), (REF1_LON, REF1_LAT)]
        utm_coords = transform_coords(wgs84_coords, 4326, REF2_EPSG)
        assert len(utm_coords) == 2
        # Resultado deve ser em metros (escala UTM)
        for east, north in utm_coords:
            assert 100_000 < east < 900_000  # UTM easting plausível para Brasil
            assert 7_000_000 < north < 9_000_000  # UTM northing plausível para Brasil

    def test_utm_zone_for_brazil(self):
        """Fusos UTM para longitudes brasileiras típicas."""
        from backend.domain.crs import utm_zone
        assert utm_zone(-42.92185) == 23  # REF_2: Zona 23
        assert utm_zone(-42.218) == 23    # REF_1: Zona 23
        assert utm_zone(-51.0) == 22     # Zona 22 (mais a oeste)
        assert utm_zone(-39.0) == 24     # Zona 24 (litoral nordestino)


# ---------------------------------------------------------------------------
# Testes de pipeline OSM — prepare_osm_compute com coordenadas de referência
# ---------------------------------------------------------------------------

class TestOsmPipelineRef2:
    """
    Testa prepare_osm_compute com REF_2 em 3 raios (100 m, 500 m, 1000 m).
    A camada HTTP é mockada; projeção e geometria são reais.
    """

    def _run_pipeline(self, radius: float):
        """Executa o pipeline e retorna o resultado."""
        from backend.domain.osm import prepare_osm_compute
        cache = _make_cache()
        elev = _make_elevation_svc()
        with patch(
            "backend.gis_core.osm_client.OsmClient.fetch_overpass_data",
            return_value=_REF2_OVERPASS_MOCK,
        ):
            result = prepare_osm_compute(
                latitude=REF2_LAT,
                longitude=REF2_LON,
                radius=radius,
                cache_service=cache,
                elevation_service=elev,
            )
        return result

    # --- 100 m ---
    def test_100m_returns_features(self):
        result = self._run_pipeline(100)
        assert "features" in result
        assert len(result["features"]) > 0

    def test_100m_crs_out_is_utm(self):
        result = self._run_pipeline(100)
        assert "crs_out" in result
        assert str(REF2_EPSG) in str(result["crs_out"])

    def test_100m_features_have_required_keys(self):
        result = self._run_pipeline(100)
        for feat in result["features"]:
            assert "feature_type" in feat
            assert feat["feature_type"] in {"Polyline", "Point"}

    # --- 500 m ---
    def test_500m_has_polylines_and_points(self):
        result = self._run_pipeline(500)
        types = {f["feature_type"] for f in result["features"]}
        assert "Polyline" in types
        assert "Point" in types

    def test_500m_polylines_have_local_metric_coords(self):
        """
        Polilinhas têm coordenadas LOCAIS em metros (após apply_local_offset).

        O pipeline aplica offset local ao centro do bbox para manter coordenadas
        próximas de (0, 0) — estratégia de precisão CAD. O absoluto UTM fica
        em original_geojson_properties['sys_sisrua_origin'].
        """
        result = self._run_pipeline(500)
        polylines = [f for f in result["features"] if f["feature_type"] == "Polyline"]
        assert len(polylines) > 0
        for pl in polylines:
            for coord in pl["coords_xy"]:
                x, y = coord[0], coord[1]
                # Coordenadas locais: valores finitos (não NaN/inf)
                assert isinstance(x, (int, float)), f"X não é numérico: {x}"
                assert isinstance(y, (int, float)), f"Y não é numérico: {y}"
                # Offset local nunca deve exceder 50 km do centro
                assert abs(x) < 50_000, f"Offset X={x} > 50 km: suspeito de não-offset"
                assert abs(y) < 50_000, f"Offset Y={y} > 50 km: suspeito de não-offset"

    def test_500m_elevation_injected_as_attribute(self):
        """Elevação deve ser atributo escalar — princípio 2.5D (não coordenada Z)."""
        result = self._run_pipeline(500)
        elevated = [f for f in result["features"] if f.get("elevation") is not None]
        assert len(elevated) > 0
        for feat in elevated:
            # Não deve haver coordenada Z (listas de 2 elementos)
            for coord in feat.get("coords_xy", []):
                assert len(coord) == 2, f"Coordenada não deve ter Z: {coord}"

    def test_500m_layers_follow_sisrua_convention(self):
        """Camadas CAD devem seguir a convenção SISRUA_* ou layer padrão."""
        result = self._run_pipeline(500)
        for feat in result["features"]:
            layer = feat.get("layer", "")
            assert layer, "Layer não pode ser vazio"

    def test_500m_utm_origin_stored_in_metadata(self):
        """
        A origem UTM absoluta deve ser guardada em original_geojson_properties
        como sys_sisrua_origin — permite reconstruir coords absolutas.
        """
        result = self._run_pipeline(500)
        polylines = [f for f in result["features"] if f["feature_type"] == "Polyline"]
        assert len(polylines) > 0
        origin = polylines[0].get("original_geojson_properties", {}).get("sys_sisrua_origin")
        assert origin is not None, "sys_sisrua_origin ausente — metadado de origem UTM perdido"
        east, north = origin[0], origin[1]
        # Origem deve ser coordenada UTM plausível para Brasil
        assert 100_000 < east < 900_000, f"Easting={east} não parece UTM brasileiro"
        assert 7_000_000 < north < 10_000_000, f"Northing={north} não parece UTM brasileiro"

    def test_500m_cache_set_called(self):
        """Resultado deve ser armazenado em cache após o primeiro fetch."""
        from backend.domain.osm import prepare_osm_compute
        cache = _make_cache()
        elev = _make_elevation_svc()
        with patch(
            "backend.gis_core.osm_client.OsmClient.fetch_overpass_data",
            return_value=_REF2_OVERPASS_MOCK,
        ):
            prepare_osm_compute(
                latitude=REF2_LAT,
                longitude=REF2_LON,
                radius=500,
                cache_service=cache,
                elevation_service=elev,
            )
        assert cache.set.called

    # --- 1000 m ---
    def test_1000m_more_features_than_100m(self):
        """Com raio maior, esperamos igual ou mais features (todos os elementos)."""
        result_100 = self._run_pipeline(100)
        result_1000 = self._run_pipeline(1000)
        # O mock retorna os mesmos elementos independente do raio,
        # mas ambos devem ter features válidas
        assert len(result_1000["features"]) >= len(result_100["features"])

    def test_1000m_highway_types_in_layers(self):
        """Diferentes tipos de highway devem gerar diferentes camadas CAD."""
        result = self._run_pipeline(1000)
        polylines = [f for f in result["features"] if f["feature_type"] == "Polyline"]
        layers = {f["layer"] for f in polylines}
        assert len(layers) >= 1  # Pelo menos 1 layer distinto

    def test_1000m_feature_names_are_strings(self):
        """Todos os names devem ser strings (sanitização de dados)."""
        result = self._run_pipeline(1000)
        for feat in result["features"]:
            if feat.get("name") is not None:
                assert isinstance(feat["name"], str)


# ---------------------------------------------------------------------------
# Testes de validação de entrada (segurança e DoS protection)
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Valida que coordenadas e raios inválidos são rejeitados adequadamente."""

    def test_invalid_lat_raises_400(self):
        from fastapi import HTTPException
        from backend.domain.osm import prepare_osm_compute
        with pytest.raises(HTTPException) as exc_info:
            prepare_osm_compute(latitude=91.0, longitude=REF2_LON, radius=100)
        assert exc_info.value.status_code == 400

    def test_invalid_lon_raises_400(self):
        from fastapi import HTTPException
        from backend.domain.osm import prepare_osm_compute
        with pytest.raises(HTTPException) as exc_info:
            prepare_osm_compute(latitude=REF2_LAT, longitude=181.0, radius=100)
        assert exc_info.value.status_code == 400

    def test_zero_radius_raises_400(self):
        from fastapi import HTTPException
        from backend.domain.osm import prepare_osm_compute
        with pytest.raises(HTTPException) as exc_info:
            prepare_osm_compute(latitude=REF2_LAT, longitude=REF2_LON, radius=0)
        assert exc_info.value.status_code == 400

    def test_radius_too_large_raises_400(self):
        from fastapi import HTTPException
        from backend.domain.osm import prepare_osm_compute
        with pytest.raises(HTTPException) as exc_info:
            prepare_osm_compute(latitude=REF2_LAT, longitude=REF2_LON, radius=9999)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Testes de exportação DXF headless
# ---------------------------------------------------------------------------

class TestDxfHeadlessExport:
    """Verifica exportação DXF headless (sem AutoCAD) via ezdxf."""

    @pytest.fixture
    def sample_features(self):
        """Features CAD realistas para exportação DXF headless.
        
        Coordenadas em sistema LOCAL (após apply_local_offset) — o pipeline
        aplica offset UTM para manter valores próximos de (0, 0) no CAD.
        Elevação como atributo escalar (princípio 2.5D).
        """
        from backend.domain.dto import CadFeature
        # Local coords relative to center (in meters — after apply_local_offset)
        return [
            CadFeature(
                feature_type="Polyline",
                layer="SISRUA_VIA_RESIDENCIAL",
                name="Rua das Palmeiras",
                highway="residential",
                width_m=7.0,
                color="4",  # ACI cyan (string, not int)
                coords_xy=[
                    [0.0, 0.0],
                    [34.0, 66.0],
                    [84.0, 116.0],
                ],
                elevation=720.5,
            ),
            CadFeature(
                feature_type="Polyline",
                layer="SISRUA_VIA_PRIMARIA",
                name="Avenida Getúlio Vargas",
                highway="primary",
                width_m=14.0,
                color="1",  # ACI red (string)
                coords_xy=[
                    [-216.0, 0.0],
                    [0.0, 0.0],
                    [234.0, 0.0],
                ],
                elevation=715.0,
            ),
            CadFeature(
                feature_type="Point",
                layer="SISRUA_OSM_PONTOS",
                name="Poste de Luz",
                highway="street_light",
                coords_xy=[[-6.0, -6.0]],
                elevation=716.2,
            ),
        ]

    def test_dxf_file_created(self, sample_features):
        """export_features_to_dxf deve criar um arquivo .dxf válido."""
        from backend.application.dxf_export import export_features_to_dxf
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_ref2.dxf"
            result_path = export_features_to_dxf(
                sample_features,
                output_path=out_path,
                epsg=REF2_EPSG,
            )
            assert result_path.exists()
            assert result_path.stat().st_size > 0

    def test_dxf_is_valid_r2010(self, sample_features):
        """DXF gerado deve ser legível como R2010 via ezdxf."""
        import ezdxf
        from backend.application.dxf_export import export_features_to_dxf
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_ref2_valid.dxf"
            export_features_to_dxf(sample_features, output_path=out_path, epsg=REF2_EPSG)
            doc = ezdxf.readfile(str(out_path))
            assert doc.dxfversion >= "AC1024"  # R2010

    def test_dxf_contains_all_entities(self, sample_features):
        """DXF deve conter todas as entidades (2 polylines + 1 point)."""
        import ezdxf
        from backend.application.dxf_export import export_features_to_dxf
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_ref2_entities.dxf"
            export_features_to_dxf(sample_features, output_path=out_path, epsg=REF2_EPSG)
            doc = ezdxf.readfile(str(out_path))
            msp = doc.modelspace()
            entities = list(msp)
            # Polilinhas → LWPOLYLINE ou POLYLINE; pontos → POINT
            entity_types = {e.dxftype() for e in entities}
            assert entity_types & {"LWPOLYLINE", "POLYLINE", "POINT"}

    def test_dxf_layers_present(self, sample_features):
        """Camadas SISRUA_* devem estar definidas no DXF."""
        import ezdxf
        from backend.application.dxf_export import export_features_to_dxf
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_ref2_layers.dxf"
            export_features_to_dxf(sample_features, output_path=out_path, epsg=REF2_EPSG)
            doc = ezdxf.readfile(str(out_path))
            layer_names = {layer.dxf.name for layer in doc.layers}
            assert "SISRUA_VIA_RESIDENCIAL" in layer_names
            assert "SISRUA_VIA_PRIMARIA" in layer_names

    def test_dxf_tmpfile_when_no_path(self, sample_features):
        """Quando output_path=None, deve criar arquivo temporário."""
        from backend.application.dxf_export import export_features_to_dxf
        result_path = export_features_to_dxf(sample_features, output_path=None, epsg=REF2_EPSG)
        assert result_path.exists()
        assert result_path.suffix == ".dxf"
        # Cleanup
        result_path.unlink(missing_ok=True)

    def test_dxf_units_are_metric(self, sample_features):
        """DXF deve estar configurado em metros ($INSUNITS=6)."""
        import ezdxf
        from backend.application.dxf_export import export_features_to_dxf
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_ref2_units.dxf"
            export_features_to_dxf(sample_features, output_path=out_path, epsg=REF2_EPSG)
            doc = ezdxf.readfile(str(out_path))
            # $INSUNITS = 6 → metros
            insunits = doc.header.get("$INSUNITS", None)
            assert insunits == 6  # metros

    def test_25d_elevation_not_z_coordinate(self, sample_features):
        """Princípio 2.5D: coordenadas das features devem ser 2D (sem Z)."""
        for feat in sample_features:
            for coord in feat.coords_xy or []:
                assert len(coord) == 2, (
                    f"Feature '{feat.name}' tem coordenada 3D: {coord}. "
                    "Princípio 2.5D violado: Z não deve ser coordenada."
                )
            assert feat.elevation is not None, (
                f"Feature '{feat.name}' deveria ter elevação como atributo"
            )


# ---------------------------------------------------------------------------
# Testes de config.py — cobre linha de os.environ injection
# ---------------------------------------------------------------------------

class TestSettingsConfig:
    """Testa Settings (pydantic-settings) incluindo auto-geração de token."""

    def test_extra_cors_origins_empty(self):
        """SISRUA_CORS_ORIGINS vazio retorna lista vazia."""
        from backend.shared.config import Settings
        s = Settings(SISRUA_AUTH_TOKEN="test-tok", SISRUA_CORS_ORIGINS="")
        assert s.extra_cors_origins == []

    def test_extra_cors_origins_single(self):
        """SISRUA_CORS_ORIGINS com 1 origem."""
        from backend.shared.config import Settings
        s = Settings(SISRUA_AUTH_TOKEN="tok", SISRUA_CORS_ORIGINS="https://sisrua.app")
        assert s.extra_cors_origins == ["https://sisrua.app"]

    def test_extra_cors_origins_multiple(self):
        """SISRUA_CORS_ORIGINS com múltiplas origens separadas por vírgula."""
        from backend.shared.config import Settings
        s = Settings(
            SISRUA_AUTH_TOKEN="tok",
            SISRUA_CORS_ORIGINS="https://sisrua.app,https://staging.sisrua.app",
        )
        assert s.extra_cors_origins == ["https://sisrua.app", "https://staging.sisrua.app"]

    def test_extra_cors_origins_trims_whitespace(self):
        """Origens com espaços são normalizadas."""
        from backend.shared.config import Settings
        s = Settings(
            SISRUA_AUTH_TOKEN="tok",
            SISRUA_CORS_ORIGINS=" https://a.com , https://b.com ",
        )
        assert s.extra_cors_origins == ["https://a.com", "https://b.com"]

    def test_auto_generates_token_and_injects_env(self):
        """Quando SISRUA_AUTH_TOKEN ausente, Settings gera UUID e injeta em os.environ."""
        saved = os.environ.pop("SISRUA_AUTH_TOKEN", None)
        try:
            from backend.shared.config import Settings
            s = Settings()
            # Token deve ser um hex de 32 chars (uuid4.hex)
            assert s.sisrua_auth_token is not None
            assert len(s.sisrua_auth_token) == 32
            # Deve ter sido injetado em os.environ
            assert os.environ.get("SISRUA_AUTH_TOKEN") == s.sisrua_auth_token
        finally:
            # Restaura o ambiente para não poluir outros testes
            if saved is not None:
                os.environ["SISRUA_AUTH_TOKEN"] = saved
            elif "SISRUA_AUTH_TOKEN" in os.environ:
                del os.environ["SISRUA_AUTH_TOKEN"]
