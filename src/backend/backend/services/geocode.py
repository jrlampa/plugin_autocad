import os
import re
import math
import requests
import logging
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException
from backend.gis_core.crs import sirgas2000_utm_epsg
from pyproj import Transformer

logger = logging.getLogger(__name__)

def parse_utm(query: str) -> Optional[Tuple[float, float, str]]:
    """
    Tries to parse UTM coordinates from string.
    Supported formats: 
    - "K 216330 7528658" (Zone Letter E N)
    - "23K 216330 7528658" (Zone Letter E N)
    - "216330, 7528658" (E, N) - Assumes defaults for Brazil if zone missing
    """
    # Pattern for "ZoneLetter Easting Northing" or just "Easting Northing"
    # Example: K 216330 7528658
    utm_match = re.search(r'(?:([0-9]{1,2})?\s*([C-X]))?\s*([0-9]{6}(?:\.[0-9]+)?)\s*[,/|\s]\s*([0-9]{7}(?:\.[0-9]+)?)', query, re.IGNORECASE)
    
    if not utm_match:
        return None

    zone_num_str, zone_letter, easting_str, northing_str = utm_match.groups()
    easting = float(easting_str)
    northing = float(northing_str)
    
    # Defaults for Brazil if not specified
    # K is roughly latitude -24 to -16 (Rio/SP/Espírito Santo area)
    default_zone = os.environ.get("DEFAULT_UTM_ZONE", "23")
    zone_num = int(zone_num_str) if zone_num_str else int(default_zone)
    
    is_northern = False
    if zone_letter:
        # N and above are northern hemisphere
        # C-M are southern, N-X are northern
        if zone_letter.upper() >= 'N':
            is_northern = True
            
    # EPSG for SIRGAS 2000 UTM
    # South: 31960 + zone
    # North: 31960 (actually SIRGAS 2000 / UTM zone N is different, usually 31900 range)
    # But for Brazil (mostly South), we use 31960 + zone.
    if not is_northern:
        epsg = 31960 + zone_num
    else:
        # Placeholder for North zones if needed, for now stick to South
        epsg = 31960 + zone_num 

    try:
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(easting, northing)
        
        if math.isfinite(lat) and math.isfinite(lon):
            return lat, lon, f"UTM {zone_num}{zone_letter or ''} {easting:.0f}E {northing:.0f}N"
    except Exception as e:
        logger.error(f"utm_transform_failed: {str(e)} for query: {query}")
        
    return None

def parse_lat_lon(query: str) -> Optional[Tuple[float, float, str]]:
    """Tries to parse DD coordinates (e.g. -21.123, -41.456)"""
    ll_match = re.search(r'(-?[0-9]{1,2}\.[0-9]+)\s*[,/|\s]\s*(-?[0-9]{1,3}\.[0-9]+)', query)
    if ll_match:
        lat = float(ll_match.group(1))
        lon = float(ll_match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon, f"{lat:.6f}, {lon:.6f}"
    return None

def smart_geocode(query: str) -> Dict[str, Any]:
    """
    Orchestrates coordinate parsing and Nominatim lookup.
    """
    # 1. Try Lat/Lon
    res = parse_lat_lon(query)
    if res:
        return {"latitude": res[0], "longitude": res[1], "display_name": res[2]}
        
    # 2. Try UTM
    res = parse_utm(query)
    if res:
        return {"latitude": res[0], "longitude": res[1], "display_name": res[2]}
        
    # 3. Fallback to Nominatim
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        user_agent = os.environ.get("NOMINATIM_USER_AGENT", "sisRUA-AutoCAD-Plugin/1.1 (enterprise-support@sisrua.com)")
        headers = {
            "User-Agent": user_agent
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data:
            item = data[0]
            return {
                "latitude": float(item["lat"]),
                "longitude": float(item["lon"]),
                "display_name": item["display_name"]
            }
    except Exception as e:
        logger.error(f"nominatim_failed: {str(e)} for query: {query}")
        
    raise HTTPException(status_code=404, detail=f"Localização não encontrada para: {query}")
