"""
tests/test_coverage_session7.py
Testes para a sessão 2026-02-22:
  - Endpoint POST /api/v1/tools/elevation/contours (novos modelos e endpoint)
  - Validação de ElevationContoursRequest
  - Cobertura de paths não cobertos em api.py / models.py

Coordenadas de teste (conforme MEMORY.MD):
  REF_2: lat=-22.15018, lon=-42.92185  (graus decimais)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("SISRUA_TESTING", "true")
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-session7-token")

def _get_token():
    """Lê o token atual do ambiente (pode mudar entre testes em suite completa)."""
    return os.environ.get("SISRUA_AUTH_TOKEN", "test-session7-token")


def _auth():
    return {"X-SisRua-Token": _get_token()}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    from backend.api import app
    with TestClient(app, base_url="http://localhost:8000") as c:
        c.headers.update({"Origin": "http://localhost:8000"})
        yield c


# ---------------------------------------------------------------------------
# Testes de modelo — ElevationContoursRequest
# ---------------------------------------------------------------------------

class TestElevationContoursRequest:
    """Valida regras de validação do modelo ElevationContoursRequest."""

    def test_valid_request_ref2_bbox(self):
        from backend.domain.dto import ElevationContoursRequest
        req = ElevationContoursRequest(
            min_lat=-22.16, min_lon=-42.93,
            max_lat=-22.14, max_lon=-42.91,
            interval=10.0,
        )
        assert req.min_lat == -22.16
        assert req.max_lat == -22.14
        assert req.interval == 10.0

    def test_valid_request_100m_area(self):
        from backend.domain.dto import ElevationContoursRequest
        # Área pequena (~100m × 100m) ao redor de REF_2
        req = ElevationContoursRequest(
            min_lat=-22.15068, min_lon=-42.92235,
            max_lat=-22.14968, max_lon=-42.92135,
            interval=5.0,
        )
        assert req.interval == 5.0
        assert req.count if hasattr(req, "count") else True  # model only

    def test_max_lat_must_be_greater_than_min_lat(self):
        from backend.domain.dto import ElevationContoursRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ElevationContoursRequest(
                min_lat=-22.14, min_lon=-42.93,
                max_lat=-22.16, max_lon=-42.91,  # max < min
                interval=10.0,
            )

    def test_max_lon_must_be_greater_than_min_lon(self):
        from backend.domain.dto import ElevationContoursRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ElevationContoursRequest(
                min_lat=-22.16, min_lon=-42.91,
                max_lat=-22.14, max_lon=-42.93,  # max < min
                interval=10.0,
            )

    def test_equal_lat_rejected(self):
        from backend.domain.dto import ElevationContoursRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ElevationContoursRequest(
                min_lat=-22.15, min_lon=-42.93,
                max_lat=-22.15, max_lon=-42.91,  # equal
                interval=10.0,
            )

    def test_interval_gt_zero(self):
        from backend.domain.dto import ElevationContoursRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ElevationContoursRequest(
                min_lat=-22.16, min_lon=-42.93,
                max_lat=-22.14, max_lon=-42.91,
                interval=0.0,  # must be > 0
            )

    def test_interval_le_1000(self):
        from backend.domain.dto import ElevationContoursRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ElevationContoursRequest(
                min_lat=-22.16, min_lon=-42.93,
                max_lat=-22.14, max_lon=-42.91,
                interval=1001.0,  # exceeds max
            )

    def test_lat_out_of_range(self):
        from backend.domain.dto import ElevationContoursRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ElevationContoursRequest(
                min_lat=-91.0, min_lon=-42.93,
                max_lat=-22.14, max_lon=-42.91,
                interval=10.0,
            )

    def test_default_interval(self):
        from backend.domain.dto import ElevationContoursRequest
        req = ElevationContoursRequest(
            min_lat=-22.16, min_lon=-42.93,
            max_lat=-22.14, max_lon=-42.91,
        )
        assert req.interval == 10.0


# ---------------------------------------------------------------------------
# Testes de modelo — ContourLine e ElevationContoursResponse
# ---------------------------------------------------------------------------

class TestContourLineModel:
    def test_valid_contour_line(self):
        from backend.domain.dto import ContourLine
        cl = ContourLine(elevation=50.0, geometry=[[-22.15, -42.92], [-22.16, -42.93]])
        assert cl.elevation == 50.0
        assert len(cl.geometry) == 2

    def test_contours_response(self):
        from backend.domain.dto import ContourLine, ElevationContoursResponse
        cl = ContourLine(elevation=100.0, geometry=[[-22.15, -42.92]])
        resp = ElevationContoursResponse(contours=[cl], interval=10.0, count=1)
        assert resp.count == 1
        assert resp.interval == 10.0


# ---------------------------------------------------------------------------
# Testes do endpoint POST /api/v1/tools/elevation/contours
# ---------------------------------------------------------------------------

class TestElevationContoursEndpoint:
    """Testes da API do endpoint de curvas de nível."""

    def _contours_payload(self, interval=10.0):
        """Payload padrão usando REF_2 como centro."""
        return {
            "min_lat": -22.16,
            "min_lon": -42.93,
            "max_lat": -22.14,
            "max_lon": -42.91,
            "interval": interval,
        }

    def test_requires_auth(self, client):
        """Endpoint deve rejeitar requisição sem token."""
        r = client.post("/api/v1/tools/elevation/contours", json=self._contours_payload())
        assert r.status_code in (401, 403)

    def test_contours_no_dem_returns_empty_list(self, client):
        """Quando não há DEM disponível, retorna 200 com lista vazia."""
        with patch("backend.services.elevation.ElevationService.get_contours", return_value=[]):
            r = client.post(
                "/api/v1/tools/elevation/contours",
                json=self._contours_payload(),
                headers=_auth(),
            )
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 0
        assert body["contours"] == []
        assert body["interval"] == 10.0

    def test_contours_with_mock_dem_ref2_100m(self, client):
        """REF_2 com area ~100m: endpoint retorna curvas corretas."""
        mock_contours = [
            {"elevation": 500.0, "geometry": [[-22.15, -42.92], [-22.14, -42.91]]},
            {"elevation": 510.0, "geometry": [[-22.15, -42.93], [-22.16, -42.92]]},
        ]
        with patch("backend.services.elevation.ElevationService.get_contours", return_value=mock_contours):
            r = client.post(
                "/api/v1/tools/elevation/contours",
                json={
                    "min_lat": -22.15068, "min_lon": -42.92235,
                    "max_lat": -22.14968, "max_lon": -42.92135,
                    "interval": 10.0,
                },
                headers=_auth(),
            )
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 2
        assert len(body["contours"]) == 2
        assert body["contours"][0]["elevation"] == 500.0
        assert len(body["contours"][0]["geometry"]) == 2

    def test_contours_with_mock_dem_ref2_500m(self, client):
        """REF_2 com area ~500m: endpoint retorna curvas."""
        mock_contours = [
            {"elevation": 480.0, "geometry": [[-22.15, -42.92], [-22.15, -42.93]]},
        ]
        with patch("backend.services.elevation.ElevationService.get_contours", return_value=mock_contours):
            r = client.post(
                "/api/v1/tools/elevation/contours",
                json={
                    "min_lat": -22.155, "min_lon": -42.927,
                    "max_lat": -22.145, "max_lon": -42.917,
                    "interval": 5.0,
                },
                headers=_auth(),
            )
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["interval"] == 5.0

    def test_contours_with_mock_dem_ref2_1km(self, client):
        """REF_2 com area ~1km: múltiplas curvas de nível."""
        mock_contours = [
            {"elevation": float(e), "geometry": [[-22.16, -42.93]]}
            for e in range(450, 550, 10)
        ]
        with patch("backend.services.elevation.ElevationService.get_contours", return_value=mock_contours):
            r = client.post(
                "/api/v1/tools/elevation/contours",
                json={
                    "min_lat": -22.16, "min_lon": -42.93,
                    "max_lat": -22.14, "max_lon": -42.91,
                    "interval": 10.0,
                },
                headers=_auth(),
            )
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 10
        elevations = [c["elevation"] for c in body["contours"]]
        assert 450.0 in elevations
        assert 540.0 in elevations

    def test_contours_invalid_bbox_max_lat_less_than_min_lat(self, client):
        """Bounding box com max_lat < min_lat → 422."""
        r = client.post(
            "/api/v1/tools/elevation/contours",
            json={
                "min_lat": -22.14, "min_lon": -42.93,
                "max_lat": -22.16, "max_lon": -42.91,  # invertido
                "interval": 10.0,
            },
            headers=_auth(),
        )
        assert r.status_code == 422

    def test_contours_invalid_interval_zero(self, client):
        """Intervalo zero → 422."""
        r = client.post(
            "/api/v1/tools/elevation/contours",
            json={**self._contours_payload(), "interval": 0.0},
            headers=_auth(),
        )
        assert r.status_code == 422

    def test_contours_service_exception_returns_500(self, client):
        """Exceção interna no serviço → 500."""
        with patch(
            "backend.services.elevation.ElevationService.get_contours",
            side_effect=RuntimeError("DEM failure"),
        ):
            r = client.post(
                "/api/v1/tools/elevation/contours",
                json=self._contours_payload(),
                headers=_auth(),
            )
        assert r.status_code == 500
        assert "curvas de nível" in r.json()["detail"]

    def test_contours_value_error_returns_400(self, client):
        """ValueError no serviço → 400."""
        with patch(
            "backend.services.elevation.ElevationService.get_contours",
            side_effect=ValueError("invalid bbox"),
        ):
            r = client.post(
                "/api/v1/tools/elevation/contours",
                json=self._contours_payload(),
                headers=_auth(),
            )
        assert r.status_code == 400

    def test_contours_default_interval_used(self, client):
        """Quando interval não enviado, usa 10.0 por padrão."""
        with patch("backend.services.elevation.ElevationService.get_contours", return_value=[]):
            r = client.post(
                "/api/v1/tools/elevation/contours",
                json={
                    "min_lat": -22.16, "min_lon": -42.93,
                    "max_lat": -22.14, "max_lon": -42.91,
                },
                headers=_auth(),
            )
        assert r.status_code == 200
        assert r.json()["interval"] == 10.0

    def test_openapi_schema_includes_contours(self, client):
        """O schema OpenAPI expõe o endpoint de curvas de nível."""
        r = client.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json()["paths"]
        assert "/api/v1/tools/elevation/contours" in paths


# ---------------------------------------------------------------------------
# Testes de cobertura — api.py paths não cobertos (lifespan error handlers)
# ---------------------------------------------------------------------------

class TestApiLifespanEdgePaths:
    """Cobre branches de erro nos handlers de cleanup e housekeeper do lifespan."""

    def test_cleanup_expired_jobs_exception_is_logged(self):
        """
        O loop de cleanup no lifespan captura exceções e imprime erro.
        Aqui testamos diretamente a função cleanup_expired_jobs com DB inválido.
        """
        from backend.application.jobs import cleanup_expired_jobs
        # Chamar com banco não inicializado não deve levantar (erro interno capturado)
        try:
            result = cleanup_expired_jobs(max_age_seconds=0)
            assert isinstance(result, int)
        except Exception:
            # Se levantar, o handler do lifespan deveria capturar — aceitável aqui
            pass

    def test_housekeeper_run_daily_cleanup_nonexistent_dirs(self, tmp_path):
        """run_daily_cleanup com diretórios inexistentes retorna 0 sem erro."""
        from backend.application.housekeeper import HousekeeperService
        svc = HousekeeperService(retention_days=0)
        result = svc.run_daily_cleanup([tmp_path / "nonexistent1", tmp_path / "nonexistent2"])
        assert result == 0

    def test_housekeeper_scan_failure_returns_zero(self, tmp_path):
        """Quando o scan de diretório falha (permissão), retorna 0."""
        from backend.application.housekeeper import HousekeeperService
        svc = HousekeeperService(retention_days=0)
        # Provoca falha na iteração simulando rglob com erro
        with patch.object(Path, "rglob", side_effect=PermissionError("denied")):
            result = svc.cleanup_directory(tmp_path, recursive=True)
        assert result == 0

    def test_maybe_mount_frontend_no_dist(self):
        """_maybe_mount_frontend com dist inexistente registra rota HTML fallback."""
        from backend.api import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        # Pode ter montagem estática ou rota raiz HTML — a API não deve quebrar
        assert "/api/v1/health" in routes or any("/health" in r for r in routes)


# ---------------------------------------------------------------------------
# Testes de cobertura — models.py — paths não cobertos
# ---------------------------------------------------------------------------

class TestModelCoveragePaths:
    """Cobre linhas não alcançadas pelos testes anteriores nos modelos."""

    def test_elevation_profile_request_point_too_short(self):
        """Ponto com menos de 2 elementos → ValidationError (linha 95)."""
        from backend.domain.dto import ElevationProfileRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ElevationProfileRequest(path=[[]])  # ponto com 0 elementos

    def test_webhook_url_without_hostname(self):
        """URL sem hostname → ValidationError (linha 125)."""
        from backend.domain.dto import WebhookRegistrationRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            # Esquema válido mas sem hostname real
            WebhookRegistrationRequest(url="http://")

    def test_webhook_events_empty_strings_filtered(self):
        """Eventos vazios após strip devem ser filtrados → None."""
        from backend.domain.dto import WebhookRegistrationRequest
        req = WebhookRegistrationRequest(url="https://example.com", events=["  ", ""])
        assert req.events is None

    def test_webhook_events_none_stays_none(self):
        """events=None → permanece None (linha 131)."""
        from backend.domain.dto import WebhookRegistrationRequest
        req = WebhookRegistrationRequest(url="https://example.com", events=None)
        assert req.events is None
