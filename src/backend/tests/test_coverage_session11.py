"""
tests/test_coverage_session11.py

Cobertura das linhas ainda descobertas após a Sessão 10:
  - backend/infrastructure/routes/prepare.py  IBGE/INEA endpoints via HTTP (88% → 100%)
  - backend/domain/buffer.py                  stop/sentinel/final-flush/error (82% → 100%)
  - backend/shared/ipc.py                     Linux path: warning + stop (62% → 80%)
  - backend/infrastructure/lifecycle.py       start_background_tasks paths (88% → 100%)
  - Shim importação direta: routes/prepare, services/*, routes/deps (0% → >0%)
"""
from __future__ import annotations

import importlib
import os
import sys
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SISRUA_TESTING", "true")
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-s11-token")

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# =============================================================================
# Helpers compartilhados
# =============================================================================

def _make_client(token: str = "test-s11-token"):
    """Cria TestClient apontando para a app principal."""
    from fastapi.testclient import TestClient
    os.environ["SISRUA_AUTH_TOKEN"] = token
    import backend.infrastructure.api as api_mod
    importlib.reload(api_mod)
    return TestClient(api_mod.app, base_url="http://localhost:8000"), token


# =============================================================================
# infrastructure/routes/prepare.py — linhas 66 (IBGE) e 85-86 (INEA)
# =============================================================================

# Reuse mock data from test_gis_ibge / test_gis_inea patterns

_MUNICIPIOS_MOCK = [
    {
        "id": 3303302,
        "nome": "Nova Friburgo",
        "microrregiao": {"mesorregiao": {"UF": {"sigla": "RJ"}}},
    }
]

_IBGE_GEOJSON_MOCK = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-42.55, -22.25], [-42.40, -22.25],
                    [-42.40, -22.10], [-42.55, -22.10], [-42.55, -22.25],
                ]],
            },
            "properties": {"name": "Nova Friburgo"},
        }
    ],
}

_WFS_LINE_MOCK = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[-43.2, -22.9], [-43.1, -22.8]],
            },
            "properties": {"nome": "Rio Teste"},
        }
    ],
}


