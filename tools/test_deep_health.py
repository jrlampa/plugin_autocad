
import unittest
from fastapi.testclient import TestClient
from backend.api import app

class TestDeepHealth(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
    def test_deep_health(self):
        # Fake Auth
        with unittest.mock.patch("backend.api.AUTH_TOKEN", "test-token"):
            headers = {"X-SisRua-Token": "test-token"}
            response = self.client.get("/api/v1/health/detailed", headers=headers)
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            print("Deep Health Response:", data)
            
            self.assertIn("status", data)
            self.assertIn("components", data)
            self.assertIn("database", data["components"])
            self.assertIn("cache", data["components"])
            
            # DB should be up in test environment
            self.assertEqual(data["components"]["database"]["status"], "up")

if __name__ == "__main__":
    import unittest.mock
    unittest.main()
