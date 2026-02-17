import subprocess
import os
import sys
import time
import requests
import json
import socket
from pathlib import Path

# --- Configuration ---
UTM_QUERY = "24K 0216330 7528658"
RADIUS = 2000
TIMEOUT_E2E = 120 # Overpass can be slow
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_EXE = REPO_ROOT / "bundle-template" / "sisRUA.bundle" / "Contents" / "backend" / "sisrua_backend.exe"
LOCAL_SISRUA_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "sisRUA"

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def find_token():
    token_file = LOCAL_SISRUA_DIR / "backend_token.txt"
    # We might need to wait for the backend to write it if it's a fresh start
    for _ in range(10):
        if token_file.exists():
            return token_file.read_text().strip()
        time.sleep(1)
    return None

def run_audit():
    print("="*60)
    print("      sisRUA ROBUST E2E AUDIT SUITE (V1.1)")
    print("="*60)
    
    if not BACKEND_EXE.exists():
        print(f"[ERROR] Backend EXE not found at: {BACKEND_EXE}")
        print("Please run build_release.cmd first.")
        return False
    
    port = get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    token = "audit_token_" + socket.gethostname() # Deterministic but unique enough
    
    print(f"[*] Starting Backend EXE on port {port}...")
    # Start process with pipes to capture output and set the token
    env = os.environ.copy()
    env["SISRUA_AUTH_TOKEN"] = token
    env["SISRUA_TESTING"] = "true" # Suppress IPC server to avoid pipe busy errors
    
    backend_proc = subprocess.Popen(
        [str(BACKEND_EXE), "--host", "127.0.0.1", "--port", str(port), "--log-level", "info"],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        cwd=str(BACKEND_EXE.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env
    )
    
    def log_reader(pipe, prefix):
        for line in iter(pipe.readline, ''):
            # Print only relevant info to avoid noise
            if "INFO" in line or "ERROR" in line or "WARNING" in line:
                print(f"    [{prefix}] {line.strip()}")
            
    import threading
    threading.Thread(target=log_reader, args=(backend_proc.stdout, "BACKEND-OUT"), daemon=True).start()
    threading.Thread(target=log_reader, args=(backend_proc.stderr, "BACKEND-ERR"), daemon=True).start()

    try:
        # 1. Wait for Health
        print("[*] Waiting for backend to become healthy...")
        start_wait = time.time()
        healthy = False
        while time.time() - start_wait < 120:
            try:
                resp = requests.get(f"{base_url}/api/v1/health", timeout=2)
                if resp.status_code == 200:
                    healthy = True
                    break
                else:
                    print(f"    [WAIT] Status: {resp.status_code}")
            except Exception as e:
                # Quietly wait
                pass
            time.sleep(2)
        
        if not healthy:
            print(f"[FAIL] Backend failed to start or respond to health check within 120s at {base_url}.")
            return False
        
        # 2. Use the token we set
        headers = {"X-SisRua-Token": token}
        print(f"[*] Auth Token established: {token}")
        
        # 3. Geocode lookup for UTM
        print(f"[*] Step 1/3: Geocoding UTM Coordinate: {UTM_QUERY}")
        geo_resp = requests.get(f"{base_url}/api/v1/tools/geocode", params={"query": UTM_QUERY}, headers=headers, timeout=10)
        if geo_resp.status_code != 200:
            print(f"[FAIL] Geocode failed: {geo_resp.text}")
            return False
            
        geo_data = geo_resp.json()
        lat, lon = geo_data["latitude"], geo_data["longitude"]
        print(f"    [OK] Resolved to: {lat:.6f}, {lon:.6f} ({geo_data['display_name']})")
        
        # 4. Robust Street Generation (2km radius)
        print(f"[*] Step 2/3: Generating Street Data (Radius: {RADIUS}m)... This covers ~12.5km2 area.")
        start_gen = time.time()
        prep_payload = {
            "latitude": lat,
            "longitude": lon,
            "radius": RADIUS
        }
        
        prep_resp = requests.post(f"{base_url}/api/v1/prepare/osm", json=prep_payload, headers=headers, timeout=TIMEOUT_E2E)
        
        duration = time.time() - start_gen
        if prep_resp.status_code != 200:
            print(f"[FAIL] Street generation failed after {duration:.2f}s: {prep_resp.text}")
            return False
            
        prep_data = prep_resp.json()
        features = prep_data.get("features", [])
        print(f"    [OK] Generation complete in {duration:.2f}s.")
        print(f"    [DATA] Total Features: {len(features)}")
        
        # 5. Data Integrity Audit
        print("[*] Step 3/3: Auditing Data Integrity...")
        if not features:
            print("[FAIL] Generated feature set is empty.")
            return False
            
        layers = set(f["layer"] for f in features)
        print(f"    [AUDIT] Layers found: {', '.join(layers)}")
        
        vias = [f for f in features if "Vias" in f["layer"]]
        infra = [f for f in features if "Infraestrutura" in f["layer"]]
        contorno = [f for f in features if "CURVAS_NIVEL" in f["layer"]]
        
        print(f"    [METRICS] Vias (Polylines): {len(vias)}")
        print(f"    [METRICS] Infrastructure Assets: {len(infra)}")
        print(f"    [METRICS] Contour Lines: {len(contorno)}")
        
        if len(vias) == 0:
            print("[FAIL] Robustness check failed: No street geometry found in 2km radius.")
            return False
            
        # Check for Audit Summary
        audit_summary = prep_data.get("audit_summary", {})
        if audit_summary:
            print(f"    [AUDIT] Compliance Score: {audit_summary.get('compliance_score', 'N/A')}")
        
        print("="*60)
        print("      PASS: E2E ROBUSTNESS AUDIT COMPLETED SUCCESSFULLY")
        print("="*60)
        return True

    except Exception as e:
        print(f"[FATAL] Audit crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("[*] Shutting down backend...")
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=5)
        except:
            backend_proc.kill()

if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)