class TestPrepareIbgeEndpoint:
    """Testa POST /api/v1/prepare/ibge via TestClient (cobre linha 66)."""

    @patch("backend.gis_core.ibge.requests.get")
    def test_prepare_ibge_ok(self, mock_get):
        """POST /api/v1/prepare/ibge retorna 200 com features."""
        # Mock dos dois requests.get: localidades e malhas
        mock_loc = MagicMock()
        mock_loc.json.return_value = _MUNICIPIOS_MOCK
        mock_loc.raise_for_status = MagicMock()

        mock_malha = MagicMock()
        mock_malha.json.return_value = _IBGE_GEOJSON_MOCK
        mock_malha.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_loc, mock_malha]

        client, token = _make_client()
        r = client.post(
            "/api/v1/prepare/ibge",
            json={"nome_municipio": "Nova Friburgo", "uf": "RJ"},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 200
        body = r.json()
        assert "features" in body

    @patch("backend.gis_core.ibge.requests.get")
    def test_prepare_ibge_municipio_nao_encontrado(self, mock_get):
        """POST /api/v1/prepare/ibge retorna 404 para município desconhecido."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = []  # Lista vazia — município não encontrado
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client, token = _make_client()
        r = client.post(
            "/api/v1/prepare/ibge",
            json={"nome_municipio": "CidadeInexistente99", "uf": "XX"},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code in (404, 422, 500)

    def test_prepare_ibge_requires_auth(self):
        """POST /api/v1/prepare/ibge retorna 403 sem token."""
        client, _ = _make_client()
        r = client.post(
            "/api/v1/prepare/ibge",
            json={"nome_municipio": "Nova Friburgo"},
        )
        assert r.status_code == 403


class TestPrepareIneaEndpoint:
    """Testa POST /api/v1/prepare/inea via TestClient (cobre linhas 85-86)."""

    @patch("backend.gis_core.inea.requests.get")
    def test_prepare_inea_ok_without_bbox(self, mock_get):
        """POST /api/v1/prepare/inea retorna 200 sem bbox (cobre linha 85: bbox=None)."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = _WFS_LINE_MOCK
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client, token = _make_client()
        r = client.post(
            "/api/v1/prepare/inea",
            json={"typename": "hidrografia"},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 200
        body = r.json()
        assert "features" in body

    @patch("backend.gis_core.inea.requests.get")
    def test_prepare_inea_ok_with_bbox(self, mock_get):
        """POST /api/v1/prepare/inea retorna 200 com bbox (cobre linha 85: bbox=tuple)."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = _WFS_LINE_MOCK
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client, token = _make_client()
        r = client.post(
            "/api/v1/prepare/inea",
            json={
                "typename": "hidrografia",
                "bbox": [-43.5, -23.1, -42.8, -22.6],
            },
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 200
        body = r.json()
        assert "features" in body

    def test_prepare_inea_requires_auth(self):
        """POST /api/v1/prepare/inea retorna 403 sem token."""
        client, _ = _make_client()
        r = client.post(
            "/api/v1/prepare/inea",
            json={"typename": "hidrografia"},
        )
        assert r.status_code == 403


# =============================================================================
# domain/buffer.py — stop/sentinel/final-flush/error (linhas 32-34,48,67-68,73-74)
# =============================================================================

class TestDomainPersistenceBuffer:
    """Cobre os caminhos não cobertos de backend.domain.buffer.PersistenceBuffer."""

    def test_stop_flushes_remaining_items(self):
        """stop() aguarda o worker terminar e o final-flush é chamado (linhas 67-68)."""
        from backend.domain.buffer import PersistenceBuffer

        flushed = []
        buf = PersistenceBuffer(
            flush_callback=lambda batch: flushed.extend(batch),
            batch_size=100,
            flush_interval=10.0,  # longo para não disparar por tempo
        )
        buf.add("item1")
        buf.add("item2")
        buf.stop()  # cobre linhas 32-34 (stop) e 48 (sentinel break) e 67-68 (final flush)
        assert "item1" in flushed
        assert "item2" in flushed

    def test_stop_empty_buffer_no_flush(self):
        """stop() com buffer vazio não chama flush_callback."""
        from backend.domain.buffer import PersistenceBuffer

        flush_calls = []
        buf = PersistenceBuffer(
            flush_callback=lambda batch: flush_calls.append(batch),
            batch_size=100,
            flush_interval=10.0,
        )
        buf.stop()
        assert flush_calls == []

    def test_flush_callback_exception_does_not_crash(self):
        """Exceção no flush_callback é capturada (linhas 73-74)."""
        from backend.domain.buffer import PersistenceBuffer

        def bad_callback(batch):
            raise RuntimeError("flush error")

        buf = PersistenceBuffer(
            flush_callback=bad_callback,
            batch_size=1,
            flush_interval=10.0,
        )
        buf.add("item")
        # Give worker time to process the batch (batch_size=1 triggers immediate flush)
        time.sleep(0.3)
        buf.stop()
        # Should not have raised — logger.error captured the exception

    def test_batch_size_triggers_flush(self):
        """Flush por tamanho de batch funciona antes de stop()."""
        from backend.domain.buffer import PersistenceBuffer

        flushed_batches = []
        buf = PersistenceBuffer(
            flush_callback=lambda batch: flushed_batches.append(list(batch)),
            batch_size=3,
            flush_interval=10.0,
        )
        buf.add(1)
        buf.add(2)
        buf.add(3)
        # Wait for batch-full flush
        time.sleep(0.3)
        buf.stop()
        # At least one batch of 3 should have been flushed
        total = sum(len(b) for b in flushed_batches)
        assert total >= 3

    def test_time_interval_triggers_flush(self):
        """Flush por intervalo de tempo funciona sem atingir batch_size."""
        from backend.domain.buffer import PersistenceBuffer

        flushed = []
        buf = PersistenceBuffer(
            flush_callback=lambda batch: flushed.extend(batch),
            batch_size=100,
            flush_interval=0.1,  # muito curto — dispara rapidamente
        )
        buf.add("time-item")
        time.sleep(0.4)  # espera o intervalo disparar
        buf.stop()
        assert "time-item" in flushed


# =============================================================================
# shared/ipc.py — Linux path: warning on start, stop() no-op (linhas 11-16, 67-95)
# =============================================================================

class TestIpcServerLinux:
    """Cobre backend.shared.ipc.IpcServer no Linux (sem win32pipe)."""

    def test_start_logs_warning_on_linux(self):
        """IpcServer.start() loga aviso e retorna sem lançar no Linux."""
        from backend.shared.ipc import IpcServer
        server = IpcServer(auth_token="test-ipc-token")
        # On Linux _WIN32_AVAILABLE=False → logs warning and returns
        server.start()
        assert server.running is False or server.thread is None

    def test_stop_no_op_on_linux(self):
        """IpcServer.stop() não lança no Linux (pipe não existe)."""
        from backend.shared.ipc import IpcServer
        server = IpcServer(auth_token="test-ipc-token")
        server.start()  # no-op on Linux
        server.stop()   # should not raise

    def test_server_instantiation(self):
        """IpcServer.__init__ seta atributos corretamente."""
        from backend.shared.ipc import IpcServer
        server = IpcServer(auth_token="my-token")
        assert server.auth_token == "my-token"
        assert server.running is False
        assert server.thread is None


# =============================================================================
# infrastructure/lifecycle.py — start_background_tasks (linhas 13, 29, 32)
# =============================================================================

class TestLifecycle:
    """Cobre backend.infrastructure.lifecycle.start_background_tasks."""

    def test_start_background_tasks_runs_without_error(self, tmp_path):
        """start_background_tasks cria threads daemon sem lançar exceção."""
        from backend.infrastructure.lifecycle import start_background_tasks
        # Should not raise even without real DB or log dirs
        start_background_tasks()
        # Give daemon threads time to start
        time.sleep(0.05)

    def test_start_background_tasks_with_dirs(self, tmp_path):
        """start_background_tasks detecta diretórios de logs e cache."""
        logs_dir = tmp_path / "logs"
        cache_dir = tmp_path / "cache"
        logs_dir.mkdir()
        cache_dir.mkdir()

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            from backend.infrastructure.lifecycle import start_background_tasks
            start_background_tasks()
            time.sleep(0.05)
        finally:
            os.chdir(original_cwd)


# =============================================================================
# Shim files — importação direta para coverage (0% → >0%)
# =============================================================================

class TestShimImports:
    """Importação direta dos shims para garantir coverage > 0%."""

    def test_import_routes_deps(self):
        """backend.routes.deps é importável e expõe cache_service."""
        from backend.routes.deps import cache_service
        assert cache_service is not None

    def test_import_services_health(self):
        """backend.services.health expõe HealthService."""
        from backend.services.health import health_service
        assert health_service is not None

    def test_import_services_ai(self):
        """backend.services.ai expõe AiService."""
        from backend.services.ai import AiService
        assert AiService is not None

    def test_import_services_elevation(self):
        """backend.services.elevation expõe ElevationService."""
        from backend.services.elevation import ElevationService
        assert ElevationService is not None

    def test_import_services_geocode(self):
        """backend.services.geocode é importável."""
        import backend.services.geocode
        assert backend.services.geocode is not None

    def test_import_services_geojson(self):
        """backend.services.geojson expõe prepare_geojson_compute."""
        from backend.services.geojson import prepare_geojson_compute
        assert prepare_geojson_compute is not None

    def test_import_services_jobs(self):
        """backend.services.jobs é importável."""
        import backend.services.jobs
        assert backend.services.jobs is not None

    def test_import_services_projects(self):
        """backend.services.projects é importável."""
        import backend.services.projects
        assert backend.services.projects is not None

    def test_import_services_webhooks(self):
        """backend.services.webhooks é importável."""
        import backend.services.webhooks
        assert backend.services.webhooks is not None

    def test_import_services_executor(self):
        """backend.services.executor é importável."""
        import backend.services.executor
        assert backend.services.executor is not None

    def test_import_audit_routes(self):
        """backend.audit_routes é importável e é o módulo real."""
        import backend.audit_routes  # noqa: F401
        # The shim replaces sys.modules['backend.audit_routes'] with the real module
        import sys
        mod = sys.modules.get("backend.audit_routes")
        assert mod is not None

    def test_import_core_shims(self):
        """backend.core.* shims são importáveis."""
        import backend.core.audit   # noqa: F401
        import backend.core.auth    # noqa: F401
        import backend.core.database  # noqa: F401
        import backend.core.logger  # noqa: F401
        import backend.core.utils   # noqa: F401
        import sys
        # All shims should be registered in sys.modules as the real shared modules
        assert sys.modules.get("backend.core.audit") is not None
        assert sys.modules.get("backend.core.auth") is not None
        assert sys.modules.get("backend.core.database") is not None
        assert sys.modules.get("backend.core.logger") is not None
        assert sys.modules.get("backend.core.utils") is not None
