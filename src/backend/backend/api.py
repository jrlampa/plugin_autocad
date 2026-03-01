# backend/api.py - Alias de compatibilidade para testes legados
# O módulo principal está em backend.infrastructure.api

import os
import uuid

if not os.environ.get("SISRUA_AUTH_TOKEN"):
    os.environ["SISRUA_AUTH_TOKEN"] = uuid.uuid4().hex

# Exporta o token atual do ambiente para compatibilidade com testes.
AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN")

from backend.infrastructure.api import app, ai_service, export_service  # noqa: F401,E402
from backend.application.webhooks import webhook_service  # noqa: F401,E402

# Mantém tokens aceitos em testes quando este shim é recarregado.
_tokens = getattr(getattr(app, "state", None), "master_tokens", None)
if _tokens is None:
    app.state.master_tokens = set()
    _tokens = app.state.master_tokens
if AUTH_TOKEN:
    _tokens.add(AUTH_TOKEN)
