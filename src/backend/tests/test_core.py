import pytest
import time
import math
from unittest.mock import MagicMock
from fastapi import HTTPException
from pydantic import ValidationError
from backend.shared.rate_limit import TokenBucket, RateLimiter
from backend.shared.utils import (
    cache_key, norm_optional_str, sanitize_jsonable, 
    get_color_from_elevation, estimate_width_m, get_layer_name
)
from backend.shared.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenException
from backend.domain.dto import (
    PrepareOsmRequest, ElevationQueryRequest, ElevationProfileRequest,
    PrepareJobRequest, WebhookRegistrationRequest,
)

# --- Rate Limit Tests ---
def test_token_bucket():
    bucket = TokenBucket(capacity=2, refill_rate=1.0)
    assert bucket.consume(1) is True
    assert bucket.consume(1) is True
    assert bucket.consume(1) is False
    
    # Wait for refill
    time.sleep(1.1)
    assert bucket.consume(1) is True

import asyncio

def test_rate_limiter():
    limiter = RateLimiter(calls=2, period=1)
    request = MagicMock()
    request.client.host = "127.0.0.1"
    
    async def run_test():
        await limiter(request)
        await limiter(request)
        with pytest.raises(HTTPException) as excinfo:
            await limiter(request)
        assert excinfo.value.status_code == 429
        
    asyncio.run(run_test())

# --- Utils Tests ---
def test_cache_key():
    key1 = cache_key(["a", "b"])
    key2 = cache_key(["a", "b"])
    key3 = cache_key(["a", "c"])
    assert key1 == key2
    assert key1 != key3
    assert len(key1) == 64

def test_norm_optional_str():
    assert norm_optional_str("  hello  ") == "hello"
    assert norm_optional_str(None) is None
    assert norm_optional_str(float('nan')) is None
    assert norm_optional_str("NaN") is None
    assert norm_optional_str("") is None

def test_sanitize_jsonable():
    data = {
        "a": 1,
        "b": float('nan'),
        "c": [1, 2, float('inf')],
        "d": {"nested": float('-inf')}
    }
    sanitized = sanitize_jsonable(data)
    assert sanitized["b"] is None
    assert sanitized["c"][2] is None
    assert sanitized["d"]["nested"] is None
    assert sanitized["a"] == 1

def test_get_color_from_elevation():
    assert get_color_from_elevation(10, 0, 100) == "5" # Blue (ratio 0.1)
    assert get_color_from_elevation(95, 0, 100) == "1" # Red (ratio 0.95)
    assert get_color_from_elevation(50, 0, 100) == "3" # Green (ratio 0.5)
    assert get_color_from_elevation(10, 10, 10) == "255,255,255"

def test_estimate_width_m():
    assert estimate_width_m(None, "residential") == 5.0
    assert estimate_width_m(None, "motorway") == 20.0
    assert estimate_width_m(None, "unknown") == 6.0
    assert estimate_width_m(None, None) is None

# --- Layer Mapping Tests ---
def test_get_layer_name_highway():
    assert get_layer_name({"highway": "residential"}) == "SISRUA_Vias_Locais"
    assert get_layer_name({"highway": "primary"}) == "SISRUA_Vias_Arteriais"
    assert get_layer_name({"highway": "motorway"}) == "SISRUA_Vias_Expressas"

def test_get_layer_name_unknown_returns_default():
    assert get_layer_name({"amenity": "bench"}) == "SISRUA_DEFAULT"
    assert get_layer_name({}) == "SISRUA_DEFAULT"

def test_get_layer_name_custom_default():
    result = get_layer_name({"unknown": "tag"}, default="MY_LAYER")
    assert result == "MY_LAYER"

# --- Coordinate Validation Tests ---
def test_prepare_osm_request_valid():
    req = PrepareOsmRequest(latitude=-22.15018, longitude=-42.92185, radius=500.0)
    assert req.latitude == -22.15018
    assert req.longitude == -42.92185
    assert req.radius == 500.0

def test_prepare_osm_request_invalid_latitude():
    with pytest.raises(ValidationError):
        PrepareOsmRequest(latitude=91.0, longitude=-42.92185, radius=500.0)

