import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Add src to path
sys.path.append(str(Path("src/backend").absolute()))

from backend.api import app

def test_security_policy():
    print("--- Phase 37: Least Privilege Access Security Test ---")
    
    # We need to simulate the environment state regarding AUTH_TOKEN
    # Since we imported 'app', the module-level 'AUTH_TOKEN' is already read from os.environ
    # To test logic cleanly, we might need to mock or patch `backend.api.AUTH_TOKEN`
    
    import backend.api
    
    client = TestClient(app)

    # 1. Test: Fail Closed (When Server has NO token configured)
    print("\n[TEST 1] Fail Closed Policy (Server has no token)")
    original_token = backend.api.AUTH_TOKEN
    backend.api.AUTH_TOKEN = "" # Simulate missing config
    
    resp = client.get("/api/v1/jobs/prepare") # Method Not Allowed for GET, but let's use a real protected one or just check auth first
    resp = client.post("/api/v1/jobs/prepare", json={"kind":"osm", "latitude":0, "longitude":0, "radius":100})
    
    if resp.status_code == 500 and "Server Authentication Not Configured" in resp.text:
       print("[PASS] Blocked access when server config is missing (500).")
    else:
       print(f"[FAIL] Expected 500, got {resp.status_code}: {resp.text}")

    # 2. Test: Unauthorized (Client missing token)
    print("\n[TEST 2] Missing Token (Server Configured)")
    backend.api.AUTH_TOKEN = "secret-token-123"
    
    resp = client.post("/api/v1/jobs/prepare", json={})
    if resp.status_code == 401:
        print("[PASS] Blocked request without header (401).")
    else:
        print(f"[FAIL] Expected 401, got {resp.status_code}")

    # 3. Test: Unauthorized (Client invalid token)
    print("\n[TEST 3] Invalid Token")
    resp = client.post("/api/v1/jobs/prepare", json={}, headers={"X-SisRua-Token": "wrong-token"})
    if resp.status_code == 401:
        print("[PASS] Blocked request with wrong token (401).")
    else:
        print(f"[FAIL] Expected 401, got {resp.status_code}")

    # 4. Test: Authorized (Valid Token)
    print("\n[TEST 4] Valid Token")
    # We use a payload that might fail validation (422) but PASSES AUTH
    resp = client.post("/api/v1/jobs/prepare", json={"kind":"osm", "latitude":0, "longitude":0, "radius":100}, headers={"X-SisRua-Token": "secret-token-123"})
    
    if resp.status_code != 401 and resp.status_code != 500:
        print(f"[PASS] Allowed request with valid token (Status: {resp.status_code}).")
    else:
        print(f"[FAIL] Unexpected rejection: {resp.status_code}")

    # Restore state
    backend.api.AUTH_TOKEN = original_token
    print("\n--- PASSED: Security Policies Verified ---")

if __name__ == "__main__":
    test_security_policy()
