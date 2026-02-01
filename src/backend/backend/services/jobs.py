import time
import uuid
from backend.core.interfaces import IEventBus
from backend.core.logger import get_logger, get_trace_id

logger = get_logger(__name__)

# Lock para proteger job_store contra race conditions
_job_store_lock = threading.Lock()

# In-memory storage for job statuses and results.
job_store: Dict[str, Dict[str, Any]] = {}

def init_job(kind: str) -> str:
    job_id = str(uuid.uuid4())
    now = time.time()
    trace_id = get_trace_id()
    
    with _job_store_lock:
        job_store[job_id] = {
            "job_id": job_id,
            "kind": kind,
            "status": "queued",
            "progress": 0.0,
            "message": "Aguardando...",
            "result": None,
            "error": None,
            "cancelled": False, # Cancellation state stored directly in job dict
            "created_at": now,
            "updated_at": now,
            "trace_id": trace_id
        }
    logger.info("job_created", job_id=job_id, kind=kind, trace_id=trace_id)
    return job_id

def update_job(
    job_id: str, 
    event_bus: IEventBus,
    *, 
    status: str | None = None, 
    progress: float | None = None, 
    message: str | None = None, 
    result: Dict | None = None, 
    error: str | None = None
) -> None:
    now = time.time()
    with _job_store_lock:
        job = job_store.get(job_id)
        if not job or job.get("cancelled", False):
            return
            
        job["updated_at"] = now
        if status is not None:
            old_status = job.get("status")
            job["status"] = status
            
            if status != old_status:
                event_map = {"processing": "job_started", "completed": "job_completed", "failed": "job_failed"}
                event = event_map.get(status)
                if event:
                    # Idempotency Key: Ensures this specific transition is only broadcast once
                    idem_key = f"job_event:{job_id}:{status}"
                    event_bus.publish(event, job.copy(), idempotency_key=idem_key)

        if progress is not None:
            job["progress"] = float(max(0.0, min(1.0, progress)))
        if message is not None:
            job["message"] = message
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error

def check_cancellation(job_id: str):
    """
    Checks if a job was marked as cancelled. 
    Worker threads call this to abort execution.
    """
    with _job_store_lock:
        job = job_store.get(job_id)
        if job and job.get("cancelled"):
            raise RuntimeError("CANCELLED")

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _job_store_lock:
        return job_store.get(job_id)

def cancel_job(job_id: str) -> bool:
    """Marks a job as cancelled if it is still running."""
    with _job_store_lock:
        job = job_store.get(job_id)
        if not job or job["status"] in ("completed", "failed"):
            return False
            
        job["cancelled"] = True
        job["status"] = "failed"
        job["message"] = "Cancelado pelo usuário."
        job["error"] = "CANCELLED"
        job["updated_at"] = time.time()
    return True

def cleanup_expired_jobs(max_age_seconds: int = 3600):
    now = time.time()
    jobs_to_delete = []
    
    with _job_store_lock:
        for job_id, job in job_store.items():
            if job["status"] in ("completed", "failed"):
                if now - job["updated_at"] > max_age_seconds:
                    jobs_to_delete.append(job_id)
        
        for job_id in jobs_to_delete:
            del job_store[job_id]
                
    return len(jobs_to_delete)
