import uuid
import threading
from typing import Dict, Any, Optional

# Lock para proteger job_store contra race conditions
_job_store_lock = threading.Lock()

# In-memory storage for job statuses and results.
job_store: Dict[str, Dict[str, Any]] = {}

# Track which jobs have been requested to cancel
cancellation_tokens: Dict[str, bool] = {}

def init_job(kind: str) -> str:
    job_id = str(uuid.uuid4())
    with _job_store_lock:
        job_store[job_id] = {
            "job_id": job_id,
            "kind": kind,
            "status": "queued",
            "progress": 0.0,
            "message": "Aguardando...",
            "result": None,
            "error": None,
        }
    return job_id

def update_job(job_id: str, *, status: str | None = None, progress: float | None = None, message: str | None = None, result: Dict | None = None, error: str | None = None) -> None:
    with _job_store_lock:
        job = job_store.get(job_id)
        if not job:
            return
        if status is not None:
            job["status"] = status
        if progress is not None:
            job["progress"] = float(max(0.0, min(1.0, progress)))
        if message is not None:
            job["message"] = message
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error

def check_cancellation(job_id: str):
    if cancellation_tokens.get(job_id):
        raise RuntimeError("CANCELLED")

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _job_store_lock:
        return job_store.get(job_id)

def cancel_job(job_id: str) -> bool:
    """Return True if cancelled, False if not found or already done."""
    with _job_store_lock:
        job = job_store.get(job_id)
        if not job:
            return False
        
        # If already finished, do nothing
        if job["status"] in ("completed", "failed"):
            return True
            
        cancellation_tokens[job_id] = True
        job["status"] = "failed"
        job["message"] = "Cancelamento solicitado..."
        job["error"] = "CANCELLED"
    return True
