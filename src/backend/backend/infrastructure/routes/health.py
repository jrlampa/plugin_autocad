"""
backend/routes/health.py
Router de saúde e autenticação.
"""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request

import backend.shared.auth as auth
from backend.shared.auth import AUTH_HEADER_NAME, SESSION_DURATION, _get_master_token, require_token
from backend.domain.dto import DeepHealthResponse, HealthResponse
from backend.application.health import health_service

router = APIRouter()


@router.get("/api/v1/health", tags=["Health"], response_model=HealthResponse)
async def health_check():
    """Verifica se a API está online."""
    return HealthResponse(status="ok")


@router.get("/health", tags=["Health"], include_in_schema=False)
async def health_check_legacy():
    """Fallback para versões antigas do plugin ou monitoramento simples."""
    return {"status": "ok"}


@router.get("/api/v1/auth/check", tags=["Health"])
async def auth_check(_: None = Depends(require_token)):
    """Verifica se o token de autenticação é válido."""
    return {"status": "ok", "message": "Authenticated"}


@router.post("/api/v1/auth/session", tags=["Health"])
async def create_session(
    request: Request,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME),
):
    """
    ISO 27001 – Handshake de sessão.
    Troca o Master Token por um Session Token de curta duração (30 min).
    """
    state = getattr(getattr(request, "app", None), "state", None)
    master_tokens = getattr(state, "master_tokens", None) or set()
    env_master = _get_master_token()

    if env_master and x_sisrua_token == env_master:
        master_tokens = {env_master}
    if env_master:
        master_tokens = set(master_tokens)
        master_tokens.add(env_master)

    if not master_tokens or x_sisrua_token not in master_tokens:
        raise HTTPException(status_code=401, detail="Invalid Master Token")

    session_token = f"sess_{uuid.uuid4().hex}"
    auth.SESSION_TOKENS[session_token] = time.time() + SESSION_DURATION

    return {"session_token": session_token, "expires_in": SESSION_DURATION}


@router.get("/api/v1/health/detailed", tags=["Health"], response_model=DeepHealthResponse)
async def health_detailed(_: None = Depends(require_token)):
    """Verificação profunda de saúde: DB, Cache e Configuração."""
    return health_service.check_health()
