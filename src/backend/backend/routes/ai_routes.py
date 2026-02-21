"""
backend/routes/ai_routes.py
Router do assistente AI (Groq LLM + RAG interno).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.auth import require_token
from backend.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str


@router.post("/api/v1/ai/chat", tags=["AI"], response_model=ChatResponse)
async def chat_with_ai(
    req: ChatRequest,
    _: None = Depends(require_token),
):
    """Interação com o assistente sisRUA AI (Groq/LLaMA)."""
    import backend.api as _api
    try:
        reply = _api.ai_service.generate_response(req.message, req.context, req.job_id)
        return ChatResponse(response=reply)
    except Exception as e:
        logger.error("ai_chat_failed", error=str(e))
        return ChatResponse(response="AI unavailable.")
