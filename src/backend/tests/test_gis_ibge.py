"""
tests/test_gis_ibge.py
Testes unitários para o módulo backend.gis_core.ibge.
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.gis_core.ibge import (
    _buscar_codigo_municipio,
    _malha_municipio_to_features,
    _collect_coords,
    prepare_ibge_compute,
)

# ---------------------------------------------------------------------------
# Fixtures / Mock data
# ---------------------------------------------------------------------------

_MUNICIPIOS_MOCK = [
    {
        "id": 3303302,
        "nome": "Nova Friburgo",
        "microrregiao": {
            "mesorregiao": {
                "UF": {"sigla": "RJ"}
            }
        },
    },
    {
        "id": 3548708,
        "nome": "Nova Friburgo",  # Homônimo hipotético em SP
        "microrregiao": {
            "mesorregiao": {
                "UF": {"sigla": "SP"}
            }
        },
    },
]

_GEOJSON_MOCK = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-42.55, -22.25],
                        [-42.40, -22.25],
                        [-42.40, -22.10],
                        [-42.55, -22.10],
                        [-42.55, -22.25],
                    ]
                ],
            },
            "properties": {"name": "Nova Friburgo"},
        }
    ],
}


# ---------------------------------------------------------------------------
# Testes de _buscar_codigo_municipio
# ---------------------------------------------------------------------------

@patch("backend.gis_core.ibge.requests.get")
def test_buscar_codigo_municipio_encontrado(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _MUNICIPIOS_MOCK
    mock_get.return_value = mock_resp

    cod = _buscar_codigo_municipio("Nova Friburgo", uf="RJ")
    assert cod == 3303302


@patch("backend.gis_core.ibge.requests.get")
def test_buscar_codigo_municipio_sem_uf(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _MUNICIPIOS_MOCK
    mock_get.return_value = mock_resp

    # Sem UF, retorna o primeiro encontrado
    cod = _buscar_codigo_municipio("Nova Friburgo")
    assert cod in (3303302, 3548708)


@patch("backend.gis_core.ibge.requests.get")
def test_buscar_codigo_municipio_nao_encontrado(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _MUNICIPIOS_MOCK
    mock_get.return_value = mock_resp

    cod = _buscar_codigo_municipio("Cidade Inexistente")
    assert cod is None


@patch("backend.gis_core.ibge.requests.get")
def test_buscar_codigo_municipio_uf_errada(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _MUNICIPIOS_MOCK
    mock_get.return_value = mock_resp

    # Nova Friburgo existe em RJ e SP (mock), mas buscamos em MG
    cod = _buscar_codigo_municipio("Nova Friburgo", uf="MG")
    assert cod is None


# ---------------------------------------------------------------------------
# Testes de _malha_municipio_to_features
# ---------------------------------------------------------------------------

def test_malha_to_features_polygon():
    features = _malha_municipio_to_features(_GEOJSON_MOCK, "Nova Friburgo", epsg_out=31983)
    assert len(features) == 1
    feat = features[0]
    assert feat.feature_type == "Polyline"
    assert feat.layer == "SISRUA_IBGE_LIMITE"
    assert feat.name is not None and "Nova Friburgo" in feat.name
    assert len(feat.coords_xy) >= 4  # anel poligonal projetado


def test_malha_to_features_empty_geojson():
    features = _malha_municipio_to_features(
        {"type": "FeatureCollection", "features": []},
        "Vazio", epsg_out=31983
    )
    assert features == []


def test_malha_to_features_invalid_geometry():
    bad_geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "INVALID"}, "properties": {}}
        ],
    }
    # Deve retornar lista vazia sem lançar exceção
    features = _malha_municipio_to_features(bad_geojson, "Teste", epsg_out=31983)
    assert features == []


# ---------------------------------------------------------------------------
# Testes de _collect_coords
# ---------------------------------------------------------------------------

def test_collect_coords_point():
    out: list = []
    _collect_coords({"type": "Point", "coordinates": [-42.5, -22.3]}, out)
    assert out == [[-42.5, -22.3]]


def test_collect_coords_linestring():
    out: list = []
    _collect_coords(
        {"type": "LineString", "coordinates": [[-42.5, -22.3], [-42.4, -22.2]]}, out
    )
    assert len(out) == 2


def test_collect_coords_polygon():
    out: list = []
    _collect_coords(
        {
            "type": "Polygon",
            "coordinates": [[[-42.5, -22.3], [-42.4, -22.3], [-42.4, -22.2], [-42.5, -22.3]]],
        },
        out,
    )
    assert len(out) == 4


def test_collect_coords_empty():
    out: list = []
    _collect_coords({}, out)
    assert out == []


# ---------------------------------------------------------------------------
# Testes de prepare_ibge_compute (integração)
# ---------------------------------------------------------------------------

@patch("backend.gis_core.ibge.requests.get")
def test_prepare_ibge_compute_sucesso(mock_get):
    def side_effect(url, **kwargs):
        resp = MagicMock()
        if "localidades" in url:
            resp.json.return_value = _MUNICIPIOS_MOCK
        else:
            resp.json.return_value = _GEOJSON_MOCK
        return resp

    mock_get.side_effect = side_effect

    cache_svc = MagicMock()
    cache_svc.get.return_value = None

    result = prepare_ibge_compute("Nova Friburgo", uf="RJ", cache_service=cache_svc)

    assert "features" in result
    assert "crs_out" in result
    assert result["crs_out"].startswith("EPSG:")
    assert len(result["features"]) >= 1
    assert result["features"][0]["layer"] == "SISRUA_IBGE_LIMITE"


@patch("backend.gis_core.ibge.requests.get")
def test_prepare_ibge_compute_municipio_nao_encontrado(mock_get):
    from fastapi import HTTPException

    mock_resp = MagicMock()
    mock_resp.json.return_value = []  # Lista vazia — nenhum município
    mock_get.return_value = mock_resp

    cache_svc = MagicMock()
    cache_svc.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        prepare_ibge_compute("Municipio Inexistente", uf=None, cache_service=cache_svc)

    assert exc_info.value.status_code == 404


@patch("backend.gis_core.ibge.requests.get")
def test_prepare_ibge_compute_cache_hit(mock_get):
    cache_svc = MagicMock()
    cache_svc.get.return_value = {
        "features": [],
        "crs_out": "EPSG:31983",
        "cache_hit": False,
    }

    result = prepare_ibge_compute("Nova Friburgo", uf="RJ", cache_service=cache_svc)

    # Não deve chamar a API se há cache
    mock_get.assert_not_called()
    assert result["cache_hit"] is True


@patch("backend.gis_core.ibge.requests.get")
def test_prepare_ibge_compute_falha_api(mock_get):
    from fastapi import HTTPException
    import requests as req_lib

    def side_effect(url, **kwargs):
        if "localidades" in url:
            resp = MagicMock()
            resp.json.return_value = _MUNICIPIOS_MOCK
            return resp
        raise req_lib.exceptions.ConnectionError("Timeout")

    mock_get.side_effect = side_effect

    cache_svc = MagicMock()
    cache_svc.get.return_value = None  # Sem cache

    with pytest.raises(HTTPException) as exc_info:
        prepare_ibge_compute("Nova Friburgo", uf="RJ", cache_service=cache_svc)

    assert exc_info.value.status_code == 503
