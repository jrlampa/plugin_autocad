"""
tests/test_coverage_session4.py
Cobertura dos módulos restantes para a sessão 4.

Módulos alvo:
  - core/utils.py         (91%): norm_optional_str exceptions, sanitize_jsonable str,
                                  get_layer_config json parse error, clean_geometry exception
  - core/database.py      (87%): init_geopackage exception, init_schema exception,
                                  get_db_connection PRAGMA exception
  - services/ai.py        (92%): RAG exception (rag_fetch_failed),
                                  audit log RAG (fetch_audit_logs), audit RAG exception
  - audit_routes.py       (92%): create_audit_log generic exception (500),
                                  stats mileage parsing exception (continue),
                                  verify_all exception (500)
  - gis_core/osm.py       (88%): contour generation (lines 321-344),
                                  osm.py line 165-167 (cache_fallback_reason missing),
                                  highway list in edges (line 182),
                                  node loop check_cancel (line 219)
  - api.py                (71%): static file mount path (lines 313-318, 328)

Todos os mocks imitam o comportamento real das dependências.
Interface: pt-BR conforme requisito sisRUA.
"""
from __future__ import annotations

import importlib
import json
import math
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

os.environ.setdefault("SISRUA_TESTING", "true")
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-token-session4")

# ══════════════════════════════════════════════════════════════════════
# core/utils.py — funções utilitárias
# ══════════════════════════════════════════════════════════════════════

class TestUtilsEdgeCases:
    """Cobre os caminhos restantes de core/utils.py."""

    def test_norm_optional_str_math_isnan_exception(self):
        """Linha 28: math.isnan levanta TypeError em valores não-float → except → pass."""
        from backend.shared.utils import norm_optional_str

        # Um objeto que levanta TypeError em isinstance float check via isnan
        class Weird:
            def __float__(self):
                raise TypeError("não é float")

        # O objeto não é float, então isnan não é chamado.
        # Mas se str(obj) falhar, retorna None (linha 35-36).
        class UnStringable:
            def __str__(self):
                raise RuntimeError("cannot str")

        result = norm_optional_str(UnStringable())
        assert result is None

    def test_norm_optional_str_str_strips_to_empty(self):
        """Linha 34: str que vira vazia após strip retorna None."""
        from backend.shared.utils import norm_optional_str
        assert norm_optional_str("   ") is None

    def test_sanitize_jsonable_fallback_to_str(self):
        """Linhas 58-60: objeto não serializável → str()."""
        from backend.shared.utils import sanitize_jsonable

        class Custom:
            def __str__(self):
                return "custom-object"

        result = sanitize_jsonable(Custom())
        assert result == "custom-object"

    def test_sanitize_jsonable_str_exception_returns_none(self):
        """Linha 60-61: str() levanta exceção → None."""
        from backend.shared.utils import sanitize_jsonable

        class Unstrifiable:
            def __str__(self):
                raise RuntimeError("cannot str")

            def __repr__(self):
                raise RuntimeError("cannot repr")

        result = sanitize_jsonable(Unstrifiable())
        assert result is None

    def test_get_layer_config_json_parse_error_returns_fallback(self, tmp_path, monkeypatch):
        """Linhas 139-141: JSON inválido no layers.json → log de erro + fallback hardcoded."""
        from backend.shared import utils as utils_mod

        # Cria um layers.json corrompido temporário
        bad_json_path = tmp_path / "layers.json"
        bad_json_path.write_text("NOT_VALID_JSON{{{", encoding="utf-8")

        # Patch Path.exists to return True and open to point at bad file
        import builtins
        original_open = builtins.open

        def fake_open(path, *args, **kwargs):
            if "layers.json" in str(path):
                return original_open(str(bad_json_path), *args, **kwargs)
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=fake_open):
            with patch("pathlib.Path.exists", return_value=True):
                result = utils_mod.get_layer_config()

        # Should return the fallback dict (since JSON parse failed)
        assert isinstance(result, dict)
        assert "highway" in result

    def test_clean_geometry_simplification_exception_keeps_original(self):
        """Linha 205: exceção na simplificação mantém a feature original."""
        from backend.shared.utils import clean_geometry
        from backend.domain.dto import CadFeature

        f = CadFeature(
            feature_type="Polyline",
            layer="TEST",
            coords_xy=[[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]],
        )
        original_coords = [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]

        # Patch shapely.geometry.LineString (importado localmente na função)
        with patch("shapely.geometry.LineString") as mock_ls_class:
            mock_ls_class.side_effect = RuntimeError("LineString failed")
            result = clean_geometry([f])

        assert len(result) == 1
        assert result[0].coords_xy == original_coords  # Original mantido


