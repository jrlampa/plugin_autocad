import unittest
import json
from fastapi.testclient import TestClient
from backend.api import app

# Simulate a v0.5.0 Client Payload (OSM Job)
V0_5_0_PAYLOAD = {
    "kind": "osm",
    "latitude": -21.76,
    "longitude": -41.32,
    "radius": 500.0
}

class TestContractCompatibility(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Mock AUTH
        self.headers = {"X-SisRua-Token": ""} # Assuming empty token allowed in dev or mocked
        # Note: In api.py, AUTH_TOKEN defaults to os.environ or "".
        # If strict token is enforced, I need to match it.
        # But _require_token says "if not AUTH_TOKEN: raise 500".
        # I should assume the environment sets one or I mock it.
        # api.py: AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN") or ""
        # if "" -> 500.
        # So I need to patch keys.
        
    def test_job_submission_v050(self):
        """
        Ensures that the v0.5.0 payload structure still works
        after Phase 47 refactor.
        """
        # Patch auth to be simple
        with unittest.mock.patch("backend.api.AUTH_TOKEN", "test-token"):
            headers = {"X-SisRua-Token": "test-token"}
            
            response = self.client.post("/api/v1/jobs/prepare", json=V0_5_0_PAYLOAD, headers=headers)
            
            if response.status_code != 200:
                print(f"Failed with {response.status_code}: {response.text}")
                
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            self.assertIn("job_id", data)
            self.assertIn(data["status"], ["queued", "processing"])
            print(f"[PASS] v0.5.0 Payload accepted. Job ID: {data['job_id']}")

            # Clean up job?
            # It runs in background thread. Ideally we cancel it or let it fail/finish.

if __name__ == "__main__":
    import unittest.mock
    unittest.main()
