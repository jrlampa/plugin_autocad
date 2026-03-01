"""
backend.application/geocode.py
Serviço de geocodificação inteligente — custo zero.

Estratégia (em ordem de prioridade):
  1. Coordenadas decimais diretas  (ex.: -22.15018, -42.92185)
  2. Coordenadas UTM SIRGAS 2000   (ex.: 23K 788547 7634925)
  3. Geocodificação por endereço    (Nominatim / OSM — gratuito)

Responsabilidade única: parseamento e geocodificação de queries de texto.
Segurança: query sanitizada antes do envio à API externa (max 200 chars).
"""
from __future__ import annotations

import re
from typing import Optional

from backend.shared.logger import get_logger

logger = get_logger(__name__)

# Limites de sanitização
_MAX_QUERY_LEN = 200

# Regex: lat/lon decimal  (ex.: "-22.15018, -42.92185" | "-22.15018 -42.92185")
_RE_LATLON = re.compile(
    r"^\s*(?P<lat>-?\d{1,3}(?:\.\d+)?)\s*[,;\s]\s*(?P<lon>-?\d{1,3}(?:\.\d+)?)\s*$"
)

# Regex: UTM compacto  (ex.: "23K 788547 7634925" | "788547, 7634925")
# Aceita zona opcional (ex.: "23K") + Easting + Northing
_RE_UTM = re.compile(
    r"^\s*(?:(?P<zone>\d{1,2}[A-Za-z])\s+)?"
    r"(?P<easting>\d{5,7}(?:\.\d+)?)\s*[,\s]\s*"
    r"(?P<northing>\d{6,7}(?:\.\d+)?)\s*$"
)

# Nominatim endpoint público (OSM) — gratuito, sem chave de API
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def _sanitize_query(text: str) -> str:
    """Remove caracteres perigosos e trunca o query para segurança."""
    # Remove tags HTML/script, caracteres de controle e injeção CRLF
    clean = re.sub(r"[<>\"'`;\\\r\n\x00]", "", text)
    return clean.strip()[:_MAX_QUERY_LEN]


def _try_parse_latlon(text: str) -> Optional[dict]:
    """Tenta interpretar o texto como lat/lon decimal."""
    m = _RE_LATLON.match(text)
    if not m:
        return None
    lat = float(m.group("lat"))
    lon = float(m.group("lon"))
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    logger.debug("geocode_latlon_parsed", lat=lat, lon=lon)
    return {"latitude": lat, "longitude": lon, "source": "latlon_direct"}


def _try_parse_utm(text: str) -> Optional[dict]:
    """
    Tenta interpretar o texto como coordenadas UTM SIRGAS 2000.
    Aceita opcionalmente a designação de zona (ex.: "23K").
    Valida que o northing parece Sul (> 6_000_000 m, representativo do Brasil).
    """
    m = _RE_UTM.match(text)
    if not m:
        return None

    easting = float(m.group("easting"))
    northing = float(m.group("northing"))

    # Heurística: easting válido para UTM (100_000 – 999_000 m)
    if not (100_000 <= easting <= 999_000):
        return None
    # Heurística: northing para Brasil Sul (6_500_000 – 9_999_999 m)
    if not (6_000_000 <= northing <= 10_000_000):
        return None

    zone_str = m.group("zone")
    # Detecta zona automaticamente ou usa a informada
    if zone_str:
        zone_num = int(re.match(r"\d+", zone_str).group())
    else:
        # Fallback: zona 23 (mais comum no Brasil)
        zone_num = 23

    epsg = 31960 + zone_num  # SIRGAS 2000 / UTM zone

    try:
        from backend.gis_core.crs import utm_to_latlon

        lat, lon = utm_to_latlon(easting, northing, epsg)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return None
        logger.debug("geocode_utm_parsed", easting=easting, northing=northing, epsg=epsg)
        return {"latitude": lat, "longitude": lon, "source": "utm_direct", "epsg": epsg}
    except Exception as exc:
        logger.warning("geocode_utm_parse_failed", error=str(exc))
        return None


def _nominatim_geocode(query: str) -> Optional[dict]:
    """
    Geocodifica um endereço usando Nominatim (OSM) — gratuito, sem chave de API.
    Prioriza resultados no Brasil (countrycodes=br).

    Conformidade com Nominatim Usage Policy:
    - User-Agent identificado (obrigatório pela política OSM)
    - Uso moderado: esta função é protegida pelo rate limiter da API
      (/api/v1/tools/geocode requer autenticação, limitado a 5 req/min/IP)
    - Não executa crawling em massa; respostas são cacheadas via frontend
    """
    import requests

    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "br",
        "accept-language": "pt-BR",
    }
    # User-Agent obrigatório conforme Nominatim Usage Policy
    # Versão derivada do pacote para evitar string hardcoded
    try:
        from importlib.metadata import version as _pkg_version
        _ver = _pkg_version("sisrua-backend")
    except Exception:
        _ver = "0.1.0"
    headers = {
        "User-Agent": f"sisRUA-GIS/{_ver} (https://github.com/jrlampa/plugin_autocad)"
    }

    try:
        resp = requests.get(_NOMINATIM_URL, params=params, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            # Segunda tentativa sem filtro de país
            params.pop("countrycodes", None)
            resp = requests.get(_NOMINATIM_URL, params=params, headers=headers, timeout=8)
            resp.raise_for_status()
            data = resp.json()
        if data:
            item = data[0]
            lat = float(item["lat"])
            lon = float(item["lon"])
            display_name = item.get("display_name", "")
            logger.info("geocode_nominatim_hit", query=query, display_name=display_name)
            return {
                "latitude": lat,
                "longitude": lon,
                "display_name": display_name,
                "source": "nominatim",
            }
    except Exception as exc:
        logger.warning("geocode_nominatim_failed", query=query, error=str(exc))
    return None


def geocode(query: str) -> Optional[dict]:
    """
    Geocodifica um texto de entrada (endereço, lat/lon ou UTM).

    Prioridade:
      1. lat/lon decimal    — sem rede externa
      2. UTM SIRGAS 2000    — sem rede externa
      3. Nominatim/OSM      — requer rede (gratuito)

    Args:
        query: Texto de entrada (max 200 chars após sanitização).

    Returns:
        Dict com ``latitude``, ``longitude`` e ``source``, ou None se não encontrado.
    """
    if not query or not query.strip():
        return None

    clean = _sanitize_query(query)
    if not clean:
        return None

    # 1. lat/lon
    result = _try_parse_latlon(clean)
    if result:
        return result

    # 2. UTM
    result = _try_parse_utm(clean)
    if result:
        return result

    # 3. Nominatim
    from backend.services import geocode as _geocode_compat

    result = _geocode_compat._nominatim_geocode(clean)
    return result