def test_prepare_osm_request_invalid_longitude():
    with pytest.raises(ValidationError):
        PrepareOsmRequest(latitude=-22.15018, longitude=181.0, radius=500.0)

def test_prepare_osm_request_invalid_radius_zero():
    with pytest.raises(ValidationError):
        PrepareOsmRequest(latitude=-22.15018, longitude=-42.92185, radius=0.0)

def test_prepare_osm_request_invalid_radius_too_large():
    with pytest.raises(ValidationError):
        PrepareOsmRequest(latitude=-22.15018, longitude=-42.92185, radius=50001.0)

def test_elevation_query_request_valid():
    req = ElevationQueryRequest(latitude=-22.15018, longitude=-42.92185)
    assert req.latitude == -22.15018

def test_elevation_query_request_invalid_lat():
    with pytest.raises(ValidationError):
        ElevationQueryRequest(latitude=-91.0, longitude=-42.92185)

def test_elevation_query_request_invalid_lon():
    with pytest.raises(ValidationError):
        ElevationQueryRequest(latitude=-22.15018, longitude=-181.0)

def test_elevation_profile_request_valid():
    req = ElevationProfileRequest(path=[[-22.15018, -42.92185], [-22.16, -42.93]])
    assert len(req.path) == 2

def test_elevation_profile_request_too_few_points():
    with pytest.raises(ValidationError):
        ElevationProfileRequest(path=[[-22.15018, -42.92185]])

def test_elevation_profile_request_invalid_lat_in_path():
    with pytest.raises(ValidationError):
        ElevationProfileRequest(path=[[-91.0, -42.92185], [-22.16, -42.93]])

def test_elevation_profile_request_invalid_lon_in_path():
    with pytest.raises(ValidationError):
        ElevationProfileRequest(path=[[-22.15018, -181.0], [-22.16, -42.93]])

def test_prepare_job_request_osm_valid():
    req = PrepareJobRequest(kind="osm", latitude=-22.15018, longitude=-42.92185, radius=100.0)
    assert req.kind == "osm"
    assert req.radius == 100.0

def test_prepare_job_request_osm_invalid_coords():
    with pytest.raises(ValidationError):
        PrepareJobRequest(kind="osm", latitude=200.0, longitude=-42.92185, radius=100.0)

# --- Circuit Breaker Tests ---
def test_circuit_breaker_flow():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    
    def failing_func():
        raise ValueError("Fail")
    
    decorated = cb(failing_func)
    
    # First failure
    with pytest.raises(ValueError):
        decorated()
    assert cb.state == CircuitState.CLOSED
    
    # Second failure -> Open
    with pytest.raises(ValueError):
        decorated()
    assert cb.state == CircuitState.OPEN
    
    # Calls blocked
    with pytest.raises(CircuitBreakerOpenException):
        decorated()
        
    # Wait for recovery
    time.sleep(0.15)
    
    # Next call -> Half Open
    def success_func():
        return "ok"
    
    decorated_success = cb(success_func)
    assert decorated_success() == "ok"
    assert cb.state == CircuitState.CLOSED


# --- WebhookRegistrationRequest Validation Tests ---
def test_webhook_valid_https_url():
    req = WebhookRegistrationRequest(url="https://example.com/webhook")
    assert req.url == "https://example.com/webhook"

def test_webhook_valid_http_url():
    req = WebhookRegistrationRequest(url="http://internal.corp/hook")
    assert req.url == "http://internal.corp/hook"

def test_webhook_invalid_scheme_rejected():
    with pytest.raises(ValidationError):
        WebhookRegistrationRequest(url="ftp://evil.com/steal")

def test_webhook_file_scheme_rejected():
    with pytest.raises(ValidationError):
        WebhookRegistrationRequest(url="file:///etc/passwd")

def test_webhook_no_scheme_rejected():
    with pytest.raises(ValidationError):
        WebhookRegistrationRequest(url="evil.com/steal")

def test_webhook_events_sanitized():
    req = WebhookRegistrationRequest(
        url="https://example.com/hook",
        events=["  project_saved  ", "job_completed", "x" * 200],
    )
    assert req.events is not None
    assert req.events[0] == "project_saved"
    assert req.events[1] == "job_completed"
    assert len(req.events[2]) == 128  # Truncado a 128 chars

