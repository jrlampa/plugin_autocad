import time
import requests
from typing import Optional, List, Any, Dict, Union
from backend.models import (
    JobStatusResponse, PrepareJobRequest, PrepareResponse,
    ElevationQueryRequest, ElevationPointResponse, WebhookRegistrationRequest,
    HealthResponse
)

class SisRuaClient:
    """
    Typed Python SDK for sisRUA Backend.
    Provides sync wrappers for core API endpoints.
    """
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "X-SisRua-Token": self.token,
            "Accept": "application/json"
        })

    def check_health(self) -> bool:
        """Verifies if the API is reachable and healthy."""
        try:
            r = self.session.get(f"{self.base_url}/health", timeout=5)
            return r.status_code == 200 and r.json().get("status") == "ok"
        except Exception:
            return False

    def get_elevation(self, lat: float, lon: float) -> Optional[float]:
        """Retrieves elevation for a specific point."""
        r = self.session.post(
            f"{self.base_url}/tools/elevation/query",
            json={"latitude": lat, "longitude": lon}
        )
        r.raise_for_status()
        data = ElevationPointResponse(**r.json())
        return data.elevation

    def create_job(
        self, 
        kind: str, 
        latitude: Optional[float] = None, 
        longitude: Optional[float] = None, 
        radius: Optional[float] = None, 
        geojson: Optional[Any] = None
    ) -> JobStatusResponse:
        """Triggers a data preparation job (osm or geojson)."""
        payload = PrepareJobRequest(
            kind=kind, 
            latitude=latitude, 
            longitude=longitude, 
            radius=radius, 
            geojson=geojson
        )
        r = self.session.post(
            f"{self.base_url}/jobs/prepare",
            json=payload.model_dump(exclude_none=True)
        )
        r.raise_for_status()
        return JobStatusResponse(**r.json())

    def get_job_status(self, job_id: str) -> JobStatusResponse:
        """Retrieves the current status of a job."""
        r = self.session.get(f"{self.base_url}/jobs/{job_id}")
        r.raise_for_status()
        return JobStatusResponse(**r.json())

    def wait_for_job(self, job_id: str, timeout: int = 300, poll_interval: float = 2.0) -> JobStatusResponse:
        """
        Polls a job until it reaches a terminal state (completed or failed).
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.get_job_status(job_id)
            if status.status in ("completed", "failed"):
                return status
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

    
    def register_webhook(self, url: str, events: Optional[List[str]] = None) -> bool:
        """Registers a webhook listener."""
        payload = WebhookRegistrationRequest(url=url, events=events)
        r = self.session.post(
            f"{self.base_url}/webhooks/register",
            json=payload.model_dump(exclude_none=True)
        )
        return r.status_code == 200

    @property
    def ai(self) -> 'AiClient':
        """Access AI capabilities."""
        return AiClient(self)

class AiClient:
    def __init__(self, client: SisRuaClient):
        self.client = client

    def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Sends a message to the AI and returns the response."""
        payload = {"message": message}
        if context:
            payload["context"] = context
            
        r = self.client.session.post(
            f"{self.client.base_url}/ai/chat",
            json=payload
        )
        r.raise_for_status()
        return r.json().get("response", "")
