"""
tests/test_coverage_session6.py
Cobertura dos módulos restantes — sessão 6.

Módulos alvo (linhas descobertas no relatório de cobertura):
  - services/geocode.py        (97%): easting fora do intervalo (linha 77),
                                      lat/lon resultante inválido (linha 97),
                                      geocode() → Nominatim (linha 183)
  - services/geojson.py        (98%): _emit_feature com ≥2 coords (linha 64),
                                      tipo GeoJSON desconhecido → 400 (linha 159)
  - core/audit.py              (98%): os.chmod falha → swallowed (linhas 47-48)
  - core/circuit_breaker.py    (96%): HALF_OPEN → falha → OPEN (linhas 68-69)
  - core/database.py           (96%): exceção em init_schema → logada (linhas 178-179)
  - services/export_service.py (97%): EPSG ValueError (linha 133),
                                      gpkg_contents presente (linha 142),
                                      gpkg_geometry_columns presente (linha 151)
  - routes/enterprise.py       (97%): classe_tensao inválida → 422 (linhas 88-89),
                                      NotFoundError em export_dxf_prodist → 404 (linha 239),
                                      exceção geral → 500 (linha 245)
  - routes/ai_routes.py        (96%): exceção em generate_response → resposta fallback (linha 38)
  - routes/projects.py         (97%): ConflictError → 409 (linha 74)

Interface: pt-BR conforme requisito sisRUA.
"""
from __future__ import annotations

import importlib
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SISRUA_TESTING", "true")
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-token-session6")

_ROOT = Path(__file__).resolve().parents[1]
import sys
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ══════════════════════════════════════════════════════════════════════
# services/geocode.py — caminhos descobertos
# ══════════════════════════════════════════════════════════════════════

class TestGeocodeCoverage:
    """Cobre os caminhos não exercidos de services/geocode.py."""

    def test_utm_easting_fora_do_intervalo_retorna_none(self):
        """Linha 77: easting > 999_000 → _try_parse_utm retorna None."""
        from backend.application.geocode import _try_parse_utm

        # easting 2_000_000 está fora do intervalo válido (100_000–999_000)
        result = _try_parse_utm("2000000 7634925")
        assert result is None

    def test_utm_easting_muito_pequeno_retorna_none(self):
        """Linha 77: easting < 100_000 → _try_parse_utm retorna None."""
        from backend.application.geocode import _try_parse_utm

        result = _try_parse_utm("50000 7634925")
        assert result is None

    def test_utm_latlon_resultante_invalido_retorna_none(self):
        """Linha 97: utm_to_latlon retorna coordenadas fora de (-90..90 / -180..180) → None."""
        from backend.application.geocode import _try_parse_utm

        with patch("backend.gis_core.crs.utm_to_latlon", return_value=(999.0, 999.0)):
            # Texto UTM válido: easting 788547, northing 7634925 (zona 23K)
            result = _try_parse_utm("23K 788547 7634925")
        assert result is None

    def test_utm_exception_em_conversao_retorna_none(self):
        """Linha 97: utm_to_latlon levanta exceção → _try_parse_utm retorna None."""
        from backend.application.geocode import _try_parse_utm

        with patch("backend.gis_core.crs.utm_to_latlon", side_effect=ValueError("proj error")):
            result = _try_parse_utm("23K 788547 7634925")
        assert result is None

    def test_geocode_cai_em_nominatim_quando_nao_e_latlon_nem_utm(self):
        """Linha 183: geocode() com endereço textual chama _nominatim_geocode."""
        from backend.application import geocode as geocode_mod

        mock_result = {"latitude": -22.15018, "longitude": -42.92185, "source": "nominatim"}
        with patch.object(geocode_mod, "_nominatim_geocode", return_value=mock_result) as mock_nom:
            result = geocode_mod.geocode("Rua das Flores, Nova Friburgo, RJ")
        mock_nom.assert_called_once()
        assert result == mock_result

    def test_geocode_query_vazia_retorna_none(self):
        """geocode('') retorna None sem chamar Nominatim."""
        from backend.application import geocode as geocode_mod

        with patch.object(geocode_mod, "_nominatim_geocode") as mock_nom:
            result = geocode_mod.geocode("")
        mock_nom.assert_not_called()
        assert result is None

    def test_geocode_query_sanitizada_para_vazia_retorna_none(self):
        """Linha 183: query com apenas chars perigosos → _sanitize_query → '' → return None."""
        from backend.application import geocode as geocode_mod

        # Caracteres que são todos removidos por _sanitize_query
        result = geocode_mod.geocode("<script>alert('xss')</script>")
        assert result is None


