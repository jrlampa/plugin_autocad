"""
tests/test_dxf_abnt.py
Testes de conformidade ABNT para exportação DXF — módulo gis_core/abnt.py.

Normas cobertas:
  - ABNT NBR 14166:1998 — Rede de referência cadastral municipal
  - ABNT NBR 13133:2021 — Execução de levantamento topográfico
  - ABNT NBR 15777:2009 — Representação de informação geográfica digital

Coordenadas de referência (conforme MEMORY.MD):
  REF_1 — Campo (UTM 23K): E=788547, N=7634925
  REF_2 — Projeto (lat/lon -22.15018°, -42.92185°): E≈714316, N≈7549084

Separado de test_dxf.py (modularização — regra 500 linhas).
"""
from __future__ import annotations

import math
from typing import List

import pytest

from backend.models import CadFeature
from backend.services.dxf_export import export_features_to_dxf

# ---------------------------------------------------------------------------
# Coordenadas de referência (UTM 23S SIRGAS 2000 / EPSG:31983)
# ---------------------------------------------------------------------------
REF_E = 714316.0   # Easting (m) para -22.15018°, -42.92185°
REF_N = 7549084.0  # Northing (m) para -22.15018°, -42.92185°
REF2_E = 788547.0  # UTM 23K 788547 (campo)
REF2_N = 7634925.0 # UTM 23K 7634925 (campo)


def _make_road(
    name: str = "Rua Teste",
    layer: str = "SISRUA_OSM_HIGHWAY",
    length_m: float = 100.0,
    elevation: float = 850.0,
) -> CadFeature:
    """Cria uma polilinha CAD de rua alinhada ao leste, com origem em REF_E, REF_N."""
    return CadFeature(
        feature_type="Polyline",
        layer=layer,
        name=name,
        highway="residential",
        coords_xy=[
            [REF_E, REF_N],
            [REF_E + length_m, REF_N],
        ],
        elevation=elevation,
        width_m=6.0,
    )


# ---------------------------------------------------------------------------
# Testes do módulo abnt.py — importações e API pública
# ---------------------------------------------------------------------------

def test_abnt_module_imports():
    """O módulo abnt.py deve importar sem erros."""
    from backend.gis_core.abnt import (
        AbntDrawingMetadata,
        build_default_metadata,
        validate_utm_coordinates,
        nearest_abnt_escala,
        ABNT_ESCALAS_CADASTRAIS,
    )
    assert AbntDrawingMetadata is not None
    assert ABNT_ESCALAS_CADASTRAIS


def test_abnt_metadata_defaults():
    """AbntDrawingMetadata com valores padrão deve ter campos SIRGAS 2000."""
    from backend.gis_core.abnt import AbntDrawingMetadata

    meta = AbntDrawingMetadata()
    assert "SIRGAS 2000" in meta.datum
    assert meta.unidade == "m"
    assert meta.epsg == 31983


def test_abnt_escala_str():
    """Notação de escala ABNT deve usar ponto como separador de milhar."""
    from backend.gis_core.abnt import AbntDrawingMetadata

    meta_1k = AbntDrawingMetadata(escala=1_000)
    meta_25k = AbntDrawingMetadata(escala=25_000)
    meta_500 = AbntDrawingMetadata(escala=500)

    assert meta_1k.escala_str() == "1:1.000"
    assert meta_25k.escala_str() == "1:25.000"
    assert meta_500.escala_str() == "1:500"


def test_abnt_tolerancia_por_escala():
    """Tolerâncias planimétricas devem seguir NBR 13133:2021 §8.5."""
    from backend.gis_core.abnt import AbntDrawingMetadata

    meta_1k = AbntDrawingMetadata(escala=1_000)
    meta_500 = AbntDrawingMetadata(escala=500)
    meta_10k = AbntDrawingMetadata(escala=10_000)
    meta_25k = AbntDrawingMetadata(escala=25_000)

    assert meta_1k.tolerancia_m() == pytest.approx(0.20)   # 0,2 mm × 1000
    assert meta_500.tolerancia_m() == pytest.approx(0.10)  # 0,2 mm × 500
    assert meta_10k.tolerancia_m() == pytest.approx(2.00)  # 0,2 mm × 10000
    assert meta_25k.tolerancia_m() == pytest.approx(5.00)  # 0,2 mm × 25000


