import time
import os
from fastapi import Header, HTTPException, Request
from backend.shared.config import config

# Configurações de Sessão
SESSION_TOKENS: dict[str, float] = {}
SESSION_DURATION = 3600  # 1 hora
AUTH_HEADER_NAME = "X-SisRua-Token"

def _get_master_token() -> str:
    """Lê o master token da configuração centralizada."""
    # Importante: para testes, permitir simular "server not configured" removendo
    # a env var. O backend garante o token via backend.infrastructure.api.
    return os.environ.get("SISRUA_AUTH_TOKEN")


def is_valid_session(token: str) -> bool:
    """Verifica se um session token existe e não expirou (sliding window)."""
    if token not in SESSION_TOKENS:
        return False
    if time.time() > SESSION_TOKENS[token]:
        del SESSION_TOKENS[token]
        return False
    SESSION_TOKENS[token] = time.time() + SESSION_DURATION
    return True


def require_token(
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME),
    request: Request = None,
) -> None:
    """
    Dependência FastAPI: protege endpoints contra chamadas não autorizadas.
    Aceita Master Token (bootstrap IPC) ou Session Token de curta duração.
    """
    master_tokens: set[str] | None = None
    if request is not None:
        state = getattr(getattr(request, "app", None), "state", None)
        master_tokens = getattr(state, "master_tokens", None)

    env_master = _get_master_token()
    if master_tokens is None:
        master_tokens = {env_master} if env_master else set()
    elif env_master:
        # Garante que o token atual do ambiente também seja aceito.
        master_tokens = set(master_tokens)
        master_tokens.add(env_master)

    if not master_tokens:
        raise HTTPException(status_code=500, detail="Server Authentication Not Configured")

    if not x_sisrua_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if x_sisrua_token in master_tokens:
        return

    if is_valid_session(x_sisrua_token):
        return

    raise HTTPException(status_code=401, detail="Invalid or Expired Token")
