"""
backend/routes/deps.py
Raiz de composição (Composition Root).
Instâncias singleton de serviços compartilhados entre todos os routers.
"""
from __future__ import annotations

import os
from pathlib import Path

from backend.services.cache import cache_service
from backend.services.webhooks import webhook_service
from backend.services.ai import AiService
from backend.services.export_service import ExportService
from backend.services.projects import ProjectService
from backend.services.executor import JobExecutor
from backend.core.bus import InMemoryEventBus

# --- Composition Root ---
event_bus = InMemoryEventBus(cache=cache_service)
project_service = ProjectService(event_bus=event_bus)
job_executor = JobExecutor(cache_service=cache_service)
ai_service = AiService()

_db_path = (
    Path(os.environ["LOCALAPPDATA"]) / "sisRUA" / "projects.db"
    if os.environ.get("LOCALAPPDATA")
    else Path.home() / ".sisrua" / "projects.db"
)
export_service = ExportService(db_path=_db_path)

# Wiring: WebhookService escuta eventos do barramento interno
event_bus.subscribe("job_started", lambda p: webhook_service.broadcast("job_started", p))
event_bus.subscribe("job_completed", lambda p: webhook_service.broadcast("job_completed", p))
event_bus.subscribe("job_failed", lambda p: webhook_service.broadcast("job_failed", p))
event_bus.subscribe("project_saved", lambda p: webhook_service.broadcast("project_saved", p))
event_bus.subscribe("project_updated", lambda p: webhook_service.broadcast("project_updated", p))
