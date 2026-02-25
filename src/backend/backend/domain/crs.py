"""
backend/domain/crs.py
Re-exporta funções de CRS de `backend.gis_core.crs`.
"""
from backend.gis_core.crs import (
    utm_zone,
    sirgas2000_utm_epsg,
    latlon_to_utm,
    utm_to_latlon,
    transform_coords,
)

__all__ = [
    "utm_zone",
    "sirgas2000_utm_epsg",
    "latlon_to_utm",
    "utm_to_latlon",
    "transform_coords",
]
