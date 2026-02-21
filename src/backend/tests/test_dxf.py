"""
tests/test_dxf.py
Testes headless de geração e validação de arquivos .dxf via ezdxf.

Coordenadas de referência (conforme MEMORY.MD):
  - Lat/Lon: -22.15018°, -42.92185° (EPSG:4326)
  - UTM 23K: E=788547, N=7634925 (SIRGAS 2000 / EPSG:31983)
  - Raios de teste: 100 m, 500 m, 1000 m

Princípio 2.5D: elevação armazenada como XDATA, NÃO como coordenada Z.
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import List

import pytest

from backend.models import CadFeature
from backend.services.dxf_export import (
    APPID_SISRUA,
    export_features_to_dxf,
)

# ---------------------------------------------------------------------------
# Coordenadas de referência (UTM 23S SIRGAS 2000 / EPSG:31983)
# ---------------------------------------------------------------------------
# Localização: -22.15018°, -42.92185° (EPSG:4326)
# UTM calculado: E≈714316, N≈7549084 (EPSG:31983)
REF_E = 714316.0   # Easting (m)
REF_N = 7549084.0  # Northing (m)

# Segunda coordenada de referência (23K 788547 7634925 conforme MEMORY.MD)
REF2_E = 788547.0
REF2_N = 7634925.0


def _make_road(
    name: str = "Rua Teste",
    layer: str = "SISRUA_OSM_HIGHWAY",
    length_m: float = 100.0,
    elevation: float = 850.0,
) -> CadFeature:
    """Cria uma polilinha CAD de rua alinhada ao leste, com a origem em REF_E, REF_N."""
    coords = [
        [REF_E, REF_N],
        [REF_E + length_m, REF_N],
    ]
    return CadFeature(
        feature_type="Polyline",
        layer=layer,
        name=name,
        highway="residential",
        coords_xy=coords,
        elevation=elevation,
        width_m=6.0,
    )


def _make_point(
    name: str = "Poste Teste",
    layer: str = "SISRUA_OSM_NODES",
    block_name: str = "POSTE",
    elevation: float = 851.5,
) -> CadFeature:
    return CadFeature(
        feature_type="Point",
        layer=layer,
        name=name,
        insertion_point_xy=[REF_E, REF_N],
        block_name=block_name,
        rotation=0.0,
        scale=1.0,
        elevation=elevation,
    )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------
@pytest.fixture()
def dxf_path(tmp_path):
    """Gera um DXF de teste com features padrão e retorna o caminho."""
    features: List[CadFeature] = [
        _make_road("Rua Principal", "SISRUA_OSM_HIGHWAY", length_m=100.0, elevation=850.0),
        _make_road("Rua Secundária", "SISRUA_OSM_RESIDENTIAL", length_m=500.0, elevation=852.3),
        _make_road("Via 1km", "SISRUA_OSM_HIGHWAY", length_m=1000.0, elevation=845.0),
        _make_point("Poste AT", "SISRUA_OSM_NODES", "POSTE", elevation=851.5),
    ]
    out = tmp_path / "test_sisrua.dxf"
    return export_features_to_dxf(features, output_path=out)


# ---------------------------------------------------------------------------
# Testes de estrutura do DXF
# ---------------------------------------------------------------------------
def test_dxf_file_is_created(dxf_path):
    """O arquivo .dxf deve existir após a exportação."""
    assert dxf_path.exists()
    assert dxf_path.stat().st_size > 0


def test_dxf_is_valid_and_readable(dxf_path):
    """O DXF gerado deve ser lido pelo ezdxf sem erros."""
    import ezdxf

    doc = ezdxf.readfile(str(dxf_path))
    assert doc is not None
    assert doc.dxfversion >= "AC1024"  # R2010+


def test_dxf_layers_are_created(dxf_path):
    """As camadas sisRUA devem estar presentes no documento."""
    import ezdxf

    doc = ezdxf.readfile(str(dxf_path))
    layer_names = {layer.dxf.name for layer in doc.layers}

    assert "SISRUA_OSM_HIGHWAY" in layer_names
    assert "SISRUA_OSM_RESIDENTIAL" in layer_names
    assert "SISRUA_OSM_NODES" in layer_names


def test_dxf_polyline_count(dxf_path):
    """Deve haver exatamente 3 polilinhas (ruas) no modelspace."""
    import ezdxf

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    polylines = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
    assert len(polylines) == 3


def test_dxf_polyline_vertex_count(dxf_path):
    """Cada polilinha deve ter exatamente 2 vértices."""
    import ezdxf

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    for pline in msp.query("LWPOLYLINE"):
        vertices = list(pline.vertices())
        assert len(vertices) == 2, f"Esperava 2 vértices, obteve {len(vertices)}"


def test_dxf_polyline_coordinates_are_2d(dxf_path):
    """2.5D: as coordenadas das polilinhas devem ser 2D (Z=0 ou omitido)."""
    import ezdxf

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    for pline in msp.query("LWPOLYLINE"):
        for x, y in pline.vertices():
            # Coordenadas não devem ser NaN ou Inf
            assert math.isfinite(x), f"X não finito: {x}"
            assert math.isfinite(y), f"Y não finito: {y}"
        # Polilinha 2D: elevation é o dxf.elevation (Z do plano), deve ser 0 por padrão
        assert pline.dxf.elevation == 0.0


def test_dxf_25d_elevation_in_xdata(dxf_path):
    """2.5D: elevação deve estar em XDATA (APPID SISRUA), NÃO como Z geométrico."""
    import ezdxf

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    plines = list(msp.query("LWPOLYLINE"))
    assert plines, "Nenhuma polilinha encontrada"

    # A primeira polilinha tem elevation=850.0
    pline = plines[0]
    xdata = pline.get_xdata(APPID_SISRUA)
    assert xdata is not None, "XDATA SISRUA ausente na polilinha"

    xdata_str = " ".join(str(tag.value) for tag in xdata)
    assert "sisrua:elevation" in xdata_str
    assert "850.0" in xdata_str


def test_dxf_polyline_length_100m(tmp_path):
    """Polilinha de 100 m deve ter comprimento correto (±0.1 m)."""
    import ezdxf

    features = [_make_road(length_m=100.0)]
    out = tmp_path / "test_100m.dxf"
    export_features_to_dxf(features, output_path=out)

    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()

    pline = next(iter(msp.query("LWPOLYLINE")))
    vertices = list(pline.vertices())
    x0, y0 = vertices[0]
    x1, y1 = vertices[1]
    length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)

    assert abs(length - 100.0) < 0.1, f"Comprimento esperado ≈100 m, obteve {length:.3f} m"


def test_dxf_polyline_length_500m(tmp_path):
    """Polilinha de 500 m deve ter comprimento correto (±0.1 m)."""
    import ezdxf

    features = [_make_road(length_m=500.0)]
    out = tmp_path / "test_500m.dxf"
    export_features_to_dxf(features, output_path=out)

    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()

    pline = next(iter(msp.query("LWPOLYLINE")))
    vertices = list(pline.vertices())
    x0, y0 = vertices[0]
    x1, y1 = vertices[1]
    length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)

    assert abs(length - 500.0) < 0.1, f"Comprimento esperado ≈500 m, obteve {length:.3f} m"


def test_dxf_polyline_length_1km(tmp_path):
    """Polilinha de 1 km deve ter comprimento correto (±0.1 m)."""
    import ezdxf

    features = [_make_road(length_m=1000.0)]
    out = tmp_path / "test_1km.dxf"
    export_features_to_dxf(features, output_path=out)

    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()

    pline = next(iter(msp.query("LWPOLYLINE")))
    vertices = list(pline.vertices())
    x0, y0 = vertices[0]
    x1, y1 = vertices[1]
    length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)

    assert abs(length - 1000.0) < 0.1, f"Comprimento esperado ≈1000 m, obteve {length:.3f} m"


def test_dxf_reference_coordinates(tmp_path):
    """As coordenadas de referência (UTM 23K) devem estar corretas no DXF."""
    import ezdxf

    features = [_make_road(length_m=100.0)]
    out = tmp_path / "test_ref.dxf"
    export_features_to_dxf(features, output_path=out)

    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()

    pline = next(iter(msp.query("LWPOLYLINE")))
    vertices = list(pline.vertices())
    x0, y0 = vertices[0]

    assert abs(x0 - REF_E) < 0.01, f"Easting esperado {REF_E}, obteve {x0}"
    assert abs(y0 - REF_N) < 0.01, f"Northing esperado {REF_N}, obteve {y0}"


def test_dxf_point_feature(tmp_path):
    """Feature do tipo Point deve gerar um POINT ou INSERT no DXF."""
    import ezdxf

    features = [_make_point()]
    out = tmp_path / "test_point.dxf"
    export_features_to_dxf(features, output_path=out)

    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()

    inserts = list(msp.query("INSERT"))
    points = list(msp.query("POINT"))

    assert len(inserts) + len(points) >= 1, "Nenhum INSERT ou POINT encontrado"


def test_dxf_empty_features(tmp_path):
    """Exportação com lista vazia deve gerar DXF válido (sem entidades)."""
    import ezdxf

    out = tmp_path / "test_empty.dxf"
    export_features_to_dxf([], output_path=out)

    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    assert list(msp) == []


def test_dxf_invalid_polyline_skipped(tmp_path):
    """Polilinha com menos de 2 pontos não deve ser adicionada ao DXF."""
    import ezdxf

    bad_feat = CadFeature(
        feature_type="Polyline",
        layer="TEST",
        coords_xy=[[0.0, 0.0]],  # Apenas 1 ponto — inválido
    )
    out = tmp_path / "test_invalid.dxf"
    export_features_to_dxf([bad_feat], output_path=out)

    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    polylines = list(msp.query("LWPOLYLINE"))
    assert len(polylines) == 0, "Polilinha inválida não deveria ter sido adicionada"


def test_dxf_multiple_layers_independent(tmp_path):
    """Features em camadas diferentes não devem se misturar."""
    import ezdxf

    features = [
        _make_road("R1", "LAYER_A", length_m=100.0),
        _make_road("R2", "LAYER_B", length_m=200.0),
        _make_road("R3", "LAYER_A", length_m=300.0),
    ]
    out = tmp_path / "test_layers.dxf"
    export_features_to_dxf(features, output_path=out)

    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()

    layer_a = [e for e in msp.query("LWPOLYLINE") if e.dxf.layer == "LAYER_A"]
    layer_b = [e for e in msp.query("LWPOLYLINE") if e.dxf.layer == "LAYER_B"]

    assert len(layer_a) == 2
    assert len(layer_b) == 1


def test_dxf_crs_pipeline_integration():
    """
    Integração pipeline CRS: coordenada lat/lon de referência deve gerar
    features com coordenadas UTM corretas ao passar pelo serviço geojson.
    """
    import json
    from backend.services.geojson import prepare_geojson_compute

    # Coordenadas de referência: -22.15018°, -42.92185°
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"highway": "residential", "name": "Via Referência"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-42.92185, -22.15018],
                        [-42.92085, -22.15018],  # ~90 m a leste
                    ],
                },
            }
        ],
    }

    result = prepare_geojson_compute(geojson)
    assert result is not None
    assert len(result["features"]) >= 1

    feat_dict = result["features"][0]
    coords = feat_dict.get("coords_xy", [])
    assert len(coords) >= 2

    # O easting deve ser próximo de 714316 (±200 m de tolerância para a conversão)
    x0 = coords[0][0]
    assert abs(x0 - REF_E) < 200, f"Easting UTM esperado ≈{REF_E}, obteve {x0:.1f}"
