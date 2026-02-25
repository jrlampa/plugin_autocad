"""
backend/gis_core/ibge.py
Integração com a API gratuita do IBGE (Instituto Brasileiro de Geografia e Estatística).

APIs utilizadas:
  - Malhas Geográficas v3: https://servicodados.ibge.gov.br/api/v3/malhas
    → Limites municipais em GeoJSON (subdivisão: municipio)
  - Localidades v1: https://servicodados.ibge.gov.br/api/v3/localidades/municipios
    → Lista de municípios com código IBGE

Responsabilidade única: busca e projeção de feições IBGE para CadFeature,
pronto para desenho em AutoCAD via pipeline sisRUA.
"""
from __future__ import annotations

import math
from typing import List, Optional, Callable, Any

import requests
from fastapi import HTTPException

from backend.core.logger import get_logger
from backend.core.utils import cache_key, sanitize_jsonable, get_layer_name
from backend.gis_core.crs import sirgas2000_utm_epsg
from backend.models import CadFeature

logger = get_logger(__name__)

# Endpoints da API pública do IBGE (sem autenticação)
_IBGE_MALHAS_URL = "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{cod}"
_IBGE_LOCALIDADES_URL = "https://servicodados.ibge.gov.br/api/v3/localidades/municipios"

# Camada CAD para feições IBGE
_LAYER_MUNICIPIO = "SISRUA_IBGE_MUNICIPIO"
_LAYER_LIMITE = "SISRUA_IBGE_LIMITE"


def _buscar_codigo_municipio(nome_municipio: str, uf: Optional[str] = None) -> Optional[int]:
    """
    Busca o código IBGE de um município pelo nome (e opcionalmente UF).

    Args:
        nome_municipio: Nome do município (case-insensitive, ignora acentos simples).
        uf:             Sigla da UF (ex.: 'RJ', 'SP'). Opcional.

    Returns:
        Código IBGE do município ou None se não encontrado.
    """
    resp = requests.get(_IBGE_LOCALIDADES_URL, timeout=15)
    resp.raise_for_status()
    municipios = resp.json()

    nome_lower = nome_municipio.strip().lower()

    for m in municipios:
        mname = (m.get("nome") or "").strip().lower()
        if mname == nome_lower:
            if uf:
                m_uf = (m.get("microrregiao", {}).get("mesorregiao", {})
                         .get("UF", {}).get("sigla") or "").upper()
                if m_uf != uf.strip().upper():
                    continue
            return m.get("id")

    return None


def _malha_municipio_to_features(
    geojson: dict,
    nome_municipio: str,
    epsg_out: int,
) -> List[CadFeature]:
    """
    Converte o GeoJSON de malha municipal do IBGE em lista de CadFeature.

    Args:
        geojson:         GeoJSON retornado pela API de malhas.
        nome_municipio:  Nome do município (para metadados).
        epsg_out:        Código EPSG da projeção UTM SIRGAS 2000.

    Returns:
        Lista de CadFeature (Polyline) representando o limite municipal.
    """
    from pyproj import Transformer  # type: ignore
    from shapely.geometry import shape, MultiPolygon, Polygon, LineString  # type: ignore

    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_out}", always_xy=True)
    features: List[CadFeature] = []

    geojson_features = geojson.get("features") or []
    if not geojson_features and geojson.get("type") in ("Polygon", "MultiPolygon"):
        geojson_features = [{"type": "Feature", "geometry": geojson, "properties": {}}]

    for feat in geojson_features:
        geom_dict = feat.get("geometry") or feat
        props = feat.get("properties") or {}
        try:
            geom = shape(geom_dict)
        except Exception as exc:
            logger.warning("ibge_geom_parse_error", error=str(exc))
            continue

        polygons: List[Any] = []
        if isinstance(geom, Polygon):
            polygons = [geom]
        elif isinstance(geom, MultiPolygon):
            polygons = list(geom.geoms)

        for poly in polygons:
            # Exterior ring → polyline
            ext_coords = list(poly.exterior.coords)
            projected = [transformer.transform(lon, lat) for lon, lat in ext_coords]
            coords_xy = [[float(x), float(y)] for x, y in projected
                         if math.isfinite(x) and math.isfinite(y)]

            if len(coords_xy) >= 2:
                cad_props = sanitize_jsonable({
                    **props,
                    "ibge:municipio": nome_municipio,
                    "ibge:tipo": "limite_municipal",
                })
                features.append(
                    CadFeature(
                        feature_type="Polyline",
                        layer=_LAYER_LIMITE,
                        name=f"Limite — {nome_municipio}",
                        coords_xy=coords_xy,
                        original_geojson_properties=cad_props,
                    )
                )

    return features


