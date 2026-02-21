"""
tests/test_coverage_boost.py
Unit tests targeting previously uncovered code paths.
Goal: raise overall backend coverage from 71% to ≥80%.

Each test group is labelled with the module it exercises.
"""
import os
import json
import time
import sqlite3
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# gis_core/engine_mock.py — AutoCADMock (0% → 100%)
# ---------------------------------------------------------------------------

def test_engine_mock_draw_polyline_open():
    from backend.gis_core.engine_mock import AutoCADMock
    m = AutoCADMock(precision_noise=0.0)
    m.draw_polyline([[0, 0], [1, 0], [1, 1]], layer="ROADS")
    assert len(m.db) == 1
    assert m.db[0]["type"] == "Polyline"
    assert m.db[0]["layer"] == "ROADS"
    assert m.db[0]["closed"] is False


def test_engine_mock_draw_polyline_closed():
    from backend.gis_core.engine_mock import AutoCADMock
    m = AutoCADMock(precision_noise=0.0)
    m.draw_polyline([[0, 0], [1, 0], [1, 1], [0, 0]], layer="LOTS")
    assert m.db[0]["closed"] is True


def test_engine_mock_get_layer_count():
    from backend.gis_core.engine_mock import AutoCADMock
    m = AutoCADMock(precision_noise=0.0)
    m.draw_polyline([[0, 0], [1, 1]], layer="A")
    m.draw_polyline([[0, 0], [2, 2]], layer="A")
    m.draw_polyline([[0, 0], [3, 3]], layer="B")
    counts = m.get_layer_count()
    assert counts == {"A": 2, "B": 1}


def test_engine_mock_noise_is_bounded():
    from backend.gis_core.engine_mock import AutoCADMock
    precision_noise = 1e-3
    m = AutoCADMock(precision_noise=precision_noise)
    m.draw_polyline([[0, 0], [1, 1]], layer="0")
    max_x = 1.0 + 2 * precision_noise
    max_y = 1.0 + 2 * precision_noise
    for x, y in m.db[0]["coords"]:
        assert abs(x) <= max_x
        assert abs(y) <= max_y


# ---------------------------------------------------------------------------
# services/housekeeper.py — HousekeeperService (0% → 80%+)
# ---------------------------------------------------------------------------

def test_housekeeper_cleanup_nonexistent_dir(tmp_path):
    from backend.services.housekeeper import HousekeeperService
    svc = HousekeeperService(retention_days=1)
    missing = tmp_path / "does_not_exist"
    result = svc.cleanup_directory(missing)
    assert result == 0


def test_housekeeper_cleanup_deletes_old_files(tmp_path):
    from backend.services.housekeeper import HousekeeperService
    svc = HousekeeperService(retention_days=0)  # 0 days → everything is old
    old_file = tmp_path / "old.txt"
    old_file.write_text("old content")
    # Force mtime to be in the past
    old_time = time.time() - 10
    os.utime(old_file, (old_time, old_time))

    result = svc.cleanup_directory(tmp_path)
    assert result >= 1
    assert not old_file.exists()


def test_housekeeper_cleanup_keeps_new_files(tmp_path):
    from backend.services.housekeeper import HousekeeperService
    svc = HousekeeperService(retention_days=7)
    new_file = tmp_path / "new.txt"
    new_file.write_text("fresh content")
    result = svc.cleanup_directory(tmp_path)
    assert result == 0
    assert new_file.exists()


def test_housekeeper_cleanup_recursive(tmp_path):
    from backend.services.housekeeper import HousekeeperService
    svc = HousekeeperService(retention_days=0)
    sub = tmp_path / "sub"
    sub.mkdir()
    old_file = sub / "deep_old.log"
    old_file.write_text("data")
    old_time = time.time() - 10
    os.utime(old_file, (old_time, old_time))

    result = svc.cleanup_directory(tmp_path, recursive=True)
    assert result >= 1


def test_housekeeper_dry_run_no_deletion(tmp_path):
    from backend.services.housekeeper import HousekeeperService
    svc = HousekeeperService(retention_days=0)
    svc.dry_run = True
    f = tmp_path / "file.txt"
    f.write_text("x")
    old_time = time.time() - 10
    os.utime(f, (old_time, old_time))
    result = svc.cleanup_directory(tmp_path)
    assert result >= 1  # counted but not deleted
    assert f.exists()


