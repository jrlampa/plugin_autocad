"""
tests/test_jobs_tools_coverage.py
Targeted tests for services/jobs.py and routes/tools.py uncovered branches.
Coverage targets:
  - services/jobs.py  73% → 94%   (stale idem key, cancelled update, check_cancellation, cleanup+idem, persist batch)
  - routes/tools.py   69% → 100%  (ValueError/Exception paths in query_elevation, query_profile)
  - routes/jobs.py    77% → 100%  (dedup hit, cancel not-found)
"""
from __future__ import annotations

import importlib
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("SISRUA_TESTING", "true")
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-token-jobs")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_jobs_mod():
    """Return a fresh backend.services.jobs module (clears job_store/idempotency_map)."""
    import backend.application.jobs as m
    importlib.reload(m)
    return m


# ===========================================================================
# services/jobs.py — pure unit tests
# ===========================================================================


class TestJobsServiceBranches:
    """Exercises uncovered branches in services/jobs.py."""

    def test_init_job_stale_idempotency_key(self):
        """Line 83: stale key in idempotency_map (job_id not in job_store) → removed, new job created."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        stale_key = "stale-key-abc"
        # Manually plant a stale entry
        jmod.idempotency_map[stale_key] = "nonexistent-job-id"

        job_id, is_new = jmod.init_job("geojson", idempotency_key=stale_key)

        assert is_new is True, "Stale key must produce a new job"
        assert job_id in jmod.job_store, "New job must exist in job_store"
        # The stale key should have been cleaned and replaced with the new job_id
        assert jmod.idempotency_map.get(stale_key) == job_id

    def test_update_job_on_cancelled_job_is_noop(self):
        """Line 122-123: updating a cancelled job returns immediately without changes."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        job_id, _ = jmod.init_job("geojson")
        jmod.job_store[job_id]["cancelled"] = True
        original_message = jmod.job_store[job_id]["message"]

        bus = MagicMock()
        jmod.update_job(job_id, bus, status="completed", message="should-not-apply")

        # Status and message must be unchanged
        assert jmod.job_store[job_id]["status"] == "queued"
        assert jmod.job_store[job_id]["message"] == original_message
        bus.publish.assert_not_called()

    def test_update_job_nonexistent_job_is_noop(self):
        """Line 122: updating a job that doesn't exist returns immediately."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        bus = MagicMock()
        jmod.update_job("nonexistent-id", bus, status="completed")  # must not raise
        bus.publish.assert_not_called()

    def test_check_cancellation_raises_for_cancelled_job(self):
        """Line 158-159: check_cancellation raises RuntimeError when job is cancelled."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        job_id, _ = jmod.init_job("osm")
        jmod.job_store[job_id]["cancelled"] = True

        with pytest.raises(RuntimeError, match="CANCELLED"):
            jmod.check_cancellation(job_id)

    def test_check_cancellation_noop_for_active_job(self):
        """check_cancellation does nothing for a running (non-cancelled) job."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        job_id, _ = jmod.init_job("osm")
        jmod.check_cancellation(job_id)  # must not raise

    def test_cancel_job_already_completed_returns_false(self):
        """Line 169-170: cancel_job returns False for completed jobs."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        job_id, _ = jmod.init_job("geojson")
        jmod.job_store[job_id]["status"] = "completed"

        result = jmod.cancel_job(job_id)
        assert result is False

    def test_cancel_job_already_failed_returns_false(self):
        """cancel_job returns False for already-failed jobs."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        job_id, _ = jmod.init_job("geojson")
        jmod.job_store[job_id]["status"] = "failed"

        result = jmod.cancel_job(job_id)
        assert result is False

    def test_cancel_job_nonexistent_returns_false(self):
        """cancel_job returns False for nonexistent job_id."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        result = jmod.cancel_job("does-not-exist")
        assert result is False

    def test_cleanup_expired_jobs_removes_idempotency_key(self):
        """Lines 191-193: cleanup removes idempotency_map entry for expired jobs."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        idem_key = "cleanup-test-key"
        job_id, _ = jmod.init_job("geojson", idempotency_key=idem_key)

        # Mark as completed and make it look old (2 hours ago)
        jmod.job_store[job_id]["status"] = "completed"
        jmod.job_store[job_id]["updated_at"] = time.time() - 7200

        removed = jmod.cleanup_expired_jobs(max_age_seconds=3600)

        assert removed == 1
        assert job_id not in jmod.job_store
        assert idem_key not in jmod.idempotency_map

    def test_cleanup_expired_jobs_keeps_recent_jobs(self):
        """cleanup_expired_jobs leaves recently completed jobs alone."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        job_id, _ = jmod.init_job("geojson")
        jmod.job_store[job_id]["status"] = "completed"
        # updated just now

        removed = jmod.cleanup_expired_jobs(max_age_seconds=3600)
        assert removed == 0
        assert job_id in jmod.job_store

    def test_persist_jobs_batch_exception_handled(self, tmp_path, monkeypatch):
        """Lines 61-62: _persist_jobs_batch swallows DB exceptions gracefully."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        def bad_conn():
            raise OSError("disk full")

        monkeypatch.setattr("backend.services.jobs.get_db_connection", bad_conn)

        # Must not raise — exception is logged and swallowed
        jmod._persist_jobs_batch([{"job_id": "x", "kind": "geojson", "status": "completed",
                                    "created_at": 0.0, "updated_at": 0.0, "result": None}])

    def test_update_job_publishes_event_on_status_change(self):
        """Line 136: update_job publishes event when status transitions."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        job_id, _ = jmod.init_job("geojson")
        bus = MagicMock()

        jmod.update_job(job_id, bus, status="processing")

        bus.publish.assert_called_once()
        call_args = bus.publish.call_args
        assert call_args[0][0] == "job_started"

    def test_update_job_no_event_for_same_status(self):
        """No event published when transitioning to the same status."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        job_id, _ = jmod.init_job("geojson")
        # Job starts at "queued"
        bus = MagicMock()
        jmod.update_job(job_id, bus, status="queued")  # same status → no publish

        bus.publish.assert_not_called()


# ===========================================================================
# routes/tools.py — error path tests via TestClient
# ===========================================================================


def _make_tools_client(monkeypatch, tmp_path):
    """Build TestClient for api.app, returns (client, token)."""
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "tools-token")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from backend import api as api_mod
    importlib.reload(api_mod)
    from fastapi.testclient import TestClient
    return TestClient(api_mod.app, base_url="http://localhost:8000"), "tools-token"


class TestToolsRouteErrorPaths:
    """Exercises lines 40-44 and 62-66 in routes/tools.py."""

    def test_query_elevation_value_error_returns_400(self, monkeypatch, tmp_path):
        """Line 40-41: ValueError in ElevationService → 400."""
        client, token = _make_tools_client(monkeypatch, tmp_path)

        import backend.routes.tools as tools_mod
        import backend.application.elevation as elev_mod

        class _BadElevValError:
            def __init__(self, *a, **kw): pass
            def get_elevation_at_point(self, lat, lon):
                raise ValueError("coordinate out of range")

        monkeypatch.setattr(elev_mod, "ElevationService", _BadElevValError)
        importlib.reload(tools_mod)

        r = client.post(
            "/api/v1/tools/elevation/query",
            json={"latitude": -22.15018, "longitude": -42.92185},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 400
        assert "coordinate out of range" in r.json()["detail"]

    def test_query_elevation_generic_error_returns_500(self, monkeypatch, tmp_path):
        """Line 42-44: generic Exception in ElevationService → 500."""
        client, token = _make_tools_client(monkeypatch, tmp_path)

        import backend.application.elevation as elev_mod

        class _BadElevGeneric:
            def __init__(self, *a, **kw): pass
            def get_elevation_at_point(self, lat, lon):
                raise RuntimeError("DEM unavailable")

        monkeypatch.setattr(elev_mod, "ElevationService", _BadElevGeneric)

        r = client.post(
            "/api/v1/tools/elevation/query",
            json={"latitude": -22.15018, "longitude": -42.92185},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 500
        assert "elevação" in r.json()["detail"].lower()

    def test_query_profile_value_error_returns_400(self, monkeypatch, tmp_path):
        """Line 62-63: ValueError in profile ElevationService → 400."""
        client, token = _make_tools_client(monkeypatch, tmp_path)

        import backend.application.elevation as elev_mod

        class _BadProfileValError:
            def __init__(self, *a, **kw): pass
            def get_elevation_profile(self, coords):
                raise ValueError("empty path not allowed")

        monkeypatch.setattr(elev_mod, "ElevationService", _BadProfileValError)

        r = client.post(
            "/api/v1/tools/elevation/profile",
            json={"path": [[-22.15018, -42.92185], [-22.15118, -42.92285]]},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 400
        assert "empty path not allowed" in r.json()["detail"]

    def test_query_profile_generic_error_returns_500(self, monkeypatch, tmp_path):
        """Line 64-66: generic Exception in profile → 500."""
        client, token = _make_tools_client(monkeypatch, tmp_path)

        import backend.application.elevation as elev_mod

        class _BadProfileGeneric:
            def __init__(self, *a, **kw): pass
            def get_elevation_profile(self, coords):
                raise RuntimeError("rasterio crash")

        monkeypatch.setattr(elev_mod, "ElevationService", _BadProfileGeneric)

        r = client.post(
            "/api/v1/tools/elevation/profile",
            json={"path": [[-22.15018, -42.92185], [-22.15118, -42.92285]]},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 500
        assert "perfil" in r.json()["detail"].lower()


# ===========================================================================
# routes/jobs.py — uncovered branches
# ===========================================================================


class TestJobsRouteBranches:
    """Exercises lines 86 and 96-101 in routes/jobs.py."""

    def _make_jobs_client(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SISRUA_AUTH_TOKEN", "jobs-route-token")
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        from backend import api as api_mod
        importlib.reload(api_mod)
        # Clear rate limiter state so tests don't interfere with each other
        import backend.shared.rate_limit as rl_mod
        rl_mod._limiters.clear()
        from fastapi.testclient import TestClient
        client = TestClient(api_mod.app, base_url="http://localhost:8000")
        client.headers.update({"Origin": "http://localhost:8000"})
        return client, "jobs-route-token"

    def test_duplicate_prepare_job_deduped(self, monkeypatch, tmp_path):
        """Line 86: second identical job request returns existing job_id (is_new=False)."""
        client, token = self._make_jobs_client(monkeypatch, tmp_path)
        headers = {"X-SisRua-Token": token}
        payload = {
            "kind": "geojson",
            "geojson": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"layer": "V_TEST"},
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[-42.92185, -22.15018], [-42.92085, -22.14918]],
                        },
                    }
                ],
            },
        }

        r1 = client.post("/api/v1/jobs/prepare", json=payload, headers=headers)
        r2 = client.post("/api/v1/jobs/prepare", json=payload, headers=headers)

        assert r1.status_code == 200
        assert r2.status_code == 200
        # Both requests return the same job_id (idempotent)
        assert r1.json()["job_id"] == r2.json()["job_id"]

    def test_cancel_nonexistent_job_returns_404(self, monkeypatch, tmp_path):
        """Lines 96-101: cancelling a non-existent job returns 404."""
        client, token = self._make_jobs_client(monkeypatch, tmp_path)
        headers = {"X-SisRua-Token": token}

        r = client.delete("/api/v1/jobs/nonexistent-job-id", headers=headers)
        assert r.status_code == 404
        assert "não encontrado" in r.json()["detail"].lower()

    def test_cancel_completed_job_returns_ok(self, monkeypatch, tmp_path):
        """cancel_job_endpoint returns 200 when cancel_job returns False for completed job (job still exists)."""
        import backend.application.jobs as jmod
        importlib.reload(jmod)

        client, token = self._make_jobs_client(monkeypatch, tmp_path)
        headers = {"X-SisRua-Token": token}

        # Create a completed job directly in job_store
        job_id, _ = jmod.init_job("geojson")
        jmod.job_store[job_id]["status"] = "completed"

        r = client.delete(f"/api/v1/jobs/{job_id}", headers=headers)
        # cancel_job returns False (already completed), but job exists → 200
        assert r.status_code == 200

    def test_get_job_nonexistent_returns_404(self, monkeypatch, tmp_path):
        """Line 86: GET /api/v1/jobs/{id} for unknown id → 404."""
        client, token = self._make_jobs_client(monkeypatch, tmp_path)
        r = client.get("/api/v1/jobs/does-not-exist-at-all",
                       headers={"X-SisRua-Token": token})
        assert r.status_code == 404
        assert "não encontrado" in r.json()["detail"].lower()

    def test_create_job_init_raises_value_error_returns_422(self, monkeypatch, tmp_path):
        """Lines 70-72: ValueError during init_job → 422."""
        client, token = self._make_jobs_client(monkeypatch, tmp_path)

        import backend.routes.jobs as route_mod
        monkeypatch.setattr(route_mod, "init_job",
                            lambda *a, **kw: (_ for _ in ()).throw(ValueError("bad kind")))

        r = client.post(
            "/api/v1/jobs/prepare",
            json={"kind": "geojson", "geojson": {"type": "FeatureCollection", "features": []}},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 422

    def test_create_job_init_raises_runtime_returns_500(self, monkeypatch, tmp_path):
        """Lines 73-75: unexpected Exception during init_job → 500."""
        client, token = self._make_jobs_client(monkeypatch, tmp_path)

        import backend.routes.jobs as route_mod
        monkeypatch.setattr(route_mod, "init_job",
                            lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("db down")))

        r = client.post(
            "/api/v1/jobs/prepare",
            json={"kind": "geojson", "geojson": {"type": "FeatureCollection", "features": []}},
            headers={"X-SisRua-Token": token},
        )
        assert r.status_code == 500