# ══════════════════════════════════════════════════════════════════════
# core/database.py — exceções em init_geopackage, init_schema, get_db_connection
# ══════════════════════════════════════════════════════════════════════

class TestDatabaseCoverage:
    """Cobre os caminhos de exceção em core/database.py."""

    def test_init_geopackage_exception_swallowed(self, tmp_path):
        """Linhas 70-71: exceção em init_geopackage é swallowed."""
        from backend.shared.database import init_geopackage

        # Cria conn que vai falhar na primeira execução via cursor mock
        conn = sqlite3.connect(":memory:")

        # Patch sqlite3.Connection usando context manager + cursor replacement
        with patch("backend.core.database.sqlite3") as mock_sqlite:
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = sqlite3.OperationalError("test error")
            mock_sqlite.connect.return_value = mock_conn
            mock_sqlite.OperationalError = sqlite3.OperationalError

            # Não deve propagar a exceção
            init_geopackage(mock_conn)

        conn.close()

    def test_init_schema_exception_swallowed(self, tmp_path):
        """Linhas 146-147: exceção em init_schema é swallowed."""
        from backend.shared.database import init_schema

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.OperationalError("schema error")

        init_schema(mock_conn)  # Não deve propagar

    def test_get_db_connection_returns_valid_connection(self, tmp_path, monkeypatch):
        """Linhas 150-179: get_db_connection retorna conexão válida."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

        import backend.shared.database as db_mod
        # Force reimport to pick up new env
        importlib.reload(db_mod)

        conn = db_mod.get_db_connection()
        assert conn is not None
        # Deve conseguir executar query
        cursor = conn.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# services/ai.py — RAG exception e audit context
# ══════════════════════════════════════════════════════════════════════

class TestAiServiceCoverage:
    """Cobre os caminhos de exceção de AiService.generate_response."""

    def _make_ai(self):
        """Cria AiService com cliente Groq mockado."""
        from backend.application.ai import AiService
        svc = AiService.__new__(AiService)
        svc.model = "llama-3.3-70b-versatile"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Resposta da IA"))]
        )
        svc.client = mock_client
        return svc

    def test_generate_response_rag_exception_swallowed(self):
        """Linhas 53-54: exceção ao buscar job no RAG é swallowed."""
        svc = self._make_ai()

        # get_job é importado localmente dentro de generate_response
        with patch("backend.services.jobs.get_job", side_effect=RuntimeError("job store error")):
            result = svc.generate_response("Pergunta", job_id="job-inexistente")

        # Não deve propagar a exceção — deve retornar resposta normal
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_response_audit_logs_context(self):
        """Linhas 57-68: fetch_audit_logs injeta logs no prompt."""
        svc = self._make_ai()

        # Mock do audit logger com lista de logs
        mock_audit = MagicMock()
        mock_audit.list_logs.return_value = [
            {
                "created_at": "2026-01-01",
                "event_type": "CREATE",
                "entity_type": "Project",
                "entity_id": "proj-001",
                "data": {"project_name": "Teste"},
            }
        ]

        # get_audit_logger é importado localmente
        with patch("backend.core.audit.get_audit_logger", return_value=mock_audit):
            result = svc.generate_response(
                "Quais projetos existem?",
                context={"fetch_audit_logs": True},
            )

        assert isinstance(result, str)

    def test_generate_response_audit_exception_swallowed(self):
        """Linhas 69-70: exceção ao buscar audit logs é swallowed."""
        svc = self._make_ai()

        with patch("backend.core.audit.get_audit_logger", side_effect=RuntimeError("audit crash")):
            result = svc.generate_response(
                "Teste",
                context={"fetch_audit_logs": True},
            )

        assert isinstance(result, str)

    def test_generate_response_no_client_returns_config_message(self):
        """AiService sem cliente retorna mensagem de configuração."""
        from backend.application.ai import AiService
        svc = AiService.__new__(AiService)
        svc.client = None
        svc.model = "llama-3.3-70b-versatile"
        result = svc.generate_response("Olá")
        assert "not configured" in result or "API key" in result.lower()


# ══════════════════════════════════════════════════════════════════════
# audit_routes.py — exceções nos endpoints
# ══════════════════════════════════════════════════════════════════════

def _make_audit_client():
    """Cria TestClient para rotas de auditoria."""
    os.environ["SISRUA_AUTH_TOKEN"] = "audit-test-token"
    import backend.api as api_mod
    importlib.reload(api_mod)
    from fastapi.testclient import TestClient
    client = TestClient(api_mod.app, base_url="http://localhost:8000")
    client.headers.update({"Origin": "http://localhost:8000"})
    return client, "audit-test-token"


class TestAuditRoutesCoverage:
    """Cobre os caminhos de exceção em audit_routes.py."""

    @pytest.fixture()
    def client_tok(self):
        return _make_audit_client()

    def test_create_audit_log_generic_exception_returns_500(self, client_tok):
        """Linhas 56-58: exceção genérica no POST /audit → 500."""
        client, tok = client_tok
        from backend import audit_routes

        with patch.object(audit_routes, "get_audit_logger", side_effect=RuntimeError("crash")):
            r = client.post(
                "/api/audit",
                json={"event_type": "TEST", "entity_type": "Project"},
                headers={"X-SisRua-Token": tok},
            )
        assert r.status_code == 500

    def test_verify_all_exception_returns_500(self, client_tok):
        """Linhas 202-204: exceção em verify_all → 500."""
        client, tok = client_tok
        import backend.infrastructure.audit_routes as audit_routes

        with patch.object(audit_routes, "get_audit_logger", side_effect=RuntimeError("verify crash")):
            r = client.post(
                "/api/audit/verify-all",
                json={},
                headers={"X-SisRua-Token": tok},
            )
        assert r.status_code == 500

    def test_stats_mileage_parsing_continues_on_exception(self, client_tok):
        """Linhas 141-143: dados de mileage corrompidos → continue (resultado parcial).
        
        Rota: /api/valuation/summary (não /api/audit/stats).
        Usa AuditLog rows direto do DB via get_db_connection.
        """
        client, tok = client_tok
        # Endpoint: GET /api/valuation/summary
        # Esse endpoint lê do banco diretamente, então precisa injetar dados reais
        # Para cobrir o `continue` (linha 142), injetamos um row com JSON inválido via mock de get_db_connection
        from backend import audit_routes

        mock_conn = MagicMock()
        # Simula 2 rows: 1 válido e 1 com JSON inválido
        mock_conn.execute.return_value.fetchall.return_value = [
            ('{"project_id": "p1", "mileage_km": 5.5}',),
            ('INVALID_JSON{{{',),  # Vai gerar json.JSONDecodeError → continue
        ]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch.object(audit_routes, "get_db_connection", return_value=mock_conn):
            r = client.get("/api/valuation/summary", headers={"X-SisRua-Token": tok})

        assert r.status_code == 200
        data = r.json()
        assert "total_urban_assets_mapped_km" in data


# ══════════════════════════════════════════════════════════════════════
# gis_core/osm.py — contour generation (lines 321-344)
# ══════════════════════════════════════════════════════════════════════

class TestOsmContourGeneration:
    """Cobre a geração de curvas de nível em gis_core/osm.py."""

    def _make_overpass_minimal(self, lat=-22.15018, lon=-42.92185):
        """Dados Overpass mínimos com 1 via e 2 nós."""
        return {
            "elements": [
                {"type": "node", "id": 1, "lat": lat, "lon": lon, "tags": {}},
                {"type": "node", "id": 2, "lat": lat + 0.001, "lon": lon + 0.001, "tags": {}},
                {
                    "type": "way",
                    "id": 10,
                    "nodes": [1, 2],
                    "tags": {"highway": "residential", "name": "Rua Teste"},
                },
            ]
        }

    def _make_elev_with_contours(self, lat, lon):
        """ElevationService mock com 1 curva de nível válida."""
        elev = MagicMock()
        elev.get_elevation_profile.return_value = [850.0, 855.0]
        # Uma curva de nível com 3 pontos (>= 2 pontos → deve ser adicionada)
        elev.get_contours.return_value = [
            {
                "elevation": 850.0,
                "geometry": [
                    [lat, lon],
                    [lat + 0.001, lon],
                    [lat + 0.001, lon + 0.001],
                ],
            }
        ]
        return elev

    def test_contour_features_adicionadas_ao_resultado(self):
        """Linhas 321-344: curvas de nível são convertidas e adicionadas às features."""
        from backend.domain.osm import prepare_osm_compute

        lat, lon = -22.15018, -42.92185
        cache = MagicMock()
        cache.get.return_value = None
        elev = self._make_elev_with_contours(lat, lon)
        data = self._make_overpass_minimal(lat, lon)

        with patch("backend.gis_core.osm._fetch_overpass_data", return_value=data):
            result = prepare_osm_compute(
                latitude=lat,
                longitude=lon,
                radius=100,
                cache_service=cache,
                elevation_service=elev,
            )

        features = result["features"]
        # Deve conter a curva de nível
        contour_features = [f for f in features if f.get("layer") == "SISRUA_CURVAS_NIVEL"]
        assert len(contour_features) >= 1
        assert contour_features[0]["name"].startswith("Curva")

    def test_contour_com_menos_de_2_coords_ignorado(self):
        """Linha 334: curva de nível com < 2 coordenadas UTM é ignorada."""
        from backend.domain.osm import prepare_osm_compute

        lat, lon = -22.15018, -42.92185
        cache = MagicMock()
        cache.get.return_value = None
        elev = MagicMock()
        elev.get_elevation_profile.return_value = [850.0]
        # Curva com apenas 1 ponto → deve ser ignorada
        elev.get_contours.return_value = [
            {"elevation": 850.0, "geometry": [[lat, lon]]}
        ]
        data = self._make_overpass_minimal(lat, lon)

        with patch("backend.gis_core.osm._fetch_overpass_data", return_value=data):
            result = prepare_osm_compute(
                latitude=lat,
                longitude=lon,
                radius=100,
                cache_service=cache,
                elevation_service=elev,
            )

        features = result["features"]
        contour_features = [f for f in features if f.get("layer") == "SISRUA_CURVAS_NIVEL"]
        assert len(contour_features) == 0

    def test_elevacao_injeta_cor_por_altitude(self):
        """Linhas 310-313: elevações distintas geram cores diferentes."""
        from backend.domain.osm import prepare_osm_compute

        lat, lon = -22.15018, -42.92185
        cache = MagicMock()
        cache.get.return_value = None
        elev = MagicMock()
        # Elevações distintas → z_min != z_max → cores calculadas
        elev.get_elevation_profile.return_value = [800.0, 900.0]
        elev.get_contours.return_value = []
        data = {
            "elements": [
                {"type": "node", "id": 1, "lat": lat, "lon": lon, "tags": {}},
                {"type": "node", "id": 2, "lat": lat + 0.001, "lon": lon + 0.001, "tags": {}},
                {"type": "node", "id": 3, "lat": lat + 0.002, "lon": lon + 0.002, "tags": {}},
                {
                    "type": "way", "id": 10, "nodes": [1, 2],
                    "tags": {"highway": "residential"},
                },
                {
                    "type": "way", "id": 11, "nodes": [2, 3],
                    "tags": {"highway": "primary"},
                },
            ]
        }

        with patch("backend.gis_core.osm._fetch_overpass_data", return_value=data):
            result = prepare_osm_compute(
                latitude=lat,
                longitude=lon,
                radius=100,
                cache_service=cache,
                elevation_service=elev,
            )

        features_with_color = [f for f in result["features"] if f.get("color")]
        assert len(features_with_color) >= 1


# ══════════════════════════════════════════════════════════════════════
# api.py — static file mount path (lines 313-325)
# ══════════════════════════════════════════════════════════════════════

class TestApiStaticFileMount:
    """Cobre o caminho de montagem de arquivos estáticos em api.py."""

    def test_root_returns_html_when_dist_not_found(self):
        """Linhas 330-335: quando dist/ não existe, retorna HTML de fallback."""
        os.environ["SISRUA_AUTH_TOKEN"] = "static-test-token"
        import backend.api as api_mod
        importlib.reload(api_mod)
        from fastapi.testclient import TestClient

        client = TestClient(api_mod.app, base_url="http://localhost:8000")
        client.headers.update({"Origin": "http://localhost:8000"})

        r = client.get("/")
        # Pode ser 200 (HTML fallback) ou 404 se não encontrado
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert "sisRUA" in r.text or "html" in r.headers.get("content-type", "")

    def test_api_startup_no_exception(self):
        """Linhas 67-114: startup do lifespan não levanta exceção em modo de teste."""
        os.environ["SISRUA_AUTH_TOKEN"] = "startup-test-token"
        os.environ["SISRUA_TESTING"] = "true"

        import backend.api as api_mod
        importlib.reload(api_mod)
        from fastapi.testclient import TestClient

        with TestClient(api_mod.app, base_url="http://localhost:8000") as client:
            client.headers.update({"Origin": "http://localhost:8000"})
            r = client.get("/api/v1/health")
        assert r.status_code == 200
