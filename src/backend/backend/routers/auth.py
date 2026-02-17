import time
import uuid
import logging
from fastapi import APIRouter, Header, HTTPException, Depends
from backend.core.config import AUTH_TOKEN, AUTH_HEADER_NAME, SESSION_TOKENS, SESSION_DURATION
from backend.core.security import require_token

router = APIRouter(tags=["Authentication"])
logger = logging.getLogger(__name__)

@router.get("/api/v1/auth/check")
async def auth_check(_ = Depends(require_token)):
    """Verifica se o token de autenticação é válido."""
    return {"status": "ok", "message": "Authenticated"}

@router.post("/api/v1/auth/session")
async def create_session(x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    """
    ISO 27001: Session Token Handshake.
    Troca o Master Token por um Session Token de curta duração.
    """
    if not AUTH_TOKEN or x_sisrua_token != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid Master Token")
    
    session_token = f"sess_{uuid.uuid4().hex}"
    SESSION_TOKENS[session_token] = time.time() + SESSION_DURATION
    
    logger.info("session_created", token_id=session_token[:10])
    return {"session_token": session_token, "expires_in": SESSION_DURATION}
