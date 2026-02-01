import time
import unittest
from backend.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, CircuitState

class TestCircuitBreaker(unittest.TestCase):
    def test_circuit_breaker_flow(self):
        print("--- Testing Circuit Breaker State Machine ---")
        
        # 1. Setup a breaker with low threshold
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
        
        # Mock function that fails
        @cb
        def fragile_function(should_fail=False):
            if should_fail:
                raise ValueError("Oops")
            return "Success"
        
        # 2. Closed State (Normal)
        print("[1] Testing CLOSED state...")
        self.assertEqual(fragile_function(should_fail=False), "Success")
        self.assertEqual(cb.state, CircuitState.CLOSED)
        
        # 3. Trigger Failures
        print("[2] Triggering failures...")
        try: fragile_function(should_fail=True)
        except ValueError: pass
        
        try: fragile_function(should_fail=True)
        except ValueError: pass
        
        # Should be OPEN now (threshold=2 reached)
        print(f"[Check] State is now: {cb.state}")
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        # 4. Verify Fail Fast (Open State)
        print("[3] Verifying Fail Fast (OPEN state)...")
        with self.assertRaises(CircuitBreakerOpenException):
             # Even successful call should be blocked
            fragile_function(should_fail=False)
            
        # 5. Wait for Recovery Timeout
        print("[4] Waiting for recovery timeout (1.1s)...")
        time.sleep(1.1)
        
        # Should be HALF-OPEN on next call (handled inside _check_state which runs before logic)
        # But simply calling it will check state.
        # Ideally, we call it, it transitions to HALF_OPEN, runs function.
        # If success -> CLOSED.
        
        print("[5] Verifying Recovery (HALF-OPEN -> CLOSED)...")
        result = fragile_function(should_fail=False)
        self.assertEqual(result, "Success")
        self.assertEqual(cb.state, CircuitState.CLOSED)
        print("[PASS] Circuit recovered properly.")

if __name__ == "__main__":
    unittest.main()
