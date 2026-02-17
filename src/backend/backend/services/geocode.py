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
    # Pattern for "Zone Num Letter Easting Northing"
    # Easting: 6 or 7 digits (to allow leading zero like 0803412)
    # Northing: 7 digits
    utm_match = re.search(
        r'(?:([0-9]{1,2})?\s*([C-X]))?\s*([0-9]{6,7}(?:\.[0-9]+)?)\s*[,/|\s]\s*([0-9]{7,8}(?:\.[0-9]+)?)', 
        query, re.IGNORECASE
    )
    
    if not utm_match:
        return None

    zone_num_str, zone_letter, easting_str, northing_str = utm_match.groups()
    easting = float(easting_str)
    northing = float(northing_str)
    
    # Defaults for Brazil if not specified
    default_zone = os.environ.get("DEFAULT_UTM_ZONE", "23")
    zone_num = int(zone_num_str) if zone_num_str else int(default_zone)
    
    # UTM Latitude Bands: C-M are South, N-X are North.
    is_northern = False
    if zone_letter:
        if zone_letter.upper() >= 'N':
            is_northern = True
            
    # SIRGAS 2000 UTM EPSG mapping
    # South: 31960 + zone (e.g. 31983 for 23S)
    # North: 31954 + zone (e.g. 31974 for 20N)
    if not is_northern:
        epsg = 31960 + zone_num
    else:
        epsg = 31954 + zone_num 

    try:
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(easting, northing)
        
        if math.isfinite(lat) and math.isfinite(lon):
            # Format back to canonical UTM display
            display_name = f"UTM {zone_num}{zone_letter.upper() if zone_letter else '?' } {easting:.0f}E {northing:.0f}N"
            return lat, lon, display_name
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
