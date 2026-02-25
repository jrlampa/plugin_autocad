"""
tests/test_remaining_paths.py
Targeted unit tests for code paths still below 90% coverage.

Modules: services/geojson.py, services/health.py, services/executor.py,
         core/retry.py, routes/projects.py, routes/webhooks.py, routes/prepare.py
"""
import importlib
import os
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# services/geojson.py — remaining branches (82% → 93%)
# ---------------------------------------------------------------------------

def test_first_lonlat_falsy_obj():
    from backend.application.geojson import first_lonlat
    assert first_lonlat(None) == (0.0, 0.0)
    assert first_lonlat({}) == (0.0, 0.0)


def test_first_lonlat_feature_collection_multilinestring():
    from backend.application.geojson import first_lonlat
    geo = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": {
            "type": "MultiLineString",
            "coordinates": [[[-42.9219, -22.1502], [-42.9218, -22.1503]]]
        }, "properties": {}}]
    }
    lon, lat = first_lonlat(geo)
    assert lon == pytest.approx(-42.9219)


def test_first_lonlat_feature_linestring():
    from backend.application.geojson import first_lonlat
    geo = {"type": "Feature",
           "geometry": {"type": "LineString",
                        "coordinates": [[-42.9219, -22.1502], [-42.9218, -22.1503]]},
           "properties": {}}
    assert first_lonlat(geo)[0] == pytest.approx(-42.9219)


def test_first_lonlat_feature_multilinestring():
    from backend.application.geojson import first_lonlat
    geo = {"type": "Feature",
           "geometry": {"type": "MultiLineString",
                        "coordinates": [[[-42.9219, -22.1502], [-42.9218, -22.1503]]]},
           "properties": {}}
    assert first_lonlat(geo)[0] == pytest.approx(-42.9219)


def test_first_lonlat_feature_point():
    from backend.application.geojson import first_lonlat
    geo = {"type": "Feature",
           "geometry": {"type": "Point", "coordinates": [-42.9219, -22.1502]},
           "properties": {}}
    lon, lat = first_lonlat(geo)
    assert lon == pytest.approx(-42.9219)
    assert lat == pytest.approx(-22.1502)


def test_prepare_geojson_single_feature_input():
    from backend.application.geojson import prepare_geojson_compute
    geo = {"type": "Feature",
           "geometry": {"type": "LineString",
                        "coordinates": [[-42.9219, -22.1502], [-42.9218, -22.1503]]},
           "properties": {"highway": "residential"}}
    with patch("backend.services.elevation.ElevationService.get_elevation_profile",
               return_value=[None]):
        result = prepare_geojson_compute(geo)
    assert len(result["features"]) == 1


def test_prepare_geojson_string_input_parsed():
    import json
    from backend.application.geojson import prepare_geojson_compute
    geo = {"type": "Feature",
           "geometry": {"type": "LineString",
                        "coordinates": [[-42.9219, -22.1502], [-42.9218, -22.1503]]},
           "properties": {}}
    with patch("backend.services.elevation.ElevationService.get_elevation_profile",
               return_value=[None]):
        result = prepare_geojson_compute(json.dumps(geo))
    assert result["features"] is not None


def test_prepare_geojson_multilinestring_geometry():
    from backend.application.geojson import prepare_geojson_compute
    geo = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {
        "type": "MultiLineString",
        "coordinates": [
            [[-42.9219, -22.1502], [-42.9218, -22.1503]],
            [[-42.9217, -22.1504], [-42.9216, -22.1505]]
        ]
    }, "properties": {"highway": "primary"}}]}
    with patch("backend.services.elevation.ElevationService.get_elevation_profile",
               return_value=[None, None]):
        result = prepare_geojson_compute(geo)
    assert len(result["features"]) == 2


def test_prepare_geojson_unsupported_root_type_raises_400():
    from backend.application.geojson import prepare_geojson_compute
    from fastapi import HTTPException
    geo = {"type": "Geometry", "coordinates": [-42.9, -22.1]}
    with pytest.raises(HTTPException) as exc_info:
        prepare_geojson_compute(geo)
    assert exc_info.value.status_code == 400


def test_prepare_geojson_elevation_exception_swallowed():
    from backend.application.geojson import prepare_geojson_compute
    geo = {"type": "Feature",
           "geometry": {"type": "LineString",
                        "coordinates": [[-42.9219, -22.1502], [-42.9218, -22.1503]]},
           "properties": {}}
    with patch("backend.services.elevation.ElevationService.get_elevation_profile",
               side_effect=RuntimeError("DEM unavailable")):
        result = prepare_geojson_compute(geo)
    assert "features" in result


