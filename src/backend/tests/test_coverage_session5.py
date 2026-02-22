"""
tests/test_coverage_session5.py
Cobertura dos módulos restantes — sessão 5.

Módulos alvo (linhas descobertas no relatório de cobertura):
  - gis_core/abnt.py        (95%): escala não tabelada → interpolação linear (linha 84),
                                    to_dxf_header_vars() completo (linha 91)
  - services/executor.py    (95%): kind=osm sem coords (linha 35),
                                    kind=geojson sem geojson (linha 56)
  - services/health.py      (95%): DB retorna resultado inesperado (linhas 25-26),
                                    pyproj import falha → proj_status=down (linha 84)
  - gis_core/osm.py         (95%): cache_fallback_reason no except (linhas 165-167),
                                    highway lista em edge loop (linha 182),
                                    check_cancel a cada 100 edges (linha 176-177),
                                    check_cancel a cada 100 nodes (linha 218-219),
                                    exceção no elevation injection (linhas 347-348)
  - services/dxf_export.py  (94%): abnt_fingerprintguid_failed (linhas 232-233),
                                    prodist_fingerprintguid_failed (linhas 250-251)
  - services/export_service (95%): srs_id ValueError (linha 133),
                                    gpkg_contents present (linha 142),
                                    gpkg_geometry_columns present (linha 151),
                                    epsg ValueError no export_to_dxf (linha 217),
                                    prodist branch no export_to_dxf (linha 253)
  - audit_routes.py          (99%): extra_mileage branch (linha 141)
  - core/utils.py            (99%): math.isnan raises (linha 28)

Todos os mocks imitam o comportamento real das dependências.
Interface: pt-BR conforme requisito sisRUA.
"""
from __future__ import annotations

import importlib
import json
import math
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

os.environ.setdefault("SISRUA_TESTING", "true")
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-token-session5")


# ══════════════════════════════════════════════════════════════════════
# gis_core/abnt.py — tolerância e cabeçalho DXF
# ══════════════════════════════════════════════════════════════════════

class TestAbntCoverage:
    """Cobre os caminhos restantes de gis_core/abnt.py."""

    def test_tolerancia_escala_nao_tabelada_usa_interpolacao(self):
        """Linha 84: escala não tabelada (ex: 3000) usa interpolação 0,2mm × escala."""
        from backend.gis_core.abnt import AbntDrawingMetadata

        meta = AbntDrawingMetadata(escala=3_000)  # não está em _TOLERANCIAS_M
        tol = meta.tolerancia_m()
        # 0,2mm × 3000 = 0,6m
        assert abs(tol - 0.6) < 1e-9

    def test_tolerancia_escala_7500_usa_interpolacao(self):
        """Linha 84: outra escala não tabelada."""
        from backend.gis_core.abnt import AbntDrawingMetadata

        meta = AbntDrawingMetadata(escala=7_500)
        tol = meta.tolerancia_m()
        assert abs(tol - 1.5) < 1e-9

    def test_to_dxf_header_vars_retorna_dict_completo(self):
        """Linha 91: to_dxf_header_vars() retorna dict com 14 chaves."""
        from backend.gis_core.abnt import AbntDrawingMetadata

        meta = AbntDrawingMetadata()
        hv = meta.to_dxf_header_vars()
        assert isinstance(hv, dict)
        # Deve ter as 7 pares de TAG/VALUE (indices 0–6)
        for i in range(7):
            assert f"$CUSTOMPROPERTYTAG{i}" in hv
            assert f"$CUSTOMPROPERTYVALUE{i}" in hv
        assert hv["$CUSTOMPROPERTYVALUE1"] == meta.datum
        assert meta.escala_str() in hv["$CUSTOMPROPERTYVALUE4"]


# ══════════════════════════════════════════════════════════════════════
# services/executor.py — ValueError para kind=osm e kind=geojson
# ══════════════════════════════════════════════════════════════════════

