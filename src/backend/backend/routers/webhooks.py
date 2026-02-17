from typing import List, Optional
from fastapi import APIRouter, Header, Depends
from backend.models import WebhookRegistrationRequest
from backend.core.security import require_token
from backend.core.config import AUTH_HEADER_NAME
from backend.services.webhooks import webhook_service

router = APIRouter(tags=["Infrastructure"])

@router.post("/api/v1/webhooks/register")
async def register_webhook(
    req: WebhookRegistrationRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Register a new URL to receive system events via webhook."""
    await require_token(x_sisrua_token)
    webhook_id = webhook_service.register(req.url, events=req.events)
    return {"webhook_id": webhook_id, "status": "active"}
