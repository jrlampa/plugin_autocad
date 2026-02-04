def utm_zone(longitude: float) -> int:
    """
    Calculates the UTM zone for a given longitude.
    Zone = int((lon + 180) / 6) + 1
    Clamped between 1 and 60.
    """
    zone = int((longitude + 180) // 6) + 1
    return max(1, min(60, zone))


def sirgas2000_utm_epsg(latitude: float, longitude: float) -> int:
    """
    Determines the EPSG code for SIRGAS 2000 / UTM zone based on lat/lon.
    For Brazil (Southern Hemisphere), the family is EPSG:31960 + zone.
    Example: Zone 24S -> 31984.
    """
    zone = utm_zone(longitude)
    # Roadmap assumes SIRGAS 2000 / UTM.
    # Formula for South zones: 31960 + zone.
    return 31960 + zone
