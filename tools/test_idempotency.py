
import os
import sys

# Set Env Var BEFORE imports
os.environ["SISRUA_AUTH_TOKEN"] = "test-token"

# Add src/backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/backend')))

import unittest
from fastapi.testclient import TestClient
from backend.api import app

class TestIdempotency(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear Rate Limiters to avoid pollution from other tests
        from backend.core.rate_limit import _limiters
        _limiters.clear()
        # Clear idempotency map? It's in-memory. 
        # But we interact via API, so we can't easily clear it without restarting app or accessing internal var.
        # We will use random payloads to ensure uniqueness per test run.
        
    def test_idempotent_creation(self):
        from unittest import mock
        
        with mock.patch("backend.api.AUTH_TOKEN", "test-token"):
            import uuid
            # Unique coords
            lat = -21.0
            lon = -41.0 + (uuid.uuid4().int % 1000) / 1000.0
            
            payload = {
                "kind": "osm", 
                "latitude": lat, 
                "longitude": lon, 
                "radius": 100
            }
            
            print("\n[Test] Sending Request 1...")
            resp1 = self.client.post("/api/v1/jobs/prepare", json=payload, headers={"X-SisRua-Token": "test-token"}) 
            
            if resp1.status_code != 200:
                print(f"[Test] Failed req 1: {resp1.status_code} - {resp1.text}")
                
            json1 = resp1.json()
            job_id_1 = json1.get("job_id")
            print(f"[Test] Request 1 Job ID: {job_id_1}")
            self.assertIsNotNone(job_id_1)
            
            print("[Test] Sending Request 1 (Duplicate)...")
            resp2 = self.client.post("/api/v1/jobs/prepare", json=payload, headers={"X-SisRua-Token": "test-token"}) 
            json2 = resp2.json()
            job_id_2 = json2.get("job_id")
            print(f"[Test] Request 2 Job ID: {job_id_2}")
            
            self.assertEqual(job_id_1, job_id_2, "Job IDs should MATCH for identical payloads")
            
            print("[Test] Sending Request 3 (Different Payload)...")
            payload3 = payload.copy()
            payload3["radius"] = 200 # Change
            resp3 = self.client.post("/api/v1/jobs/prepare", json=payload3, headers={"X-SisRua-Token": "test-token"}) 
            json3 = resp3.json()
            job_id_3 = json3.get("job_id")
            print(f"[Test] Request 3 Job ID: {job_id_3}")
            
            self.assertNotEqual(job_id_1, job_id_3, "Job ID should be NEW for different payload")
            
            print("[Test] SUCCESS: Idempotency Verified.")

if __name__ == "__main__":
    # Ensure Auth is bypassed or configured
    os.environ["SISRUA_AUTH_TOKEN"] = "" # Disable auth for test
    unittest.main()