def test_abnt_validate_utm_coordinates_valid():
    """Coordenadas UTM de referência devem ser válidas conforme ABNT NBR 14166."""
    from backend.gis_core.abnt import validate_utm_coordinates

    # REF_1 (campo): UTM 23K 788547 7634925
    assert validate_utm_coordinates(REF2_E, REF2_N) is True
    # REF_2 (projeto): E≈714316, N≈7549084
    assert validate_utm_coordinates(REF_E, REF_N) is True


def test_abnt_validate_utm_coordinates_invalid():
    """Coordenadas fora do território brasileiro devem ser rejeitadas."""
    from backend.gis_core.abnt import validate_utm_coordinates

    # Easting fora dos limites brasileiros
    assert validate_utm_coordinates(50_000.0, 7_549_084.0) is False
    assert validate_utm_coordinates(950_000.0, 7_549_084.0) is False
    # Northing fora dos limites
    assert validate_utm_coordinates(714_316.0, 500_000.0) is False


def test_abnt_nearest_escala():
    """nearest_abnt_escala deve retornar a escala ABNT NBR 13133 mais próxima."""
    from backend.gis_core.abnt import nearest_abnt_escala

    assert nearest_abnt_escala(800) == 1_000
    assert nearest_abnt_escala(499) == 500
    assert nearest_abnt_escala(3_000) == 2_000
    assert nearest_abnt_escala(7_000) == 5_000


def test_abnt_build_default_metadata_epsg():
    """build_default_metadata deve derivar zona UTM e label do EPSG."""
    from backend.gis_core.abnt import build_default_metadata

    meta = build_default_metadata(epsg=31983)
    assert meta.zona_utm == "23S"
    assert "23S" in meta.crs_label
    assert "31983" in meta.crs_label
    assert meta.epsg == 31983


def test_abnt_comment_lines_content():
    """to_comment_lines deve conter campos obrigatórios da NBR 14166."""
    from backend.gis_core.abnt import AbntDrawingMetadata

    meta = AbntDrawingMetadata()
    joined = " ".join(meta.to_comment_lines())
    assert "ABNT" in joined
    assert "SIRGAS" in joined
    assert "UTM" in joined
    assert meta.escala_str() in joined


def test_abnt_dxf_header_fingerprintguid(tmp_path):
    """DXF exportado com metadados ABNT deve ter $FINGERPRINTGUID com rastreabilidade sisRUA."""
    import ezdxf
    from backend.gis_core.abnt import AbntDrawingMetadata

    meta = AbntDrawingMetadata(
        crs_label="SIRGAS 2000 / UTM Zona 23S (EPSG:31983)",
        epsg=31983,
        escala=1_000,
        orgao="Teste Automatizado",
    )

    out = tmp_path / "test_abnt_header.dxf"
    export_features_to_dxf(
        [_make_road("Via ABNT", length_m=100.0)],
        output_path=out,
        metadata=meta,
    )

    doc = ezdxf.readfile(str(out))
    assert doc.dxfversion >= "AC1024", "DXF deve ser R2010+"
    fingerprint = doc.header.get("$FINGERPRINTGUID", "")
    assert "sisrua" in fingerprint
    assert "23S" in fingerprint


def test_abnt_dxf_default_metadata_applied(tmp_path):
    """export_features_to_dxf sem metadata explícito deve usar build_default_metadata."""
    import ezdxf

    out = tmp_path / "test_default_meta.dxf"
    export_features_to_dxf(
        [_make_road(length_m=500.0)],
        output_path=out,
        epsg=31983,
    )

    doc = ezdxf.readfile(str(out))
    assert doc is not None
    fingerprint = doc.header.get("$FINGERPRINTGUID", "")
    assert "sisrua" in fingerprint