def test_housekeeper_run_daily_cleanup(tmp_path):
    from backend.services.housekeeper import HousekeeperService
    svc = HousekeeperService(retention_days=0)
    f = tmp_path / "old.json"
    f.write_text("{}")
    old_time = time.time() - 10
    os.utime(f, (old_time, old_time))
    total = svc.run_daily_cleanup([tmp_path])
    assert total >= 1


# ---------------------------------------------------------------------------
# core/audit.py — AuditLogger (48% → 85%+)
# ---------------------------------------------------------------------------

def _fresh_audit_logger(tmp_path: Path):
    """Creates an AuditLogger backed by a fresh temp DB."""
    from backend.core.audit import AuditLogger
    from backend.core.database import get_db_connection

    db_path = tmp_path / "audit_test.db"
    os.environ["LOCALAPPDATA"] = str(tmp_path)

    with patch("backend.core.audit.get_db_connection") as mock_conn:
        # Use real fresh SQLite DB for full path coverage
        def make_conn():
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS AuditLog (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL, entity_type TEXT NOT NULL,
                    entity_id TEXT, user_id TEXT, timestamp REAL NOT NULL,
                    data_json TEXT, signature TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            return conn

        mock_conn.side_effect = make_conn
        logger = AuditLogger.__new__(AuditLogger)
        logger.secret_key = os.urandom(32)
        return logger, mock_conn, make_conn


def test_audit_compute_signature_deterministic(tmp_path):
    from backend.core.audit import AuditLogger
    logger = AuditLogger.__new__(AuditLogger)
    logger.secret_key = b"test-secret-32-bytes-exactly!!!"
    sig1 = logger._compute_signature("CREATE", "Project", "p1", "user1", 1000.0, {"x": 1})
    sig2 = logger._compute_signature("CREATE", "Project", "p1", "user1", 1000.0, {"x": 1})
    assert sig1 == sig2
    assert len(sig1) == 64  # HMAC-SHA256 hex digest


def test_audit_compute_signature_varies_with_input(tmp_path):
    from backend.core.audit import AuditLogger
    logger = AuditLogger.__new__(AuditLogger)
    logger.secret_key = b"test-secret-32-bytes-exactly!!!"
    sig1 = logger._compute_signature("CREATE", "Project", "p1", "user1", 1000.0, {})
    sig2 = logger._compute_signature("DELETE", "Project", "p1", "user1", 1000.0, {})
    assert sig1 != sig2


def test_audit_log_and_verify(tmp_path):
    """Full round-trip: log() then verify() returns True."""
    db_path = tmp_path / "test.db"
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    os.environ["SISRUA_TESTING"] = "true"

    with patch("backend.core.audit.get_db_connection") as mock_gdc:
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS AuditLog (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL, entity_type TEXT NOT NULL,
                entity_id TEXT, user_id TEXT, timestamp REAL NOT NULL,
                data_json TEXT, signature TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Each call to get_db_connection returns a NEW connection to same DB
        def make_conn():
            return sqlite3.connect(str(db_path))

        mock_gdc.side_effect = make_conn

        from backend.core.audit import AuditLogger
        auditor = AuditLogger.__new__(AuditLogger)
        auditor.secret_key = os.urandom(32)

        audit_id = auditor.log("CREATE", "Project", "p-test", {"name": "proj"}, user_id="usr1")
        assert isinstance(audit_id, int)

        is_valid = auditor.verify(audit_id)
        assert is_valid is True


def test_audit_verify_not_found(tmp_path):
    db_path = tmp_path / "empty.db"
    with patch("backend.core.audit.get_db_connection") as mock_gdc:
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS AuditLog (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL, entity_type TEXT NOT NULL,
                entity_id TEXT, user_id TEXT, timestamp REAL NOT NULL,
                data_json TEXT, signature TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        def make_conn():
            return sqlite3.connect(str(db_path))

        mock_gdc.side_effect = make_conn

        from backend.core.audit import AuditLogger
        auditor = AuditLogger.__new__(AuditLogger)
        auditor.secret_key = os.urandom(32)
        assert auditor.verify(99999) is False


def test_audit_list_logs_returns_entries(tmp_path):
    db_path = tmp_path / "list.db"
    with patch("backend.core.audit.get_db_connection") as mock_gdc:
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS AuditLog (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL, entity_type TEXT NOT NULL,
                entity_id TEXT, user_id TEXT, timestamp REAL NOT NULL,
                data_json TEXT, signature TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn_main.execute(
            "INSERT INTO AuditLog (event_type, entity_type, entity_id, user_id, timestamp, data_json, signature) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("CREATE", "Project", "p1", "sys", time.time(), '{"a":1}', "sig"),
        )
        conn_main.commit()

        def make_conn():
            return sqlite3.connect(str(db_path))

        mock_gdc.side_effect = make_conn

        from backend.core.audit import AuditLogger
        auditor = AuditLogger.__new__(AuditLogger)
        auditor.secret_key = os.urandom(32)
        logs = auditor.list_logs(limit=10)
        assert len(logs) == 1
        assert logs[0]["event_type"] == "CREATE"
        assert logs[0]["entity_type"] == "Project"


def test_audit_list_logs_invalid_json(tmp_path):
    db_path = tmp_path / "bad_json.db"
    with patch("backend.core.audit.get_db_connection") as mock_gdc:
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS AuditLog (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL, entity_type TEXT NOT NULL,
                entity_id TEXT, user_id TEXT, timestamp REAL NOT NULL,
                data_json TEXT, signature TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Insert a row with malformed data_json
        conn_main.execute(
            "INSERT INTO AuditLog (event_type, entity_type, entity_id, user_id, timestamp, data_json, signature) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("UPDATE", "CadFeature", "c1", "sys", time.time(), "NOT_JSON{{{", "sig"),
        )
        conn_main.commit()

        def make_conn():
            return sqlite3.connect(str(db_path))

        mock_gdc.side_effect = make_conn

        from backend.core.audit import AuditLogger
        auditor = AuditLogger.__new__(AuditLogger)
        auditor.secret_key = os.urandom(32)
        logs = auditor.list_logs()
        # Should not raise; bad JSON → empty dict
        assert logs[0]["data"] == {}


def test_audit_secret_generated_fresh(tmp_path):
    """_load_or_generate_secret generates a new secret when none exists."""
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.core.audit import AuditLogger
    auditor = AuditLogger()
    assert isinstance(auditor.secret_key, bytes)
    assert len(auditor.secret_key) == 32

    secret_file = tmp_path / "sisRUA" / ".audit_secret"
    assert secret_file.exists()


def test_audit_secret_loaded_existing(tmp_path):
    """_load_or_generate_secret loads the existing secret file."""
    secret_dir = tmp_path / "sisRUA"
    secret_dir.mkdir(parents=True)
    secret_file = secret_dir / ".audit_secret"
    fixed_secret = b"A" * 32
    secret_file.write_bytes(fixed_secret)

    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.core.audit import AuditLogger
    auditor = AuditLogger()
    assert auditor.secret_key == fixed_secret


# ---------------------------------------------------------------------------
# services/projects.py — ProjectService CRUD (51% → 90%+)
# ---------------------------------------------------------------------------

def _mock_project_service():
    """Returns a ProjectService with mocked audit logger."""
    from backend.services.projects import ProjectService
    svc = ProjectService()
    svc.audit = MagicMock()
    svc.audit.log.return_value = 1
    return svc


def test_project_service_create(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    os.environ["SISRUA_TESTING"] = "true"
    with patch("backend.services.projects.get_db_connection") as mock_gdc:
        db_path = tmp_path / "create.db"
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn_main.commit()
        conn_main.close()

        def make_conn():
            return sqlite3.connect(str(db_path))

        mock_gdc.side_effect = make_conn

        svc = _mock_project_service()
        result = svc.create_project("My New Project", crs_out="EPSG:31983")

    assert result["project_name"] == "My New Project"
    assert result["crs_out"] == "EPSG:31983"
    assert "project_id" in result
    assert result["version"] == 1


def test_project_service_create_with_event_bus(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    with patch("backend.services.projects.get_db_connection") as mock_gdc:
        db_path = tmp_path / "cre_bus.db"
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn_main.commit()
        conn_main.close()

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        mock_bus = MagicMock()
        svc = _mock_project_service()
        svc.event_bus = mock_bus

        result = svc.create_project("Bus Project")

    mock_bus.publish.assert_called_once()
    event_name = mock_bus.publish.call_args[0][0]
    assert event_name == "project_saved"


def test_project_service_list(tmp_path):
    with patch("backend.services.projects.get_db_connection") as mock_gdc:
        db_path = tmp_path / "list.db"
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME, crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn_main.execute(
            "INSERT INTO Projects VALUES (?,?,?,?,?)",
            ("pid1", "Alpha", "2024-01-01", "EPSG:31983", 1),
        )
        conn_main.commit()
        conn_main.close()

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        svc = _mock_project_service()
        projects = svc.list_projects()

    assert len(projects) == 1
    assert projects[0]["project_name"] == "Alpha"


def test_project_service_delete_success(tmp_path):
    with patch("backend.services.projects.get_db_connection") as mock_gdc:
        db_path = tmp_path / "del.db"
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME, crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS CadFeatures (
                feature_id INTEGER PRIMARY KEY, project_id TEXT, feature_type TEXT NOT NULL, layer TEXT, name TEXT,
                highway TEXT, width_m REAL, color TEXT, elevation REAL, slope REAL,
                original_geojson_properties TEXT, coords_xy TEXT,
                insertion_point_xy TEXT, block_name TEXT, rotation REAL, scale REAL
            )
        """)
        conn_main.execute(
            "INSERT INTO Projects VALUES (?,?,?,?,?)",
            ("pid-del", "ToDelete", "2024-01-01", "EPSG:31983", 1),
        )
        conn_main.commit()
        conn_main.close()

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        svc = _mock_project_service()
        svc.delete_project("pid-del")

    # Verify project is gone
    conn_check = sqlite3.connect(str(db_path))
    row = conn_check.execute("SELECT 1 FROM Projects WHERE project_id='pid-del'").fetchone()
    conn_check.close()
    assert row is None


def test_project_service_delete_not_found(tmp_path):
    from backend.services.projects import NotFoundError
    with patch("backend.services.projects.get_db_connection") as mock_gdc:
        db_path = tmp_path / "del_nf.db"
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME, crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS CadFeatures (
                feature_id INTEGER PRIMARY KEY, project_id TEXT, feature_type TEXT NOT NULL, layer TEXT, name TEXT,
                highway TEXT, width_m REAL, color TEXT, elevation REAL, slope REAL,
                original_geojson_properties TEXT, coords_xy TEXT,
                insertion_point_xy TEXT, block_name TEXT, rotation REAL, scale REAL
            )
        """)
        conn_main.commit()
        conn_main.close()

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        svc = _mock_project_service()
        import pytest
        with pytest.raises(NotFoundError):
            svc.delete_project("does-not-exist")


def test_project_service_delete_event_bus(tmp_path):
    with patch("backend.services.projects.get_db_connection") as mock_gdc:
        db_path = tmp_path / "del_bus.db"
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME, crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS CadFeatures (
                feature_id INTEGER PRIMARY KEY, project_id TEXT, feature_type TEXT NOT NULL, layer TEXT, name TEXT,
                highway TEXT, width_m REAL, color TEXT, elevation REAL, slope REAL,
                original_geojson_properties TEXT, coords_xy TEXT,
                insertion_point_xy TEXT, block_name TEXT, rotation REAL, scale REAL
            )
        """)
        conn_main.execute(
            "INSERT INTO Projects VALUES (?,?,?,?,?)",
            ("pid-bus", "BusProject", "2024-01-01", "EPSG:31983", 1),
        )
        conn_main.commit()
        conn_main.close()

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        mock_bus = MagicMock()
        svc = _mock_project_service()
        svc.event_bus = mock_bus
        svc.delete_project("pid-bus")

    mock_bus.publish.assert_called_once_with("project_deleted", {"project_id": "pid-bus"})


def test_project_service_update_success(tmp_path):
    with patch("backend.services.projects.get_db_connection") as mock_gdc:
        db_path = tmp_path / "upd.db"
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME, crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn_main.execute(
            "INSERT INTO Projects VALUES (?,?,?,?,?)",
            ("p-upd", "OldName", "2024-01-01", "EPSG:31983", 1),
        )
        conn_main.commit()
        conn_main.close()

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        svc = _mock_project_service()
        updated = svc.update_project("p-upd", {"project_name": "NewName"}, expected_version=1)

    assert updated["project_name"] == "NewName"
    assert updated["version"] == 2


def test_project_service_update_not_found(tmp_path):
    from backend.services.projects import NotFoundError
    with patch("backend.services.projects.get_db_connection") as mock_gdc:
        db_path = tmp_path / "upd_nf.db"
        conn_main = sqlite3.connect(str(db_path))
        conn_main.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
                creation_date DATETIME, crs_out TEXT, version INTEGER DEFAULT 1
            )
        """)
        conn_main.commit()
        conn_main.close()

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        svc = _mock_project_service()
        import pytest
        with pytest.raises(NotFoundError):
            svc.update_project("ghost", {"project_name": "X"}, expected_version=1)


# ---------------------------------------------------------------------------
# services/webhooks.py — WebhookService (59% → 85%+)
# ---------------------------------------------------------------------------

def test_webhook_register_url():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WEBHOOK_URL", None)
        from backend.services.webhooks import WebhookService
        svc = WebhookService()
        svc.register_url("http://example.com/hook")
        assert "http://example.com/hook" in svc.urls


def test_webhook_register_url_no_duplicate():
    from backend.services.webhooks import WebhookService
    svc = WebhookService()
    svc.register_url("http://example.com/hook")
    svc.register_url("http://example.com/hook")
    assert svc.urls.count("http://example.com/hook") == 1


def test_webhook_broadcast_no_urls():
    from backend.services.webhooks import WebhookService
    svc = WebhookService()
    svc.urls.clear()
    # Should not raise even with no registered URLs
    svc.broadcast("test_event", {"data": "value"})


def test_webhook_broadcast_submits_to_executor():
    from backend.services.webhooks import WebhookService
    svc = WebhookService()
    svc.urls = ["http://example.com/hook"]
    mock_executor = MagicMock()
    svc.executor = mock_executor
    svc.broadcast("test_event", {"key": "val"})
    mock_executor.submit.assert_called_once()


def test_webhook_deliver_success():
    from backend.services.webhooks import WebhookService
    svc = WebhookService()
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch("backend.services.webhooks.requests.post", return_value=mock_response) as mock_post:
        svc._deliver("http://example.com/hook", {"event": "test", "data": {}})
    mock_post.assert_called_once()


def test_webhook_deliver_http_error():
    from backend.services.webhooks import WebhookService
    svc = WebhookService()
    mock_response = MagicMock()
    mock_response.status_code = 500
    with patch("backend.services.webhooks.requests.post", return_value=mock_response):
        # Should not raise
        svc._deliver("http://example.com/hook", {"event": "test"})


def test_webhook_deliver_network_exception():
    from backend.services.webhooks import WebhookService
    svc = WebhookService()
    with patch("backend.services.webhooks.requests.post", side_effect=ConnectionError("refused")):
        # Should not raise
        svc._deliver("http://example.com/hook", {"event": "test"})


def test_webhook_static_url_from_env(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "http://static-hook.example.com/webhook")
    from backend.services import webhooks as wh_mod
    import importlib
    importlib.reload(wh_mod)
    svc = wh_mod.WebhookService()
    assert "http://static-hook.example.com/webhook" in svc.urls


# ---------------------------------------------------------------------------
# services/cache.py — CacheService (67% → 90%+)
# ---------------------------------------------------------------------------

def test_cache_set_and_get_filesystem(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.services.cache import CacheService
    svc = CacheService()
    svc.set("test:key", {"answer": 42})
    result = svc.get("test:key")
    assert result == {"answer": 42}


def test_cache_get_missing_returns_none(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.services.cache import CacheService
    svc = CacheService()
    result = svc.get("nonexistent:key")
    assert result is None


def test_cache_set_overwrite(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.services.cache import CacheService
    svc = CacheService()
    svc.set("overwrite:key", {"v": 1})
    svc.set("overwrite:key", {"v": 2})
    result = svc.get("overwrite:key")
    assert result["v"] == 2


def test_cache_key_sanitization(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.services.cache import CacheService
    svc = CacheService()
    # Keys with special chars should be sanitized to filesystem-safe names
    svc.set("ns:key/sub\\path", {"ok": True})
    result = svc.get("ns:key/sub\\path")
    assert result["ok"] is True


def test_cache_redis_set_skipped_when_none(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.services.cache import CacheService
    svc = CacheService()
    svc.redis = None
    # Should not raise
    svc._safe_redis_set("k", {"v": 1})


def test_cache_redis_get_skipped_when_none(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.services.cache import CacheService
    svc = CacheService()
    svc.redis = None
    result = svc.get("some:key")
    assert result is None


def test_cache_redis_fallback_on_exception(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.services.cache import CacheService
    svc = CacheService()
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("redis down")
    svc.redis = mock_redis
    # Should fall through to file cache without raising
    result = svc.get("any:key")
    assert result is None


# ---------------------------------------------------------------------------
# services/ai.py — AiService (68% → 85%+)
# ---------------------------------------------------------------------------

def test_ai_no_api_key_returns_message():
    with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
        os.environ.pop("GROQ_API_KEY", None)
        from backend.services.ai import AiService
        svc = AiService()
        # Clear the cached flag so warning fires
        AiService._notified_missing_key = False
        svc.client = None
        result = svc.generate_response("Hello?")
    assert result == "AI Service is not configured (missing API key)."


def test_ai_with_api_key_calls_groq():
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
        from backend.services.ai import AiService
        import importlib
        from backend.services import ai as ai_mod
        with patch("backend.services.ai.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Hello from AI"))]
            )

            svc = AiService()
            result = svc.generate_response("What is sisRUA?")

    assert result == "Hello from AI"


def test_ai_groq_exception_returns_fallback():
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
        from backend.services.ai import AiService
        with patch("backend.services.ai.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            mock_client.chat.completions.create.side_effect = RuntimeError("API down")

            svc = AiService()
            result = svc.generate_response("test")

    assert result == "I'm having trouble connecting to my brain right now. Please try again later."


def test_ai_rag_context_with_job_id():
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
        from backend.services.ai import AiService
        with patch("backend.services.ai.Groq") as mock_groq, \
             patch("backend.services.jobs.get_job") as mock_get_job:
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="RAG answer"))]
            )
            mock_get_job.return_value = {
                "kind": "osm",
                "result": {"feature_count": 42},
            }

            svc = AiService()
            result = svc.generate_response("What did we process?", job_id="job-123")

    assert result == "RAG answer"


def test_ai_audit_rag_context():
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
        from backend.services.ai import AiService
        with patch("backend.services.ai.Groq") as mock_groq, \
             patch("backend.core.audit.get_audit_logger") as mock_get_al:
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Audit answer"))]
            )
            mock_audit = MagicMock()
            mock_audit.list_logs.return_value = [
                {
                    "event_type": "CREATE", "entity_type": "Project",
                    "entity_id": "p1", "data": "{}", "created_at": "2024-01-01",
                }
            ]
            mock_get_al.return_value = mock_audit

            svc = AiService()
            result = svc.generate_response(
                "What happened?", context={"fetch_audit_logs": True}
            )

    assert result == "Audit answer"


# ---------------------------------------------------------------------------
# services/export_service.py — ExportService (50% → 75%+)
# ---------------------------------------------------------------------------

def _make_export_db(tmp_path: Path, project_id: str = "proj-1") -> Path:
    """Creates a minimal SQLite DB with one project and zero features."""
    db_path = tmp_path / "export.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Projects (
            project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL,
            creation_date DATETIME, crs_out TEXT, version INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS CadFeatures (
            feature_id INTEGER PRIMARY KEY, project_id TEXT, feature_type TEXT NOT NULL,
            layer TEXT, name TEXT, highway TEXT, width_m REAL, color TEXT,
            elevation REAL, slope REAL, original_geojson_properties TEXT,
            coords_xy TEXT, insertion_point_xy TEXT, block_name TEXT,
            rotation REAL, scale REAL
        )
    """)
    conn.execute(
        "INSERT INTO Projects VALUES (?,?,?,?,?)",
        (project_id, "Test Project", "2024-01-01", "EPSG:31983", 1),
    )
    conn.commit()
    conn.close()
    return db_path


def test_export_geojson_empty_project(tmp_path):
    from backend.services.export_service import ExportService
    db_path = _make_export_db(tmp_path, "geoj-1")
    svc = ExportService(db_path=db_path)
    path = svc.export_project_to_geojson("geoj-1")
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["type"] == "FeatureCollection"
    assert data["features"] == []
    assert data["metadata"]["project_id"] == "geoj-1"


def test_export_geojson_not_found(tmp_path):
    from backend.services.export_service import ExportService
    from backend.services.projects import NotFoundError
    db_path = _make_export_db(tmp_path, "geoj-exists")
    svc = ExportService(db_path=db_path)
    import pytest
    with pytest.raises(NotFoundError):
        svc.export_project_to_geojson("nonexistent-project")


def test_export_geojson_with_features(tmp_path):
    from backend.services.export_service import ExportService
    db_path = _make_export_db(tmp_path, "geoj-2")
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT INTO CadFeatures
           (project_id, feature_type, layer, name, highway, width_m, color, elevation,
            slope, original_geojson_properties, coords_xy, insertion_point_xy, block_name, rotation, scale)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "geoj-2", "Polyline", "ROADS", "Rua A", "residential", 6.0, "7",
            None, None, '{"source":"osm"}',
            json.dumps([[0.0, 0.0], [1.0, 1.0]]),
            None, None, 0.0, 1.0,
        ),
    )
    conn.commit()
    conn.close()

    svc = ExportService(db_path=db_path)
    path = svc.export_project_to_geojson("geoj-2")
    data = json.loads(path.read_text())
    assert len(data["features"]) == 1
    assert data["features"][0]["geometry"]["type"] == "LineString"


def test_export_geopackage_empty_project(tmp_path):
    from backend.services.export_service import ExportService
    db_path = _make_export_db(tmp_path, "gpkg-1")
    svc = ExportService(db_path=db_path)
    path = svc.export_project_to_geopackage("gpkg-1")
    assert path.exists()
    assert path.suffix == ".gpkg"


def test_export_geopackage_not_found(tmp_path):
    from backend.services.export_service import ExportService
    from backend.services.projects import NotFoundError
    db_path = _make_export_db(tmp_path, "gpkg-exists")
    svc = ExportService(db_path=db_path)
    import pytest
    with pytest.raises(NotFoundError):
        svc.export_project_to_geopackage("ghost-project")


def test_export_dxf_empty_project(tmp_path):
    from backend.services.export_service import ExportService
    db_path = _make_export_db(tmp_path, "dxf-1")
    svc = ExportService(db_path=db_path)
    path = svc.export_project_to_dxf("dxf-1", escala=1000)
    assert path.exists()
    assert path.suffix == ".dxf"


def test_export_dxf_not_found(tmp_path):
    from backend.services.export_service import ExportService
    from backend.services.projects import NotFoundError
    db_path = _make_export_db(tmp_path, "dxf-exists")
    svc = ExportService(db_path=db_path)
    import pytest
    with pytest.raises(NotFoundError):
        svc.export_project_to_dxf("nonexistent")


def test_export_dxf_with_polyline_feature(tmp_path):
    from backend.services.export_service import ExportService
    db_path = _make_export_db(tmp_path, "dxf-feat")
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT INTO CadFeatures
           (project_id, feature_type, layer, name, highway, width_m, color, elevation,
            slope, original_geojson_properties, coords_xy, insertion_point_xy, block_name, rotation, scale)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "dxf-feat", "Polyline", "ROADS", "Rua B", "primary", 8.0, "3",
            10.5, 0.02, '{"source":"osm"}',
            json.dumps([[788500.0, 7634900.0], [788600.0, 7634900.0]]),
            None, None, 0.0, 1.0,
        ),
    )
    conn.commit()
    conn.close()

    svc = ExportService(db_path=db_path)
    path = svc.export_project_to_dxf("dxf-feat", escala=1000)
    assert path.exists()
    # Read DXF content to verify it was written properly
    content = path.read_text(encoding="utf-8", errors="ignore")
    assert "ENDSEC" in content  # DXF structural marker
