"""
backend.application/dxf_export.py
Serviço de exportação DXF (headless, usando ezdxf).

Princípio 2.5D: elevação como atributo XDATA — NÃO como coordenada Z.
As polilinhas são desenhadas em 2D (Z=0); a elevação é preservada como
atributo não-gráfico para uso em relatórios e BIM-LITE.

Conformidade:
  - ABNT NBR 14166:1998 / NBR 13133:2021 (padrão)
  - ANEEL/PRODIST (quando norma da concessionária está ativa)

Quando ProdistMetadata é fornecido, os metadados ABNT são substituídos
pelos metadados PRODIST no cabeçalho DXF. Além disso, faixas de segurança
(buffers) são geradas geometricamente para cada rede elétrica classificada
conforme NR-10:2016 e PRODIST Módulo 3 §3.4.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional

from backend.shared.logger import get_logger
from backend.domain.abnt import AbntDrawingMetadata, build_default_metadata
from backend.domain.prodist import ProdistMetadata, TensaoClasse, camada_buffer_aneel
from backend.domain.dto import CadFeature

logger = get_logger(__name__)

# Constantes de camadas sisRUA (conformes ao padrão CAD interno)
APPID_SISRUA = "SISRUA"
XDATA_ELEVATION_KEY = 1000  # Group code para string em XDATA (ezdxf DXF group code)

# ---------------------------------------------------------------------------
# BIM-LITE XDATA schema — "uma rua sabe que é uma rua"
# Todos os campos são strings (group code 1000) para máxima compatibilidade.
# Prefixo: "sisrua:<chave>=<valor>"
# ---------------------------------------------------------------------------
LAYER_SISRUA_TOPO = "SISRUA_TOPO"  # Curvas de nível SRTM

# Mapeamento camada → classe de tensão para geração automática de buffers PRODIST
_LAYER_CLASSE_MAP: dict[str, TensaoClasse] = {
    "SISRUA_ANEEL_BT": TensaoClasse.BT,
    "SISRUA_ANEEL_MT": TensaoClasse.MT,
    "SISRUA_ANEEL_AT": TensaoClasse.AT,
}


def generate_prodist_buffer_features(
    features: List[CadFeature],
    prodist_metadata: ProdistMetadata,
) -> List[CadFeature]:
    """
    Gera faixas de segurança (buffers) ANEEL/PRODIST como features CAD.

    Para cada polilinha em camadas SISRUA_ANEEL_*, computa um polígono
    buffer usando shapely conforme as distâncias definidas em NR-10:2016
    (Tabela 1) e PRODIST Módulo 3 §3.4. O resultado é uma lista de
    CadFeature do tipo Polyline na camada SISRUA_ANEEL_BUFFER_*.

    Princípio 2.5D: os polígonos de buffer são 2D (Z=0); a elevação da
    feature original é propagada como atributo `elevation` via XDATA.

    Args:
        features:         Lista de features CAD de origem.
        prodist_metadata: Metadados PRODIST com distâncias de buffer.

    Returns:
        Lista de CadFeature representando os polígonos de buffer.
    """
    try:
        from shapely.geometry import LineString
    except ImportError:
        logger.warning("shapely_not_available_buffers_skipped")
        return []

    buffer_features: List[CadFeature] = []

    for feat in features:
        if feat.feature_type != "Polyline":
            continue

        layer = feat.layer or "0"

        # Detecta classe de tensão pelo layer ou usa a do metadado PRODIST
        classe = _LAYER_CLASSE_MAP.get(layer, prodist_metadata.classe_tensao)

        from backend.domain.prodist import buffer_de_seguranca_m
        dist_m = buffer_de_seguranca_m(classe)
        buffer_layer = camada_buffer_aneel(classe)

        coords = feat.coords_xy
        if not coords or len(coords) < 2:
            continue

        try:
            line = LineString([(float(x), float(y)) for x, y in coords])
            # cap_style=2 → flat caps (BufferCapStyle.flat)
            # join_style=2 → mitre joins (BufferJoinStyle.mitre)
            # Flat caps e mitre joins produzem faixas retangulares que
            # representam fielmente a faixa de servidão conforme PRODIST.
            buffered = line.buffer(dist_m, cap_style=2, join_style=2)
            exterior = list(buffered.exterior.coords)
            if len(exterior) < 3:
                continue

            buffer_features.append(
                CadFeature(
                    feature_type="Polyline",
                    layer=buffer_layer,
                    name=f"Buffer PRODIST {classe.value}",
                    coords_xy=[[float(x), float(y)] for x, y in exterior],
                    elevation=feat.elevation,
                )
            )
        except Exception as exc:
            logger.warning("prodist_buffer_failed", layer=layer, error=str(exc))

    logger.info(
        "prodist_buffers_generated",
        input_features=len(features),
        buffer_features=len(buffer_features),
    )
    return buffer_features


def export_features_to_dxf(
    features: List[CadFeature],
    output_path: Optional[Path] = None,
    crs_label: str = "SIRGAS 2000 UTM",
    metadata: Optional[AbntDrawingMetadata] = None,
    epsg: int = 31983,
    prodist_metadata: Optional[ProdistMetadata] = None,
    include_prodist_buffers: bool = False,
) -> Path:
    """
    Converte uma lista de CadFeature em um arquivo DXF R2010.

    Quando `prodist_metadata` é fornecido, os metadados ANEEL/PRODIST são
    injetados no cabeçalho DXF em substituição aos metadados ABNT.
    Caso contrário, usa metadados ABNT NBR 14166/13133.

    Args:
        features:               Lista de features CAD (Polyline ou Point).
        output_path:            Caminho de saída. Se None, usa arquivo temporário.
        crs_label:              Rótulo do CRS para metadados do header (legado).
        metadata:               Metadados ABNT explícitos. Se None, derivados de `epsg`.
        epsg:                   Código EPSG da projeção (usado apenas quando `metadata`
                                não é fornecido e `prodist_metadata` é None).
        prodist_metadata:       Metadados PRODIST. Quando presente, substitui ABNT.
        include_prodist_buffers: Quando True e `prodist_metadata` não é None,
                                gera faixas de segurança geométricas (NR-10:2016)
                                nas camadas SISRUA_ANEEL_BUFFER_*.

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

    # Gera buffers PRODIST quando solicitado (faixas de segurança NR-10:2016)
    all_features = list(features)
    if prodist_metadata is not None and include_prodist_buffers:
        buffer_feats = generate_prodist_buffer_features(features, prodist_metadata)
        all_features.extend(buffer_feats)
        _ensure_layers(doc, buffer_feats)

    for feat in all_features:
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
        features=len(all_features),
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


