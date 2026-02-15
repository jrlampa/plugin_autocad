from __future__ import annotations
import os
import uuid
from typing import Dict

# Security: If no token provided (EXE mode), generate one for IPC handshake.
AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN")
if not AUTH_TOKEN:
    AUTH_TOKEN = uuid.uuid4().hex

AUTH_HEADER_NAME = "X-SisRua-Token"

# Session Token Management
SESSION_TOKENS: Dict[str, float] = {}
SESSION_DURATION = 1800 # 30 minutes
