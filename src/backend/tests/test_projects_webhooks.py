"""
tests/test_projects_webhooks.py
Split from test_coverage_boost.py (>500 lines rule).
Covers: services/projects.py, services/webhooks.py
"""
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# services/projects.py — ProjectService CRUD (51% → 90%+)
# ---------------------------------------------------------------------------

def _mock_project_service():
    """Returns a ProjectService with mocked audit logger."""
    from backend.application.projects import ProjectService
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

        mock_gdc.side_effect = lambda: sqlite3.connect(str(db_path))

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

        svc.create_project("Bus Project")

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

    conn_check = sqlite3.connect(str(db_path))
    row = conn_check.execute("SELECT 1 FROM Projects WHERE project_id='pid-del'").fetchone()
    conn_check.close()
    assert row is None


def test_project_service_delete_not_found(tmp_path):
    import pytest
    from backend.application.projects import NotFoundError
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
    import pytest
    from backend.application.projects import NotFoundError
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
        with pytest.raises(NotFoundError):
            svc.update_project("ghost", {"project_name": "X"}, expected_version=1)


# ---------------------------------------------------------------------------
# services/webhooks.py — WebhookService (59% → 100%)
# ---------------------------------------------------------------------------

def test_webhook_register_url():
    os.environ.pop("WEBHOOK_URL", None)
    from backend.application.webhooks import WebhookService
    svc = WebhookService()
    svc.register_url("http://example.com/hook")
    assert "http://example.com/hook" in svc.urls


def test_webhook_register_url_no_duplicate():
    from backend.application.webhooks import WebhookService
    svc = WebhookService()
    svc.register_url("http://example.com/hook")
    svc.register_url("http://example.com/hook")
    assert svc.urls.count("http://example.com/hook") == 1


def test_webhook_broadcast_no_urls():
    from backend.application.webhooks import WebhookService
    svc = WebhookService()
    svc.urls.clear()
    # Should not raise even with no registered URLs
    svc.broadcast("test_event", {"data": "value"})


def test_webhook_broadcast_submits_to_executor():
    from backend.application.webhooks import WebhookService
    svc = WebhookService()
    svc.urls = ["http://example.com/hook"]
    mock_executor = MagicMock()
    svc.executor = mock_executor
    svc.broadcast("test_event", {"key": "val"})
    mock_executor.submit.assert_called_once()


def test_webhook_deliver_success():
    from backend.application.webhooks import WebhookService
    svc = WebhookService()
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch("backend.services.webhooks.requests.post", return_value=mock_response) as mock_post:
        svc._deliver("http://example.com/hook", {"event": "test", "data": {}})
    mock_post.assert_called_once()


def test_webhook_deliver_http_error():
    from backend.application.webhooks import WebhookService
    svc = WebhookService()
    mock_response = MagicMock()
    mock_response.status_code = 500
    with patch("backend.services.webhooks.requests.post", return_value=mock_response):
        # Should not raise
        svc._deliver("http://example.com/hook", {"event": "test"})


def test_webhook_deliver_network_exception():
    from backend.application.webhooks import WebhookService
    svc = WebhookService()
    with patch("backend.services.webhooks.requests.post", side_effect=ConnectionError("refused")):
        # Should not raise
        svc._deliver("http://example.com/hook", {"event": "test"})


def test_webhook_static_url_from_env(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "http://static-hook.example.com/webhook")
    from backend.application import webhooks as wh_mod
    import importlib
    importlib.reload(wh_mod)
    svc = wh_mod.WebhookService()
    assert "http://static-hook.example.com/webhook" in svc.urls
