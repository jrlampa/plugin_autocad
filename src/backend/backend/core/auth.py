"""
backend/core/auth.py
Módulo de autenticação — ISO 27001.
Centraliza o estado de tokens e a dependência FastAPI de validação.

Nota: AUTH_TOKEN é lido do ambiente em tempo de execução (via _get_master_token)
para suportar reload de módulos em testes sem perder o token configurado.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Dict

from fastapi import Header, HTTPException

AUTH_HEADER_NAME = "X-SisRua-Token"

# Session tokens de curta duração: {token: timestamp_expiry}
# Este dict é estável durante a vida do processo (não é recarregado com api.py).
SESSION_TOKENS: Dict[str, float] = {}
SESSION_DURATION = 1800  # 30 minutos


def _get_master_token() -> str:
    """Lê o master token do ambiente em tempo de execução."""
    return os.environ.get("SISRUA_AUTH_TOKEN", "")


def is_valid_session(token: str) -> bool:
    """Verifica se um session token existe e não expirou (sliding window)."""
    if token not in SESSION_TOKENS:
        return False
    if time.time() > SESSION_TOKENS[token]:
        del SESSION_TOKENS[token]
        return False
    SESSION_TOKENS[token] = time.time() + SESSION_DURATION
    return True


def require_token(x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)) -> None:
    """
    Dependência FastAPI: protege endpoints contra chamadas não autorizadas.
    Aceita Master Token (bootstrap IPC) ou Session Token de curta duração.
    """
    master = _get_master_token()
    if not master:
        raise HTTPException(status_code=500, detail="Server Authentication Not Configured")

    if not x_sisrua_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if x_sisrua_token == master:
        return

    if is_valid_session(x_sisrua_token):
        return

    raise HTTPException(status_code=401, detail="Invalid or Expired Token")
