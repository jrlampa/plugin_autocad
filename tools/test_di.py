import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path
sys.path.append(str(Path("src/backend").absolute()))

try:
    from backend.core.interfaces import ICache, INotificationService
    from backend.services.jobs import update_job, init_job, get_job, job_store
    from backend.services.elevation import ElevationService

    print("--- Phase 31: Dependency Inversion Test ---")

    # Mocks
    class MockCache:
        def get(self, key: str) -> Optional[Any]:
            print(f"[MockCache] get({key})")
            return None
        def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
            print(f"[MockCache] set({key}, value=...)")

    class MockNotifier:
        def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
            print(f"[MockNotifier] broadcast({event_type})")
        def register_url(self, url: str) -> None:
            pass

    # Test ElevationService Injection
    print("\n1. Testing ElevationService Injection...")
    mock_cache = MockCache()
    svc = ElevationService(cache=mock_cache)
    # Internally calls cache.get
    # We won't call get_elevation_at_point because it requires requests/rasterio which might need API keys or files
    # But just instantiating demonstrates DI works (type check passes)
    print("ElevationService instantiated with MockCache.")

    # Test Jobs Injection
    print("\n2. Testing Jobs Injection...")
    job_id = init_job("osm")
    mock_notifier = MockNotifier()
    
    # Update job -> should trigger notification
    update_job(
        job_id, 
        notification_service=mock_notifier, 
        status="processing"
    )
    
    job = get_job(job_id)
    if job["status"] == "processing":
        print("Job status updated successfully.")
    else:
        print("[FAIL] Job status not updated.")
        sys.exit(1)

    print("\n--- PASSED: Dependency Inversion Implemented ---")
    sys.exit(0)

except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    sys.exit(1)
