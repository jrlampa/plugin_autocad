import requests
import os
import json

BASE_URL = "http://127.0.0.1:8000"
# Use the AUTH_HEADER_NAME found in C# (SisRuaPlugin.cs)
AUTH_HEADER_NAME = "X-SisRua-Token"
AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN", "test-token")
HEADERS = {AUTH_HEADER_NAME: AUTH_TOKEN}

def test_backward_compatibility():
    print("--- Phase 20: Backward Compatibility Test ---")
    
    # 1. Test /api/v1/health (no auth)
    print("\n[1/4] Testing /health (no auth)...")
    r = requests.get(f"{BASE_URL}/api/v1/health")
    print(f"Status: {r.status_code}, Body: {r.json()}")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # 2. Test /api/v1/auth/check (v0.4.0 headers)
    print("\n[2/4] Testing /auth/check (X-SisRua-Token header)...")
    r = requests.get(f"{BASE_URL}/api/v1/auth/check", headers=HEADERS)
    print(f"Status: {r.status_code}, Body: {r.json()}")
    assert r.status_code == 200

    # 3. Test Sync OSM Preparation (Legacy MVP Flow)
    print("\n[3/4] Testing sync /prepare/osm (Legacy MVP Payload)...")
    payload = {
        "latitude": -21.7634,
        "longitude": -41.3235,
        "radius": 100.0
    }
    r = requests.post(f"{BASE_URL}/api/v1/prepare/osm", json=payload, headers=HEADERS)
    print(f"Status: {r.status_code}")
    assert r.status_code == 200
    data = r.json()
    assert "features" in data
    print(f"Received {len(data['features'])} features.")
    
    # 4. Verify Phase 2 Data in Sync Response
    if len(data['features']) > 0:
        feat = data['features'][0]
        print(f"Sample Feature keys: {feat.keys()}")
        # Should have elevation if available
        if "elevation" in feat:
            print(f"Elevation detected: {feat['elevation']}")

    print("\n--- PASSED: v0.5.0 is backward compatible with v0.4.x clients ---")

if __name__ == "__main__":
    test_backward_compatibility()
