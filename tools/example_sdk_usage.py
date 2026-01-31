import sys
import os
import time
from pathlib import Path

# Add src/sdk to PYTHONPATH to find sisrua_sdk
# and src/backend to find backend.models
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT / "src" / "sdk"))
sys.path.append(str(ROOT / "src" / "backend"))

from sisrua_sdk import SisRuaClient

def main():
    print("--- Phase 27: Internal SDK Usage Example ---")
    
    # Configuration
    BASE_URL = "http://127.0.0.1:8000/api/v1"
    AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN", "test-token-123")
    
    client = SisRuaClient(BASE_URL, AUTH_TOKEN)
    
    # 1. Health Check
    print("Step 1: Checking API Health...")
    if not client.check_health():
        print(" [ERROR] API is offline or unreachable.")
        return
    print(" [OK] API is healthy.")

    # 2. Elevation Query
    print("Step 2: Querying elevation for Campos, Brazil...")
    elev = client.get_elevation(-21.76, -41.32)
    print(f" [RESULT] Elevation: {elev}m" if elev else " [ERROR] Failed to get elevation.")

    # 3. Create OSM Job
    print("Step 3: Creating OSM Job...")
    job = client.create_job("osm", latitude=-21.76, longitude=-41.32, radius=300)
    print(f" [OK] Job created: {job.job_id} (Status: {job.status})")

    # 4. Wait for Completion
    print("Step 4: Waiting for job completion...")
    final_status = client.wait_for_job(job.job_id, timeout=60, poll_interval=1.0)
    print(f" [DONE] Final Status: {final_status.status}")
    
    if final_status.status == "completed" and final_status.result:
        print(f" [RESULT] Features prepared: {len(final_status.result.features)}")
    elif final_status.error:
        print(f" [ERROR] Job failed: {final_status.error}")

    print("\n--- PASSED: SDK end-to-end flow verified. ---")

if __name__ == "__main__":
    main()
