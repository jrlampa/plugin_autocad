import os
import sys
import time
from pathlib import Path

# Add src/backend to path
sys.path.append(str(Path(__file__).parent.parent / "src" / "backend"))

from backend.services.cache import cache_service
from backend.core.utils import cache_dir

def test_tiered_cache():
    print("--- Phase 26: Tiered Cache Test ---")
    
    test_key = "test_cache_key_v2"
    test_data = {"hello": "world", "timestamp": time.time()}
    
    # 1. Clear existing cache
    print("Clearing existing cache...")
    file_path = cache_dir() / f"{test_key}.json"
    if file_path.exists():
        file_path.unlink()
    if cache_service.redis:
        cache_service.redis.delete(test_key)

    # 2. Verify Miss
    print("Verifying miss...")
    assert cache_service.get(test_key) is None, "Should be a miss"

    # 3. Set Cache
    print("Setting cache...")
    cache_service.set(test_key, test_data)

    # 4. Verify L1 Hit (Redis)
    if cache_service.redis:
        print("Verifying L1 (Redis) hit...")
        # Delete from file to ensure we hit Redis
        if file_path.exists():
            file_path.unlink()
        
        hit = cache_service.get(test_key)
        assert hit and hit["hello"] == "world", "Redis hit failed"
        print(" [OK] Redis hit verified.")
    else:
        print(" [SKIP] Redis hit (Redis not available).")

    # 5. Verify L2 Hit (Filesystem)
    print("Verifying L2 (Filesystem) hit...")
    # Repopulate file, clear Redis
    cache_service.set(test_key, test_data)
    if cache_service.redis:
        cache_service.redis.delete(test_key)
    
    hit = cache_service.get(test_key)
    assert hit and hit["hello"] == "world", "Filesystem hit failed"
    print(" [OK] Filesystem hit verified.")
    
    # 6. Verify Read-through (Filesystem -> Redis)
    if cache_service.redis:
        print("Verifying read-through population...")
        # Check if Redis was repopulated by the previous 'get'
        redis_data = cache_service.redis.get(test_key)
        assert redis_data is not None, "Redis should have been repopulated"
        print(" [OK] Read-through verified.")

    print("\n--- PASSED: Tiered Cache verified. ---")

if __name__ == "__main__":
    test_tiered_cache()