def _build_bim_xdata(feat: CadFeature) -> list:
    """
    Constrói a lista de tuplas XDATA BIM-LITE para uma feature.

    Esquema sisRUA (Half-way BIM):
      sisrua:class    — classe da entidade (street, point, block)
      sisrua:highway  — tag highway do OSM (primary, secondary, residential…)
      sisrua:name     — nome da via ou elemento
      sisrua:width_m  — largura estimada em metros
      sisrua:elevation — elevação 2.5D em metros
      sisrua:slope    — inclinação em percentual
      sisrua:layer    — camada CAD lógica
    """
    xdata = []
    if feat.feature_type == "Point" and feat.block_name:
        entity_class = "block"
    elif feat.highway:
        entity_class = "street"
    else:
        entity_class = feat.feature_type.lower()
    xdata.append((XDATA_ELEVATION_KEY, f"sisrua:class={entity_class}"))
    if feat.highway:
        xdata.append((XDATA_ELEVATION_KEY, f"sisrua:highway={feat.highway}"))
    if feat.name:
        xdata.append((XDATA_ELEVATION_KEY, f"sisrua:name={feat.name}"))
    if feat.width_m is not None:
        xdata.append((XDATA_ELEVATION_KEY, f"sisrua:width_m={feat.width_m:.2f}"))
    if feat.elevation is not None:
        xdata.append((XDATA_ELEVATION_KEY, f"sisrua:elevation={feat.elevation:.4f}m"))
    if feat.slope is not None:
        xdata.append((XDATA_ELEVATION_KEY, f"sisrua:slope={feat.slope:.2f}pct"))
    if feat.layer:
        xdata.append((XDATA_ELEVATION_KEY, f"sisrua:layer={feat.layer}"))
    return xdata