def test_webhook_events_empty_list_becomes_none():
    req = WebhookRegistrationRequest(
        url="https://example.com/hook",
        events=["   ", ""],
    )
    assert req.events is None

def test_webhook_events_none_allowed():
    req = WebhookRegistrationRequest(url="https://example.com/hook", events=None)
    assert req.events is None


# --- AuditLogger.list_logs() Tests ---

def test_audit_list_logs_returns_list():
    """list_logs() should return a list (even empty when DB has no records)."""
    from unittest.mock import patch, MagicMock
    from backend.shared.audit import AuditLogger

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = []

    with patch("backend.core.audit.get_db_connection", return_value=mock_conn):
        logger_inst = AuditLogger.__new__(AuditLogger)
        logger_inst._secret = b"x" * 32
        result = logger_inst.list_logs(limit=10)

    assert isinstance(result, list)


def test_audit_list_logs_returns_correct_fields():
    """list_logs() should include audit_id, event_type, entity_type, entity_id, data."""
    import json
    from unittest.mock import patch, MagicMock
    from backend.shared.audit import AuditLogger

    fake_row = (
        42,           # audit_id
        "CREATE",     # event_type
        "Project",    # entity_type
        "proj-001",   # entity_id
        "system",     # user_id
        1700000000.0, # timestamp
        json.dumps({"project_name": "Rua A"}),  # data_json
        "2026-01-01 00:00:00",  # created_at
    )
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = [fake_row]

    with patch("backend.core.audit.get_db_connection", return_value=mock_conn):
        logger_inst = AuditLogger.__new__(AuditLogger)
        logger_inst._secret = b"x" * 32
        result = logger_inst.list_logs(limit=5)

    assert len(result) == 1
    entry = result[0]
    assert entry["audit_id"] == 42
    assert entry["event_type"] == "CREATE"
    assert entry["entity_type"] == "Project"
    assert entry["entity_id"] == "proj-001"
    assert entry["data"] == {"project_name": "Rua A"}


def test_audit_list_logs_entity_type_filter():
    """list_logs(entity_type=...) should pass entity_type as SQL parameter."""
    from unittest.mock import patch, MagicMock
    from backend.shared.audit import AuditLogger

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = []

    with patch("backend.core.audit.get_db_connection", return_value=mock_conn):
        logger_inst = AuditLogger.__new__(AuditLogger)
        logger_inst._secret = b"x" * 32
        logger_inst.list_logs(entity_type="CadFeature", limit=5)

    # entity_type should appear twice in params (column = ? OR ? IS NULL)
    call_args = mock_conn.execute.call_args
    sql_params = call_args[0][1]
    assert sql_params.count("CadFeature") == 2


def test_audit_list_logs_entity_id_filter():
    """list_logs(entity_id=...) should pass entity_id as SQL parameter."""
    from unittest.mock import patch, MagicMock
    from backend.shared.audit import AuditLogger

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = []

    with patch("backend.core.audit.get_db_connection", return_value=mock_conn):
        logger_inst = AuditLogger.__new__(AuditLogger)
        logger_inst._secret = b"x" * 32
        logger_inst.list_logs(entity_id="proj-999")

    call_args = mock_conn.execute.call_args
    sql_params = call_args[0][1]
    assert sql_params.count("proj-999") == 2


def test_audit_list_logs_event_type_filter():
    """list_logs(event_type=...) should pass event_type as SQL parameter."""
    from unittest.mock import patch, MagicMock
    from backend.shared.audit import AuditLogger

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = []

    with patch("backend.core.audit.get_db_connection", return_value=mock_conn):
        logger_inst = AuditLogger.__new__(AuditLogger)
        logger_inst._secret = b"x" * 32
        logger_inst.list_logs(event_type="DELETE")

    call_args = mock_conn.execute.call_args
    sql_params = call_args[0][1]
    assert sql_params.count("DELETE") == 2


