"""
tests/test_bim_lite_xdata.py
Testes do esquema XData BIM-LITE completo e da exportação de curvas de nível
na layer SISRUA_TOPO.

Half-way BIM: "uma rua sabe que é uma rua" — cada entidade CAD carrega seu
contexto semântico em XDATA: classe, tipo de via, nome, largura, elevação e
inclinação. As curvas de nível SRTM são adicionadas na layer SISRUA_TOPO,
habilitando o overlay topográfico na escala primária 1:1.000.

Coordenadas de referência (MEMORY.MD):
  REF_E = 714316.0 m  (SIRGAS 2000 UTM 23S — lat -22.15018°, lon -42.92185°)
  REF_N = 7549084.0 m
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

import pytest

from backend.domain.dto import CadFeature
from backend.application.dxf_export import (
    APPID_SISRUA,
    LAYER_SISRUA_TOPO,
    XDATA_ELEVATION_KEY,
    _build_bim_xdata,
    add_contours_to_dxf,
    export_features_to_dxf,
)

# ---------------------------------------------------------------------------
# Coordenadas de referência
# ---------------------------------------------------------------------------
REF_E = 714316.0
REF_N = 7549084.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _polyline(
    highway: str = "residential",
    name: str = "Rua Teste",
    layer: str = "SISRUA_OSM_HIGHWAY",
    width_m: float = 6.0,
    elevation: float = 850.0,
    slope: float = 1.5,
    coords: list | None = None,
) -> CadFeature:
    if coords is None:
        coords = [[REF_E, REF_N], [REF_E + 100, REF_N]]
    return CadFeature(
        feature_type="Polyline",
        layer=layer,
        name=name,
        highway=highway,
        width_m=width_m,
        elevation=elevation,
        slope=slope,
        coords_xy=coords,
    )


def _point(
    name: str = "Poste",
    block_name: str | None = "POSTE",
    elevation: float = 851.5,
) -> CadFeature:
    return CadFeature(
        feature_type="Point",
        layer="SISRUA_OSM_NODES",
        name=name,
        insertion_point_xy=[REF_E, REF_N],
        block_name=block_name,
        elevation=elevation,
    )


def _get_xdata_strings(entity) -> list[str]:
    """Extrai os valores string das tuplas XDATA do APPID SISRUA."""
    try:
        xd = entity.get_xdata(APPID_SISRUA)
        return [v for gc, v in xd if gc == XDATA_ELEVATION_KEY]
    except Exception:
        return []


def _export_and_open(features: List[CadFeature]):
    """Exporta features para DXF temporário e retorna (doc, msp)."""
    import ezdxf
    path = export_features_to_dxf(features)
    doc = ezdxf.readfile(str(path))
    return doc, doc.modelspace()


# ===========================================================================
# TestBimLiteXdataBuilder — unit tests da função _build_bim_xdata
# ===========================================================================

class TestBimLiteXdataBuilder:
    """Valida o esquema BIM-LITE retornado por _build_bim_xdata."""

    def test_street_class_when_highway_set(self):
        feat = _polyline(highway="primary")
        xdata = _build_bim_xdata(feat)
        strings = [v for _, v in xdata]
        assert "sisrua:class=street" in strings

    def test_polyline_class_when_no_highway(self):
        feat = CadFeature(
            feature_type="Polyline",
            layer="SISRUA_OSM_HIGHWAY",
            coords_xy=[[0, 0], [10, 0]],
        )
        xdata = _build_bim_xdata(feat)
        strings = [v for _, v in xdata]
        assert "sisrua:class=polyline" in strings

    def test_block_class_for_point_with_block_name(self):
        feat = _point(block_name="POSTE")
        xdata = _build_bim_xdata(feat)
        strings = [v for _, v in xdata]
        assert "sisrua:class=block" in strings

    def test_point_class_for_point_without_block(self):
        feat = _point(block_name=None)
        xdata = _build_bim_xdata(feat)
        strings = [v for _, v in xdata]
        assert "sisrua:class=point" in strings

    def test_highway_field_present(self):
        feat = _polyline(highway="primary")
        strings = [v for _, v in _build_bim_xdata(feat)]
        assert "sisrua:highway=primary" in strings

    def test_name_field_present(self):
        feat = _polyline(name="Av. Rio Branco")
        strings = [v for _, v in _build_bim_xdata(feat)]
        assert "sisrua:name=Av. Rio Branco" in strings

    def test_width_m_field_present(self):
        feat = _polyline(width_m=7.5)
        strings = [v for _, v in _build_bim_xdata(feat)]
        assert any("sisrua:width_m=7.50" in s for s in strings)

    def test_elevation_field_present(self):
        feat = _polyline(elevation=1234.5678)
        strings = [v for _, v in _build_bim_xdata(feat)]
        assert any("sisrua:elevation=1234.5678m" in s for s in strings)

    def test_slope_field_present(self):
        feat = _polyline(slope=3.75)
        strings = [v for _, v in _build_bim_xdata(feat)]
        assert any("sisrua:slope=3.75pct" in s for s in strings)

    def test_layer_field_present(self):
        feat = _polyline(layer="SISRUA_RUA_SECUNDARIA")
        strings = [v for _, v in _build_bim_xdata(feat)]
        assert "sisrua:layer=SISRUA_RUA_SECUNDARIA" in strings

    def test_all_group_codes_are_1000(self):
        feat = _polyline()
        xdata = _build_bim_xdata(feat)
        assert all(gc == XDATA_ELEVATION_KEY for gc, _ in xdata)

    def test_no_highway_no_highway_field(self):
        feat = CadFeature(feature_type="Polyline", layer="L", coords_xy=[[0, 0], [1, 0]])
        strings = [v for _, v in _build_bim_xdata(feat)]
        assert not any("sisrua:highway=" in s for s in strings)

    def test_none_elevation_no_elevation_field(self):
        feat = CadFeature(
            feature_type="Polyline", layer="L",
            highway="track", coords_xy=[[0, 0], [1, 0]]
        )
        strings = [v for _, v in _build_bim_xdata(feat)]
        assert not any("sisrua:elevation=" in s for s in strings)


# ===========================================================================
# TestBimLiteXdataInDxf — valida xdata no DXF real (integração ezdxf)
# ===========================================================================

class TestBimLiteXdataInDxf:
    """Valida que o DXF exportado contém o esquema BIM-LITE correto."""

    def test_polyline_has_bim_class_in_dxf(self):
        feat = _polyline(highway="residential")
        doc, msp = _export_and_open([feat])
        plines = list(msp.query("LWPOLYLINE"))
        strings = _get_xdata_strings(plines[0])
        assert "sisrua:class=street" in strings

    def test_polyline_has_highway_in_dxf(self):
        feat = _polyline(highway="secondary")
        doc, msp = _export_and_open([feat])
        plines = list(msp.query("LWPOLYLINE"))
        strings = _get_xdata_strings(plines[0])
        assert "sisrua:highway=secondary" in strings

    def test_polyline_has_name_in_dxf(self):
        feat = _polyline(name="Rua das Palmeiras")
        doc, msp = _export_and_open([feat])
        plines = list(msp.query("LWPOLYLINE"))
        strings = _get_xdata_strings(plines[0])
        assert "sisrua:name=Rua das Palmeiras" in strings

    def test_polyline_has_width_in_dxf(self):
        feat = _polyline(width_m=8.0)
        doc, msp = _export_and_open([feat])
        plines = list(msp.query("LWPOLYLINE"))
        strings = _get_xdata_strings(plines[0])
        assert any("sisrua:width_m=8.00" in s for s in strings)

    def test_polyline_has_elevation_in_dxf(self):
        feat = _polyline(elevation=750.0)
        doc, msp = _export_and_open([feat])
        plines = list(msp.query("LWPOLYLINE"))
        strings = _get_xdata_strings(plines[0])
        assert any("sisrua:elevation=750.0000m" in s for s in strings)

    def test_polyline_has_slope_in_dxf(self):
        feat = _polyline(slope=2.5)
        doc, msp = _export_and_open([feat])
        plines = list(msp.query("LWPOLYLINE"))
        strings = _get_xdata_strings(plines[0])
        assert any("sisrua:slope=2.50pct" in s for s in strings)

    def test_polyline_has_layer_in_dxf(self):
        feat = _polyline(layer="SISRUA_OSM_HIGHWAY")
        doc, msp = _export_and_open([feat])
        plines = list(msp.query("LWPOLYLINE"))
        strings = _get_xdata_strings(plines[0])
        assert "sisrua:layer=SISRUA_OSM_HIGHWAY" in strings

    def test_point_block_has_bim_class(self):
        feat = _point(block_name="POSTE")
        doc, msp = _export_and_open([feat])
        inserts = list(msp.query("INSERT"))
        strings = _get_xdata_strings(inserts[0])
        assert "sisrua:class=block" in strings

    def test_point_simple_has_bim_class(self):
        feat = _point(block_name=None)
        doc, msp = _export_and_open([feat])
        points = list(msp.query("POINT"))
        strings = _get_xdata_strings(points[0])
        assert "sisrua:class=point" in strings

    def test_polyline_width_set_as_const_width(self):
        """A largura da via também deve ser refletida como const_width da LWPolyline."""
        feat = _polyline(width_m=6.0)
        doc, msp = _export_and_open([feat])
        plines = list(msp.query("LWPOLYLINE"))
        assert plines[0].dxf.const_width == pytest.approx(6.0)

    def test_multiple_features_each_has_bim_xdata(self):
        features = [
            _polyline(name="Rua A", highway="primary"),
            _polyline(name="Rua B", highway="secondary",
                      coords=[[REF_E + 200, REF_N], [REF_E + 300, REF_N]]),
        ]
        doc, msp = _export_and_open(features)
        plines = list(msp.query("LWPOLYLINE"))
        assert len(plines) == 2
        for pline in plines:
            strings = _get_xdata_strings(pline)
            assert "sisrua:class=street" in strings


# ===========================================================================
# TestDxfContourLayer — valida add_contours_to_dxf
# ===========================================================================

class TestDxfContourLayer:
    """Valida a geração de curvas de nível (SISRUA_TOPO) em DXF headless."""

    @pytest.fixture
    def doc_with_features(self):
        """Cria um DXF com uma feição urbana base."""
        feat = _polyline()
        path = export_features_to_dxf([feat])
        import ezdxf
        return ezdxf.readfile(str(path))

    def test_creates_sisrua_topo_layer(self, doc_with_features):
        doc = doc_with_features
        contours = [{"elevation": 850.0, "coords": [[0, 0], [100, 0], [100, 100]]}]
        add_contours_to_dxf(doc, contours)
        assert LAYER_SISRUA_TOPO in doc.layers

    def test_topo_layer_color_is_cyan(self, doc_with_features):
        """Layer SISRUA_TOPO deve ter cor ciano (ACI 4)."""
        doc = doc_with_features
        contours = [{"elevation": 850.0, "coords": [[0, 0], [100, 0]]}]
        add_contours_to_dxf(doc, contours)
        layer = doc.layers.get(LAYER_SISRUA_TOPO)
        assert layer.dxf.color == 4

    def test_returns_correct_count(self, doc_with_features):
        doc = doc_with_features
        contours = [
            {"elevation": 850.0, "coords": [[0, 0], [100, 0]]},
            {"elevation": 860.0, "coords": [[0, 10], [100, 10], [100, 20]]},
        ]
        count = add_contours_to_dxf(doc, contours)
        assert count == 2

    def test_skips_short_coords(self, doc_with_features):
        """Curvas com menos de 2 coordenadas devem ser ignoradas."""
        doc = doc_with_features
        contours = [
            {"elevation": 850.0, "coords": [[0, 0]]},        # 1 ponto → skip
            {"elevation": 860.0, "coords": []},              # vazio → skip
            {"elevation": 870.0, "coords": [[0, 0], [10, 0]]},  # válida
        ]
        count = add_contours_to_dxf(doc, contours)
        assert count == 1

    def test_empty_input_returns_zero(self, doc_with_features):
        doc = doc_with_features
        assert add_contours_to_dxf(doc, []) == 0
        assert add_contours_to_dxf(doc, None) == 0

    def test_contour_xdata_class(self, doc_with_features):
        """Cada curva de nível deve ter sisrua:class=contour em XDATA."""
        doc = doc_with_features
        contours = [{"elevation": 850.0, "coords": [[0, 0], [100, 0]]}]
        add_contours_to_dxf(doc, contours)
        msp = doc.modelspace()
        topo_lines = [e for e in msp.query("LWPOLYLINE")
                      if e.dxf.layer == LAYER_SISRUA_TOPO]
        assert len(topo_lines) == 1
        strings = _get_xdata_strings(topo_lines[0])
        assert "sisrua:class=contour" in strings

    def test_contour_xdata_elevation(self, doc_with_features):
        """Cada curva de nível deve ter sisrua:elevation=<elev>m em XDATA."""
        doc = doc_with_features
        contours = [{"elevation": 870.5, "coords": [[0, 0], [100, 0]]}]
        add_contours_to_dxf(doc, contours)
        msp = doc.modelspace()
        topo_lines = [e for e in msp.query("LWPOLYLINE")
                      if e.dxf.layer == LAYER_SISRUA_TOPO]
        strings = _get_xdata_strings(topo_lines[0])
        assert any("sisrua:elevation=870.50m" in s for s in strings)

    def test_contour_xdata_interval(self, doc_with_features):
        """Metadado de intervalo deve aparecer em XDATA."""
        doc = doc_with_features
        contours = [{"elevation": 880.0, "coords": [[0, 0], [100, 0]]}]
        add_contours_to_dxf(doc, contours, interval=5.0)
        msp = doc.modelspace()
        topo_lines = [e for e in msp.query("LWPOLYLINE")
                      if e.dxf.layer == LAYER_SISRUA_TOPO]
        strings = _get_xdata_strings(topo_lines[0])
        assert any("sisrua:interval=5.0m" in s for s in strings)

    def test_contour_entities_are_in_topo_layer(self, doc_with_features):
        """As entidades de curva de nível devem estar na layer SISRUA_TOPO."""
        doc = doc_with_features
        contours = [
            {"elevation": 850.0, "coords": [[0, 0], [100, 0]]},
            {"elevation": 860.0, "coords": [[0, 10], [100, 10]]},
        ]
        add_contours_to_dxf(doc, contours)
        msp = doc.modelspace()
        topo_lines = [e for e in msp.query("LWPOLYLINE")
                      if e.dxf.layer == LAYER_SISRUA_TOPO]
        assert len(topo_lines) == 2

    def test_urban_features_not_in_topo_layer(self, doc_with_features):
        """Feições urbanas não devem ser movidas para SISRUA_TOPO."""
        doc = doc_with_features
        contours = [{"elevation": 850.0, "coords": [[0, 0], [100, 0]]}]
        add_contours_to_dxf(doc, contours)
        msp = doc.modelspace()
        urban_lines = [e for e in msp.query("LWPOLYLINE")
                       if e.dxf.layer != LAYER_SISRUA_TOPO]
        assert len(urban_lines) >= 1

    def test_multiple_add_calls_idempotent_layer(self, doc_with_features):
        """Chamar add_contours_to_dxf duas vezes não duplica a layer."""
        doc = doc_with_features
        contours = [{"elevation": 850.0, "coords": [[0, 0], [100, 0]]}]
        add_contours_to_dxf(doc, contours)
        add_contours_to_dxf(doc, contours)
        # A layer deve existir exatamente uma vez
        assert len([l for l in doc.layers if l.dxf.name == LAYER_SISRUA_TOPO]) == 1


# ===========================================================================
# TestExportServiceWithTopo — valida export_project_with_topo (integração DB)
# ===========================================================================

class TestExportServiceWithTopo:
    """Valida o método ExportService.export_project_with_topo."""

    @pytest.fixture
    def svc(self, tmp_path):
        """Cria ExportService com DB temporário contendo um projeto e feições."""
        import sqlite3
        import json
        from backend.application.export_service import ExportService

        db = tmp_path / "test.db"
        project_id = "proj-topo-01"
        conn = sqlite3.connect(str(db))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME, crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS CadFeatures (
                feature_id INTEGER PRIMARY KEY, project_id TEXT,
                feature_type TEXT NOT NULL, layer TEXT, name TEXT,
                highway TEXT, width_m REAL, color TEXT,
                elevation REAL, slope REAL,
                original_geojson_properties TEXT,
                coords_xy TEXT, insertion_point_xy TEXT,
                block_name TEXT, rotation REAL, scale REAL
            )
        """)
        conn.execute(
            "INSERT INTO Projects (project_id, project_name, crs_out, version) "
            "VALUES (?, ?, ?, ?)",
            (project_id, "Projeto Topo", "EPSG:31983", 1),
        )
        conn.execute(
            """INSERT INTO CadFeatures
               (project_id, feature_type, layer, name, highway, width_m, color,
                elevation, slope, original_geojson_properties, coords_xy,
                insertion_point_xy, block_name, rotation, scale)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id, "Polyline", "SISRUA_OSM_HIGHWAY", "Rua Topo",
                "residential", 6.0, None, 850.0, 1.5,
                json.dumps({}),
                json.dumps([[REF_E, REF_N], [REF_E + 100, REF_N]]),
                json.dumps([]), None, 0.0, 1.0,
            ),
        )
        conn.commit()
        conn.close()
        return ExportService(db_path=db), project_id

    def test_export_with_no_contours_returns_dxf(self, svc):
        service, project_id = svc
        path = service.export_project_with_topo(project_id, contour_lines=None)
        assert path.exists()
        assert path.suffix == ".dxf"

    def test_export_with_no_contours_no_topo_layer(self, svc):
        import ezdxf
        service, project_id = svc
        path = service.export_project_with_topo(project_id, contour_lines=[])
        doc = ezdxf.readfile(str(path))
        assert LAYER_SISRUA_TOPO not in doc.layers

    def test_export_with_contours_creates_topo_layer(self, svc):
        import ezdxf
        service, project_id = svc
        contours = [
            {"elevation": 850.0, "coords": [[REF_E, REF_N], [REF_E + 50, REF_N]]},
            {"elevation": 860.0, "coords": [[REF_E, REF_N + 10], [REF_E + 50, REF_N + 10]]},
        ]
        path = service.export_project_with_topo(
            project_id, contour_lines=contours, contour_interval=10.0
        )
        doc = ezdxf.readfile(str(path))
        assert LAYER_SISRUA_TOPO in doc.layers

    def test_export_with_contours_correct_count(self, svc):
        import ezdxf
        service, project_id = svc
        contours = [
            {"elevation": 850.0, "coords": [[0, 0], [100, 0]]},
            {"elevation": 860.0, "coords": [[0, 10], [100, 10]]},
            {"elevation": 870.0, "coords": [[0, 20], [100, 20]]},
        ]
        path = service.export_project_with_topo(project_id, contour_lines=contours)
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()
        topo_lines = [e for e in msp.query("LWPOLYLINE")
                      if e.dxf.layer == LAYER_SISRUA_TOPO]
        assert len(topo_lines) == 3

    def test_export_with_topo_urban_features_preserved(self, svc):
        """Feições urbanas devem ser preservadas mesmo com curvas de nível."""
        import ezdxf
        service, project_id = svc
        contours = [{"elevation": 850.0, "coords": [[0, 0], [100, 0]]}]
        path = service.export_project_with_topo(project_id, contour_lines=contours)
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()
        urban = [e for e in msp.query("LWPOLYLINE")
                 if e.dxf.layer != LAYER_SISRUA_TOPO]
        assert len(urban) >= 1