def _add_polyline(msp, feat: CadFeature) -> None:
    """Adiciona uma polilinha 2D (Z=0) com XDATA BIM-LITE completo (2.5D)."""
    coords = feat.coords_xy
    if not coords or len(coords) < 2:
        return

    # 2.5D: coordenadas sempre 2D (X, Y). Z=0 por padrão.
    points_2d = [(float(x), float(y)) for x, y in coords]
    layer = feat.layer or "0"

    pline = msp.add_lwpolyline(points_2d, dxfattribs={"layer": layer})

    # BIM-LITE: XDATA completo ("uma rua sabe que é uma rua")
    xdata = _build_bim_xdata(feat)
    if xdata:
        pline.set_xdata(APPID_SISRUA, xdata)

    # Largura como propriedade constante da polilinha
    if feat.width_m is not None:
        pline.dxf.const_width = max(0.0, float(feat.width_m))


def _add_point(msp, feat: CadFeature) -> None:
    """Adiciona um ponto de inserção (INSERT ou POINT) com XDATA BIM-LITE completo."""
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
        xdata = _build_bim_xdata(feat)
        if xdata:
            insert.set_xdata(APPID_SISRUA, xdata)
    else:
        # POINT simples quando não há bloco definido
        pt = msp.add_point((x, y, 0.0), dxfattribs={"layer": layer})
        xdata = _build_bim_xdata(feat)
        if xdata:
            pt.set_xdata(APPID_SISRUA, xdata)


def add_contours_to_dxf(
    doc,
    contour_lines: list,
    interval: float = 10.0,
) -> int:
    """
    Adiciona curvas de nível SRTM ao documento DXF na layer SISRUA_TOPO.

    Cria (ou reutiliza) a layer ``SISRUA_TOPO`` com cor ciano (ACI 4) e
    desenha cada curva como uma LWPolyline 2D. A elevação de cada curva é
    armazenada em XDATA BIM-LITE (``sisrua:class=contour``,
    ``sisrua:elevation=<elev>m``).

    Args:
        doc:            Documento ezdxf já criado (R2010+).
        contour_lines:  Lista de dicts ``{"elevation": float,
                        "coords": [[x, y], ...]}``.
                        ``coords`` devem estar em metros (CRS projetado).
        interval:       Intervalo de curvas de nível em metros (apenas para
                        metadados; não altera a geometria).

    Returns:
        Número de curvas de nível adicionadas ao desenho.
    """
    if not contour_lines:
        return 0

    # Registra APPID se ainda não existir (idempotente)
    if APPID_SISRUA not in doc.appids:
        doc.appids.new(APPID_SISRUA)  # pragma: no cover

    # Cria layer SISRUA_TOPO com cor ciano (ACI 4) se ainda não existir
    if LAYER_SISRUA_TOPO not in doc.layers:
        doc.layers.new(LAYER_SISRUA_TOPO, dxfattribs={"color": 4})

    msp = doc.modelspace()
    count = 0
    for line in contour_lines:
        coords = line.get("coords") or []
        elev = line.get("elevation")
        if len(coords) < 2:
            continue
        points_2d = [(float(c[0]), float(c[1])) for c in coords]
        pline = msp.add_lwpolyline(
            points_2d, dxfattribs={"layer": LAYER_SISRUA_TOPO}
        )
        xdata = [(XDATA_ELEVATION_KEY, "sisrua:class=contour")]
        if elev is not None:
            xdata.append((XDATA_ELEVATION_KEY, f"sisrua:elevation={elev:.2f}m"))
            xdata.append(
                (XDATA_ELEVATION_KEY, f"sisrua:interval={interval:.1f}m")
            )
        pline.set_xdata(APPID_SISRUA, xdata)
        count += 1
    return count
