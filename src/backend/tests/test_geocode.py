"""
tests/test_geocode.py
Testes unitários e de integração para o serviço de geocodificação.

Cobre:
  - Parsing de lat/lon decimal (sem rede externa)
  - Parsing de coordenadas UTM SIRGAS 2000 (sem rede externa)
  - Sanitização de input (segurança)
  - Endpoint GET /api/v1/tools/geocode

Coordenadas de referência (conforme MEMORY.MD):
  REF_1: UTM 23K 788547 7634925
  REF_2: lat=-22.15018°, lon=-42.92185° → UTM E≈714316, N≈7549084
"""
from __future__ import annotations

import os
import importlib
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SISRUA_TESTING", "true")

from backend.services.geocode import (
    _sanitize_query,
    _try_parse_latlon,
    _try_parse_utm,
    geocode,
)


# ---------------------------------------------------------------------------
# Testes de sanitização
# ---------------------------------------------------------------------------

class TestSanitizeQuery:
    def test_remove_html_tags(self):
        assert "<script>" not in _sanitize_query("<script>alert(1)</script>")

    def test_remove_single_quotes(self):
        assert "'" not in _sanitize_query("'; DROP TABLE--")

    def test_remove_crlf(self):
        assert "\r" not in _sanitize_query("line1\r\nline2")
        assert "\n" not in _sanitize_query("line1\r\nline2")

    def test_remove_null_byte(self):
        assert "\x00" not in _sanitize_query("foo\x00bar")

    def test_truncate_to_200_chars(self):
        long = "a" * 300
        assert len(_sanitize_query(long)) <= 200

    def test_strip_whitespace(self):
        result = _sanitize_query("  -22.15018, -42.92185  ")
        assert result == "-22.15018, -42.92185"

    def test_empty_string(self):
        assert _sanitize_query("") == ""

    def test_backslash_removed(self):
        assert "\\" not in _sanitize_query("foo\\bar")


# ---------------------------------------------------------------------------
# Testes de parse lat/lon
# ---------------------------------------------------------------------------

class TestTryParseLatlon:
    def test_ref2_decimal_comma(self):
        """REF_2: -22.15018, -42.92185 deve ser reconhecida."""
        r = _try_parse_latlon("-22.15018, -42.92185")
        assert r is not None
        assert abs(r["latitude"] - (-22.15018)) < 1e-5
        assert abs(r["longitude"] - (-42.92185)) < 1e-5
        assert r["source"] == "latlon_direct"

    def test_ref2_decimal_space(self):
        """REF_2 com espaço como separador."""
        r = _try_parse_latlon("-22.15018 -42.92185")
        assert r is not None
        assert abs(r["latitude"] - (-22.15018)) < 1e-5

    def test_positive_coords(self):
        r = _try_parse_latlon("51.5074, -0.1278")
        assert r is not None
        assert abs(r["latitude"] - 51.5074) < 1e-4

    def test_invalid_latitude_out_of_range(self):
        assert _try_parse_latlon("91.0, -42.0") is None

    def test_invalid_longitude_out_of_range(self):
        assert _try_parse_latlon("-22.15, -181.0") is None

    def test_address_not_parsed(self):
        assert _try_parse_latlon("Rua das Flores, Nova Friburgo") is None

    def test_semicolon_separator(self):
        r = _try_parse_latlon("-22.15018; -42.92185")
        assert r is not None


# ---------------------------------------------------------------------------
# Testes de parse UTM
# ---------------------------------------------------------------------------

class TestTryParseUtm:
    def test_ref1_utm_with_zone(self):
        """REF_1: 23K 788547 7634925 deve ser reconhecida e convertida."""
        r = _try_parse_utm("23K 788547 7634925")
        assert r is not None
        assert r["source"] == "utm_direct"
        # Lat/lon aproximados para a coordenada UTM 23K 788547 7634925
        assert -25.0 < r["latitude"] < -18.0  # sul do Brasil
        assert -50.0 < r["longitude"] < -38.0

    def test_ref2_utm_no_zone(self):
        """REF_2 em UTM sem zona (714316 7549084) — zona 23 inferida."""
        r = _try_parse_utm("714316 7549084")
        assert r is not None
        # Deve estar próximo de lat≈-22.15, lon≈-42.92
        assert -25.0 < r["latitude"] < -20.0

    def test_utm_comma_separator(self):
        r = _try_parse_utm("714316, 7549084")
        assert r is not None

    def test_easting_too_small(self):
        assert _try_parse_utm("1000, 7549084") is None

    def test_northing_too_small(self):
        assert _try_parse_utm("714316, 100000") is None

    def test_address_not_parsed(self):
        assert _try_parse_utm("Rua das Flores") is None

    def test_source_label(self):
        r = _try_parse_utm("788547 7634925")
        assert r is not None
        assert r["source"] == "utm_direct"


# ---------------------------------------------------------------------------
# Testes do geocode() principal
# ---------------------------------------------------------------------------