def test_audit_list_logs_combined_filters():
    """list_logs() with all three filters should pass all values as parameters."""
    from unittest.mock import patch, MagicMock
    from backend.shared.audit import AuditLogger

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = []

    with patch("backend.core.audit.get_db_connection", return_value=mock_conn):
        logger_inst = AuditLogger.__new__(AuditLogger)
        logger_inst._secret = b"x" * 32
        logger_inst.list_logs(entity_type="Project", event_type="CREATE", limit=10)

    call_args = mock_conn.execute.call_args
    sql_params = call_args[0][1]
    assert sql_params.count("Project") == 2
    assert sql_params.count("CREATE") == 2
    assert 10 in sql_params


def test_audit_list_logs_invalid_json_data_handled():
    """list_logs() should tolerate invalid data_json without raising an exception."""
    from unittest.mock import patch, MagicMock
    from backend.shared.audit import AuditLogger

    fake_row = (1, "DELETE", "Project", "p1", "system", 0.0, "not-json", None)
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = [fake_row]

    with patch("backend.core.audit.get_db_connection", return_value=mock_conn):
        logger_inst = AuditLogger.__new__(AuditLogger)
        logger_inst._secret = b"x" * 32
        result = logger_inst.list_logs()

    # Should not raise — returns empty dict for malformed JSON
    assert result[0]["data"] == {}


def test_ipc_server_noop_on_non_windows():
    """IpcServer.start() should be a no-op on non-Windows systems (Linux/macOS)."""
    import sys
    from unittest.mock import patch
    from backend.shared.ipc import IpcServer

    server = IpcServer("test-token")
    # Patch _WIN32_AVAILABLE to False (simulating Linux)
    with patch("backend.core.ipc._WIN32_AVAILABLE", False):
        server.start()

    # Should NOT have started a thread
    assert server.thread is None
    assert server.running is False


# --- database.py: init_schema() Tests ---

def test_fresh_db_has_projects_table(tmp_path):
    """A new connection should automatically create the Projects table."""
    from backend.shared.database import get_db_connection
    import os
    db_path = tmp_path / "test.db"
    os.environ["SISRUA_TESTING"] = "true"
    conn = get_db_connection(db_path=db_path)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "Projects" in tables
    finally:
        conn.close()


def test_fresh_db_has_auditlog_table(tmp_path):
    """A new connection should automatically create the AuditLog table."""
    from backend.shared.database import get_db_connection
    import os
    db_path = tmp_path / "test_audit.db"
    os.environ["SISRUA_TESTING"] = "true"
    conn = get_db_connection(db_path=db_path)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "AuditLog" in tables
    finally:
        conn.close()


def test_fresh_db_has_cadfeatures_table(tmp_path):
    """A new connection should automatically create the CadFeatures table."""
    from backend.shared.database import get_db_connection
    import os
    db_path = tmp_path / "test_cad.db"
    os.environ["SISRUA_TESTING"] = "true"
    conn = get_db_connection(db_path=db_path)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "CadFeatures" in tables
    finally:
        conn.close()


def test_fresh_db_audit_insert_works(tmp_path):
    """INSERT into AuditLog must succeed on a fresh DB without prior seed."""
    from backend.shared.database import get_db_connection
    import os
    import time
    db_path = tmp_path / "test_insert.db"
    os.environ["SISRUA_TESTING"] = "true"
    conn = get_db_connection(db_path=db_path)
    try:
        conn.execute(
            "INSERT INTO AuditLog (event_type, entity_type, entity_id, user_id, timestamp, data_json, signature) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("CREATE", "Project", "p-1", "system", time.time(), '{"test": 1}', "sig123"),
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM AuditLog").fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_fresh_db_project_insert_works(tmp_path):
    """INSERT into Projects must succeed on a fresh DB without prior seed."""
    from backend.shared.database import get_db_connection
    import os
    db_path = tmp_path / "test_proj.db"
    os.environ["SISRUA_TESTING"] = "true"
    conn = get_db_connection(db_path=db_path)
    try:
        conn.execute(
            "INSERT INTO Projects (project_id, project_name, crs_out, version) VALUES (?, ?, ?, ?)",
            ("uuid-test", "My Project", "EPSG:31983", 1),
        )
        conn.commit()
        row = conn.execute("SELECT project_name FROM Projects WHERE project_id = ?", ("uuid-test",)).fetchone()
        assert row[0] == "My Project"
    finally:
        conn.close()
