from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Header, Depends
from backend.core.security import require_token
from backend.core.config import AUTH_HEADER_NAME
from backend.services.ai import AiService

router = APIRouter(tags=["AI Intelligence"])
ai_service = AiService()

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str

@router.post("/api/v1/ai/chat", response_model=ChatResponse)
async def chat_with_ai(
    req: ChatRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Interact with sisRUA AI Assistant."""
    await require_token(x_sisrua_token)
    res = ai_service.chat(req.message, context=req.context, job_id=req.job_id)
    return ChatResponse(response=res)