class TestGeocode:
    def test_empty_returns_none(self):
        assert geocode("") is None

    def test_none_like_whitespace(self):
        assert geocode("   ") is None

    def test_latlon_priority_over_nominatim(self):
        """lat/lon direto deve retornar sem chamar Nominatim."""
        with patch("backend.services.geocode._nominatim_geocode") as mock_nom:
            r = geocode("-22.15018, -42.92185")
            assert r is not None
            mock_nom.assert_not_called()

    def test_utm_priority_over_nominatim(self):
        """UTM direto deve retornar sem chamar Nominatim."""
        with patch("backend.services.geocode._nominatim_geocode") as mock_nom:
            r = geocode("23K 788547 7634925")
            assert r is not None
            mock_nom.assert_not_called()

    def test_address_calls_nominatim(self):
        """Endereço textual deve acionar Nominatim."""
        mock_result = {"latitude": -22.28, "longitude": -42.53, "source": "nominatim"}
        with patch("backend.services.geocode._nominatim_geocode", return_value=mock_result):
            r = geocode("Nova Friburgo, RJ")
        assert r is not None
        assert r["source"] == "nominatim"

    def test_address_nominatim_returns_none(self):
        """Quando Nominatim não encontra nada, geocode() retorna None."""
        with patch("backend.services.geocode._nominatim_geocode", return_value=None):
            assert geocode("endereço inválido que não existe xyz123") is None

    def test_ref1_utm_roundtrip(self):
        """REF_1 UTM deve retornar lat/lon dentro da faixa esperada."""
        r = geocode("23K 788547 7634925")
        assert r is not None
        assert -25.0 < r["latitude"] < -18.0
        assert -50.0 < r["longitude"] < -38.0

    def test_ref2_latlon_exact(self):
        """REF_2 lat/lon deve retornar os valores exatos."""
        r = geocode("-22.15018, -42.92185")
        assert r is not None
        assert abs(r["latitude"] - (-22.15018)) < 1e-5
        assert abs(r["longitude"] - (-42.92185)) < 1e-5


# ---------------------------------------------------------------------------
# Testes do endpoint /api/v1/tools/geocode
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client_and_token():
    import backend.api as api_mod
    importlib.reload(api_mod)
    c = TestClient(api_mod.app, base_url="http://localhost:8000")
    token = os.environ.get("SISRUA_AUTH_TOKEN", "test-token-123")
    os.environ.setdefault("SISRUA_AUTH_TOKEN", token)
    return c, token


class TestGeocodeEndpoint:
    def test_latlon_returns_200(self, client_and_token):
        client, token = client_and_token
        r = client.get(
            "/api/v1/tools/geocode",
            params={"query": "-22.15018, -42.92185"},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 200
        data = r.json()
        assert abs(data["latitude"] - (-22.15018)) < 1e-5
        assert abs(data["longitude"] - (-42.92185)) < 1e-5
        assert data["source"] == "latlon_direct"

    def test_utm_returns_200(self, client_and_token):
        client, token = client_and_token
        r = client.get(
            "/api/v1/tools/geocode",
            params={"query": "23K 788547 7634925"},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "utm_direct"
        assert -25.0 < data["latitude"] < -18.0

    def test_address_nominatim_mocked(self, client_and_token):
        """Endereço textual chama Nominatim (mockado para não depender de rede)."""
        client, token = client_and_token
        mock_result = {
            "latitude": -22.28,
            "longitude": -42.53,
            "source": "nominatim",
            "display_name": "Nova Friburgo, RJ, Brasil",
        }
        with patch("backend.services.geocode._nominatim_geocode", return_value=mock_result):
            r = client.get(
                "/api/v1/tools/geocode",
                params={"query": "Nova Friburgo RJ"},
                headers={"X-SisRua-Token": token},
            )
        assert r.status_code == 200
        assert r.json()["source"] == "nominatim"

    def test_not_found_returns_404(self, client_and_token):
        client, token = client_and_token
        with patch("backend.services.geocode._nominatim_geocode", return_value=None):
            r = client.get(
                "/api/v1/tools/geocode",
                params={"query": "xyzxyzxyz_nao_existe_999"},
                headers={"X-SisRua-Token": token},
            )
        assert r.status_code == 404

    def test_requires_auth(self, client_and_token):
        client, _ = client_and_token
        r = client.get("/api/v1/tools/geocode", params={"query": "-22.15, -42.92"})
        assert r.status_code in (401, 403)

    def test_empty_query_rejected(self, client_and_token):
        """Query muito curta (min_length=1) deve retornar 422."""
        client, token = client_and_token
        r = client.get(
            "/api/v1/tools/geocode",
            params={"query": ""},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 422

    def test_query_too_long_rejected(self, client_and_token):
        """Query acima de 200 chars deve retornar 422."""
        client, token = client_and_token
        long_q = "a" * 201
        r = client.get(
            "/api/v1/tools/geocode",
            params={"query": long_q},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 422

    def test_ref2_500m_radius_context(self, client_and_token):
        """REF_2 com contexto de 500m — geocode deve retornar coords corretas."""
        client, token = client_and_token
        r = client.get(
            "/api/v1/tools/geocode",
            params={"query": "-22.15018, -42.92185"},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 200
        data = r.json()
        # Verifica que as coordenadas são válidas para criar buffer 500m
        assert -90 <= data["latitude"] <= 90
        assert -180 <= data["longitude"] <= 180

    def test_ref2_1km_radius_context(self, client_and_token):
        """REF_2 com contexto de 1km — geocode retorna coords adequadas."""
        client, token = client_and_token
        r = client.get(
            "/api/v1/tools/geocode",
            params={"query": "-22.15018, -42.92185"},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 200

    def test_ref1_100m_radius_context(self, client_and_token):
        """REF_1 (UTM 23K 788547 7634925) com contexto 100m."""
        client, token = client_and_token
        r = client.get(
            "/api/v1/tools/geocode",
            params={"query": "23K 788547 7634925"},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "utm_direct"
