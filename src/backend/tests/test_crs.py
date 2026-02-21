"""
tests/test_crs.py
Testes do módulo gis_core/crs.py.

Coordenadas de referência padrão (conforme MEMORY.MD):
  REF_1 — Campo:   UTM 23K  E=788547,  N=7634925  (lat≈-21.365°, lon≈-42.218°)
  REF_2 — Projeto: Lat/Lon -22.15018°, -42.92185° → UTM E≈714316, N≈7549084
"""
import math
import pytest
from backend.gis_core.crs import (
    utm_zone,
    sirgas2000_utm_epsg,
    latlon_to_utm,
    utm_to_latlon,
    transform_coords,
)

# ---------------------------------------------------------------------------
# Coordenadas de referência
# ---------------------------------------------------------------------------
# REF_1: coordenada de campo (UTM puro)
REF1_E = 788547.0
REF1_N = 7634925.0
REF1_EPSG = 31983  # Zona 23S

# REF_2: coordenada de projeto (lat/lon convertida para UTM)
REF2_LAT = -22.15018
REF2_LON = -42.92185
REF2_E = 714316.0  # ±1 m
REF2_N = 7549084.0  # ±1 m
REF2_EPSG = 31983   # Zona 23S


# ---------------------------------------------------------------------------
# Testes de zona UTM
# ---------------------------------------------------------------------------
def test_utm_zone_calculation():
    assert utm_zone(-43.0) == 23   # Rio de Janeiro
    assert utm_zone(-46.6) == 23   # São Paulo
    assert utm_zone(-41.3) == 24   # Campos dos Goytacazes (aprox.)
    assert utm_zone(-180.0) == 1
    assert utm_zone(179.9) == 60
    assert utm_zone(0.0) == 31


# ---------------------------------------------------------------------------
# Testes de EPSG SIRGAS 2000
# ---------------------------------------------------------------------------
def test_sirgas2000_utm_epsg():
    # Campos dos Goytacazes, RJ → Zona 24S → 31984
    assert sirgas2000_utm_epsg(-21.7634, -41.3235) == 31984
    # São Paulo, SP → Zona 23S → 31983
    assert sirgas2000_utm_epsg(-23.55, -46.63) == 31983
    # Acre → Zona 18 → 31978
    assert sirgas2000_utm_epsg(-10.0, -73.0) == 31978

def test_sirgas2000_utm_epsg_ref1():
    """REF_1 (lon≈-42.218) deve mapear para Zona 23S → EPSG:31983."""
    lat_ref1, lon_ref1 = utm_to_latlon(REF1_E, REF1_N, REF1_EPSG)
    epsg = sirgas2000_utm_epsg(lat_ref1, lon_ref1)
    assert epsg == REF1_EPSG

def test_sirgas2000_utm_epsg_ref2():
    """REF_2 (-22.15018°, -42.92185°) deve mapear para Zona 23S → EPSG:31983."""
    epsg = sirgas2000_utm_epsg(REF2_LAT, REF2_LON)
    assert epsg == REF2_EPSG


# ---------------------------------------------------------------------------
# Testes de transformação latlon_to_utm
# ---------------------------------------------------------------------------
def test_latlon_to_utm_ref2_easting(tolerance_m=1.0):
    """Easting de REF_2 deve estar a ≤1 m do valor esperado."""
    e, n, epsg = latlon_to_utm(REF2_LAT, REF2_LON)
    assert epsg == REF2_EPSG
    assert abs(e - REF2_E) < tolerance_m, f"Easting esperado ≈{REF2_E} m, obteve {e:.1f} m"

def test_latlon_to_utm_ref2_northing(tolerance_m=1.0):
    """Northing de REF_2 deve estar a ≤1 m do valor esperado."""
    e, n, epsg = latlon_to_utm(REF2_LAT, REF2_LON)
    assert abs(n - REF2_N) < tolerance_m, f"Northing esperado ≈{REF2_N} m, obteve {n:.1f} m"

def test_latlon_to_utm_explicit_epsg():
    """Passando EPSG explícito deve retornar o mesmo EPSG."""
    e, n, epsg = latlon_to_utm(REF2_LAT, REF2_LON, epsg_out=REF2_EPSG)
    assert epsg == REF2_EPSG

def test_latlon_to_utm_finite_coords():
    """Coordenadas convertidas devem ser finitas."""
    e, n, _ = latlon_to_utm(REF2_LAT, REF2_LON)
    assert math.isfinite(e)
    assert math.isfinite(n)


# ---------------------------------------------------------------------------
# Testes de transformação utm_to_latlon
# ---------------------------------------------------------------------------
def test_utm_to_latlon_ref1(tolerance_deg=0.001):
    """Reversão de REF_1 (UTM) deve retornar lat/lon próximos."""
    lat, lon = utm_to_latlon(REF1_E, REF1_N, REF1_EPSG)
    # REF_1: aprox. -21.365°, -42.218° (conforme pyproj)
    assert abs(lat - (-21.365)) < tolerance_deg, f"Latitude REF_1 inesperada: {lat}"
    assert abs(lon - (-42.218)) < tolerance_deg, f"Longitude REF_1 inesperada: {lon}"

def test_utm_to_latlon_roundtrip_ref2(tolerance_m=0.1):
    """Roundtrip REF_2: lat/lon → UTM → lat/lon deve fechar em <0.1 m."""
    e, n, epsg = latlon_to_utm(REF2_LAT, REF2_LON)
    lat2, lon2 = utm_to_latlon(e, n, epsg)
    # Verifica que o roundtrip é estável (erro < 0.1 m ≈ 0.000001°)
    assert abs(lat2 - REF2_LAT) < 1e-4, f"Latitude roundtrip diverge: {lat2}"
    assert abs(lon2 - REF2_LON) < 1e-4, f"Longitude roundtrip diverge: {lon2}"


# ---------------------------------------------------------------------------
# Testes de transform_coords
# ---------------------------------------------------------------------------
def test_transform_coords_ref2():
    """transform_coords deve produzir os mesmos valores que latlon_to_utm."""
    # Entrada: (lon, lat) no formato always_xy
    result = transform_coords([(REF2_LON, REF2_LAT)], epsg_in=4326, epsg_out=REF2_EPSG)
    assert len(result) == 1
    x, y = result[0]
    assert abs(x - REF2_E) < 1.0
    assert abs(y - REF2_N) < 1.0

def test_transform_coords_roundtrip():
    """Transformação de ida e volta deve ser estável."""
    pts_in = [(REF2_LON, REF2_LAT)]
    pts_utm = transform_coords(pts_in, epsg_in=4326, epsg_out=REF2_EPSG)
    pts_back = transform_coords(pts_utm, epsg_in=REF2_EPSG, epsg_out=4326)
    lon_back, lat_back = pts_back[0]
    assert abs(lat_back - REF2_LAT) < 1e-4
    assert abs(lon_back - REF2_LON) < 1e-4
