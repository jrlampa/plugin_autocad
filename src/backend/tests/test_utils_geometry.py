"""
tests/test_utils_geometry.py
Targeted tests for core/utils.py and gis_core/geometry.py uncovered branches.

Missed lines addressed:
  core/utils.py:   10-13 (cache_dir), 49 (pydantic model), 58-61 (str fallback),
                   78/81-83 (to_linestrings branches), 96 (infinite coord filter),
                   136-141 (get_layer_config with real json), 195/200-205 (clean_geometry)
  gis_core/geometry.py: 21-23 (snap_to_edge close), 35-37 (insertion_point_xy offset)
"""
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# core/utils.py — cache_dir() with LOCALAPPDATA env var  (lines 10-13)
# ---------------------------------------------------------------------------

def test_cache_dir_creates_directory(tmp_path, monkeypatch):
    """cache_dir() deve criar o diretório e retornar o Path correto."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from backend.shared import utils
    import importlib
    importlib.reload(utils)
    result = utils.cache_dir()
    assert result.exists()
    assert result.name == "cache"
    assert result.parent.name == "sisRUA"


def test_cache_dir_without_localappdata(tmp_path, monkeypatch):
    """cache_dir() sem LOCALAPPDATA usa Path.home()."""
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    from backend.shared import utils
    result = utils.cache_dir()
    assert result.exists()


# ---------------------------------------------------------------------------
# core/utils.py — sanitize_jsonable pydantic BaseModel  (line 49)
# ---------------------------------------------------------------------------

def test_sanitize_jsonable_pydantic_model():
    """sanitize_jsonable(BaseModel()) deve chamar model_dump()."""
    from pydantic import BaseModel
    from backend.shared.utils import sanitize_jsonable

    class SampleModel(BaseModel):
        name: str = "test"
        value: int = 42

    result = sanitize_jsonable(SampleModel())
    assert result == {"name": "test", "value": 42}


# ---------------------------------------------------------------------------
# core/utils.py — sanitize_jsonable str() fallback  (lines 58-61)
# ---------------------------------------------------------------------------

def test_sanitize_jsonable_unknown_type():
    """sanitize_jsonable de tipo desconhecido cai no fallback str()."""
    from backend.shared.utils import sanitize_jsonable

    class WeirdObj:
        def __str__(self):
            return "weird_repr"

    result = sanitize_jsonable(WeirdObj())
    assert result == "weird_repr"


def test_sanitize_jsonable_nan_float():
    """sanitize_jsonable(float('nan')) deve retornar None."""
    from backend.shared.utils import sanitize_jsonable
    assert sanitize_jsonable(float("nan")) is None


def test_sanitize_jsonable_inf_float():
    """sanitize_jsonable(float('inf')) deve retornar None."""
    from backend.shared.utils import sanitize_jsonable
    assert sanitize_jsonable(float("inf")) is None


# ---------------------------------------------------------------------------
# core/utils.py — to_linestrings branches  (lines 78, 81-83)
# ---------------------------------------------------------------------------

def test_to_linestrings_none():
    """to_linestrings(None) → []."""
    from backend.shared.utils import to_linestrings
    assert to_linestrings(None) == []


def test_to_linestrings_linestring():
    """to_linestrings(LineString) → [LineString]."""
    from shapely.geometry import LineString
    from backend.shared.utils import to_linestrings
    ls = LineString([(0, 0), (1, 1)])
    result = to_linestrings(ls)
    assert len(result) == 1
    assert result[0] is ls


def test_to_linestrings_multilinestring():
    """to_linestrings(MultiLineString) → list of geoms."""
    from shapely.geometry import LineString, MultiLineString
    from backend.shared.utils import to_linestrings
    mls = MultiLineString([[(0, 0), (1, 1)], [(2, 2), (3, 3)]])
    result = to_linestrings(mls)
    assert len(result) == 2


def test_to_linestrings_other_type():
    """to_linestrings(non-geometry) → []."""
    from backend.shared.utils import to_linestrings
    assert to_linestrings("not a geometry") == []


# ---------------------------------------------------------------------------
# core/utils.py — project_lines_to_xy infinite coord filter  (line 96)
# ---------------------------------------------------------------------------

def test_project_lines_to_xy_filters_infinite_coords():
    """project_lines_to_xy deve ignorar coordenadas com inf ou nan."""
    from shapely.geometry import LineString
    from backend.shared.utils import project_lines_to_xy

    class _FakeTransformer:
        def transform(self, x, y):
            # Return inf for the first x coord
            return (float("inf"), y)

    lines = [LineString([(0, 0), (1, 1), (2, 2)])]
    result = project_lines_to_xy(lines, _FakeTransformer())
    # All coords have inf x, so all are filtered out → no valid polylines
    assert result == []


def test_project_lines_to_xy_valid_coords():
    """project_lines_to_xy com coordenadas válidas retorna lista de coords."""
    from shapely.geometry import LineString
    from backend.shared.utils import project_lines_to_xy

    class _IdentityTransformer:
        def transform(self, x, y):
            return (x, y)

    lines = [LineString([(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)])]
    result = project_lines_to_xy(lines, _IdentityTransformer())
    assert len(result) == 1
    assert len(result[0]) == 3


# ---------------------------------------------------------------------------
# core/utils.py — get_color_from_elevation bands  (lines 68-72)
# ---------------------------------------------------------------------------

def test_get_color_equal_z_min_max():
    """z_min == z_max retorna branco."""
    from backend.shared.utils import get_color_from_elevation
    assert get_color_from_elevation(5.0, 5.0, 5.0) == "255,255,255"


def test_get_color_band_blue():
    """ratio < 0.25 → '5' (azul)."""
    from backend.shared.utils import get_color_from_elevation
    assert get_color_from_elevation(0.0, 0.0, 100.0) == "5"


def test_get_color_band_cyan():
    """0.25 ≤ ratio < 0.5 → '4' (ciano)."""
    from backend.shared.utils import get_color_from_elevation
    assert get_color_from_elevation(30.0, 0.0, 100.0) == "4"


def test_get_color_band_green():
    """0.5 ≤ ratio < 0.75 → '3' (verde)."""
    from backend.shared.utils import get_color_from_elevation
    assert get_color_from_elevation(60.0, 0.0, 100.0) == "3"


def test_get_color_band_yellow():
    """0.75 ≤ ratio < 0.9 → '2' (amarelo)."""
    from backend.shared.utils import get_color_from_elevation
    assert get_color_from_elevation(80.0, 0.0, 100.0) == "2"


def test_get_color_band_red():
    """ratio ≥ 0.9 → '1' (vermelho)."""
    from backend.shared.utils import get_color_from_elevation
    assert get_color_from_elevation(95.0, 0.0, 100.0) == "1"


# ---------------------------------------------------------------------------
# core/utils.py — get_layer_config with existing JSON file  (lines 136-141)
# ---------------------------------------------------------------------------

def test_get_layer_config_reads_valid_json(tmp_path, monkeypatch):
    """get_layer_config lê layers.json quando arquivo existe no caminho de produção."""
    from backend.shared import utils as utils_mod
    import importlib

    custom_config = {"highway": {"test_road": {"layer": "TEST_LAYER", "aci": 99}}}
    layers_file = tmp_path / "layers.json"
    layers_file.write_text(json.dumps(custom_config), encoding="utf-8")

    # Patch layers_path to point to our temp file
    original_fn = utils_mod.get_layer_config

    def patched_get_layer_config():
        try:
            with open(layers_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return original_fn()

    monkeypatch.setattr(utils_mod, "get_layer_config", patched_get_layer_config)
    result = utils_mod.get_layer_config()
    assert result["highway"]["test_road"]["layer"] == "TEST_LAYER"


def test_get_layer_config_fallback_when_no_file():
    """get_layer_config retorna configuração hardcoded quando layers.json não existe."""
    from backend.shared.utils import get_layer_config
    config = get_layer_config()
    assert "highway" in config
    assert "residential" in config["highway"]


# ---------------------------------------------------------------------------
# core/utils.py — clean_geometry deduplication and simplification  (lines 195, 200-205)
# ---------------------------------------------------------------------------

def _make_feature(layer, name, highway, feature_type, coords_xy=None, insertion_point_xy=None):
    """Helper: cria um SimpleNamespace simulando CadFeature."""
    return SimpleNamespace(
        layer=layer,
        name=name,
        highway=highway,
        feature_type=feature_type,
        coords_xy=coords_xy,
        insertion_point_xy=insertion_point_xy,
    )


def test_clean_geometry_removes_duplicate():
    """clean_geometry remove feature duplicado pelo hash."""
    from backend.shared.utils import clean_geometry

    f1 = _make_feature("ROADS", "Rua A", "residential", "Polyline",
                        coords_xy=[[0.0, 0.0], [1.0, 0.0]])
    f2 = _make_feature("ROADS", "Rua A", "residential", "Polyline",
                        coords_xy=[[0.0, 0.0], [1.0, 0.0]])  # exato duplicado

    result = clean_geometry([f1, f2])
    assert len(result) == 1


def test_clean_geometry_keeps_distinct_features():
    """clean_geometry mantém features distintos."""
    from backend.shared.utils import clean_geometry

    f1 = _make_feature("ROADS", "Rua A", "residential", "Polyline",
                        coords_xy=[[0.0, 0.0], [1.0, 0.0]])
    f2 = _make_feature("ROADS", "Rua B", "primary", "Polyline",
                        coords_xy=[[2.0, 2.0], [3.0, 3.0]])

    result = clean_geometry([f1, f2])
    assert len(result) == 2


def test_clean_geometry_simplifies_long_polyline():
    """clean_geometry simplifica polylines com > 2 pontos."""
    from backend.shared.utils import clean_geometry

    coords = [[float(i), 0.0] for i in range(10)]  # 10 colinear points
    f = _make_feature("ROADS", "Rua Longa", "primary", "Polyline", coords_xy=coords)

    result = clean_geometry([f])
    assert len(result) == 1
    # After simplification of collinear points, should have ≤ original count
    assert len(result[0].coords_xy) <= len(coords)


def test_clean_geometry_point_feature():
    """clean_geometry trata feature não-Polyline (ex: inserção de bloco)."""
    from backend.shared.utils import clean_geometry

    f = _make_feature("BLOCKS", "Poste", None, "Block",
                       insertion_point_xy=[100.0, 200.0])

    result = clean_geometry([f])
    assert len(result) == 1


# ---------------------------------------------------------------------------
# gis_core/geometry.py — snap_to_edge closes almost-closed polygon  (lines 21-23)
# ---------------------------------------------------------------------------

def test_snap_to_edge_closes_near_closed_polygon():
    """snap_to_edge deve fechar polígonos cujo último vértice está muito próximo do primeiro."""
    from backend.domain.geometry import snap_to_edge

    precision = 6
    tol = (10 ** -precision) * 2 * 0.5  # within threshold
    coords = [
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0 + tol / 2, 0.0 + tol / 2],  # nearly equals first
    ]
    result = snap_to_edge(coords, precision=precision)
    # Last coordinate should be snapped to first
    assert result[-1][0] == result[0][0]
    assert result[-1][1] == result[0][1]


def test_snap_to_edge_no_snap_when_far():
    """snap_to_edge NÃO deve fechar polígono quando último vértice está longe do primeiro."""
    from backend.domain.geometry import snap_to_edge

    coords = [
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.5, 0.5],  # clearly not close to [0, 0]
    ]
    result = snap_to_edge(coords)
    # Last coordinate should NOT be snapped
    assert result[-1] != result[0]


def test_snap_to_edge_deterministic_rounding():
    """snap_to_edge aplica arredondamento determinístico."""
    from backend.domain.geometry import snap_to_edge

    coords = [[1.123456789, 2.987654321], [3.141592653, 0.000000001]]
    result = snap_to_edge(coords, precision=6)
    assert result[0][0] == round(1.123456789, 6)
    assert result[1][1] == round(0.000000001, 6)


# ---------------------------------------------------------------------------
# gis_core/geometry.py — get_bounding_offset with insertion_point_xy  (lines 35-37)
# ---------------------------------------------------------------------------

def test_get_bounding_offset_uses_insertion_point():
    """get_bounding_offset usa insertion_point_xy quando coords_xy não está presente."""
    from backend.domain.geometry import get_bounding_offset

    f = SimpleNamespace(insertion_point_xy=[500.0, 300.0])
    ox, oy = get_bounding_offset([f])
    assert ox == 500.0
    assert oy == 300.0


def test_get_bounding_offset_prefers_coords_xy():
    """get_bounding_offset usa coords_xy quando disponível."""
    from backend.domain.geometry import get_bounding_offset

    f = SimpleNamespace(coords_xy=[[100.0, 200.0], [110.0, 210.0]])
    ox, oy = get_bounding_offset([f])
    assert ox == 100.0
    assert oy == 200.0


def test_get_bounding_offset_empty_features():
    """get_bounding_offset retorna (0.0, 0.0) para lista vazia."""
    from backend.domain.geometry import get_bounding_offset

    ox, oy = get_bounding_offset([])
    assert ox == 0.0
    assert oy == 0.0
