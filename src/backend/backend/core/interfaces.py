from typing import Protocol, Any, Optional, Dict, List

class ICache(Protocol):
    """Protocol defining the contract for a caching service."""
    def get(self, key: str) -> Optional[Any]: 
        ...

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: 
        ...

class INotificationService(Protocol):
    """Protocol defining the contract for a notification/webhook service."""
    def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None: 
        ...

    def register_url(self, url: str) -> None: 
        ...

class IEventBus(Protocol):
    """Protocol defining the contract for an event bus."""
    def publish(self, event_type: str, payload: Dict[str, Any]) -> None: 
        ...

    def subscribe(self, event_type: str, handler: Any) -> None: 
        ...
