"""
backend/gis_core/inea.py
Integração com serviços WFS/WMS do INEA (Instituto Estadual do Ambiente — RJ).

Serviços utilizados:
  - GeoServer WFS público do INEA:
    https://geoservicos.inea.rj.gov.br/geoserver/wfs
  - Parâmetros padrão: versão WFS 1.1.0, formato GeoJSON

Responsabilidade única: busca e projeção de feições ambientais do INEA
(corpos d'água, unidades de conservação, bacias hidrográficas) para
CadFeature, pronto para desenho em AutoCAD via pipeline sisRUA.
"""
from __future__ import annotations

import math
from typing import List, Optional, Callable, Any

import requests
from fastapi import HTTPException

from backend.shared.logger import get_logger
from backend.shared.utils import cache_key, sanitize_jsonable
from backend.domain.crs import sirgas2000_utm_epsg
from backend.models import CadFeature

logger = get_logger(__name__)

# Endpoint WFS público do INEA-RJ
_INEA_WFS_URL = "https://geoservicos.inea.rj.gov.br/geoserver/wfs"

# Mapeamento de tipos de feição INEA → camada CAD sisRUA
_LAYER_MAP: dict[str, str] = {
    "apa": "SISRUA_INEA_APA",
    "uc": "SISRUA_INEA_UC",
    "conserv": "SISRUA_INEA_UC",       # UnidadesConservacao
    "bacia": "SISRUA_INEA_BACIA",
    "rio": "SISRUA_INEA_HIDRO",
    "lago": "SISRUA_INEA_HIDRO",
    "hidro": "SISRUA_INEA_HIDRO",
    "default": "SISRUA_INEA_FEICOES",
}

# Tipos de feição WFS suportados (typename no GeoServer INEA)
INEA_TYPENAMES: dict[str, str] = {
    "hidrografia": "inea:RJ_Hidrografia_250000",
    "bacias": "inea:RJ_BaciasHidrograficas",
    "unidades_conservacao": "inea:RJ_UnidadesConservacao",
    "manguezais": "inea:RJ_Manguezais",
}


def _wfs_to_features(
    geojson: dict,
    typename: str,
    epsg_out: int,
) -> List[CadFeature]:
    """
    Converte GeoJSON WFS do INEA em lista de CadFeature.

    Suporta LineString, MultiLineString, Polygon e MultiPolygon.
    Polígonos são representados pelos seus anéis exteriores (polylines).

    Args:
        geojson:   GeoJSON retornado pelo WFS.
        typename:  Nome do tipo de feição WFS (para categorização).
        epsg_out:  Código EPSG da projeção UTM SIRGAS 2000.

    Returns:
        Lista de CadFeature prontas para desenho CAD.
    """
    from pyproj import Transformer  # type: ignore
    from shapely.geometry import shape, MultiPolygon, Polygon  # type: ignore
    from shapely.geometry import MultiLineString, LineString  # type: ignore

    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_out}", always_xy=True)
    features: List[CadFeature] = []

    # Determina o nome da camada CAD a partir do typename
    layer = _LAYER_MAP["default"]
    for key, val in _LAYER_MAP.items():
        if key in typename.lower():
            layer = val
            break

    for feat in (geojson.get("features") or []):
        geom_dict = feat.get("geometry")
        if not geom_dict:
            continue
        props = sanitize_jsonable(feat.get("properties") or {})
        name = props.get("nome") or props.get("name") or typename

        try:
            geom = shape(geom_dict)
        except Exception as exc:
            logger.warning("inea_geom_parse_error", error=str(exc))
            continue

        # Extrai anéis/linhas para desenho como polylines
        lines: list[list[tuple]] = []

        if isinstance(geom, (LineString, MultiLineString)):
            if isinstance(geom, LineString):
                lines = [list(geom.coords)]
            else:
                lines = [list(g.coords) for g in geom.geoms]
        elif isinstance(geom, Polygon):
            lines = [list(geom.exterior.coords)]
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                lines.append(list(poly.exterior.coords))

        for ring in lines:
            projected = [transformer.transform(lon, lat) for lon, lat in ring]
            coords_xy = [
                [float(x), float(y)]
                for x, y in projected
                if math.isfinite(x) and math.isfinite(y)
            ]
            if len(coords_xy) >= 2:
                cad_props = {**props, "inea:typename": typename}
                features.append(
                    CadFeature(
                        feature_type="Polyline",
                        layer=layer,
                        name=str(name)[:64],
                        coords_xy=coords_xy,
                        original_geojson_properties=cad_props,
                    )
                )

    return features


def prepare_inea_compute(
    typename: str,
    bbox: Optional[tuple[float, float, float, float]],
    cache_service: Any,
    check_cancel: Callable[[], None] = None,
    wfs_url: str = _INEA_WFS_URL,
) -> dict:
    """
    Pipeline principal de integração INEA:
      1. Monta a requisição WFS GetFeature
      2. Baixa as feições em formato GeoJSON
      3. Projeta para SIRGAS 2000 UTM
      4. Retorna PrepareResponse serializável

    Args:
        typename:       Nome do tipo de feição (ex.: 'hidrografia', 'bacias').
                        Deve ser uma chave de ``INEA_TYPENAMES`` ou o typename WFS direto.
        bbox:           Bounding box (min_lon, min_lat, max_lon, max_lat) em EPSG:4326.
                        Se None, recupera todas as feições (pode ser lento).
        cache_service:  Serviço de cache (ICache).
        check_cancel:   Callback de cancelamento opcional.
        wfs_url:        URL base do GeoServer WFS (sobrescrevível para testes).

    Returns:
        dict compatível com PrepareResponse (features + crs_out).

    Raises:
        HTTPException 400: typename desconhecido.
        HTTPException 503: falha na comunicação com o WFS do INEA.
    """
    from backend.models import PrepareResponse

    if check_cancel:
        check_cancel()

    # Resolve typename
    wfs_typename = INEA_TYPENAMES.get(typename, typename)

    bbox_str = ",".join(str(v) for v in bbox) + ",EPSG:4326" if bbox else None
    cache_parts = ["prepare_inea", wfs_typename, bbox_str or "all"]
    cache_k = cache_key(cache_parts)

    cached = cache_service.get(cache_k)
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    params: dict[str, str] = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": wfs_typename,
        "outputFormat": "application/json",
        "maxFeatures": "500",
    }
    if bbox_str:
        params["bbox"] = bbox_str

    try:
        if check_cancel:
            check_cancel()
        resp = requests.get(wfs_url, params=params, timeout=30)
        resp.raise_for_status()
        geojson = resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        cached = cache_service.get(cache_k)
        if cached is not None:
            cached["cache_hit"] = True
            cached["cache_fallback_reason"] = str(exc)
            return cached
        raise HTTPException(
            status_code=503,
            detail=f"Falha ao obter dados do INEA ({wfs_typename}): {exc}",
        )

    if check_cancel:
        check_cancel()

    # Determina EPSG pelo bbox ou pelo centroide das feições
    epsg_out = 31983  # default: Zona 23S (Rio de Janeiro)
    if bbox:
        lat_avg = (bbox[1] + bbox[3]) / 2
        lon_avg = (bbox[0] + bbox[2]) / 2
        epsg_out = sirgas2000_utm_epsg(lat_avg, lon_avg)

    features = _wfs_to_features(geojson, wfs_typename, epsg_out)

    payload = PrepareResponse(crs_out=f"EPSG:{epsg_out}", features=features)
    try:
        cache_service.set(cache_k, payload.model_dump())
        payload.cache_hit = False
    except Exception:
        pass

    return payload.model_dump()