def test_prepare_geojson_point_with_asset_mapping():
    from backend.application.geojson import prepare_geojson_compute
    geo = {"type": "FeatureCollection", "features": [{"type": "Feature",
           "geometry": {"type": "Point", "coordinates": [-42.9219, -22.1502]},
           "properties": {"amenity": "fire_hydrant"}}]}
    with patch("backend.services.elevation.ElevationService.get_elevation_profile",
               return_value=[]):
        result = prepare_geojson_compute(geo)
    assert len(result["features"]) == 1
    assert result["features"][0]["feature_type"] == "Point"


# ---------------------------------------------------------------------------
# services/health.py — exception paths (80% → 91%)
# ---------------------------------------------------------------------------

def test_health_database_exception():
    from backend.application.health import HealthService
    svc = HealthService()
    with patch("backend.services.health.get_db_connection",
               side_effect=RuntimeError("DB unreachable")):
        result = svc.check_health()
    assert result.components["database"].status == "down"
    assert "DB unreachable" in result.components["database"].details


def test_health_cache_exception():
    from backend.application.health import HealthService
    svc = HealthService()
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.fetchone.return_value = (1,)
    with patch("backend.services.health.get_db_connection", return_value=mock_conn), \
         patch("backend.services.health.cache_service") as mock_cache:
        mock_cache.set.side_effect = OSError("disk full")
        result = svc.check_health()
    assert result.components["cache"].status == "down"


def test_health_overall_status_down_when_db_fails():
    from backend.application.health import HealthService
    svc = HealthService()
    with patch("backend.services.health.get_db_connection",
               side_effect=RuntimeError("fail")):
        result = svc.check_health()
    assert result.status == "down"


def test_health_gis_deps_component_present():
    from backend.application.health import HealthService
    svc = HealthService()
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.fetchone.return_value = (1,)
    with patch("backend.services.health.get_db_connection", return_value=mock_conn), \
         patch("backend.services.health.cache_service") as mock_cache:
        mock_cache.set.return_value = None
        mock_cache.get.return_value = {"ts": 0}
        result = svc.check_health()
    assert "gis_core_deps" in result.components


# ---------------------------------------------------------------------------
# services/executor.py — job execution paths (81% → 93%)
# ---------------------------------------------------------------------------

def test_executor_invalid_kind_job_fails():
    from backend.application.executor import JobExecutor
    executor = JobExecutor(cache_service=MagicMock())
    mock_bus = MagicMock()
    with patch("backend.services.executor.update_job") as mock_update, \
         patch("backend.services.executor.check_cancellation"), \
         patch("backend.core.lifecycle.SHUTDOWN_EVENT") as mock_se:
        mock_se.is_set.return_value = False
        mock_payload = MagicMock()
        mock_payload.kind = "invalid_kind"
        executor.execute_prepare_job("job-err-1", mock_payload, mock_bus)
    last_call = mock_update.call_args_list[-1]
    assert last_call[1].get("status") == "failed"


def test_executor_cancelled_runtime_error():
    from backend.application.executor import JobExecutor
    executor = JobExecutor(cache_service=MagicMock())
    mock_bus = MagicMock()
    with patch("backend.services.executor.update_job") as mock_update, \
         patch("backend.services.executor.check_cancellation",
               side_effect=RuntimeError("CANCELLED")), \
         patch("backend.core.lifecycle.SHUTDOWN_EVENT") as mock_se:
        mock_se.is_set.return_value = False
        mock_payload = MagicMock(kind="osm", latitude=-22.15018,
                                 longitude=-42.92185, radius=100)
        executor.execute_prepare_job("job-can-1", mock_payload, mock_bus)
    assert any(c[1].get("error") == "CANCELLED" for c in mock_update.call_args_list)


def test_executor_shutdown_runtime_error():
    from backend.application.executor import JobExecutor
    executor = JobExecutor(cache_service=MagicMock())
    mock_bus = MagicMock()
    with patch("backend.services.executor.update_job") as mock_update, \
         patch("backend.services.executor.check_cancellation"), \
         patch("backend.core.lifecycle.SHUTDOWN_EVENT") as mock_se:
        mock_se.is_set.return_value = True
        mock_payload = MagicMock(kind="osm", latitude=-22.15018,
                                 longitude=-42.92185, radius=100)
        executor.execute_prepare_job("job-shut-1", mock_payload, mock_bus)
    assert any(c[1].get("error") == "SHUTDOWN" for c in mock_update.call_args_list)


def test_executor_other_runtime_error():
    from backend.application.executor import JobExecutor
    executor = JobExecutor(cache_service=MagicMock())
    mock_bus = MagicMock()
    with patch("backend.services.executor.update_job") as mock_update, \
         patch("backend.services.executor.check_cancellation",
               side_effect=RuntimeError("unexpected error")), \
         patch("backend.core.lifecycle.SHUTDOWN_EVENT") as mock_se:
        mock_se.is_set.return_value = False
        mock_payload = MagicMock(kind="osm", latitude=-22.15018,
                                 longitude=-42.92185, radius=100)
        executor.execute_prepare_job("job-err-rt", mock_payload, mock_bus)
    assert any(c[1].get("error") == "unexpected error"
               for c in mock_update.call_args_list)


