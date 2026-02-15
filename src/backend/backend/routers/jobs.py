import threading
import json
import hashlib
import structlog
from fastapi import APIRouter, Header, HTTPException, Depends
from backend.models import JobStatusResponse, PrepareJobRequest, HealthResponse
from backend.core.security import require_token
from backend.core.config import AUTH_HEADER_NAME
from backend.core.logger import get_logger, set_trace_id, get_trace_id
from backend.core.rate_limit import RateLimiter
from backend.services.jobs import init_job, get_job, cancel_job
from backend.core.container import event_bus, job_executor

router = APIRouter(tags=["Jobs"])
logger = get_logger(__name__)

def _run_prepare_job_sync(job_id: str, payload: PrepareJobRequest, trace_id: str) -> None:
    try:
        # Restore Trace Context in the new thread
        set_trace_id(trace_id)
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        
        job_executor.execute_prepare_job(job_id, payload, event_bus)
    finally:
        from backend.core.lifecycle import job_registry
        job_registry.remove(threading.current_thread())

@router.post("/api/v1/jobs/prepare", response_model=JobStatusResponse)
async def create_prepare_job(
    payload: PrepareJobRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME),
    _ = Depends(RateLimiter(calls=5, period=60)) 
):
    """Start an asynchronous data preparation job (OSM or GeoJSON)."""
    await require_token(x_sisrua_token)
    
    try:
        payload_dict = payload.model_dump()
        payload_json = json.dumps(payload_dict, sort_keys=True)
        idempotency_key = hashlib.sha256(payload_json.encode()).hexdigest()
        
        current_trace_id = get_trace_id()
        from backend.core.lifecycle import job_registry
        
        job_id, is_new = init_job(payload.kind, idempotency_key=idempotency_key)
        
        if is_new:
            t = threading.Thread(target=_run_prepare_job_sync, args=(job_id, payload, current_trace_id), daemon=True)
            job_registry.add(t)
            t.start()
        else:
            logger.info("job_creation_skipped_dedup", job_id=job_id)
            
        return get_job(job_id)
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        logger.error("create_job_invalid_payload", error=str(e))
        raise HTTPException(status_code=422, detail="Invalid job payload")
    except Exception as e:
        logger.error("create_job_system_failure", error=str(e), traceback=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_endpoint(
    job_id: str,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Retrieve the current status of a job."""
    await require_token(x_sisrua_token)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.delete("/api/v1/jobs/{job_id}", response_model=HealthResponse)
async def cancel_job_endpoint(
    job_id: str,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Request cancellation of a running job."""
    await require_token(x_sisrua_token)
    
    cancelled = cancel_job(job_id)
    if not cancelled:
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
    return HealthResponse(status="ok")
