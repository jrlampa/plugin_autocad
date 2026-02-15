from __future__ import annotations
import time
from fastapi import Header, HTTPException, Depends
from backend.core.config import AUTH_TOKEN, AUTH_HEADER_NAME, SESSION_TOKENS, SESSION_DURATION

def is_valid_session(token: str) -> bool:
    """Checks if a session token exists and is not expired."""
    if token not in SESSION_TOKENS:
        return False
    if time.time() > SESSION_TOKENS[token]:
        del SESSION_TOKENS[token] # Cleanup
        return False
    # Slide the window
    SESSION_TOKENS[token] = time.time() + SESSION_DURATION
    return True

async def require_token(x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    """
    Protege endpoints sensíveis contra chamadas externas na máquina do usuário.
    Aceita Master Token (bootstrap) ou Session Token (uso contínuo).
    """
    if not x_sisrua_token:
        raise HTTPException(status_code=401, detail="Authentication token required")
        
    if x_sisrua_token == AUTH_TOKEN:
        return x_sisrua_token
        
    if is_valid_session(x_sisrua_token):
        return x_sisrua_token
        
    raise HTTPException(status_code=401, detail="Invalid or expired token")
