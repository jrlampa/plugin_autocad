from __future__ import annotations
import os
import uuid
from typing import Dict

# Environment Awareness (ISO 27001)
SISRUA_ENV = os.environ.get("SISRUA_ENV", "development").lower()
IS_PROD = SISRUA_ENV in ("production", "prod", "enterprise")

# Security: In development/EXE mode, generate token for IPC.
# In PRODUCTION/Enterprise, the token MUST be provided via secure channel (Environment).
AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN")
if not AUTH_TOKEN:
    if IS_PROD:
        # Prevent silent failure with insecure defaults
        raise RuntimeError("CRITICAL SECURITY ERROR: SISRUA_AUTH_TOKEN is required in PRODUCTION mode.")
    AUTH_TOKEN = uuid.uuid4().hex

AUTH_HEADER_NAME = "X-SisRua-Token"

# Session Token Management
SESSION_TOKENS: Dict[str, float] = {}
SESSION_DURATION = 1800 # 30 minutes
