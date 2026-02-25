import time
from fastapi import Header, HTTPException
from backend.shared.config import config

# Configurações de Sessão
SESSION_TOKENS: dict[str, float] = {}
SESSION_DURATION = 3600  # 1 hora
AUTH_HEADER_NAME = "X-SisRua-Token"

def _get_master_token() -> str:
    """Lê o master token de os.environ ou, como fallback, do módulo de API em sys.modules.

    Ordem de precedência:
    1. os.environ["SISRUA_AUTH_TOKEN"] — suporta monkeypatch/setenv em testes.
    2. backend.infrastructure.api.AUTH_TOKEN — fallback para quando o env foi
       alterado por outro teste mas o módulo de API ainda guarda o token original.
    """
    import os
    import sys
    env_token = os.environ.get("SISRUA_AUTH_TOKEN", "")
    if env_token:
        return env_token
    api_mod = sys.modules.get("backend.infrastructure.api")
    if api_mod:
        return getattr(api_mod, "AUTH_TOKEN", "") or ""
    return ""


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
