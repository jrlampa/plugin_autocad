from locust import HttpUser, task, between
import random

class SisRuaUser(HttpUser):
    wait_time = between(1, 5)

    @task(10)
    def check_health(self):
        """Simulate frequent health checks from AutoCAD plugin/Frontend."""
        self.client.get("/api/v1/health")

    @task(5)
    def check_auth(self):
        """Simulate authentication checks."""
        self.client.get("/api/v1/auth/check", headers={"X-SisRua-Token": "simulated-token"})

    @task(2)
    def prepare_job(self):
        """Simulate starting a data preparation job."""
        payload = {
            "kind": "osm",
            "latitude": -21.76 + (random.random() * 0.1),
            "longitude": -41.32 + (random.random() * 0.1),
            "radius": 500
        }
        self.client.post("/api/v1/jobs/prepare", json=payload, headers={"X-SisRua-Token": "simulated-token"})

    @task(3)
    def query_audit(self):
        """Simulate audit log queries."""
        self.client.get("/api/v1/audit/stats")
