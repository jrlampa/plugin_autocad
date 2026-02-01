import queue
import threading
import time
from typing import List, Any, Callable
from backend.core.logger import get_logger

logger = get_logger(__name__)

class PersistenceBuffer:
    """
    Thread-safe buffer that accumulates items and flushes them in batches 
    using a background worker thread.
    """
    def __init__(self, 
                 flush_callback: Callable[[List[Any]], None], 
                 batch_size: int = 50, 
                 flush_interval: float = 5.0):
        
        self.queue = queue.Queue()
        self.flush_callback = flush_callback
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self.running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        
    def add(self, item: Any):
        self.queue.put(item)
        
    def stop(self):
        self.running = False
        self.queue.put(None) # Sentinel
        self._thread.join()
        
    def _worker(self):
        batch = []
        last_flush = time.time()
        
        while self.running or not self.queue.empty():
            try:
                # Wait for item with timeout to handle periodic flush
                 # If we have items in batch, wait less
                timeout = max(0.1, self.flush_interval - (time.time() - last_flush))
                item = self.queue.get(timeout=timeout)
                
                if item is None: # Sentinel
                    break
                
                batch.append(item)
                
            except queue.Empty:
                pass # Timeout reached, check flush logic
                
            # Flush conditions:
            # 1. Batch full
            # 2. Time elapsed since last flush (and batch not empty)
            is_full = len(batch) >= self.batch_size
            is_time = (time.time() - last_flush) >= self.flush_interval
            
            if batch and (is_full or is_time):
                self._flush(batch)
                batch = []
                last_flush = time.time()
                
        # Final flush
        if batch:
            self._flush(batch)

    def _flush(self, batch: List[Any]):
        try:
            self.flush_callback(batch)
        except Exception as e:
            logger.error("buffer_flush_failed", error=str(e), count=len(batch))
