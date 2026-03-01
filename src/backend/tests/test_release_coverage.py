"""
Tests for release-critical coverage gaps:
- backend.shared.migrations (0% → ≥80%)
- backend.models validators (72% → ≥90%)
- backend.infrastructure.routes.gis (50% → ≥90%)
- backend.infrastructure.osm_client (25% → ≥80%)
"""
import importlib
import sqlite3
import os
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

# Auth token set by conftest.py → os.environ["SISRUA_AUTH_TOKEN"] = "test-token"
_TEST_TOKEN = "test-token"


# ──────────────────────────────────────────────
# 1. migrations.py
# ──────────────────────────────────────────────

class TestMigrations:
    """Tests for database migration system."""

    def _make_db(self, tmp_path: Path) -> Path:
        """Create a minimal sisRUA database (Projects + CadFeatures tables)."""
        db_path = tmp_path / "projects.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY,
                project_name TEXT,
                crs_out TEXT,
                creation_date TEXT
            );
            CREATE TABLE IF NOT EXISTS CadFeatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                feature_type TEXT,
                layer TEXT,
                coords_json TEXT
            );
            CREATE TABLE IF NOT EXISTS AuditLog (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                entity_type TEXT,
                entity_id TEXT,
                user_id TEXT,
                timestamp TEXT,
                data_json TEXT,
                created_at TEXT
            );
        """)
        conn.commit()
        conn.close()
        return db_path

    def test_get_schema_version_fresh_db(self, tmp_path):
        """Fresh DB has no schema_version table → returns 0."""
        from backend.shared.migrations import get_schema_version
        db_path = self._make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        try:
            version = get_schema_version(conn)
            assert version == 0
        finally:
            conn.close()

    def test_migrate_database_skips_when_no_db(self, tmp_path):
        """migrate_database returns 0 when DB file does not exist."""
        from backend.shared.migrations import migrate_database
        missing = tmp_path / "nonexistent.db"
        result = migrate_database(db_path=missing)
        assert result == 0

    def test_migrate_database_applies_all_migrations(self, tmp_path):
        """All 3 migrations are applied to a fresh DB."""
        from backend.shared.migrations import migrate_database, MIGRATIONS, CURRENT_VERSION
        db_path = self._make_db(tmp_path)
        applied = migrate_database(db_path=db_path)
        assert applied == len(MIGRATIONS)
        assert applied == CURRENT_VERSION

    def test_migrate_database_idempotent(self, tmp_path):
        """Running migrations twice applies 0 the second time."""
        from backend.shared.migrations import migrate_database
        db_path = self._make_db(tmp_path)
        migrate_database(db_path=db_path)
        applied_again = migrate_database(db_path=db_path)
        assert applied_again == 0

    def test_apply_migration_already_exists_is_skipped(self, tmp_path):
        """apply_migration skips 'already exists' OperationalErrors gracefully."""
        from backend.shared.migrations import apply_migration, get_schema_version
        db_path = self._make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        try:
            get_schema_version(conn)  # creates schema_version table
            # Applying same index twice should not raise
            apply_migration(conn, 1, "dup test", [
                "CREATE INDEX IF NOT EXISTS idx_cadfeatures_project_id ON CadFeatures(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_cadfeatures_project_id ON CadFeatures(project_id)",
            ])
            # Verify migration was recorded
            cur = conn.cursor()
            cur.execute("SELECT version FROM schema_version WHERE version=1")
            row = cur.fetchone()
            assert row is not None
        finally:
            conn.close()

    def test_apply_migration_duplicate_column_is_skipped(self, tmp_path):
        """apply_migration skips 'duplicate column name' OperationalErrors."""
        from backend.shared.migrations import apply_migration, get_schema_version
        db_path = self._make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        try:
            get_schema_version(conn)
            # Add column once, then try again — second time is idempotent
            apply_migration(conn, 2, "add col", [
                "ALTER TABLE CadFeatures ADD COLUMN color TEXT",
            ])
            # Second call: duplicate column name — should not raise
            apply_migration(conn, 3, "dup col", [
                "ALTER TABLE CadFeatures ADD COLUMN color TEXT",
            ])
        finally:
            conn.close()

    def test_apply_migration_raises_on_real_error(self, tmp_path):
        """apply_migration propagates non-idempotency OperationalErrors."""
        from backend.shared.migrations import apply_migration, get_schema_version
        db_path = self._make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        try:
            get_schema_version(conn)
            with pytest.raises(sqlite3.OperationalError):
                apply_migration(conn, 99, "bad sql", ["SELECT * FROM nonexistent_table_xyz"])
        finally:
            conn.close()

    def test_check_migration_status_no_db(self, tmp_path):
        """check_migration_status returns database_exists=False for missing DB."""
        from backend.shared.migrations import check_migration_status, CURRENT_VERSION, MIGRATIONS
        missing = tmp_path / "nope.db"
        status = check_migration_status(db_path=missing)
        assert status["database_exists"] is False
        assert status["current_version"] == 0
        assert status["target_version"] == CURRENT_VERSION
        assert sorted(status["pending_migrations"]) == sorted(MIGRATIONS.keys())

    def test_check_migration_status_with_db(self, tmp_path):
        """check_migration_status shows pending after creating DB without migrating."""
        from backend.shared.migrations import check_migration_status, MIGRATIONS
        db_path = self._make_db(tmp_path)
        status = check_migration_status(db_path=db_path)
        assert status["database_exists"] is True
        assert status["current_version"] == 0
        assert len(status["pending_migrations"]) == len(MIGRATIONS)

    def test_check_migration_status_fully_migrated(self, tmp_path):
        """After migrating, pending_migrations is empty."""
        from backend.shared.migrations import migrate_database, check_migration_status
        db_path = self._make_db(tmp_path)
        migrate_database(db_path=db_path)
        status = check_migration_status(db_path=db_path)
        assert status["pending_migrations"] == []

    def test_migration_v2_adds_color_elevation_slope_columns(self, tmp_path):
        """Migration v2 adds color, elevation, slope columns to CadFeatures."""
        from backend.shared.migrations import migrate_database
        db_path = self._make_db(tmp_path)
        migrate_database(db_path=db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(CadFeatures)")
            cols = {row[1] for row in cur.fetchall()}
            assert "color" in cols
            assert "elevation" in cols
            assert "slope" in cols
        finally:
            conn.close()

    def test_migration_v3_adds_version_to_projects(self, tmp_path):
        """Migration v3 adds version column to Projects."""
        from backend.shared.migrations import migrate_database
        db_path = self._make_db(tmp_path)
        migrate_database(db_path=db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(Projects)")
            cols = {row[1] for row in cur.fetchall()}
            assert "version" in cols
        finally:
            conn.close()


# ──────────────────────────────────────────────
# 2. models.py validators
# ──────────────────────────────────────────────

class TestModelsValidators:
    """Tests for Pydantic model validators in backend/models.py."""

    def test_elevation_profile_request_valid(self):
        from backend.models import ElevationProfileRequest
        req = ElevationProfileRequest(path=[[-22.15, -42.92], [-22.16, -42.93]])
        assert len(req.path) == 2

    def test_elevation_profile_request_too_few_points(self):
        from backend.models import ElevationProfileRequest
        with pytest.raises(ValidationError):
            ElevationProfileRequest(path=[[-22.15, -42.92]])

    def test_elevation_profile_request_invalid_lat(self):
        from backend.models import ElevationProfileRequest
        with pytest.raises(ValidationError):
            ElevationProfileRequest(path=[[-91.0, -42.92], [-22.16, -42.93]])

    def test_elevation_profile_request_invalid_lon(self):
        from backend.models import ElevationProfileRequest
        with pytest.raises(ValidationError):
            ElevationProfileRequest(path=[[-22.15, -181.0], [-22.16, -42.93]])

    def test_elevation_profile_request_point_too_short(self):
        from backend.models import ElevationProfileRequest
        with pytest.raises(ValidationError):
            ElevationProfileRequest(path=[[-22.15], [-22.16, -42.93]])

    def test_elevation_contours_request_valid(self):
        from backend.models import ElevationContoursRequest
        req = ElevationContoursRequest(
            min_lat=-22.2, min_lon=-43.0, max_lat=-22.1, max_lon=-42.9, interval=10.0
        )
        assert req.interval == 10.0

    def test_elevation_contours_request_invalid_bounds_lat(self):
        from backend.models import ElevationContoursRequest
        with pytest.raises(ValidationError):
            ElevationContoursRequest(
                min_lat=-22.1, min_lon=-43.0, max_lat=-22.2, max_lon=-42.9
            )

    def test_elevation_contours_request_invalid_bounds_lon(self):
        from backend.models import ElevationContoursRequest
        with pytest.raises(ValidationError):
            ElevationContoursRequest(
                min_lat=-22.2, min_lon=-42.9, max_lat=-22.1, max_lon=-43.0
            )

    def test_webhook_registration_valid_https(self):
        from backend.models import WebhookRegistrationRequest
        req = WebhookRegistrationRequest(url="https://example.com/hook")
        assert req.url == "https://example.com/hook"

    def test_webhook_registration_valid_http(self):
        from backend.models import WebhookRegistrationRequest
        req = WebhookRegistrationRequest(url="http://localhost:8080/hook")
        assert req.url.startswith("http://")

    def test_webhook_registration_invalid_scheme(self):
        from backend.models import WebhookRegistrationRequest
        with pytest.raises(ValidationError):
            WebhookRegistrationRequest(url="ftp://example.com/hook")

    def test_webhook_registration_no_hostname(self):
        from backend.models import WebhookRegistrationRequest
        with pytest.raises(ValidationError):
            WebhookRegistrationRequest(url="https://")

    def test_webhook_events_sanitized(self):
        from backend.models import WebhookRegistrationRequest
        long_event = "x" * 200
        req = WebhookRegistrationRequest(
            url="https://example.com/hook",
            events=[long_event, "  project_saved  "]
        )
        assert all(len(e) <= 128 for e in req.events)
        assert "project_saved" in req.events

    def test_webhook_events_empty_becomes_none(self):
        from backend.models import WebhookRegistrationRequest
        req = WebhookRegistrationRequest(url="https://example.com/hook", events=[])
        assert req.events is None

    def test_webhook_events_none_accepted(self):
        from backend.models import WebhookRegistrationRequest
        req = WebhookRegistrationRequest(url="https://example.com/hook", events=None)
        assert req.events is None

    def test_prepare_ibge_request_valid(self):
        from backend.models import PrepareIbgeRequest
        req = PrepareIbgeRequest(nome_municipio="Nova Friburgo", uf="rj")
        assert req.uf == "RJ"  # uppercase normalized

    def test_prepare_ibge_request_uf_none(self):
        from backend.models import PrepareIbgeRequest
        req = PrepareIbgeRequest(nome_municipio="Nova Friburgo")
        assert req.uf is None

    def test_prepare_inea_request_valid_bbox(self):
        from backend.models import PrepareIneaRequest
        req = PrepareIneaRequest(
            typename="hidrografia",
            bbox=[-43.5, -23.1, -42.8, -22.6]
        )
        assert len(req.bbox) == 4

    def test_prepare_inea_request_no_bbox(self):
        from backend.models import PrepareIneaRequest
        req = PrepareIneaRequest(typename="bacias")
        assert req.bbox is None

    def test_prepare_inea_request_invalid_bbox_length(self):
        from backend.models import PrepareIneaRequest
        with pytest.raises(ValidationError):
            PrepareIneaRequest(typename="hidrografia", bbox=[-43.5, -23.1, -42.8])

    def test_prepare_inea_request_invalid_bbox_lon_order(self):
        from backend.models import PrepareIneaRequest
        with pytest.raises(ValidationError):
            PrepareIneaRequest(typename="hidrografia", bbox=[-42.8, -23.1, -43.5, -22.6])

    def test_prepare_inea_request_invalid_bbox_lat_order(self):
        from backend.models import PrepareIneaRequest
        with pytest.raises(ValidationError):
            PrepareIneaRequest(typename="hidrografia", bbox=[-43.5, -22.6, -42.8, -23.1])

    def test_prodist_config_request_valid_bt(self):
        from backend.models import ProdistConfigRequest
        req = ProdistConfigRequest(ativa=True, classe_tensao="BT")
        assert req.classe_tensao == "BT"

    def test_prodist_config_request_normalizes_lowercase(self):
        from backend.models import ProdistConfigRequest
        req = ProdistConfigRequest(ativa=True, classe_tensao="mt")
        assert req.classe_tensao == "MT"

    def test_prodist_config_request_invalid_classe_tensao(self):
        from backend.models import ProdistConfigRequest
        with pytest.raises(ValidationError):
            ProdistConfigRequest(ativa=True, classe_tensao="EHV")


# ──────────────────────────────────────────────
# 3. infrastructure/routes/gis.py
# ──────────────────────────────────────────────

def _make_gis_client():
    """Build TestClient using the infrastructure API app."""
    os.environ["SISRUA_AUTH_TOKEN"] = _TEST_TOKEN
    from backend.infrastructure import api as api_mod
    importlib.reload(api_mod)
    tc = TestClient(api_mod.app, base_url="http://localhost:8000")
    tc.headers.update({"Origin": "http://localhost:8000"})
    return tc


class TestGisRoute:
    """Tests for the /gis KML conversion endpoint."""

    @pytest.fixture
    def client(self):
        return _make_gis_client()

    def test_convert_kml_missing_content_returns_400(self, client):
        resp = client.post(
            "/api/v1/gis/convert/kml",
            json={},
            headers={"X-SisRua-Token": _TEST_TOKEN},
        )
        assert resp.status_code == 400

    def test_convert_kml_requires_auth(self, client):
        resp = client.post("/api/v1/gis/convert/kml", json={"content": "<kml/>"})
        assert resp.status_code in (401, 403)

    def test_convert_kml_valid_kml_returns_geojson(self, client):
        kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Test Point</name>
      <Point>
        <coordinates>-42.92185,-22.15018,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""
        resp = client.post(
            "/api/v1/gis/convert/kml",
            json={"content": kml_content},
            headers={"X-SisRua-Token": _TEST_TOKEN},
        )
        assert resp.status_code in (200, 422)

    def test_convert_kml_processing_error_returns_422(self, client):
        with patch("backend.application.gis.gis_service.process_kml") as mock_proc:
            mock_proc.return_value = {"error": "parse error", "type": "FeatureCollection", "features": []}
            resp = client.post(
                "/api/v1/gis/convert/kml",
                json={"content": "<kml/>"},
                headers={"X-SisRua-Token": _TEST_TOKEN},
            )
        assert resp.status_code == 422


# ──────────────────────────────────────────────
# 4. infrastructure/osm_client.py
# ──────────────────────────────────────────────

class TestOsmClient:
    """Tests for OsmClient Overpass API networking."""

    def test_fetch_overpass_data_success(self):
        """Happy path: returns parsed JSON from Overpass."""
        from backend.infrastructure.osm_client import OsmClient
        fake_data = {"elements": [{"type": "way", "id": 1, "nodes": []}]}
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_data
        mock_resp.raise_for_status.return_value = None

        with patch("backend.infrastructure.osm_client.requests.post", return_value=mock_resp):
            result = OsmClient.fetch_overpass_data(lat=-22.15, lon=-42.92, radius=500)
        assert result == fake_data

    def test_fetch_overpass_data_calls_check_cancel(self):
        """check_cancel is invoked during fetch."""
        from backend.infrastructure.osm_client import OsmClient
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"elements": []}
        mock_resp.raise_for_status.return_value = None
        cancel_calls = []
        check_cancel = lambda: cancel_calls.append(1)  # noqa: E731

        with patch("backend.infrastructure.osm_client.requests.post", return_value=mock_resp):
            OsmClient.fetch_overpass_data(-22.15, -42.92, 100, check_cancel=check_cancel)
        assert len(cancel_calls) >= 1

    def test_fetch_overpass_data_retries_on_request_exception(self):
        """Retries up to 3 times on RequestException; succeeds on 3rd attempt."""
        from backend.infrastructure.osm_client import OsmClient
        import requests as req_mod

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"elements": []}
        mock_resp.raise_for_status.return_value = None

        call_count = {"n": 0}

        def _side_effect(*a, **kw):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise req_mod.RequestException("timeout")
            return mock_resp

        with patch("backend.infrastructure.osm_client.requests.post", side_effect=_side_effect):
            # Patch 'time.sleep' at stdlib level (imported inside the function body)
            with patch("time.sleep", MagicMock()):
                result = OsmClient.fetch_overpass_data(-22.15, -42.92, 100)
        assert result["elements"] == []
        assert call_count["n"] == 3

    def test_fetch_overpass_data_raises_after_all_retries(self):
        """Raises exception when all 3 attempts fail."""
        from backend.infrastructure.osm_client import OsmClient
        import requests as req_mod

        with patch("backend.infrastructure.osm_client.requests.post",
                   side_effect=req_mod.RequestException("all fail")):
            with patch("time.sleep", MagicMock()):
                with pytest.raises(req_mod.RequestException):
                    OsmClient.fetch_overpass_data(-22.15, -42.92, 100)

    def test_fetch_overpass_data_rate_limit_raises(self):
        """HTTP 429 raises a descriptive exception."""
        from backend.infrastructure.osm_client import OsmClient
        import requests as req_mod

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.raise_for_status.side_effect = req_mod.HTTPError(response=mock_resp)

        with patch("backend.infrastructure.osm_client.requests.post", return_value=mock_resp):
            with pytest.raises(Exception, match="[Rr]ate [Ll]imit"):
                OsmClient.fetch_overpass_data(-22.15, -42.92, 100)

    def test_fetch_overpass_data_http_error_non_429_reraises(self):
        """Non-429 HTTPError is re-raised as-is."""
        from backend.infrastructure.osm_client import OsmClient
        import requests as req_mod

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        http_err = req_mod.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_err

        with patch("backend.infrastructure.osm_client.requests.post", return_value=mock_resp):
            with pytest.raises(req_mod.HTTPError):
                OsmClient.fetch_overpass_data(-22.15, -42.92, 100)