def prepare_ibge_compute(
    nome_municipio: str,
    uf: Optional[str],
    cache_service: Any,
    check_cancel: Callable[[], None] = None,
) -> dict:
    """
    Pipeline principal de integração IBGE:
      1. Resolve o código IBGE do município
      2. Baixa a malha geográfica (GeoJSON)
      3. Projeta para SIRGAS 2000 UTM
      4. Retorna PrepareResponse serializável

    Args:
        nome_municipio: Nome do município (ex.: 'Nova Friburgo').
        uf:             UF do município (ex.: 'RJ'). Recomendado para desambiguação.
        cache_service:  Serviço de cache (ICache).
        check_cancel:   Callback de cancelamento opcional.

    Returns:
        dict compatível com PrepareResponse (features + crs_out).

    Raises:
        HTTPException 404: município não encontrado.
        HTTPException 503: falha na comunicação com a API IBGE.
    """
    from backend.models import PrepareResponse

    if check_cancel:
        check_cancel()

    cache_k = cache_key(
        ["prepare_ibge", nome_municipio.lower().strip(), (uf or "").upper()]
    )
    cached = cache_service.get(cache_k)
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    try:
        cod = _buscar_codigo_municipio(nome_municipio, uf)
        if cod is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Município '{nome_municipio}'"
                    + (f" / {uf}" if uf else "")
                    + " não encontrado na base IBGE."
                ),
            )

        if check_cancel:
            check_cancel()

        url = _IBGE_MALHAS_URL.format(cod=cod)
        params = {"formato": "application/vnd.geo+json", "intrarregiao": "municipio"}
        resp = requests.get(url, params=params, timeout=20)
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
            detail=f"Falha ao obter dados do IBGE: {exc}",
        )

    if check_cancel:
        check_cancel()

    # Determina EPSG pelo centroide aproximado do GeoJSON
    epsg_out = 31983  # default: Zona 23S (cobre a maior parte do Brasil)
    try:
        all_coords = []
        for feat in (geojson.get("features") or []):
            geom = feat.get("geometry") or {}
            _collect_coords(geom, all_coords)
        if all_coords:
            lat_avg = sum(c[1] for c in all_coords) / len(all_coords)
            lon_avg = sum(c[0] for c in all_coords) / len(all_coords)
            epsg_out = sirgas2000_utm_epsg(lat_avg, lon_avg)
    except Exception:  # pragma: no cover — only for degenerate coordinate data
        pass

    features = _malha_municipio_to_features(geojson, nome_municipio, epsg_out)

    payload = PrepareResponse(crs_out=f"EPSG:{epsg_out}", features=features)
    try:
        cache_service.set(cache_k, payload.model_dump())
        payload.cache_hit = False
    except Exception:
        pass

    return payload.model_dump()


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _collect_coords(geom: dict, out: list) -> None:
    """Coleta todos os pares [lon, lat] de qualquer geometria GeoJSON."""
    gtype = geom.get("type", "")
    coords = geom.get("coordinates")
    if not coords:
        return

    if gtype == "Point":
        out.append(coords[:2])
    elif gtype in ("LineString", "MultiPoint"):
        out.extend(c[:2] for c in coords)
    elif gtype in ("Polygon", "MultiLineString"):
        for ring in coords:
            out.extend(c[:2] for c in ring)
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                out.extend(c[:2] for c in ring)
