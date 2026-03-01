"""
tests/test_cache_ai_export.py
Split from test_coverage_boost.py (>500 lines rule).
Covers: services/cache.py, services/ai.py, services/export_service.py
"""
import os
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# services/cache.py — CacheService (67% → 90%+)
# ---------------------------------------------------------------------------

def test_cache_set_and_get_filesystem(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.application.cache import CacheService
    svc = CacheService()
    svc.set("test:key", {"answer": 42})
    result = svc.get("test:key")
    assert result == {"answer": 42}


def test_cache_get_missing_returns_none(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.application.cache import CacheService
    svc = CacheService()
    result = svc.get("nonexistent:key")
    assert result is None


def test_cache_set_overwrite(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.application.cache import CacheService
    svc = CacheService()
    svc.set("overwrite:key", {"v": 1})
    svc.set("overwrite:key", {"v": 2})
    result = svc.get("overwrite:key")
    assert result == {"v": 2}


def test_cache_key_sanitization(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.application.cache import CacheService
    svc = CacheService()
    # Keys with special characters should still work
    svc.set("key/with/slashes:and?query=params", {"safe": True})
    result = svc.get("key/with/slashes:and?query=params")
    assert result == {"safe": True}


def test_cache_redis_set_skipped_when_none(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.application.cache import CacheService
    svc = CacheService()
    svc.redis = None  # no Redis configured
    # Should not raise
    svc.set("key", {"val": 1})


def test_cache_redis_get_skipped_when_none(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.application.cache import CacheService
    svc = CacheService()
    svc.redis = None
    svc.set("key_for_redis_test", {"v": 99})
    result = svc.get("key_for_redis_test")
    assert result == {"v": 99}


def test_cache_redis_fallback_on_exception(tmp_path):
    os.environ["LOCALAPPDATA"] = str(tmp_path)
    from backend.application.cache import CacheService
    svc = CacheService()
    # Simulate a Redis client that raises on get
    mock_redis = MagicMock()
    mock_redis.get.side_effect = RuntimeError("Redis connection refused")
    svc.redis = mock_redis
    # Should fall back to filesystem — set via filesystem first
    svc.redis = None
    svc.set("fallback_key", {"fallback": True})
    svc.redis = mock_redis
    # get should fall back to filesystem even when Redis raises
    result = svc.get("fallback_key")
    assert result == {"fallback": True}


# ---------------------------------------------------------------------------
# services/ai.py — AiService (68% → 92%+)
# ---------------------------------------------------------------------------

def test_ai_no_api_key_returns_message():
    os.environ.pop("GROQ_API_KEY", None)
    from backend.application.ai import AiService
    svc = AiService()
    AiService._notified_missing_key = False
    svc.client = None
    result = svc.generate_response("Hello?")
    assert result == "AI Service is not configured (missing API key)."


def test_ai_with_api_key_calls_groq():
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
        from backend.application.ai import AiService
        with patch("backend.application.ai.Groq") as mock_groq:
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
        from backend.application.ai import AiService
        with patch("backend.application.ai.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            mock_client.chat.completions.create.side_effect = RuntimeError("API down")

            svc = AiService()
            result = svc.generate_response("test")

    assert result == "I'm having trouble connecting to my brain right now. Please try again later."


def test_ai_rag_context_with_job_id():
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
        from backend.application.ai import AiService
        with patch("backend.application.ai.Groq") as mock_groq, \
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
        from backend.application.ai import AiService
        with patch("backend.application.ai.Groq") as mock_groq, \
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
# services/export_service.py — ExportService (50% → 96%+)
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
    from backend.application.export_service import ExportService
    db_path = _make_export_db(tmp_path, "geoj-1")
    svc = ExportService(db_path=db_path)
    path = svc.export_project_to_geojson("geoj-1")
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["type"] == "FeatureCollection"
    assert data["features"] == []
    assert data["metadata"]["project_id"] == "geoj-1"


def test_export_geojson_not_found(tmp_path):
    import pytest
    from backend.application.export_service import ExportService
    from backend.application.projects import NotFoundError
    db_path = _make_export_db(tmp_path, "geoj-exists")
    svc = ExportService(db_path=db_path)
    with pytest.raises(NotFoundError):
        svc.export_project_to_geojson("nonexistent-project")


def test_export_geojson_with_features(tmp_path):
    from backend.application.export_service import ExportService
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
    from backend.application.export_service import ExportService
    db_path = _make_export_db(tmp_path, "gpkg-1")
    svc = ExportService(db_path=db_path)
    path = svc.export_project_to_geopackage("gpkg-1")
    assert path.exists()
    assert path.suffix == ".gpkg"


def test_export_geopackage_not_found(tmp_path):
    import pytest
    from backend.application.export_service import ExportService
    from backend.application.projects import NotFoundError
    db_path = _make_export_db(tmp_path, "gpkg-exists")
    svc = ExportService(db_path=db_path)
    with pytest.raises(NotFoundError):
        svc.export_project_to_geopackage("ghost-project")


def test_export_dxf_empty_project(tmp_path):
    from backend.application.export_service import ExportService
    db_path = _make_export_db(tmp_path, "dxf-1")
    svc = ExportService(db_path=db_path)
    path = svc.export_project_to_dxf("dxf-1", escala=1000)
    assert path.exists()
    assert path.suffix == ".dxf"


def test_export_dxf_not_found(tmp_path):
    import pytest
    from backend.application.export_service import ExportService
    from backend.application.projects import NotFoundError
    db_path = _make_export_db(tmp_path, "dxf-exists")
    svc = ExportService(db_path=db_path)
    with pytest.raises(NotFoundError):
        svc.export_project_to_dxf("nonexistent")


def test_export_dxf_with_polyline_feature(tmp_path):
    from backend.application.export_service import ExportService
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
    content = path.read_text(encoding="utf-8", errors="ignore")
    assert "ENDSEC" in content  # DXF structural marker
