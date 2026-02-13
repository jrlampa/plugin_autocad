import unittest
from fastapi.testclient import TestClient
import os
import json
import math
from unittest.mock import patch, MagicMock

# Set environment variable before importing app
os.environ["SISRUA_AUTH_TOKEN"] = "test-token"

from backend.api import app, _run_prepare_job_sync
from backend.services.jobs import job_store, cancellation_tokens
from backend.core.utils import sanitize_jsonable, read_cache, write_cache
from backend.models import CadFeature, PrepareJobRequest

class TestApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.auth_headers = {"X-SisRua-Token": "test-token"}
        # Clear job store for each test
        job_store.clear()
        cancellation_tokens.clear()

    def test_health_check(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_auth_check_success(self):
        response = self.client.get("/api/v1/auth/check", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_auth_check_failure(self):
        response = self.client.get("/api/v1/auth/check", headers={"X-SisRua-Token": "wrong"})
        self.assertEqual(response.status_code, 401)

    @patch('backend.api.prepare_osm_compute')
    def test_prepare_osm_direct(self, mock_compute):
        mock_compute.return_value = {"features": []}
        payload = {"latitude": -21.0, "longitude": -41.0, "radius": 100}
        response = self.client.post("/api/v1/prepare/osm", json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"features": []})

    @patch('backend.api.prepare_geojson_compute')
    def test_prepare_geojson_direct(self, mock_compute):
        mock_compute.return_value = {"features": []}
        payload = {"geojson": {"type": "FeatureCollection", "features": []}}
        response = self.client.post("/api/v1/prepare/geojson", json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"features": []})

    def test_create_prepare_job(self):
        payload = {"kind": "osm", "latitude": -21.0, "longitude": -41.0, "radius": 100}
        # Mock init_job inside threading? No, it's called before threading.
        # But threading might fail if we don't mock the target or valid inputs.
        # We want to test the endpoint response, not the thread execution.
        response = self.client.post("/api/v1/jobs/prepare", json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("job_id", data)
        self.assertEqual(data["kind"], "osm")

    def test_get_job_status(self):
        job_id = "test-job"
        job_store[job_id] = {"job_id": job_id, "kind": "osm", "status": "completed", "progress": 1.0}
        response = self.client.get(f"/api/v1/jobs/{job_id}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")

    def test_get_job_not_found(self):
        response = self.client.get("/api/v1/jobs/non-existent", headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)

    def test_job_cancel(self):
        job_id = "test-job-id"
        job_store[job_id] = {"status": "running", "job_id": job_id, "kind": "osm"}
        response = self.client.delete(f"/api/v1/jobs/{job_id}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        # cancellation should set status to failed immediately in the endpoint logic?
        # api.py: cancellation_tokens[job_id] = True; job["status"] = "failed"
        self.assertTrue(cancellation_tokens.get(job_id))
        self.assertEqual(job_store[job_id]["status"], "failed")

    def test_job_cancel_not_found(self):
        response = self.client.delete("/api/v1/jobs/non-existent", headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)

    @patch('backend.api.elevation_tool_service.get_elevation_at_point')
    def test_elevation_query(self, mock_get):
        mock_get.return_value = 123.45
        payload = {"latitude": -21.0, "longitude": -41.0}
        response = self.client.post("/api/v1/tools/elevation/query", json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["elevation"], 123.45)

    def test_sanitize_jsonable(self):
        self.assertEqual(sanitize_jsonable(float('nan')), None)
        self.assertEqual(sanitize_jsonable({"a": float('inf')}), {"a": None})
        self.assertEqual(sanitize_jsonable([1, 2, float('-inf')]), [1, 2, None])
        self.assertEqual(sanitize_jsonable(CadFeature(name="test")), {"feature_type": "Polyline", "layer": None, "name": "test", "highway": None, "width_m": None, "coords_xy": None, "insertion_point_xy": None, "block_name": None, "block_filepath": None, "rotation": None, "scale": None, "color": None, "elevation": None, "slope": None})

    @patch('backend.api.prepare_osm_compute')
    def test_run_prepare_job_sync_osm(self, mock_compute):
        mock_compute.return_value = {"features": []}
        job_id = "job-123"
        job_store[job_id] = {"status": "pending"}
        payload = PrepareJobRequest(kind="osm", latitude=0, longitude=0, radius=100)
        _run_prepare_job_sync(job_id, payload)
        self.assertEqual(job_store[job_id]["status"], "completed")

    def test_run_prepare_job_sync_cancelled(self):
        job_id = "job-cancel"
        job_store[job_id] = {"status": "pending"}
        cancellation_tokens[job_id] = True
        payload = PrepareJobRequest(kind="osm", latitude=0, longitude=0, radius=100)
        # Should catch RuntimeError and set status to failed
        _run_prepare_job_sync(job_id, payload)
        self.assertEqual(job_store[job_id]["status"], "failed")
        self.assertEqual(job_store[job_id]["error"], "CANCELLED")

    def test_run_prepare_job_sync_value_error(self):
        job_id = "job-ve"
        job_store[job_id] = {"status": "pending"}
        payload = PrepareJobRequest(kind="osm", latitude=None, longitude=0, radius=100)
        _run_prepare_job_sync(job_id, payload)
        self.assertEqual(job_store[job_id]["status"], "failed")
        self.assertIn("latitude/longitude/radius são obrigatórios", job_store[job_id]["error"])

    def test_cache_real_logic(self):
        key = "test_real_cache"
        data = {"hello": "world"}
        write_cache(key, data)
        read = read_cache(key)
        self.assertEqual(read["hello"], "world")
        # Test missing cache
        self.assertIsNone(read_cache("definitely_not_there"))

    @patch('backend.api.prepare_geojson_compute')
    def test_run_prepare_job_sync_geojson(self, mock_compute):
        mock_compute.return_value = {"features": []}
        job_id = "job-geojson"
        job_store[job_id] = {"status": "pending"}
        payload = PrepareJobRequest(kind="geojson", geojson={"type": "FeatureCollection", "features": []})
        _run_prepare_job_sync(job_id, payload)
        self.assertEqual(job_store[job_id]["status"], "completed")

    def test_run_prepare_job_sync_invalid_kind(self):
        job_id = "job-invalid"
        job_store[job_id] = {"status": "pending"}
        payload = MagicMock()
        payload.kind = "invalid"
        _run_prepare_job_sync(job_id, payload)
        self.assertEqual(job_store[job_id]["status"], "failed")
        self.assertIn("kind inválido", job_store[job_id]["error"])

    def test_require_token_failure(self):
        response = self.client.get("/api/v1/auth/check") # No header
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()
