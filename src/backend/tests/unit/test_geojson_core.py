"""
Testes unitários críticos para backend/application/geojson.py
Arquivo Pareto: 218 linhas - Core GIS processing
Meta: 100% coverage para funcionalidades críticas
"""
import pytest
from unittest.mock import Mock, patch
import json
from backend.application.geojson import (
    prepare_geojson_compute,
    first_lonlat,
)
from backend.shared.utils import norm_optional_str


class TestGeoJsonCore:
    """Testes unitários para o core de processamento GeoJSON"""

    def test_first_lonlat_featurecollection_valid(self):
        """Testa extração de coordenadas de FeatureCollection válido"""
        geo = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-46.6333, -23.5505], [-46.6320, -23.5510]]
                    }
                }
            ]
        }
        
        lon, lat = first_lonlat(geo)
        
        assert lon == -46.6333
        assert lat == -23.5505

    def test_first_lonlat_feature_valid(self):
        """Testa extração de coordenadas de Feature individual"""
        geo = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [-46.6333, -23.5505]
            }
        }
        
        lon, lat = first_lonlat(geo)
        
        assert lon == -46.6333
        assert lat == -23.5505

    def test_first_lonlat_multilinestring_valid(self):
        """Testa extração de coordenadas de MultiLineString"""
        geo = {
            "type": "Feature",
            "geometry": {
                "type": "MultiLineString",
                "coordinates": [
                    [[-46.6333, -23.5505], [-46.6320, -23.5510]],
                    [[-46.6310, -23.5520], [-46.6300, -23.5530]]
                ]
            }
        }
        
        lon, lat = first_lonlat(geo)
        
        assert lon == -46.6333
        assert lat == -23.5505

    def test_first_lonlat_point_valid(self):
        """Testa extração de coordenadas de Point"""
        geo = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [-46.6333, -23.5505]
            }
        }
        
        lon, lat = first_lonlat(geo)
        
        assert lon == -46.6333
        assert lat == -23.5505

    def test_first_lonlat_empty_geo(self):
        """Testa fallback para GeoJSON vazio"""
        lon, lat = first_lonlat(None)
        
        assert lon == 0.0
        assert lat == 0.0

    def test_first_lonlat_invalid_geo(self):
        """Testa fallback para GeoJSON inválido"""
        geo = {"type": "InvalidType"}
        
        lon, lat = first_lonlat(geo)
        
        assert lon == 0.0
        assert lat == 0.0

    @patch('pyproj.Transformer.from_crs')
    @patch('backend.application.geojson.project_lines_to_xy')
    @patch('backend.application.elevation.ElevationService')
    @patch('backend.shared.utils.clean_geometry')
    def test_prepare_geojson_compute_valid_string(self, mock_clean_geometry, mock_elev_svc, mock_project_lines_to_xy, mock_transformer):
        """Testa processamento de GeoJSON string válido"""
        transformer_inst = Mock()
        transformer_inst.transform = lambda x, y: (x, y)
        transformer_inst.itransform = lambda pts: iter(pts)
        mock_transformer.return_value = transformer_inst

        mock_project_lines_to_xy.return_value = [[[1.0, 2.0], [3.0, 4.0]]]

        elev_inst = Mock()
        elev_inst.get_elevation_profile.return_value = [10.0]
        mock_elev_svc.return_value = elev_inst

        mock_clean_geometry.side_effect = lambda feats: feats
        
        geo_str = json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-46.6333, -23.5505], [-46.6320, -23.5510], [-46.6315, -23.5515]]
                    },
                    "properties": {
                        "highway": "residential",
                        "name": "Test Street"
                    }
                }
            ]
        })
        
        result = prepare_geojson_compute(geo_str)
        
        assert isinstance(result, dict)
        assert "features" in result
        assert len(result["features"]) > 0
        assert result["features"][0]["feature_type"] == "Polyline"

    def test_prepare_geojson_compute_cancelled(self):
        """Testa cancelamento do processamento via callback que levanta exceção."""
        def check_cancel():
            raise RuntimeError("cancelled")

        geo_str = json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[-46.6, -23.5], [-46.61, -23.51]]},
                    "properties": {"highway": "residential"}
                }
            ]
        })

        with pytest.raises(RuntimeError, match="cancelled"):
            prepare_geojson_compute(geo_str, check_cancel)

    def test_prepare_geojson_compute_invalid_json(self):
        """Testa handling de JSON inválido"""
        invalid_json = "{ invalid json }"
        
        with pytest.raises((ValueError, json.JSONDecodeError)):
            prepare_geojson_compute(invalid_json)

    def test_norm_optional_str_valid_values(self):
        """Testa normalização de strings opcionais"""
        assert norm_optional_str("test") == "test"
        assert norm_optional_str("") is None
        assert norm_optional_str(None) is None
        assert norm_optional_str("  trimmed  ") == "trimmed"

    def test_norm_optional_str_special_characters(self):
        """Testa normalização com caracteres especiais"""
        assert norm_optional_str("test\n\r\t") == "test"
        assert norm_optional_str("  test  ") == "test"

    @patch('backend.shared.utils.get_layer_name')
    @patch('backend.application.elevation.ElevationService')
    @patch('backend.shared.utils.clean_geometry')
    def test_prepare_geojson_compute_layer_mapping(self, mock_clean_geometry, mock_elev_svc, mock_get_layer_name):
        """Testa mapeamento de layers corretamente"""
        mock_get_layer_name.side_effect = lambda props, default=None: props.get("highway", "unknown")

        elev_inst = Mock()
        elev_inst.get_elevation_profile.return_value = []
        mock_elev_svc.return_value = elev_inst

        mock_clean_geometry.side_effect = lambda feats: feats
        
        geo_str = json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[-46.6333, -23.5505], [-46.6320, -23.5510]]},
                    "properties": {"highway": "residential"}
                },
                {
                    "type": "Feature", 
                    "geometry": {"type": "LineString", "coordinates": [[-46.6310, -23.5520], [-46.6300, -23.5530]]},
                    "properties": {"highway": "primary"}
                }
            ]
        })
        
        result = prepare_geojson_compute(geo_str)
        
        assert "features" in result
        assert len(result["features"]) == 2
        
        # Verifica se os layers foram mapeados corretamente
        for feature in result["features"]:
            assert "layer" in feature
            assert feature["layer"] in ["SISRUA_Vias_Locais", "SISRUA_Vias_Arteriais", "unknown"]

    def test_prepare_geojson_compute_coordinate_precision(self):
        """Testa precisão de coordenadas"""
        geo_str = json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-46.633308272, -23.550519923], [-46.632012345, -23.551098765]]
                    }
                }
            ]
        })
        
        result = prepare_geojson_compute(geo_str)
        
        assert "features" in result
        assert len(result["features"]) == 1
        
        feature = result["features"][0]
        coords = feature.get("coords_xy") or []
        assert len(coords) >= 2
        for coord in coords:
            assert isinstance(coord[0], (int, float))
            assert isinstance(coord[1], (int, float))

    def test_prepare_geojson_compute_empty_featurecollection(self):
        """Testa FeatureCollection vazio"""
        geo_str = json.dumps({
            "type": "FeatureCollection",
            "features": []
        })

        with pytest.raises(Exception):
            # first_lonlat falha em extrair coordenadas e a função deve retornar 400
            prepare_geojson_compute(geo_str)

    @patch('backend.application.elevation.ElevationService')
    @patch('backend.shared.utils.clean_geometry')
    def test_prepare_geojson_compute_large_input(self, mock_clean_geometry, mock_elev_svc):
        """Smoke de input grande sem travar (Pareto: robustez)."""
        elev_inst = Mock()
        elev_inst.get_elevation_profile.return_value = []
        mock_elev_svc.return_value = elev_inst

        mock_clean_geometry.side_effect = lambda feats: feats

        large_features = []
        for i in range(50):
            large_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-46.6 + i * 1e-6, -23.5], [-46.600001 + i * 1e-6, -23.500001]]
                },
                "properties": {"highway": "residential", "name": f"Street {i}"}
            })

        large_geo = {"type": "FeatureCollection", "features": large_features}
        result = prepare_geojson_compute(json.dumps(large_geo))
        assert "features" in result
        assert len(result["features"]) == 50
