
import unittest
import time
from backend.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, CircuitState

class TestCircuitBreaker(unittest.TestCase):
    def test_state_transition(self):
        # Create a breaker with low threshold and short timeout
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.2)
        
        # Test Function
        @cb
        def risky_action(should_fail=False):
            if should_fail:
                raise ValueError("Boom")
            return "Success"
            
        # 1. Normal State
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(risky_action(), "Success")
        
        # 2. Failures
        with self.assertRaises(ValueError):
            risky_action(should_fail=True)
        
        # Should still be closed (failures=1 < 2)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        
        with self.assertRaises(ValueError):
            risky_action(should_fail=True)
            
        # Should now be OPEN (failures=2 >= 2) -> But wait, logic fails ON failure.
        # Check logic: _on_failure -> failures+=1. if Closed and failures >= threshold -> Open.
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        # 3. Fast Fail
        with self.assertRaises(CircuitBreakerOpenException):
            risky_action() # Even if safe now, it blocks
            
        # 4. Recovery (Wait for timeout)
        time.sleep(0.3)
        
        # Next call should be allowed (Half-Open logic happens inside call)
        # _check_state -> if OPEN and timeout passed -> HALF_OPEN
        
        # Call successfully
        self.assertEqual(risky_action(), "Success")
        
        # Should be CLOSED again
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failures, 0)
        
    def test_half_open_failure(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        
        @cb
        def risky_action(should_fail=False):
            if should_fail:
                raise ValueError("Boom")
            return "Success"
            
        # Force Open
        try: risky_action(True) 
        except: pass
        try: risky_action(True) 
        except: pass
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        time.sleep(0.2)
        
        # Now Half-Open attempt fails
        with self.assertRaises(ValueError):
            risky_action(True)
            
        # Should revert to OPEN immediately
        self.assertEqual(cb.state, CircuitState.OPEN)

if __name__ == "__main__":
    unittest.main()
