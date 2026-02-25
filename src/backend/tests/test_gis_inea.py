"""
tests/test_gis_inea.py
Testes unitários para o módulo backend.gis_core.inea.
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.gis_core.inea import (
    _wfs_to_features,
    prepare_inea_compute,
    INEA_TYPENAMES,
    _LAYER_MAP,
)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_WFS_HIDROGRAFIA_MOCK = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-43.2, -22.9],
                    [-43.1, -22.8],
                    [-43.0, -22.7],
                ],
            },
            "properties": {"nome": "Rio Exemplo", "tipo": "rio"},
        }
    ],
}

_WFS_UC_POLYGON_MOCK = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-43.3, -22.95],
                        [-43.1, -22.95],
                        [-43.1, -22.75],
                        [-43.3, -22.75],
                        [-43.3, -22.95],
                    ]
                ],
            },
            "properties": {"nome": "APA Guapimirim", "categoria": "APA"},
        }
    ],
}

_WFS_EMPTY_MOCK = {"type": "FeatureCollection", "features": []}


# ---------------------------------------------------------------------------
# Testes de constantes / mapeamentos
# ---------------------------------------------------------------------------

def test_inea_typenames_not_empty():
    assert len(INEA_TYPENAMES) > 0
    assert "hidrografia" in INEA_TYPENAMES
    assert "bacias" in INEA_TYPENAMES
    assert "unidades_conservacao" in INEA_TYPENAMES


def test_layer_map_default_exists():
    assert "default" in _LAYER_MAP
    assert "hidro" in _LAYER_MAP
    assert "uc" in _LAYER_MAP


# ---------------------------------------------------------------------------
# Testes de _wfs_to_features
# ---------------------------------------------------------------------------

def test_wfs_to_features_linestring():
    feats = _wfs_to_features(_WFS_HIDROGRAFIA_MOCK, "inea:RJ_Hidrografia_250000", epsg_out=31983)
    assert len(feats) == 1
    f = feats[0]
    assert f.feature_type == "Polyline"
    assert f.layer == "SISRUA_INEA_HIDRO"
    assert f.name == "Rio Exemplo"
    assert len(f.coords_xy) == 3  # 3 pontos projetados


def test_wfs_to_features_polygon():
    feats = _wfs_to_features(_WFS_UC_POLYGON_MOCK, "inea:RJ_UnidadesConservacao", epsg_out=31983)
    assert len(feats) == 1
    f = feats[0]
    assert f.feature_type == "Polyline"
    assert f.layer == "SISRUA_INEA_UC"
    assert len(f.coords_xy) >= 4  # Anel exterior do polígono


def test_wfs_to_features_empty():
    feats = _wfs_to_features(_WFS_EMPTY_MOCK, "inea:RJ_Hidrografia_250000", epsg_out=31983)
    assert feats == []


def test_wfs_to_features_multilinestring():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [
                        [[-43.2, -22.9], [-43.1, -22.8]],
                        [[-43.0, -22.7], [-42.9, -22.6]],
                    ],
                },
                "properties": {"nome": "Bacia Dupla"},
            }
        ],
    }
    feats = _wfs_to_features(geojson, "inea:RJ_BaciasHidrograficas", epsg_out=31983)
    # MultiLineString com 2 linhas → 2 CadFeature
    assert len(feats) == 2


def test_wfs_to_features_invalid_geometry():
    bad = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": None, "properties": {}}
        ],
    }
    feats = _wfs_to_features(bad, "inea:RJ_Hidrografia_250000", epsg_out=31983)
    assert feats == []


# ---------------------------------------------------------------------------
# Testes de prepare_inea_compute (integração)
# ---------------------------------------------------------------------------

@patch("backend.gis_core.inea.requests.get")
def test_prepare_inea_compute_sucesso(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _WFS_HIDROGRAFIA_MOCK
    mock_get.return_value = mock_resp

    cache_svc = MagicMock()
    cache_svc.get.return_value = None

    result = prepare_inea_compute(
        typename="hidrografia",
        bbox=(-43.5, -23.1, -42.8, -22.6),
        cache_service=cache_svc,
    )

    assert "features" in result
    assert "crs_out" in result
    assert result["crs_out"].startswith("EPSG:")
    assert len(result["features"]) == 1
    assert result["features"][0]["layer"] == "SISRUA_INEA_HIDRO"

    # Verifica que o bbox foi passado como parâmetro WFS
    call_kwargs = mock_get.call_args[1]
    assert "params" in call_kwargs
    assert "bbox" in call_kwargs["params"]


@patch("backend.gis_core.inea.requests.get")
def test_prepare_inea_compute_sem_bbox(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _WFS_HIDROGRAFIA_MOCK
    mock_get.return_value = mock_resp

    cache_svc = MagicMock()
    cache_svc.get.return_value = None

    result = prepare_inea_compute(
        typename="hidrografia",
        bbox=None,
        cache_service=cache_svc,
    )

    assert "features" in result
    # Sem bbox, o parâmetro não deve ser passado
    call_kwargs = mock_get.call_args[1]
    assert "bbox" not in call_kwargs.get("params", {})


@patch("backend.gis_core.inea.requests.get")
def test_prepare_inea_compute_typename_direto(mock_get):
    """Testa que um typename WFS direto (fora do mapeamento) é passado diretamente."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = _WFS_EMPTY_MOCK
    mock_get.return_value = mock_resp

    cache_svc = MagicMock()
    cache_svc.get.return_value = None

    result = prepare_inea_compute(
        typename="inea:RJ_Manguezais",
        bbox=None,
        cache_service=cache_svc,
    )

    assert result["features"] == []
    # O typename direto deve ser usado sem mapeamento
    call_params = mock_get.call_args[1]["params"]
    assert call_params["typeName"] == "inea:RJ_Manguezais"


@patch("backend.gis_core.inea.requests.get")
def test_prepare_inea_compute_cache_hit(mock_get):
    cache_svc = MagicMock()
    cache_svc.get.return_value = {
        "features": [],
        "crs_out": "EPSG:31983",
        "cache_hit": False,
    }

    result = prepare_inea_compute(
        typename="hidrografia",
        bbox=None,
        cache_service=cache_svc,
    )

    mock_get.assert_not_called()
    assert result["cache_hit"] is True


@patch("backend.gis_core.inea.requests.get")
def test_prepare_inea_compute_falha_wfs(mock_get):
    from fastapi import HTTPException
    import requests as req_lib

    mock_get.side_effect = req_lib.exceptions.ConnectionError("WFS timeout")

    cache_svc = MagicMock()
    cache_svc.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        prepare_inea_compute(
            typename="hidrografia",
            bbox=None,
            cache_service=cache_svc,
        )

    assert exc_info.value.status_code == 503


@patch("backend.gis_core.inea.requests.get")
def test_prepare_inea_compute_url_customizada(mock_get):
    """Testa substituição de URL para ambientes de teste/staging."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = _WFS_EMPTY_MOCK
    mock_get.return_value = mock_resp

    cache_svc = MagicMock()
    cache_svc.get.return_value = None

    test_url = "https://staging.inea.rj.gov.br/geoserver/wfs"
    prepare_inea_compute(
        typename="hidrografia",
        bbox=None,
        cache_service=cache_svc,
        wfs_url=test_url,
    )

    called_url = mock_get.call_args[0][0]
    assert called_url == test_url
