import threading
import logging
from typing import Dict, List, Callable, Any, Optional
from backend.core.interfaces import IEventBus, ICache

logger = logging.getLogger(__name__)

class InMemoryEventBus:
    def __init__(self, cache: Optional[ICache] = None):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()
        self._cache = cache

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
        logger.info(f"[EventBus] Subscribed to {event_type}")

    def publish(self, event_type: str, payload: Dict[str, Any], idempotency_key: Optional[str] = None) -> None:
        if idempotency_key and self._cache:
            # Check if processed recently
            dedup_key = f"evt_dedup:{idempotency_key}"
            if self._cache.get(dedup_key):
                logger.warning(f"[EventBus] Duplicate event suppressed: {event_type} (Key: {idempotency_key})")
                return
            
            # Mark as processed (TTL 60s is enough for retries)
            self._cache.set(dedup_key, 1, ttl=60)

        # Clone list to avoid locking during execution (and prevent deadlocks if handler calls subscribe)
        with self._lock:
            handlers = self._subscribers.get(event_type, [])[:]
        
        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                logger.error(f"[EventBus] Handler failed for {event_type}: {e}", exc_info=True)