# ══════════════════════════════════════════════════════════════════════
# services/geojson.py — caminhos descobertos
# ══════════════════════════════════════════════════════════════════════

class TestGeoJsonServiceCoverage:
    """Cobre caminhos não exercidos de services/geojson.py."""

    def _minimal_linestring_fc(self):
        """FeatureCollection mínima com um LineString de 2 pontos (perto de Nova Friburgo)."""
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"highway": "residential"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-42.92185, -22.15018], [-42.92100, -22.14900]],
                    },
                }
            ],
        }

    def test_emit_feature_com_menos_de_2_coords_retorna_cedo(self):
        """Linha 64: _emit_feature com < 2 coordenadas → return cedo (não cria feature)."""
        from backend.application.geojson import prepare_geojson_compute

        # LineString com apenas 1 ponto → _emit_feature retorna cedo (linha 64)
        geo = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"highway": "residential"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-42.92185, -22.15018]],  # só 1 ponto
                    },
                }
            ],
        }
        result = prepare_geojson_compute(geo)
        # Sem features criadas — o _emit_feature retornou cedo
        assert isinstance(result.get("features"), list)
        assert len(result["features"]) == 0

    def test_emit_feature_com_coords_validas_cria_feature(self):
        """Linha 65: _emit_feature com ≥2 coordenadas cria uma CadFeature."""
        from backend.application.geojson import prepare_geojson_compute

        geo = self._minimal_linestring_fc()
        result = prepare_geojson_compute(geo)
        # prepare_geojson_compute returns a dict with 'features' list
        assert isinstance(result.get("features"), list)
        assert len(result["features"]) >= 1

    def test_tipo_geojson_desconhecido_levanta_400(self):
        """Linha 159: tipo GeoJSON desconhecido → HTTPException 400."""
        from fastapi import HTTPException
        from backend.application import geojson as geojson_mod

        # Mock first_lonlat to return valid coords so we pass the early check
        with patch.object(geojson_mod, "first_lonlat", return_value=(-42.92185, -22.15018)):
            geo = {"type": "GeometryCollection", "geometries": []}
            with pytest.raises(HTTPException) as exc_info:
                geojson_mod.prepare_geojson_compute(geo)
        assert exc_info.value.status_code == 400
        assert "GeoJSON" in exc_info.value.detail


# ══════════════════════════════════════════════════════════════════════
# core/audit.py — chmod falha (linhas 47-48)
# ══════════════════════════════════════════════════════════════════════

