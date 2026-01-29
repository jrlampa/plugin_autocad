import random
import json
import time
import requests
import os
import pathlib

def get_backend_url():
    # Try to find backend_port.txt in LocalAppData/sisRUA
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        port_file = pathlib.Path(local_app_data) / "sisRUA" / "backend_port.txt"
        if port_file.exists():
            port = port_file.read_text().strip()
            return f"http://127.0.0.1:{port}"
    return "http://127.0.0.1:61731" # Fallback

BASE_URL = get_backend_url()
AUTH_TOKEN = "test-token-123" # This might need to be dynamic too but test-token-123 is often used in tests

def get_auth_token():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        token_file = pathlib.Path(local_app_data) / "sisRUA" / "backend_token.txt"
        if token_file.exists():
            return token_file.read_text().strip()
    return AUTH_TOKEN

CURRENT_TOKEN = get_auth_token()
HEADERS = {"X-SisRua-Token": CURRENT_TOKEN}

def get_health():
    try:
        r = requests.get(f"{BASE_URL}/api/v1/health", timeout=2)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False

def run_fuzzy_json():
    print(f"\n>>> Starting FUZZY JSON test against {BASE_URL}...")
    garbage_inputs = [
        "not a json",
        "{malformed: json}",
        "[]",
        "null",
        "true",
        "{\"kind\": \"invalid_kind\"}",
        "{\"kind\": \"geojson\", \"geojson\": \"string_instead_of_obj\"}",
        "{\"kind\": \"osm\", \"latitude\": \"not_a_number\"}",
        "{\"kind\": \"osm\", \"latitude\": 99999999, \"longitude\": -99999999}", # Out of bounds
        "{\"kind\": \"geojson\", \"geojson\": {\"type\": \"Point\", \"coordinates\": [1.0, 2.0]}}" # Valid but check logic
    ]

    for i, data in enumerate(garbage_inputs):
        try:
            print(f" [Fuzz {i}] Sending: {data[:50]}...")
            r = requests.post(f"{BASE_URL}/api/v1/jobs/prepare", data=data, headers=HEADERS, timeout=3)
            # We expect 400, 422 or 401, but NEVER a 500 or process crash
            if r.status_code >= 500:
                print(f" [FAIL] Fuzz {i} caused a {r.status_code} Error!")
            else:
                print(f" [PASS] Status: {r.status_code}")
        except Exception as e:
            print(f" [ERROR] Fuzz {i} caused request failure: {e}")
        
        if not get_health():
            print(" [CRITICAL] Backend is UNHEALTHY after this request!")
            return False
    return True

def run_chaos_worker_stress():
    print("\n>>> Starting CHAOS WORKER STRESS test...")
    # Send a valid-ish request but with "poison" geometry (e.g., LineString with 1 point)
    poison_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"highway": "residential"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[0, 0]] # INVALID LineString (needs 2+ points)
                }
            }
        ]
    }
    
    try:
        payload = {"kind": "geojson", "geojson": poison_geojson}
        r = requests.post(f"{BASE_URL}/api/v1/jobs/prepare", json=payload, headers=HEADERS)
        if r.status_code == 200:
            job_id = r.json().get("job_id")
            print(f" [Chaos] Job {job_id} created. Monitoring for crash...")
            # Poll to see if it fails gracefully
            for _ in range(10):
                time.sleep(0.5)
                r2 = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}", headers=HEADERS)
                if r2.status_code != 200:
                    print(f"   [FAIL] Poll failed with {r2.status_code}")
                    break
                data = r2.json()
                status = data.get("status")
                print(f"   Status: {status}")
                if status in ("completed", "failed"):
                    if status == "failed":
                        print(f"   [OK] Job failed gracefully with error: {data.get('error')}")
                    break
    except Exception as e:
        print(f" [ERROR] Chaos test failed: {e}")

    return get_health()

if __name__ == "__main__":
    print("=== sisRUA ADVANCED TESTING EXPERIMENT (CHAOS/FUZZY) ===")
    print(f" Target: {BASE_URL}")
    if not get_health():
        print(f"ERRO: Backend em {BASE_URL} não está respondendo. Inicie o plugin/backend primeiro.")
    else:
        success = run_fuzzy_json()
        if success:
            success = run_chaos_worker_stress()
        
        if success:
            print("\n=== ALL RESEARCH TESTS PASSED (System is robust) ===")
        else:
            print("\n=== SYSTEM VULNERABILITY DETECTED ===")
