
import unittest
import threading
import time
from backend.core.lifecycle import job_registry, SHUTDOWN_EVENT

class TestGracefulShutdown(unittest.TestCase):
    def setUp(self):
        SHUTDOWN_EVENT.clear()
        
    def test_shutdown_aborts_threads(self):
        # 1. Create a dummy worker that checks for shutdown
        def worker():
            try:
                while not SHUTDOWN_EVENT.is_set():
                    time.sleep(0.1)
                print("Worker detected shutdown!")
            finally:
                job_registry.remove(threading.current_thread())
                
        t = threading.Thread(target=worker, daemon=True)
        job_registry.add(t)
        t.start()
        
        self.assertTrue(t.is_alive())
        
        # 2. Simulate Shutdown
        print("Triggering shutdown...")
        SHUTDOWN_EVENT.set()
        
        # 3. Wait for completion (Lifecycle Logic)
        job_registry.wait_for_completion(timeout=2.0)
        
        # 4. Assert thread is dead
        self.assertFalse(t.is_alive())
        print("Shutdown test passed.")

if __name__ == "__main__":
    unittest.main()