# ---------------------------------------------------------------------------
# core/retry.py — jitter + sleep path outside TESTING mode (83% → 97%)
# ---------------------------------------------------------------------------

def test_retry_jitter_sleep_path_outside_testing_mode():
    from backend.shared.retry import Retry
    call_count = [0]

    @Retry(max_retries=1, initial_delay=0.01, jitter=True, exceptions=(ValueError,))
    def flaky():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ValueError("transient")
        return "ok"

    saved = os.environ.pop("SISRUA_TESTING", None)
    try:
        with patch("time.sleep") as mock_sleep:
            result = flaky()
        assert result == "ok"
        mock_sleep.assert_called_once()
    finally:
        if saved is not None:
            os.environ["SISRUA_TESTING"] = saved


# ---------------------------------------------------------------------------
# routes/projects.py — PUT error paths (80% → 95%)
# ---------------------------------------------------------------------------

def _make_client(monkeypatch, tmp_path, token: str):
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", token)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from backend import api as api_mod
    importlib.reload(api_mod)
    import backend.shared.rate_limit as rl_mod
    rl_mod._limiters.clear()
    from fastapi.testclient import TestClient
    client = TestClient(api_mod.app, base_url="http://localhost:8000")
    client.headers.update({"Origin": "http://localhost:8000"})
    return client, token


def test_put_project_returns_409_on_conflict(monkeypatch, tmp_path):
    from backend.application.projects import ConflictError
    client, token = _make_client(monkeypatch, tmp_path, "token-proj-rp")
    with patch("backend.routes.projects.project_service.update_project",
               side_effect=ConflictError("version mismatch")):
        resp = client.put(
            "/api/v1/projects/some-id",
            json={"project_name": "New Name", "version": 99},
            headers={"X-SisRua-Token": token},
        )
    assert resp.status_code == 409


def test_put_project_returns_404_on_not_found(monkeypatch, tmp_path):
    from backend.application.projects import NotFoundError
    client, token = _make_client(monkeypatch, tmp_path, "token-proj-nf")
    with patch("backend.routes.projects.project_service.update_project",
               side_effect=NotFoundError("not found")):
        resp = client.put(
            "/api/v1/projects/ghost-id",
            json={"project_name": "New Name", "version": 1},
            headers={"X-SisRua-Token": token},
        )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# routes/webhooks.py — emit_event endpoint (80% → 100%)
# ---------------------------------------------------------------------------

def test_emit_event_calls_webhook_broadcast(monkeypatch, tmp_path):
    client, token = _make_client(monkeypatch, tmp_path, "token-wh-emit")
    from backend import api as api_mod
    with patch.object(api_mod, "webhook_service") as mock_ws:
        resp = client.post(
            "/api/v1/events/emit",
            json={"event_type": "project_saved", "payload": {"project_id": "p1"}},
            headers={"X-SisRua-Token": token},
        )
    assert resp.status_code == 200
    mock_ws.broadcast.assert_called_once_with(
        "project_saved", {"project_id": "p1"}
    )


# ---------------------------------------------------------------------------
# routes/prepare.py — sync endpoints (81% → 95%)
# ---------------------------------------------------------------------------

_MOCK_PREPARE_RESULT = {
    "crs_out": "EPSG:31983", "feature_count": 3, "features": [],
    "bbox_utm": [788000.0, 7634000.0, 789000.0, 7635000.0],
    "center_utm": [788500.0, 7634500.0], "z_min": 0.0, "z_max": 0.0,
    "healed_nodes": 0, "topology_report": {}, "cache_hit": False, "elapsed_ms": 120.0,
}


def test_prepare_osm_endpoint_success(monkeypatch, tmp_path):
    client, token = _make_client(monkeypatch, tmp_path, "token-prep-osm")
    with patch("backend.routes.prepare.prepare_osm_compute",
               return_value=_MOCK_PREPARE_RESULT):
        resp = client.post(
            "/api/v1/prepare/osm",
            json={"latitude": -22.15018, "longitude": -42.92185, "radius": 100},
            headers={"X-SisRua-Token": token},
        )
    assert resp.status_code == 200


def test_prepare_geojson_endpoint_success(monkeypatch, tmp_path):
    client, token = _make_client(monkeypatch, tmp_path, "token-prep-geo")
    geo = {"type": "FeatureCollection", "features": [{"type": "Feature",
           "geometry": {"type": "LineString",
                        "coordinates": [[-42.9219, -22.1502], [-42.9218, -22.1503]]},
           "properties": {"highway": "residential"}}]}
    with patch("backend.routes.prepare.prepare_geojson_compute",
               return_value=_MOCK_PREPARE_RESULT):
        resp = client.post(
            "/api/v1/prepare/geojson",
            json={"geojson": geo},
            headers={"X-SisRua-Token": token},
        )
    assert resp.status_code == 200