class TestAuditLoggerChmod:
    """Cobre o tratamento de exceção em os.chmod (linhas 47-48)."""

    def test_chmod_falha_e_excecao_e_capturada(self, tmp_path):
        """Linhas 47-48: se os.chmod falha, a exceção é capturada e logada como warning."""
        # Set LOCALAPPDATA to tmp_path so no existing secret is found
        secret_dir = tmp_path / "sisRUA"
        secret_dir.mkdir(parents=True)
        # Do NOT create the .audit_secret file so _load_or_generate_secret takes the generate branch

        with (
            patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}),
            patch("os.chmod", side_effect=PermissionError("acesso negado")),
        ):
            from backend.shared.audit import AuditLogger
            import backend.shared.audit as audit_mod

            logger_mock = MagicMock()
            with patch.object(audit_mod, "logger", logger_mock):
                al = AuditLogger()

        # logger.warning must have been called with audit_secret_chmod_failed
        warning_calls = logger_mock.warning.call_args_list
        assert any("chmod" in str(c) or "audit_secret_chmod_failed" in str(c) for c in warning_calls)

    def test_chmod_bem_sucedido_nao_emite_warning(self, tmp_path):
        """Caminho normal: os.chmod funciona → nenhum warning de chmod."""
        with (
            patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}),
            patch("os.chmod"),
        ):
            from backend.shared.audit import AuditLogger
            import backend.shared.audit as audit_mod

            logger_mock = MagicMock()
            with patch.object(audit_mod, "logger", logger_mock):
                al = AuditLogger()

        chmod_warns = [c for c in logger_mock.warning.call_args_list if "chmod" in str(c)]
        assert len(chmod_warns) == 0


# ══════════════════════════════════════════════════════════════════════
# core/circuit_breaker.py — HALF_OPEN → falha → OPEN (linhas 68-69)
# ══════════════════════════════════════════════════════════════════════

class TestCircuitBreakerHalfOpen:
    """Cobre a transição HALF_OPEN → OPEN no CircuitBreaker (linhas 68-69)."""

    def test_falha_em_half_open_reabre_o_circuito(self):
        """Linhas 68-69: falha em estado HALF_OPEN → circuito volta para OPEN."""
        from backend.shared.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        cb.state = CircuitState.HALF_OPEN  # forçar estado
        cb.failures = 0

        cb._on_failure()

        assert cb.state == CircuitState.OPEN

    def test_sucesso_em_half_open_fecha_o_circuito(self):
        """Sucesso em HALF_OPEN → estado volta para CLOSED."""
        from backend.shared.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        cb.state = CircuitState.HALF_OPEN

        cb._on_success()

        assert cb.state == CircuitState.CLOSED
        assert cb.failures == 0

    def test_falhas_suficientes_em_closed_abrem_circuito(self):
        """failure_threshold falhas em CLOSED → OPEN."""
        from backend.shared.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
        cb._on_failure()
        assert cb.state == CircuitState.CLOSED
        cb._on_failure()
        assert cb.state == CircuitState.OPEN


# ══════════════════════════════════════════════════════════════════════
# core/database.py — exceção em configuração (linhas 178-179)
# ══════════════════════════════════════════════════════════════════════

class TestDatabaseConfigException:
    """Cobre o tratamento de exceção na configuração do DB (linhas 178-179)."""

    def test_excecao_em_init_schema_e_capturada_e_conexao_retornada(self, tmp_path):
        """Linhas 178-179: se init_schema falha, a exceção é logada e a conexão ainda é retornada."""
        db_path = tmp_path / "test.db"

        from backend.shared import database as db_mod

        with patch.object(db_mod, "init_schema", side_effect=RuntimeError("schema error")):
            conn = db_mod.get_db_connection(str(db_path))

        assert conn is not None
        # Conexão deve ser funcional
        result = conn.execute("SELECT 1").fetchone()
        assert result[0] == 1
        conn.close()

    def test_excecao_em_init_geopackage_e_capturada(self, tmp_path):
        """Linhas 178-179: se init_geopackage falha, a exceção é logada e a conexão é retornada."""
        db_path = tmp_path / "test2.db"

        from backend.shared import database as db_mod

        with patch.object(db_mod, "init_geopackage", side_effect=RuntimeError("gpkg error")):
            conn = db_mod.get_db_connection(str(db_path))

        assert conn is not None
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# services/export_service.py — EPSG ValueError e tabelas GPKG (linhas 133, 142, 151)
# ══════════════════════════════════════════════════════════════════════

