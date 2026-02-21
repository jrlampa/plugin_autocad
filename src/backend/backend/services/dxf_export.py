"""
backend/services/dxf_export.py
Serviço de exportação DXF (headless, usando ezdxf).

Princípio 2.5D: elevação como atributo XDATA — NÃO como coordenada Z.
As polilinhas são desenhadas em 2D (Z=0); a elevação é preservada como
atributo não-gráfico para uso em relatórios e BIM-LITE.

Conformidade:
  - ABNT NBR 14166:1998 / NBR 13133:2021 (padrão)
  - ANEEL/PRODIST (quando norma da concessionária está ativa)

Quando ProdistMetadata é fornecido, os metadados ABNT são substituídos
pelos metadados PRODIST no cabeçalho DXF.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional

from backend.core.logger import get_logger
from backend.gis_core.abnt import AbntDrawingMetadata, build_default_metadata
from backend.gis_core.prodist import ProdistMetadata
from backend.models import CadFeature

logger = get_logger(__name__)

# Constantes de camadas sisRUA (conformes ao padrão CAD interno)
APPID_SISRUA = "SISRUA"
XDATA_ELEVATION_KEY = 1000  # Group code para string em XDATA


def export_features_to_dxf(
    features: List[CadFeature],
    output_path: Optional[Path] = None,
    crs_label: str = "SIRGAS 2000 UTM",
    metadata: Optional[AbntDrawingMetadata] = None,
    epsg: int = 31983,
    prodist_metadata: Optional[ProdistMetadata] = None,
) -> Path:
    """
    Converte uma lista de CadFeature em um arquivo DXF R2010.

    Quando `prodist_metadata` é fornecido, os metadados ANEEL/PRODIST são
    injetados no cabeçalho DXF em substituição aos metadados ABNT.
    Caso contrário, usa metadados ABNT NBR 14166/13133.

    Args:
        features:         Lista de features CAD (Polyline ou Point).
        output_path:      Caminho de saída. Se None, usa arquivo temporário.
        crs_label:        Rótulo do CRS para metadados do header (legado).
        metadata:         Metadados ABNT explícitos. Se None, derivados de `epsg`.
        epsg:             Código EPSG da projeção (usado apenas quando `metadata`
                          não é fornecido e `prodist_metadata` é None).
        prodist_metadata: Metadados PRODIST. Quando presente, substitui ABNT.

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

    # Registra APPID para XDATA (elevação 2.5D + metadados de norma)
    doc.appids.new(APPID_SISRUA)

    # Quando PRODIST está ativo, substitui metadados ABNT pelos da concessionária
    if prodist_metadata is not None:
        _inject_prodist_metadata(doc, prodist_metadata)
        log_norma = prodist_metadata.norma_ativa
        log_extra: dict = {
            "concessionaria": prodist_metadata.concessionaria,
            "classe_tensao": prodist_metadata.classe_tensao.value,
        }
    else:
        if metadata is None:
            metadata = build_default_metadata(epsg)
        _inject_abnt_metadata(doc, metadata)
        log_norma = "ABNT NBR 14166/13133"
        log_extra = {
            "crs": metadata.crs_label,
            "escala": metadata.escala_str(),
        }

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
    logger.info(
        "dxf_exported",
        path=str(output_path),
        features=len(features),
        norma=log_norma,
        **log_extra,
    )
    return output_path


def _inject_abnt_metadata(doc, metadata: AbntDrawingMetadata) -> None:
    """
    Injeta metadados ABNT no cabeçalho do documento DXF.

    Estratégia: grava o identificador sisRUA em $FINGERPRINTGUID (variável
    suportada em R2010+) para rastreabilidade de levantamento conforme
    ABNT NBR 14166:1998 §7.1 — Identificação do levantamento.

    Falhas de gravação são registradas em log de aviso (não interrompem
    a exportação — o DXF geométrico permanece válido mesmo sem metadados).
    """
    # Grava identificador de rastreabilidade em $FINGERPRINTGUID (R2010+)
    try:
        doc.header["$FINGERPRINTGUID"] = (
            f"sisrua|{metadata.datum}|{metadata.zona_utm}|{metadata.escala_str()}"
        )
    except Exception as exc:
        logger.warning("abnt_fingerprintguid_failed", error=str(exc))

    # XDATA no objeto APPID não é suportado diretamente em R2010;
    # propriedades customizadas completas requerem DXF R2018+ (ACDSRECORD).
    # Para compatibilidade máxima, mantemos apenas o FINGERPRINTGUID acima.
    # As linhas ABNT completas estão disponíveis via metadata.to_comment_lines().


def _inject_prodist_metadata(doc, metadata: ProdistMetadata) -> None:
    """
    Injeta metadados ANEEL/PRODIST no cabeçalho do documento DXF.

    Substitui os metadados ABNT quando a norma da concessionária está ativa.
    Usa o mesmo slot $FINGERPRINTGUID para rastreabilidade (R2010+).
    """
    try:
        doc.header["$FINGERPRINTGUID"] = metadata.to_fingerprint()
    except Exception as exc:
        logger.warning("prodist_fingerprintguid_failed", error=str(exc))


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
