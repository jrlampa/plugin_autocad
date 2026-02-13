import sys
import threading
import time
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.append(str(Path("src/backend").absolute()))

def run_test():
    try:
        from backend.core.bus import InMemoryEventBus
        from backend.core.interfaces import IEventBus

        print("--- Phase 32: Pub/Sub Integration Test ---")

        bus = InMemoryEventBus()
        
        received_events = []

        def handler_1(payload: Dict[str, Any]):
            print(f"[Handler 1] Received payload: {payload}")
            received_events.append("h1")

        def handler_2(payload: Dict[str, Any]):
            print(f"[Handler 2] Received payload: {payload}")
            received_events.append("h2")

        def handler_error(payload: Dict[str, Any]):
            print("[Handler Error] I am going to crash now...")
            raise ValueError("Oops!")

        # Subscribe
        bus.subscribe("test_event", handler_1)
        bus.subscribe("test_event", handler_2)
        bus.subscribe("test_event", handler_error) # Should not block others

        # Publish
        print("Publishing 'test_event'...")
        bus.publish("test_event", {"msg": "Hello World"})

        # Check results
        if "h1" in received_events and "h2" in received_events:
            print("[PASS] Both handlers received the event.")
        else:
            print(f"[FAIL] Missing events. Received: {received_events}")
            return 1

        print("\n--- PASSED: Event Bus functions correctly ---")
        return 0

    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_test())
