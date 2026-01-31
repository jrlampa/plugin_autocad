from typing import Dict, List, Callable, Any
import threading
import logging
from backend.core.interfaces import IEventBus

logger = logging.getLogger(__name__)

class InMemoryEventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
        logger.info(f"[EventBus] Subscribed to {event_type}")

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        # Clone list to avoid locking during execution (and prevent deadlocks if handler calls subscribe)
        with self._lock:
            handlers = self._subscribers.get(event_type, [])[:]
        
        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                logger.error(f"[EventBus] Handler failed for {event_type}: {e}", exc_info=True)