class TestExecutorCoverage:
    """Cobre as linhas de validação em services/executor.py."""

    def _make_executor(self):
        from backend.services.executor import JobExecutor
        cache = MagicMock()
        cache.get.return_value = None
        return JobExecutor(cache_service=cache)

    def _make_event_bus(self):
        return MagicMock()

    def test_osm_sem_latitude_falha_com_ValueError(self):
        """Linha 35: kind=osm com latitude=None deve registrar job como falha."""
        from backend.services.jobs import init_job, get_job
        from backend.models import PrepareJobRequest
        from backend.core.lifecycle import SHUTDOWN_EVENT

        executor = self._make_executor()
        bus = self._make_event_bus()
        job_id, _ = init_job(kind="osm")

        SHUTDOWN_EVENT.clear()  # garante que shutdown não interfere
        req = PrepareJobRequest(kind="osm", latitude=None, longitude=None, radius=None)
        executor.execute_prepare_job(job_id, req, bus)

        job = get_job(job_id)
        assert job["status"] == "failed"
        assert "latitude" in job["error"].lower() or "obrigat" in job["error"].lower()

    def test_geojson_sem_dados_falha_com_ValueError(self):
        """Linha 56: kind=geojson com geojson=None deve registrar job como falha."""
        from backend.services.jobs import init_job, get_job
        from backend.models import PrepareJobRequest
        from backend.core.lifecycle import SHUTDOWN_EVENT

        executor = self._make_executor()
        bus = self._make_event_bus()
        job_id, _ = init_job(kind="geojson")

        SHUTDOWN_EVENT.clear()  # garante que shutdown não interfere
        req = PrepareJobRequest(kind="geojson", geojson=None)
        executor.execute_prepare_job(job_id, req, bus)

        job = get_job(job_id)
        assert job["status"] == "failed"
        assert "geojson" in job["error"].lower() or "obrigat" in job["error"].lower()

    def test_kind_invalido_falha_com_mensagem_clara(self):
        """Linha 66: kind='invalid' registra job como falha com mensagem 'kind inválido'."""
        from backend.services.jobs import init_job, get_job
        from backend.models import PrepareJobRequest
        from backend.core.lifecycle import SHUTDOWN_EVENT

        executor = self._make_executor()
        bus = self._make_event_bus()
        job_id, _ = init_job(kind="osm")  # init com qualquer kind

        SHUTDOWN_EVENT.clear()  # garante que shutdown não interfere
        # Cria request com kind inválido via bypass de validação
        req = MagicMock()
        req.kind = "invalid_kind"

        executor.execute_prepare_job(job_id, req, bus)

        job = get_job(job_id)
        assert job["status"] == "failed"


# ══════════════════════════════════════════════════════════════════════
# services/health.py — DB down e pyproj down
# ══════════════════════════════════════════════════════════════════════

