
import unittest
import time
from backend.core.retry import Retry

class TestRetry(unittest.TestCase):
    def test_transient_failure(self):
        # Allow 1 failure, then success
        self.attempts = 0
        
        @Retry(max_retries=3, initial_delay=0.1, jitter=False)
        def transient():
            self.attempts += 1
            if self.attempts < 2:
                raise ValueError("Transient Boom")
            return "Success"
            
        start = time.time()
        result = transient()
        duration = time.time() - start
        
        self.assertEqual(result, "Success")
        self.assertEqual(self.attempts, 2)
        # Should have slept at least 0.1s
        self.assertGreater(duration, 0.1)
        
    def test_persistent_failure(self):
        # Always fail
        self.attempts = 0
        
        @Retry(max_retries=2, initial_delay=0.1, jitter=False)
        def persistent():
            self.attempts += 1
            raise ValueError("Boom")
            
        with self.assertRaises(ValueError):
            persistent()
            
        # 1 initial + 2 retries = 3 attempts
        self.assertEqual(self.attempts, 3)

if __name__ == "__main__":
    unittest.main()