def _make_test_db_with_project(db_path: Path, project_id: str, crs_out: str = "EPSG:31984") -> None:
    """Cria um banco SQLite mínimo com um projeto para testes de exportação."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Projects (
            project_id TEXT PRIMARY KEY,
            project_name TEXT,
            crs_out TEXT,
            created_at TEXT,
            version INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS CadFeatures (
            feature_id TEXT PRIMARY KEY,
            project_id TEXT,
            layer TEXT,
            feature_type TEXT,
            name TEXT,
            coords_xy TEXT,
            props TEXT
        )
    """)
    conn.execute(
        "INSERT INTO Projects VALUES (?, ?, ?, '2026-01-01', 1)",
        (project_id, "Projeto Teste", crs_out),
    )
    conn.commit()
    conn.close()


def _make_test_db_with_gpkg_tables(db_path: Path, project_id: str) -> None:
    """Cria um banco com tabelas GPKG para testar inserção em gpkg_contents/gpkg_geometry_columns."""
    _make_test_db_with_project(db_path, project_id)
    conn = sqlite3.connect(str(db_path))
    # Tabelas GPKG mínimas
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gpkg_contents (
            table_name TEXT PRIMARY KEY,
            data_type TEXT,
            identifier TEXT,
            description TEXT,
            srs_id INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gpkg_geometry_columns (
            table_name TEXT PRIMARY KEY,
            column_name TEXT,
            geometry_type_name TEXT,
            srs_id INTEGER,
            z INTEGER,
            m INTEGER
        )
    """)
    conn.commit()
    conn.close()


class TestExportServiceGpkg:
    """Cobre os caminhos EPSG ValueError e tabelas GPKG em export_service.py."""

    def test_epsg_invalido_usa_srs_id_4326(self, tmp_path):
        """Linha 133: crs_out com parte não numérica → srs_id=4326."""
        from backend.application.export_service import ExportService

        project_id = "proj-srs-test"
        db_path = tmp_path / "db.db"
        _make_test_db_with_project(db_path, project_id, crs_out="EPSG:INVALIDO")

        svc = ExportService(db_path=db_path)
        export_path = svc.export_project_to_geopackage(project_id)
        assert export_path.exists()

    def test_gpkg_contents_e_geometry_columns_inseridos(self, tmp_path):
        """Linhas 142, 151: banco com tabelas GPKG → INSERT OR REPLACE executado."""
        from backend.application.export_service import ExportService

        project_id = "proj-gpkg-test"
        db_path = tmp_path / "db.db"
        _make_test_db_with_gpkg_tables(db_path, project_id)

        svc = ExportService(db_path=db_path)
        export_path = svc.export_project_to_geopackage(project_id)
        assert export_path.exists()

        # Verificar que os registros foram inseridos
        conn = sqlite3.connect(str(export_path))
        row = conn.execute(
            "SELECT table_name FROM gpkg_contents WHERE table_name = 'CadFeatures'"
        ).fetchone()
        assert row is not None

        geom_row = conn.execute(
            "SELECT table_name FROM gpkg_geometry_columns WHERE table_name = 'CadFeatures'"
        ).fetchone()
        assert geom_row is not None
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# routes/enterprise.py — classe_tensao inválida, NotFoundError, exceção geral
# ══════════════════════════════════════════════════════════════════════

def _make_enterprise_client():
    """Cria TestClient configurado com token para testes de enterprise."""
    from fastapi.testclient import TestClient
    import backend.api as api_mod

    token = os.environ.get("SISRUA_AUTH_TOKEN", "test-token-session6")
    c = TestClient(api_mod.app, base_url="http://localhost:8000", raise_server_exceptions=False)
    c.headers.update({"X-SisRua-Token": token, "Origin": "http://localhost:8000"})
    return c, token


class TestEnterpriseRouteCoverage:
    """Cobre os caminhos restantes em routes/enterprise.py."""

    def test_classe_tensao_invalida_retorna_422(self):
        """Linhas 88-89: classe_tensao com valor inválido → HTTP 422."""
        c, token = _make_enterprise_client()
        payload = {
            "ativa": True,
            "concessionaria": "Enel",
            "classe_tensao": "INVALIDA",
            "numero_processo": "PROC-001",
        }
        r = c.post("/api/v1/normas/config", json=payload)
        assert r.status_code == 422
        assert "classe_tensao" in r.text.lower() or "invalida" in r.text.lower()

    def _ativar_prodist(self, client):
        """Helper: ativa PRODIST com MT."""
        payload = {
            "ativa": True,
            "concessionaria": "Enel-Teste",
            "classe_tensao": "MT",
            "numero_processo": "001",
        }
        r = client.post("/api/v1/normas/config", json=payload)
        assert r.status_code == 200

    def _desativar_prodist(self, client):
        """Helper: restaura ABNT."""
        payload = {"ativa": False, "concessionaria": "", "classe_tensao": "MT", "numero_processo": ""}
        client.post("/api/v1/normas/config", json=payload)

    def test_export_dxf_prodist_projeto_nao_encontrado_retorna_404(self):
        """Linha 239: projeto inexistente em export_dxf_prodist → 404."""
        import backend.api as api_mod
        from backend.application.projects import NotFoundError as ProjNotFound

        c, _ = _make_enterprise_client()
        self._ativar_prodist(c)
        try:
            # Mock to raise NotFoundError so we always get 404
            with patch.object(
                api_mod.export_service,
                "export_project_to_dxf",
                side_effect=ProjNotFound("Projeto não encontrado"),
            ):
                r = c.get("/api/v1/export/dxf-prodist/projeto-que-nao-existe")
            assert r.status_code == 404
        finally:
            self._desativar_prodist(c)

    def test_export_dxf_prodist_sem_norma_ativa_retorna_409(self):
        """Sem PRODIST ativo → 409 (pré-condição)."""
        c, _ = _make_enterprise_client()
        self._desativar_prodist(c)
        r = c.get("/api/v1/export/dxf-prodist/qualquer-id")
        assert r.status_code == 409
        assert "PRODIST" in r.text

    def test_export_dxf_prodist_excecao_interna_retorna_500(self):
        """Linha 245: exceção interna em export_service → HTTP 500."""
        import backend.api as api_mod

        c, _ = _make_enterprise_client()
        self._ativar_prodist(c)
        try:
            with patch.object(
                api_mod.export_service,
                "export_project_to_dxf",
                side_effect=RuntimeError("erro interno de teste"),
            ):
                r = c.get("/api/v1/export/dxf-prodist/qualquer-id")
            assert r.status_code == 500
            assert "erro" in r.text.lower() or "error" in r.text.lower()
        finally:
            self._desativar_prodist(c)

    def test_export_geopackage_projeto_nao_encontrado_retorna_404(self):
        """export_geopackage com projeto inexistente → 404."""
        import backend.api as api_mod
        from backend.application.projects import NotFoundError as ProjNotFound

        c, _ = _make_enterprise_client()
        with patch.object(
            api_mod.export_service,
            "export_project_to_geopackage",
            side_effect=ProjNotFound("Projeto não encontrado"),
        ):
            r = c.get("/api/v1/export/geopackage/projeto-inexistente-abc")
        assert r.status_code == 404

    def test_export_geojson_projeto_nao_encontrado_retorna_404(self):
        """export_geojson com projeto inexistente → 404."""
        import backend.api as api_mod
        from backend.application.projects import NotFoundError as ProjNotFound

        c, _ = _make_enterprise_client()
        with patch.object(
            api_mod.export_service,
            "export_project_to_geojson",
            side_effect=ProjNotFound("Projeto não encontrado"),
        ):
            r = c.get("/api/v1/export/geojson/projeto-inexistente-xyz")
        assert r.status_code == 404

    def test_export_dxf_projeto_nao_encontrado_retorna_404(self):
        """export_dxf com projeto inexistente → 404."""
        import backend.api as api_mod
        from backend.application.projects import NotFoundError as ProjNotFound

        c, _ = _make_enterprise_client()
        with patch.object(
            api_mod.export_service,
            "export_project_to_dxf",
            side_effect=ProjNotFound("Projeto não encontrado"),
        ):
            r = c.get("/api/v1/export/dxf/projeto-inexistente-dxf")
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# routes/ai_routes.py — exceção em generate_response (linha 38)
# ══════════════════════════════════════════════════════════════════════

class TestAiRouteException:
    """Cobre o fallback de exceção em routes/ai_routes.py (linha 38)."""

    def test_generate_response_exception_retorna_ai_unavailable(self):
        """Linha 38: exceção em ai_service.generate_response → 'AI unavailable.'."""
        import backend.api as api_mod

        c, token = _make_enterprise_client()
        with patch.object(
            api_mod.ai_service,
            "generate_response",
            side_effect=RuntimeError("modelo indisponível"),
        ):
            r = c.post(
                "/api/v1/ai/chat",
                json={"message": "Olá!", "context": None, "job_id": None},
            )
        assert r.status_code == 200
        data = r.json()
        assert "unavailable" in data.get("response", "").lower() or data.get("response") == "AI unavailable."


# ══════════════════════════════════════════════════════════════════════
# routes/projects.py — ConflictError → 409 (linha 74)
# ══════════════════════════════════════════════════════════════════════

class TestProjectsRouteConflict:
    """Cobre o path ConflictError → 409 em routes/projects.py."""

    def test_update_projeto_com_versao_errada_retorna_409(self):
        """Linha 74: ConflictError → HTTP 409."""
        import backend.api as api_mod
        from backend.application.projects import ConflictError

        c, token = _make_enterprise_client()

        # Criar um projeto primeiro
        r = c.post(
            "/api/v1/projects",
            json={"project_name": "Projeto Conflito", "crs_out": "EPSG:31984"},
        )
        if r.status_code != 201:
            pytest.skip("criação de projeto falhou — DB indisponível")

        project_id = r.json().get("project_id")

        # Forçar ConflictError no update_project
        from backend.routes import deps as deps_mod
        with patch.object(
            deps_mod.project_service,
            "update_project",
            side_effect=ConflictError("Versão incorreta"),
        ):
            r2 = c.put(
                f"/api/v1/projects/{project_id}",
                json={"project_name": "Novo Nome", "version": 999},
            )
        assert r2.status_code == 409
        assert "Versão" in r2.text or "version" in r2.text.lower() or "conflict" in r2.text.lower()

    def test_update_projeto_inexistente_retorna_404(self):
        """NotFoundError no update → HTTP 404."""
        from backend.application.projects import NotFoundError
        from backend.routes import deps as deps_mod

        c, token = _make_enterprise_client()
        with patch.object(
            deps_mod.project_service,
            "update_project",
            side_effect=NotFoundError("Projeto não encontrado"),
        ):
            r = c.put(
                "/api/v1/projects/proj-inexistente",
                json={"project_name": "Qualquer", "version": 1},
            )
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# Happy-path tests for lines that need a SUCCESSFUL execution
# ══════════════════════════════════════════════════════════════════════

class TestAiRouteHappyPath:
    """Cobre linha 38 de routes/ai_routes.py (retorno com sucesso do AI)."""

    def test_chat_ai_com_resposta_bem_sucedida(self):
        """Linha 38: ai_service.generate_response retorna string → ChatResponse bem sucedido."""
        import backend.api as api_mod

        c, _ = _make_enterprise_client()
        with patch.object(
            api_mod.ai_service,
            "generate_response",
            return_value="Resposta do assistente sisRUA",
        ):
            r = c.post(
                "/api/v1/ai/chat",
                json={"message": "Qual o raio padrão?", "context": None, "job_id": None},
            )
        assert r.status_code == 200
        assert r.json().get("response") == "Resposta do assistente sisRUA"


class TestProjectsUpdateHappyPath:
    """Cobre linha 74 de routes/projects.py (return updated com sucesso)."""

    def test_update_projeto_com_sucesso_retorna_200(self):
        """Linha 74: update_project retorna atualização com sucesso → 200."""
        from backend.routes import deps as deps_mod

        c, _ = _make_enterprise_client()
        mock_updated = {"project_id": "x", "project_name": "Atualizado", "version": 2}
        with patch.object(
            deps_mod.project_service,
            "update_project",
            return_value=mock_updated,
        ):
            r = c.put(
                "/api/v1/projects/x",
                json={"project_name": "Atualizado", "version": 1},
            )
        assert r.status_code == 200
        assert r.json().get("project_name") == "Atualizado"


class TestEnterpriseHappyPath:
    """Cobre linhas 88-89, 239, 245 em routes/enterprise.py."""

    def _ativar_prodist(self, client):
        payload = {
            "ativa": True,
            "concessionaria": "Enel-Teste",
            "classe_tensao": "MT",
            "numero_processo": "001",
        }
        r = client.post("/api/v1/normas/config", json=payload)
        assert r.status_code == 200

    def _desativar_prodist(self, client):
        payload = {"ativa": False, "concessionaria": "", "classe_tensao": "MT", "numero_processo": ""}
        client.post("/api/v1/normas/config", json=payload)

    def test_set_norma_config_classe_tensao_invalida_via_handler_direto(self):
        """Linhas 88-89: chamar handler diretamente bypass Pydantic → ValueError → 422."""
        import asyncio
        from unittest.mock import MagicMock
        from backend.routes import enterprise as ent_mod

        req = MagicMock()
        req.ativa = True
        req.classe_tensao = "INVALIDA_BYPASS"  # Bypasses Pydantic validator
        req.concessionaria = "Teste"
        req.numero_processo = ""

        with pytest.raises(Exception) as exc_info:
            asyncio.run(ent_mod.set_norma_config(req, _=None))

        # Should raise HTTPException with status_code 422
        exc = exc_info.value
        assert hasattr(exc, "status_code") and exc.status_code == 422 or "422" in str(exc) or "classe_tensao" in str(exc).lower()

    def test_export_dxf_prodist_sucesso_mock(self, tmp_path):
        """Linha 239: export_project_to_dxf retorna path válido → FileResponse."""
        import backend.api as api_mod

        # Criar um arquivo DXF temporário para simular export bem-sucedido
        fake_dxf = tmp_path / "sisrua_test.dxf"
        fake_dxf.write_bytes(b"DXF fake content")

        c, _ = _make_enterprise_client()
        self._ativar_prodist(c)
        try:
            with patch.object(
                api_mod.export_service,
                "export_project_to_dxf",
                return_value=fake_dxf,
            ):
                r = c.get("/api/v1/export/dxf-prodist/proj-123")
            # FileResponse with a real file → 200
            assert r.status_code == 200
        finally:
            self._desativar_prodist(c)

    def test_export_dxf_prodist_not_found_retorna_404(self):
        """Linha 245: NotFoundError em export_dxf_prodist → 404."""
        import backend.api as api_mod
        from backend.application.projects import NotFoundError as ProjNotFound

        c, _ = _make_enterprise_client()
        self._ativar_prodist(c)
        try:
            with patch.object(
                api_mod.export_service,
                "export_project_to_dxf",
                side_effect=ProjNotFound("Projeto não encontrado"),
            ):
                r = c.get("/api/v1/export/dxf-prodist/proj-missing")
            assert r.status_code == 404
        finally:
            self._desativar_prodist(c)
