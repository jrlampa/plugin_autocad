"""
backend/routes/jobs.py
Router de fila de jobs assíncronos (preparação de dados OSM/GeoJSON).
"""
from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, Dict


from fastapi import APIRouter, Depends, HTTPException

from backend.shared.auth import require_token
from backend.shared.logger import bind_contextvars, get_logger, get_trace_id, set_trace_id
from backend.shared.rate_limit import RateLimiter
from backend.domain.dto import HealthResponse, JobStatusResponse, PrepareJobRequest
from backend.infrastructure.routes.deps import event_bus, job_executor
from backend.application.jobs import cancel_job, get_job, init_job

logger = get_logger(__name__)
router = APIRouter()


def _run_prepare_job_sync(job_id: str, payload: PrepareJobRequest, trace_id: str) -> None:
    """Executa um job de preparação em thread separada."""
    try:
        set_trace_id(trace_id)
        bind_contextvars(trace_id=trace_id)
        job_executor.execute_prepare_job(job_id, payload, event_bus)
    finally:
        from backend.shared.lifecycle import job_registry
        job_registry.remove(threading.current_thread())


@router.post(
    "/api/v1/jobs/prepare",
    tags=["Jobs"],
    response_model=JobStatusResponse,
)
async def create_prepare_job(
    payload: PrepareJobRequest,
    _: None = Depends(require_token),
    __: None = Depends(RateLimiter(calls=5, period=60)),
):
    """Inicia um job assíncrono de preparação de dados (OSM ou GeoJSON)."""
    # Garante que o evento de shutdown seja limpo antes de iniciar um novo job.
    # Isso evita que eventos de shutdown de testes anteriores cancelem jobs novos.
    from backend.shared.lifecycle import SHUTDOWN_EVENT
    SHUTDOWN_EVENT.clear()

    try:
        payload_dict = payload.model_dump()
        payload_json = json.dumps(payload_dict, sort_keys=True)
        idempotency_key = hashlib.sha256(payload_json.encode()).hexdigest()

        current_trace_id = get_trace_id()
        from backend.shared.lifecycle import job_registry

        job_id, is_new = init_job(payload.kind, idempotency_key=idempotency_key)

        if is_new:
            t = threading.Thread(
                target=_run_prepare_job_sync,
                args=(job_id, payload, current_trace_id),
                daemon=True,
            )
            job_registry.add(t)
            t.start()
        else:
            logger.info("job_creation_skipped_dedup", job_id=job_id)

        return get_job(job_id)
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        logger.error("create_job_invalid_payload", error=str(e))
        raise HTTPException(status_code=422, detail="Payload de job inválido.")
    except Exception as e:
        logger.error("create_job_system_failure", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao criar job.")


@router.get("/api/v1/jobs/{job_id}", tags=["Jobs"], response_model=JobStatusResponse)
async def get_job_endpoint(
    job_id: str,
    _: None = Depends(require_token),
):
    """Recupera o status atual de um job (progresso e resultado)."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return job


@router.delete("/api/v1/jobs/{job_id}", tags=["Jobs"], response_model=HealthResponse)
async def cancel_job_endpoint(
    job_id: str,
    _: None = Depends(require_token),
):
    """Solicita o cancelamento de um job em execução."""
    cancelled = cancel_job(job_id)
    if not cancelled:
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado.")
    return HealthResponse(status="ok")
