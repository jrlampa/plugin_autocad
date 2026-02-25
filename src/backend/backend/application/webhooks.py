import os
import requests
import threading
import time
import concurrent.futures
from typing import List, Dict, Any, Optional

class WebhookService:
    """
    Manages registration and non-blocking delivery of webhook events.
    Thread-safe minimal implementation.
    """
    def __init__(self):
        self.urls: List[str] = []
        self._lock = threading.Lock()
        
        static_url = os.environ.get("WEBHOOK_URL")
        if static_url:
            self.urls.append(static_url)
        
        # Thread pool for async delivery
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        print(f"[webhooks] Service initialized. Static listeners: {len(self.urls)}")

    def register_url(self, url: str):
        with self._lock:
            if url not in self.urls:
                self.urls.append(url)
                print(f"[webhooks] Registered new listener: {url}")

    def broadcast(self, event_type: str, payload: Dict[str, Any]):
        if not self.urls:
            return

        envelope = {
            "event": event_type,
            "timestamp": time.time(),
            "data": payload
        }

        for url in self.urls:
            self.executor.submit(self._deliver, url, envelope)

    def _deliver(self, url: str, payload: Dict[str, Any]):
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code >= 400:
                print(f"[webhooks] Delivery to {url} failed: {response.status_code}")
        except Exception as e:
            print(f"[webhooks] Error delivering to {url}: {e}")

# Module-level singleton (Python guarantees modules are only loaded once)
webhook_service = WebhookService()
