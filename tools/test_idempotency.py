import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path
sys.path.append(str(Path("src/backend").absolute()))

try:
    from backend.core.bus import InMemoryEventBus
    from backend.core.interfaces import ICache

    print("--- Phase 33: Idempotency Logic Test ---")

    class MockCache(ICache):
        def __init__(self):
            self.store = {}
            
        def get(self, key: str) -> Optional[Any]:
            val = self.store.get(key)
            print(f"[MockCache] get({key}) -> {val}")
            return val

        def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
            print(f"[MockCache] set({key}, {value})")
            self.store[key] = value

    mock_cache = MockCache()
    bus = InMemoryEventBus(cache=mock_cache)
    
    received_events = []
    def handler(payload: Dict[str, Any]):
        received_events.append(payload)
        print(f"[Handler] Processed event: {payload}")

    bus.subscribe("test_dedup", handler)

    # 1. First event: Should pass
    print("\n1. Publishing first event (Key: A)...")
    bus.publish("test_dedup", {"msg": "first"}, idempotency_key="A")
    
    # 2. Duplicate event: Should be blocked
    print("\n2. Publishing duplicate event (Key: A)...")
    bus.publish("test_dedup", {"msg": "duplicate"}, idempotency_key="A")

    # 3. Different event: Should pass
    print("\n3. Publishing new event (Key: B)...")
    bus.publish("test_dedup", {"msg": "second"}, idempotency_key="B")

    if len(received_events) == 2:
        print("\n[PASS] Correctly processed 2 unique events and suppressed 1 duplicate.")
    else:
        print(f"\n[FAIL] Expected 2 processed events, got {len(received_events)}.")
        sys.exit(1)

    print("\n--- PASSED: Idempotency Logic Verified ---")
    sys.exit(0)

except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    sys.exit(1)
