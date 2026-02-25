import time
from fastapi import Header, HTTPException
from backend.shared.config import config

# Configurações de Sessão
SESSION_TOKENS: dict[str, float] = {}
SESSION_DURATION = 3600  # 1 hora
AUTH_HEADER_NAME = "X-SisRua-Token"

def _get_master_token() -> str:
    """Lê o master token da configuração centralizada."""
    return config.sisrua_auth_token


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
