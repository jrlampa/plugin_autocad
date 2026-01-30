import pytest
from backend.services.crs import utm_zone, sirgas2000_utm_epsg

def test_utm_zone_calculation():
    # Test cases for UTM zones
    # Brazil examples
    assert utm_zone(-43.0) == 23  # Rio de Janeiro
    assert utm_zone(-46.6) == 23  # São Paulo
    assert utm_zone(-41.3) == 24  # Campos dos Goytacazes (approx)
    
    # Edge cases
    assert utm_zone(-180.0) == 1
    assert utm_zone(179.9) == 60
    assert utm_zone(0.0) == 31

def test_sirgas2000_utm_epsg():
    # Campos dos Goytacazes, RJ (-21.76, -41.32) -> Zone 24S -> 31984
    epsg = sirgas2000_utm_epsg(-21.7634, -41.3235)
    assert epsg == 31984

    # São Paulo, SP (-23.55, -46.63) -> Zone 23S -> 31983
    epsg_sp = sirgas2000_utm_epsg(-23.55, -46.63)
    assert epsg_sp == 31983
    
    # Western limit of Brazil (Acre) - approx -73 lon -> Zone 18 or 19
    # -73 + 180 = 107 / 6 = 17.8 -> Zone 18 -> 31978
    assert sirgas2000_utm_epsg(-10.0, -73.0) == 31978
