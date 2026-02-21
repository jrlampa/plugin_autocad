"""
backend/routes/webhooks.py
Router de webhooks e eventos internos.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth import require_token
from backend.models import HealthResponse, InternalEvent, WebhookRegistrationRequest

router = APIRouter()


@router.post(
    "/api/v1/webhooks/register",
    tags=["Webhooks"],
    response_model=HealthResponse,
)
async def register_webhook(
    req: WebhookRegistrationRequest,
    _: None = Depends(require_token),
):
    """Registra uma URL para receber eventos do sistema via webhook."""
    import backend.api as _api
    _api.webhook_service.register_url(req.url)
    return HealthResponse(status="ok")


@router.post(
    "/api/v1/events/emit",
    tags=["Webhooks"],
    response_model=HealthResponse,
)
async def emit_event(
    req: InternalEvent,
    _: None = Depends(require_token),
):
    """
    Endpoint interno para o plugin AutoCAD emitir eventos (ex.: project_saved).
    """
    import backend.api as _api
    _api.webhook_service.broadcast(req.event_type, req.payload)
    return HealthResponse(status="ok")