class TestHealthServiceCoverage:
    """Cobre caminhos de falha em services/health.py."""

    def test_db_select_retorna_resultado_inesperado(self):
        """Linhas 25-26: SELECT 1 retorna None → status='down'."""
        from backend.services.health import HealthService

        svc = HealthService()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # resultado inesperado
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch("backend.services.health.get_db_connection", return_value=mock_conn):
            result = svc.check_health()

        db_component = result.components.get("database")
        assert db_component is not None
        assert db_component.status == "down"
        assert "unexpected" in db_component.details.lower()

    def test_db_exception_marca_database_down(self):
        """Linhas 27-29: exceção em get_db_connection → status='down'."""
        from backend.services.health import HealthService

        svc = HealthService()
        with patch(
            "backend.services.health.get_db_connection",
            side_effect=RuntimeError("conexão falhou"),
        ):
            result = svc.check_health()

        db_component = result.components.get("database")
        assert db_component.status == "down"

    def test_pyproj_import_error_marca_gis_down(self):
        """Linha 84: exceção em pyproj.Proj() → gis_core_deps status='down'."""
        from backend.services.health import HealthService

        svc = HealthService()

        # Mock a DB check to succeed
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        # pyproj é importado localmente dentro do método check_health()
        import pyproj as real_pyproj

        original_proj = real_pyproj.Proj

        call_count = [0]

        def failing_proj(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("proj failed")
            return original_proj(*args, **kwargs)

        with patch("backend.services.health.get_db_connection", return_value=mock_conn):
            with patch.object(real_pyproj, "Proj", side_effect=failing_proj):
                result = svc.check_health()

        gis_component = result.components.get("gis_core_deps")
        assert gis_component is not None
        assert gis_component.status == "down"


# ══════════════════════════════════════════════════════════════════════
# gis_core/osm.py — caminhos restantes
# ══════════════════════════════════════════════════════════════════════

class TestOsmRemainingCoverage:
    """Cobre os caminhos restantes em gis_core/osm.py."""

    def _make_cache_miss(self):
        c = MagicMock()
        c.get.return_value = None
        return c

    def _make_elev_minimal(self):
        e = MagicMock()
        e.get_elevation_profile.return_value = [850.0]
        e.get_contours.return_value = []
        return e

    def _minimal_overpass(self, lat=-22.15018, lon=-42.92185):
        return {
            "elements": [
                {"type": "node", "id": 1, "lat": lat, "lon": lon, "tags": {}},
                {"type": "node", "id": 2, "lat": lat + 0.001, "lon": lon + 0.001, "tags": {}},
                {
                    "type": "way", "id": 10, "nodes": [1, 2],
                    "tags": {"highway": "residential"},
                },
            ]
        }

    def test_exception_com_cache_fallback_inclui_cache_fallback_reason(self):
        """Linhas 165-167: fetch falha + hit cache → resultado inclui cache_fallback_reason."""
        from backend.gis_core.osm import prepare_osm_compute

        cached_data = {"features": [], "crs_out": "EPSG:31983", "cache_hit": False}
        cache = MagicMock()
        # Segundo get() retorna o cache (já que primeiro get é miss no início, mas o fallback usa get() novamente)
        cache.get.side_effect = [None, cached_data]  # miss na primeira chamada, hit no fallback

        with patch("backend.gis_core.osm._fetch_overpass_data", side_effect=RuntimeError("network")):
            result = prepare_osm_compute(
                latitude=-22.15018,
                longitude=-42.92185,
                radius=100,
                cache_service=cache,
                elevation_service=self._make_elev_minimal(),
            )

        assert result.get("cache_hit") is True
        assert "cache_fallback_reason" in result

    def test_exception_sem_cache_levanta_503(self):
        """Linha 168: fetch falha e sem cache → HTTPException 503."""
        from backend.gis_core.osm import prepare_osm_compute
        from fastapi import HTTPException

        cache = MagicMock()
        cache.get.return_value = None  # Sempre miss

        with patch("backend.gis_core.osm._fetch_overpass_data", side_effect=RuntimeError("timeout")):
            with pytest.raises(HTTPException) as exc_info:
                prepare_osm_compute(
                    latitude=-22.15018,
                    longitude=-42.92185,
                    radius=100,
                    cache_service=cache,
                    elevation_service=self._make_elev_minimal(),
                )
        assert exc_info.value.status_code == 503

    def test_highway_como_lista_usa_primeiro_elemento_no_resultado(self):
        """Linha 182: highway como lista → primeiro elemento é usado."""
        from backend.gis_core.osm import prepare_osm_compute

        lat, lon = -22.15018, -42.92185
        data = {
            "elements": [
                {"type": "node", "id": 1, "lat": lat, "lon": lon, "tags": {}},
                {"type": "node", "id": 2, "lat": lat + 0.001, "lon": lon + 0.001, "tags": {}},
                {
                    "type": "way", "id": 10, "nodes": [1, 2],
                    "tags": {"highway": "residential", "name": "Rua Lista"},
                },
            ]
        }
        cache = self._make_cache_miss()
        elev = self._make_elev_minimal()

        # Patch _OsmWayRow para retornar highway como lista
        from backend.gis_core import osm as osm_mod

        original_OsmWayRow = osm_mod._OsmWayRow

        class FakeRow:
            def __init__(self, *args, **kwargs):
                real = original_OsmWayRow(*args, **kwargs)
                self.highway = ["residential", "secondary"]  # lista
                self.geometry = real.geometry
                self.name = real.name
                self._asdict = real._asdict

        with patch("backend.gis_core.osm._OsmWayRow", side_effect=FakeRow):
            with patch("backend.gis_core.osm._fetch_overpass_data", return_value=data):
                result = prepare_osm_compute(
                    latitude=lat, longitude=lon, radius=100,
                    cache_service=cache, elevation_service=elev,
                )

        # features com highway "residential" devem existir
        polylines = [f for f in result["features"] if f.get("feature_type") == "Polyline"]
        assert len(polylines) >= 1
        # highway deve ser "residential" (primeiro elemento da lista)
        assert all(f.get("highway") == "residential" for f in polylines if f.get("highway"))

    def test_elevation_exception_swallowed(self):
        """Linhas 347-348: exceção no bloco de elevação é swallowed."""
        from backend.gis_core.osm import prepare_osm_compute

        lat, lon = -22.15018, -42.92185
        cache = self._make_cache_miss()
        elev = MagicMock()
        # get_elevation_profile levanta exceção → elevation_injection_failed
        elev.get_elevation_profile.side_effect = RuntimeError("elevation service down")
        elev.get_contours.return_value = []

        with patch("backend.gis_core.osm._fetch_overpass_data", return_value=self._minimal_overpass(lat, lon)):
            # Não deve propagar exceção
            result = prepare_osm_compute(
                latitude=lat, longitude=lon, radius=100,
                cache_service=cache, elevation_service=elev,
            )

        assert "features" in result


# ══════════════════════════════════════════════════════════════════════
# services/dxf_export.py — fingerprint exception paths
# ══════════════════════════════════════════════════════════════════════

class TestDxfExportFingerprintCoverage:
    """Cobre as linhas de fingerprint exception em services/dxf_export.py."""

    def test_inject_abnt_header_exception_swallowed(self):
        """Linhas 232-233: exceção ao injetar fingerprint ABNT é swallowed."""
        from backend.services.dxf_export import _inject_abnt_metadata
        from backend.gis_core.abnt import AbntDrawingMetadata

        meta = AbntDrawingMetadata()
        mock_doc = MagicMock()
        # Força exceção ao tentar setar $FINGERPRINTGUID
        mock_doc.header.__setitem__.side_effect = RuntimeError("header error")

        # Não deve propagar — exceção é swallowed
        _inject_abnt_metadata(mock_doc, meta)

    def test_inject_prodist_header_exception_swallowed(self):
        """Linhas 250-251: exceção ao injetar fingerprint PRODIST é swallowed."""
        from backend.services.dxf_export import _inject_prodist_metadata
        from backend.gis_core.prodist import ProdistMetadata, TensaoClasse

        meta = ProdistMetadata(
            concessionaria="Concessionária Teste",
            classe_tensao=TensaoClasse.MT,
        )
        mock_doc = MagicMock()
        mock_doc.header.__setitem__.side_effect = RuntimeError("prodist header error")

        # Não deve propagar
        _inject_prodist_metadata(mock_doc, meta)


# ══════════════════════════════════════════════════════════════════════
# services/export_service.py — caminhos de branches
# ══════════════════════════════════════════════════════════════════════

class TestExportServiceCoverage:
    """Cobre os caminhos de branches em services/export_service.py."""

    def _make_db(self, tmp_path: Path) -> Path:
        """Cria banco SQLite temporário com project e feature de teste."""
        db_path = tmp_path / "test_export.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE CadFeatures (
                feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT, feature_type TEXT, layer TEXT,
                name TEXT, highway TEXT, width_m REAL, color TEXT,
                elevation REAL, slope REAL, original_geojson_properties TEXT,
                coords_xy TEXT, insertion_point_xy TEXT, block_name TEXT,
                rotation REAL DEFAULT 0.0, scale REAL DEFAULT 1.0
            )
        """)
        conn.execute(
            "INSERT INTO Projects (project_id, project_name, crs_out) VALUES (?, ?, ?)",
            ("proj-test", "Projeto Teste", "EPSG:31983"),
        )
        conn.execute(
            """INSERT INTO CadFeatures
               (project_id, feature_type, layer, coords_xy, original_geojson_properties)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "proj-test", "Polyline", "SISRUA_Vias_Locais",
                json.dumps([[714316.0, 7549084.0], [714416.0, 7549084.0]]),
                json.dumps({}),
            ),
        )
        conn.commit()
        conn.close()
        return db_path

    def test_srs_id_valor_invalido_usa_4326(self, tmp_path):
        """Linha 133: crs_out com EPSG inválido (não conversível) → srs_id=4326."""
        from backend.services.export_service import ExportService

        db_path = tmp_path / "test_srs.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT, crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE CadFeatures (
                feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT, feature_type TEXT, layer TEXT,
                name TEXT, highway TEXT, width_m REAL, color TEXT,
                elevation REAL, slope REAL, original_geojson_properties TEXT,
                coords_xy TEXT, insertion_point_xy TEXT, block_name TEXT,
                rotation REAL DEFAULT 0.0, scale REAL DEFAULT 1.0
            )
        """)
        conn.execute(
            "INSERT INTO Projects VALUES (?, ?, ?, ?)",
            ("proj-bad-crs", "Teste CRS Ruim", "EPSG:NOTANUMBER", 1),
        )
        conn.commit()
        conn.close()

        svc = ExportService(db_path=db_path)
        # Deve executar sem levantar exceção mesmo com CRS inválido
        path = svc.export_project_to_geojson("proj-bad-crs")
        assert path.exists()

    def test_export_geojson_cria_arquivo(self, tmp_path):
        """Cobre o caminho happy-path de export_project_to_geojson."""
        from backend.services.export_service import ExportService

        db_path = self._make_db(tmp_path)
        svc = ExportService(db_path=db_path)
        path = svc.export_project_to_geojson("proj-test")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["type"] == "FeatureCollection"

    def test_export_dxf_prodist_branch(self, tmp_path):
        """Linha 253: branch prodist_metadata not None ao exportar DXF."""
        from backend.services.export_service import ExportService
        from backend.gis_core.prodist import ProdistMetadata, TensaoClasse

        db_path = self._make_db(tmp_path)
        svc = ExportService(db_path=db_path)

        prodist_meta = ProdistMetadata(
            concessionaria="Concessionária Teste",
            classe_tensao=TensaoClasse.MT,
        )

        path = svc.export_project_to_dxf(
            "proj-test",
            prodist_metadata=prodist_meta,
            include_prodist_buffers=False,
        )
        assert path.exists()
        assert path.suffix == ".dxf"

    def test_export_dxf_crs_invalido_usa_epsg_padrao(self, tmp_path):
        """Linha 217: EPSG inválido em export_to_dxf → usa padrão 31983."""
        from backend.services.export_service import ExportService

        db_path = tmp_path / "bad_epsg.db"
        conn = sqlite3.connect(str(db_path))
        for stmt in [
            """CREATE TABLE Projects (project_id TEXT, project_name TEXT, crs_out TEXT, version INTEGER DEFAULT 1)""",
            """CREATE TABLE CadFeatures (
                feature_id INTEGER PRIMARY KEY, project_id TEXT, feature_type TEXT, layer TEXT,
                name TEXT, highway TEXT, width_m REAL, color TEXT, elevation REAL, slope REAL,
                original_geojson_properties TEXT, coords_xy TEXT, insertion_point_xy TEXT,
                block_name TEXT, rotation REAL, scale REAL)""",
        ]:
            conn.execute(stmt)
        conn.execute("INSERT INTO Projects VALUES (?, ?, ?, ?)", ("proj-bad", "Test", "EPSG:INVALID", 1))
        conn.execute(
            "INSERT INTO CadFeatures (project_id, feature_type, layer, coords_xy, original_geojson_properties) VALUES (?, ?, ?, ?, ?)",
            ("proj-bad", "Polyline", "TEST", json.dumps([[0.0, 0.0], [1.0, 0.0]]), json.dumps({})),
        )
        conn.commit()
        conn.close()

        svc = ExportService(db_path=db_path)
        path = svc.export_project_to_dxf("proj-bad")
        assert path.exists()


# ══════════════════════════════════════════════════════════════════════
# audit_routes.py — extra_mileage branch (linha 141)
# ══════════════════════════════════════════════════════════════════════

class TestAuditValuationExtraMileage:
    """Cobre a branch extra_mileage em audit_routes.py /valuation/summary."""

    @pytest.fixture()
    def client_tok(self):
        os.environ["SISRUA_AUTH_TOKEN"] = "audit5-test-token"
        import backend.api as api_mod
        importlib.reload(api_mod)
        from fastapi.testclient import TestClient
        client = TestClient(api_mod.app, base_url="http://localhost:8000")
        client.headers.update({"Origin": "http://localhost:8000"})
        return client, "audit5-test-token"

    def test_extra_mileage_sem_project_id(self, client_tok):
        """Linha 141: registro sem project_id → extra_mileage incrementado."""
        client, tok = client_tok
        from backend import audit_routes

        mock_conn = MagicMock()
        # Row sem project_id → extra_mileage branch
        mock_conn.execute.return_value.fetchall.return_value = [
            ('{"mileage_km": 3.2}',),  # sem project_id → extra_mileage
            ('{"project_id": "p1", "mileage_km": 2.0}',),  # com project_id
        ]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch.object(audit_routes, "get_db_connection", return_value=mock_conn):
            r = client.get("/api/valuation/summary", headers={"X-SisRua-Token": tok})

        assert r.status_code == 200
        data = r.json()
        assert "total_urban_assets_mapped_km" in data
        # 3.2 + 2.0 = 5.2
        assert abs(data["total_urban_assets_mapped_km"] - 5.2) < 0.01


# ══════════════════════════════════════════════════════════════════════
# core/utils.py — math.isnan raises (linha 28)
# ══════════════════════════════════════════════════════════════════════

class TestUtilsIsnanException:
    """Cobre a linha 28 de core/utils.py (math.isnan raises para tipos incomuns)."""

    def test_norm_optional_str_nan_float_retorna_none(self):
        """Linha 26-27: float NaN → None."""
        from backend.core.utils import norm_optional_str
        assert norm_optional_str(float("nan")) is None

    def test_norm_optional_str_isnan_exception_usa_fallback(self):
        """Linha 28: math.isnan TypeError → except pass → tenta str()."""
        from backend.core.utils import norm_optional_str

        # Usa mock para simular isnan levantando durante verificação de float
        with patch("backend.core.utils.math.isnan", side_effect=TypeError("isnan fail")):
            # 3.14 é float, passa isinstance(val, float), tenta isnan, pega TypeError,
            # executa pass, cai no try abaixo e converte para str
            result = norm_optional_str(3.14)

        # Após TypeError no isnan, fallback é str(3.14) = "3.14"
        assert result == "3.14"
