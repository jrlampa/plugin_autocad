
import unittest
import time
from backend.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, CircuitState

# Mock Function
mock_call_count = 0
def external_service_mock():
    global mock_call_count
    mock_call_count += 1
    raise ConnectionError("Simulated Failure")

class TestCircuitBreakerGating(unittest.TestCase):
    def setUp(self):
        global mock_call_count
        mock_call_count = 0
        
    def test_gating_mechanism(self):
        # 1. Define Circuit Breaker with low threshold for testing
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2.0)
        
        # 2. Wrap the mock
        decorated_func = cb(external_service_mock)
        
        print("\n[Test] Triggering failures to open circuit...")
        
        # 3. Trigger Failures (3 times)
        for i in range(3):
            try:
                decorated_func()
            except ConnectionError:
                pass
        
        self.assertEqual(mock_call_count, 3, "Should have attempted 3 calls")
        self.assertEqual(cb.state, CircuitState.OPEN, "Circuit should be OPEN after 3 failures")
        
        print("[Test] Circuit is OPEN. Attempting 4th call...")
        
        # 4. Attempt 4th Call -> Should be BLOCKED (Gated)
        try:
            decorated_func()
            self.fail("Should have raised CircuitBreakerOpenException")
        except CircuitBreakerOpenException:
            print("[Test] SUCCESS: Call 4 was Gated via CircuitBreakerOpenException.")
            
        # 5. Verify Mock was NOT called for the 4th time
        self.assertEqual(mock_call_count, 3, "Mock should NOT have been incremented while OPEN")
        
        # 6. Wait for recovery
        print("[Test] Waiting for recovery timeout (2s)...")
        time.sleep(2.1)
        
        # 7. Attempt 5th Call -> Should be ALLOWED (Half-Open)
        print("[Test] Attempting 5th call (Half-Open probe)...")
        try:
            decorated_func()
        except ConnectionError:
            pass # It will fail again, re-opening circuit
            
        self.assertEqual(mock_call_count, 4, "Should have attempted probe call")
        self.assertEqual(cb.state, CircuitState.OPEN, "Circuit should be OPEN again after probe failure")
        print("[Test] SUCCESS: Probe went through and re-opened circuit.")

if __name__ == "__main__":
    unittest.main()
