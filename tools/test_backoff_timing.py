
import unittest
import time
from backend.core.retry import Retry

# Global variable to capture timestamps
call_timestamps = []

def failing_service():
    call_timestamps.append(time.time())
    raise ConnectionError("Simulated Failure")

class TestBackoffTiming(unittest.TestCase):
    def setUp(self):
        call_timestamps.clear()
        
    def test_backoff_progression(self):
        print("\n[Test] Testing Exponential Backoff Timing...")
        
        # Configure: initial=0.5s, factor=2.0, tries=3, jitter=False (for deterministic timing check)
        retry_decorator = Retry(
            max_retries=3, 
            initial_delay=0.5, 
            backoff_factor=2.0, 
            jitter=False # Disable jitter to assert exact ranges
        )
        
        decorated_func = retry_decorator(failing_service)
        
        try:
            decorated_func()
        except ConnectionError:
            pass # Expected after retries exhausted
            
        self.assertEqual(len(call_timestamps), 4, "Should have called 1 initial + 3 retries")
        
        # Calculate intervals
        intervals = []
        for i in range(1, len(call_timestamps)):
            intervals.append(call_timestamps[i] - call_timestamps[i-1])
            
        print(f"[Test] Intervals: {[f'{x:.2f}s' for x in intervals]}")
        
        # Check progression
        # Attempt 1 -> 2: wait ~0.5s
        # Attempt 2 -> 3: wait ~1.0s
        # Attempt 3 -> 4: wait ~2.0s
        
        self.assertTrue(0.5 <= intervals[0] < 0.7, f"First interval {intervals[0]:.2f}s should be ~0.5s")
        self.assertTrue(1.0 <= intervals[1] < 1.3, f"Second interval {intervals[1]:.2f}s should be ~1.0s")
        self.assertTrue(2.0 <= intervals[2] < 2.5, f"Third interval {intervals[2]:.2f}s should be ~2.0s")
        
        print("[Test] SUCCESS: Backoff doubled (0.5s -> 1.0s -> 2.0s) correctly.")

if __name__ == "__main__":
    unittest.main()
