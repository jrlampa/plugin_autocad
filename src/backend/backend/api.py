# backend/api.py - Alias de compatibilidade para testes legados
# O módulo principal está em backend.infrastructure.api
from backend.infrastructure.api import app, AUTH_TOKEN, ai_service, export_service  # noqa: F401
from backend.application.webhooks import webhook_service # noqa: F401
