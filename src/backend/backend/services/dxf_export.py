"""
backend/services/dxf_export.py
Serviço de exportação DXF (headless, usando ezdxf).

Princípio 2.5D: elevação como atributo XDATA — NÃO como coordenada Z.
As polilinhas são desenhadas em 2D (Z=0); a elevação é preservada como
atributo não-gráfico para uso em relatórios e BIM-LITE.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional

from backend.core.logger import get_logger
from backend.models import CadFeature

logger = get_logger(__name__)

# Constantes de camadas sisRUA (conformes ao padrão CAD interno)
APPID_SISRUA = "SISRUA"
XDATA_ELEVATION_KEY = 1000  # Group code para string em XDATA


def export_features_to_dxf(
    features: List[CadFeature],
    output_path: Optional[Path] = None,
    crs_label: str = "SIRGAS 2000 UTM",
) -> Path:
    """
    Converte uma lista de CadFeature em um arquivo DXF R2010.

    Args:
        features: Lista de features CAD (Polyline ou Point).
        output_path: Caminho de saída. Se None, usa arquivo temporário.
        crs_label: Rótulo do CRS para metadados do header.

    Returns:
        Path para o arquivo .dxf gerado.
    """
    try:
        import ezdxf
        from ezdxf import units
    except ImportError as exc:
        raise ImportError("ezdxf não instalado. Execute: pip install ezdxf") from exc

    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = units.M  # metros
    doc.header["$MEASUREMENT"] = 1    # sistema métrico

    msp = doc.modelspace()

    # Registra APPID para XDATA de elevação (2.5D)
    doc.appids.new(APPID_SISRUA)

    _ensure_layers(doc, features)

    for feat in features:
        if feat.feature_type == "Polyline":
            _add_polyline(msp, feat)
        elif feat.feature_type == "Point":
            _add_point(msp, feat)

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".dxf", delete=False)
        output_path = Path(tmp.name)
        tmp.close()

    doc.saveas(str(output_path))
    logger.info("dxf_exported", path=str(output_path), features=len(features))
    return output_path


def _ensure_layers(doc, features: List[CadFeature]) -> None:
    """Garante que todas as camadas referenciadas existam no documento."""
    existing = {layer.dxf.name for layer in doc.layers}
    for feat in features:
        layer = feat.layer or "0"
        if layer not in existing:
            doc.layers.new(layer)
            existing.add(layer)


def _add_polyline(msp, feat: CadFeature) -> None:
    """Adiciona uma polilinha 2D (Z=0) com elevação como XDATA (2.5D)."""
    coords = feat.coords_xy
    if not coords or len(coords) < 2:
        return

    # 2.5D: coordenadas sempre 2D (X, Y). Z=0 por padrão.
    points_2d = [(float(x), float(y)) for x, y in coords]
    layer = feat.layer or "0"

    pline = msp.add_lwpolyline(points_2d, dxfattribs={"layer": layer})

    # Elevação como XDATA (atributo não-gráfico — princípio 2.5D)
    if feat.elevation is not None:
        pline.set_xdata(
            APPID_SISRUA,
            [(XDATA_ELEVATION_KEY, f"sisrua:elevation={feat.elevation:.4f}m")],
        )

    # Largura como propriedade constante da polilinha
    if feat.width_m is not None:
        pline.dxf.const_width = max(0.0, float(feat.width_m))


def _add_point(msp, feat: CadFeature) -> None:
    """Adiciona um ponto de inserção (INSERT ou POINT) com elevação como XDATA."""
    ip = feat.insertion_point_xy
    if not ip or len(ip) < 2:
        return

    x, y = float(ip[0]), float(ip[1])
    layer = feat.layer or "0"

    if feat.block_name:
        # INSERT de bloco CAD
        insert = msp.add_blockref(
            feat.block_name,
            insert=(x, y, 0.0),
            dxfattribs={
                "layer": layer,
                "rotation": feat.rotation or 0.0,
                "xscale": feat.scale or 1.0,
                "yscale": feat.scale or 1.0,
                "zscale": feat.scale or 1.0,
            },
        )
        if feat.elevation is not None:
            insert.set_xdata(
                APPID_SISRUA,
                [(XDATA_ELEVATION_KEY, f"sisrua:elevation={feat.elevation:.4f}m")],
            )
    else:
        # POINT simples quando não há bloco definido
        pt = msp.add_point((x, y, 0.0), dxfattribs={"layer": layer})
        if feat.elevation is not None:
            pt.set_xdata(
                APPID_SISRUA,
                [(XDATA_ELEVATION_KEY, f"sisrua:elevation={feat.elevation:.4f}m")],
            )
