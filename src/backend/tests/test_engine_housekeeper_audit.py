"""
tests/test_engine_housekeeper_audit.py
Split from test_coverage_boost.py (>500 lines rule).
Covers: gis_core/engine_mock.py, services/housekeeper.py, core/audit.py
"""
import os
import json
import time
import sqlite3
from pathlib import Path
from unittest.mock import patch


# ---------------------------------------------------------------------------
# gis_core/engine_mock.py — AutoCADMock (0% → 100%)
# ---------------------------------------------------------------------------

def test_engine_mock_draw_polyline_open():
    from backend.domain.engine_mock import AutoCADMock
    m = AutoCADMock(precision_noise=0.0)
    m.draw_polyline([[0, 0], [1, 0], [1, 1]], layer="ROADS")
    assert len(m.db) == 1
    assert m.db[0]["type"] == "Polyline"
    assert m.db[0]["layer"] == "ROADS"
    assert m.db[0]["closed"] is False


def test_engine_mock_draw_polyline_closed():
    from backend.domain.engine_mock import AutoCADMock
    m = AutoCADMock(precision_noise=0.0)
    m.draw_polyline([[0, 0], [1, 0], [1, 1], [0, 0]], layer="LOTS")
    assert m.db[0]["closed"] is True


def test_engine_mock_get_layer_count():
    from backend.domain.engine_mock import AutoCADMock
    m = AutoCADMock(precision_noise=0.0)
    m.draw_polyline([[0, 0], [1, 1]], layer="A")
    m.draw_polyline([[0, 0], [2, 2]], layer="A")
    m.draw_polyline([[0, 0], [3, 3]], layer="B")
    counts = m.get_layer_count()
    assert counts == {"A": 2, "B": 1}


def test_engine_mock_noise_is_bounded():
    from backend.domain.engine_mock import AutoCADMock
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
    from backend.application.housekeeper import HousekeeperService
    svc = HousekeeperService(retention_days=1)
    missing = tmp_path / "does_not_exist"
    result = svc.cleanup_directory(missing)
    assert result == 0


def test_housekeeper_cleanup_deletes_old_files(tmp_path):
    from backend.application.housekeeper import HousekeeperService
    svc = HousekeeperService(retention_days=0)  # 0 days → everything is old
    old_file = tmp_path / "old.txt"
    old_file.write_text("old content")
    old_time = time.time() - 10
    os.utime(old_file, (old_time, old_time))

    result = svc.cleanup_directory(tmp_path)
    assert result >= 1
    assert not old_file.exists()


def test_housekeeper_cleanup_keeps_new_files(tmp_path):
    from backend.application.housekeeper import HousekeeperService
    svc = HousekeeperService(retention_days=7)
    new_file = tmp_path / "new.txt"
    new_file.write_text("fresh content")
    result = svc.cleanup_directory(tmp_path)
    assert result == 0
    assert new_file.exists()


def test_housekeeper_cleanup_recursive(tmp_path):
    from backend.application.housekeeper import HousekeeperService
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
    from backend.application.housekeeper import HousekeeperService
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
    from backend.application.housekeeper import HousekeeperService
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

def test_audit_compute_signature_deterministic(tmp_path):
    from backend.shared.audit import AuditLogger
    auditor = AuditLogger.__new__(AuditLogger)
    auditor.secret_key = b"test-secret-32-bytes-exactly!!!"
    sig1 = auditor._compute_signature("CREATE", "Project", "p1", "user1", 1000.0, {"x": 1})
    sig2 = auditor._compute_signature("CREATE", "Project", "p1", "user1", 1000.0, {"x": 1})
    assert sig1 == sig2
    assert len(sig1) == 64  # HMAC-SHA256 hex digest


def test_audit_compute_signature_varies_with_input(tmp_path):
    from backend.shared.audit import AuditLogger
    auditor = AuditLogger.__new__(AuditLogger)
    auditor.secret_key = b"test-secret-32-bytes-exactly!!!"
    sig1 = auditor._compute_signature("CREATE", "Project", "p1", "user1", 1000.0, {})
    sig2 = auditor._compute_signature("DELETE", "Project", "p1", "user1", 1000.0, {})
    assert sig1 != sig2


def test_audit_log_and_verify(tmp_path):
    """Full round-trip: log() then verify() returns True."""
    db_path = tmp_path / "test.db"
    os.environ["LOCALAPPDATA"] = str(tmp_path)

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

        from backend.shared.audit import AuditLogger
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

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        from backend.shared.audit import AuditLogger
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

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        from backend.shared.audit import AuditLogger
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
        conn_main.execute(
            "INSERT INTO AuditLog (event_type, entity_type, entity_id, user_id, timestamp, data_json, signature) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("UPDATE", "CadFeature", "c1", "sys", time.time(), "NOT_JSON{{{", "sig"),
        )
        conn_main.commit()

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

        from backend.shared.audit import AuditLogger
        auditor = AuditLogger.__new__(AuditLogger)
        auditor.secret_key = os.urandom(32)
        logs = auditor.list_logs()
        # Should not raise; bad JSON → empty dict
        assert logs[0]["data"] == {}


def test_audit_secret_generated_fresh(tmp_path):
    """_load_or_generate_secret generates a new secret when none exists."""
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.shared.audit import AuditLogger
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
    from backend.shared.audit import AuditLogger
    auditor = AuditLogger()
    assert auditor.secret_key == fixed_secret
