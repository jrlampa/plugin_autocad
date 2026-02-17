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
    Brazil spans both Southern (most) and Northern hemispheres.
    - South (S): EPSG:31960 + zone
    - North (N): EPSG:31954 + zone
    """
    zone = utm_zone(longitude)
    if latitude >= 0:
        # SIRGAS 2000 / UTM zone 18N (31972) to 22N (31976)
        # Formula: 31954 + zone. Zone 20N -> 31954 + 20 = 31974.
        return 31954 + zone
    else:
        # SIRGAS 2000 / UTM zone 18S (31978) to 25S (31985)
        # Formula: 31960 + zone. Zone 23S -> 31960 + 23 = 31983.
        return 31960 + zone
