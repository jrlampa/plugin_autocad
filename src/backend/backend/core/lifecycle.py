
import threading
import time
from typing import Set
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Global Event to signal application shutdown
SHUTDOWN_EVENT = threading.Event()

class ActiveJobRegistry:
    """Tracks active background threads to join them on shutdown."""
    def __init__(self):
        self._threads: Set[threading.Thread] = set()
        self._lock = threading.Lock()

    def add(self, t: threading.Thread):
        with self._lock:
            self._threads.add(t)

    def remove(self, t: threading.Thread):
        with self._lock:
            self._threads.discard(t)

    def wait_for_completion(self, timeout: float = 5.0):
        """Waits for active threads to finish after SHUTDOWN_EVENT is set."""
        start = time.time()
        with self._lock:
            threads = list(self._threads) # Copy
            
        count = len(threads)
        if count == 0:
            return

        logger.info("shutdown_waiting_threads", count=count, timeout=timeout)
        
        for t in threads:
            remaining = timeout - (time.time() - start)
            if remaining <= 0:
                break
            if t.is_alive():
                t.join(timeout=remaining)
        
        # Check remaining
        alive_count = sum(1 for t in threads if t.is_alive())
        if alive_count > 0:
            logger.warning("shutdown_timeout_threads_killed", count=alive_count)
        else:
            logger.info("shutdown_threads_finished_cleanly")

job_registry = ActiveJobRegistry()
