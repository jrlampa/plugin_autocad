"""
backend/gis_core/crs.py
Utilitários de Sistema de Referência de Coordenadas (CRS).

Responsabilidade única: EPSG detection + transformação de coordenadas
entre EPSG:4326 (WGS84 lat/lon) e SIRGAS 2000 / UTM (projeção métrica).

Princípio: CRS tratado no início do fluxo.
  Frontend → EPSG:4326 (Leaflet)
  Backend/CAD → SIRGAS 2000 UTM (pyproj, zona detectada automaticamente)
"""
from __future__ import annotations

from typing import List, Tuple


def utm_zone(longitude: float) -> int:
    """
    Calculates the UTM zone for a given longitude.
    Zone = int((lon + 180) / 6) + 1, clamped between 1 and 60.
    """
    zone = int((longitude + 180) // 6) + 1
    return max(1, min(60, zone))


def sirgas2000_utm_epsg(latitude: float, longitude: float) -> int:
    """
    Determines the EPSG code for SIRGAS 2000 / UTM zone based on lat/lon.
    For Brazil (Southern Hemisphere), the family is EPSG:31960 + zone.
    Example: Zone 23S -> 31983 | Zone 24S -> 31984.
    """
    zone = utm_zone(longitude)
    return 31960 + zone


def latlon_to_utm(
    latitude: float,
    longitude: float,
    epsg_out: int | None = None,
) -> Tuple[float, float, int]:
    """
    Converts a WGS84 point (lat/lon) to SIRGAS 2000 UTM.

    Args:
        latitude:  Latitude in decimal degrees (EPSG:4326).
        longitude: Longitude in decimal degrees (EPSG:4326).
        epsg_out:  Target EPSG; auto-detected from coordinates if None.

    Returns:
        Tuple (easting_m, northing_m, epsg_out).
    """
    from pyproj import Transformer  # type: ignore

    if epsg_out is None:
        epsg_out = sirgas2000_utm_epsg(latitude, longitude)

    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_out}", always_xy=True)
    easting, northing = transformer.transform(longitude, latitude)
    return easting, northing, epsg_out


def utm_to_latlon(
    easting: float,
    northing: float,
    epsg_in: int,
) -> Tuple[float, float]:
    """
    Converts a SIRGAS 2000 UTM point to WGS84 (lat/lon).

    Args:
        easting:  Easting coordinate in meters.
        northing: Northing coordinate in meters.
        epsg_in:  EPSG of the UTM projection (e.g., 31983).

    Returns:
        Tuple (latitude, longitude) in decimal degrees.
    """
    from pyproj import Transformer  # type: ignore

    transformer = Transformer.from_crs(f"EPSG:{epsg_in}", "EPSG:4326", always_xy=True)
    longitude, latitude = transformer.transform(easting, northing)
    return latitude, longitude


def transform_coords(
    coords: List[Tuple[float, float]],
    epsg_in: int,
    epsg_out: int,
) -> List[Tuple[float, float]]:
    """
    Transforms a list of coordinates between two coordinate reference systems.

    Args:
        coords:   List of (x, y) pairs in the source CRS.
        epsg_in:  EPSG of the source CRS.
        epsg_out: EPSG of the target CRS.

    Returns:
        List of (x, y) pairs in the target CRS.
    """
    from pyproj import Transformer  # type: ignore

    transformer = Transformer.from_crs(f"EPSG:{epsg_in}", f"EPSG:{epsg_out}", always_xy=True)
    return [transformer.transform(x, y) for x, y in coords]
