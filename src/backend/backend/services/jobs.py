import uuid
import threading
import time
from typing import Dict, Any, Optional

# Lock para proteger job_store contra race conditions
_job_store_lock = threading.Lock()

# In-memory storage for job statuses and results.
job_store: Dict[str, Dict[str, Any]] = {}

# Track which jobs have been requested to cancel
cancellation_tokens: Dict[str, bool] = {}

def init_job(kind: str) -> str:
    job_id = str(uuid.uuid4())
    now = time.time()
    with _job_store_lock:
        job_store[job_id] = {
            "job_id": job_id,
            "kind": kind,
            "status": "queued",
            "progress": 0.0,
            "message": "Aguardando...",
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now
        }
    return job_id

def update_job(job_id: str, *, status: str | None = None, progress: float | None = None, message: str | None = None, result: Dict | None = None, error: str | None = None) -> None:
    now = time.time()
    with _job_store_lock:
        job = job_store.get(job_id)
        if not job:
            return
        job["updated_at"] = now
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
        job["updated_at"] = time.time()
    return True

def cleanup_expired_jobs(max_age_seconds: int = 3600):
    """Removes jobs that have been completed or failed for more than max_age_seconds."""
    now = time.time()
    jobs_to_delete = []
    
    with _job_store_lock:
        for job_id, job in job_store.items():
            # Only cleanup finished jobs
            if job["status"] in ("completed", "failed"):
                if now - job["updated_at"] > max_age_seconds:
                    jobs_to_delete.append(job_id)
        
        for job_id in jobs_to_delete:
            del job_store[job_id]
            if job_id in cancellation_tokens:
                del cancellation_tokens[job_id]
                
    return len(jobs_to_delete)
