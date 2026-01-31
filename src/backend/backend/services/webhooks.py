import os
import requests
import threading
import concurrent.futures
from typing import List, Dict, Any, Optional

class WebhookService:
    """
    Manages registration and non-blocking delivery of webhook events.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WebhookService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.urls: List[str] = []
        static_url = os.environ.get("WEBHOOK_URL")
        if static_url:
            self.urls.append(static_url)
        
        # Thread pool for async delivery to avoid blocking job execution or API responses
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self._initialized = True
        print(f"[webhooks] Service initialized. Static listeners: {len(self.urls)}")

    def register_url(self, url: str):
        with self._lock:
            if url not in self.urls:
                self.urls.append(url)
                print(f"[webhooks] Registered new listener: {url}")

    def broadcast(self, event_type: str, payload: Dict[str, Any]):
        """
        Broadcasts an event to all registered listeners asynchronously.
        """
        if not self.urls:
            return

        envelope = {
            "event": event_type,
            "timestamp": threading.time.time() if hasattr(threading, "time") else __import__("time").time(),
            "data": payload
        }

        for url in self.urls:
            self.executor.submit(self._deliver, url, envelope)

    def _deliver(self, url: str, payload: Dict[str, Any]):
        try:
            # Short timeout to avoid hanging the executor local threads
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code >= 400:
                print(f"[webhooks] Delivery to {url} failed with status {response.status_code}")
        except Exception as e:
            print(f"[webhooks] Error delivering to {url}: {e}")

# Global singleton
webhook_service = WebhookService()
