import os
from pathlib import Path
from backend.core.bus import InMemoryEventBus
from backend.services.cache import cache_service
from backend.services.projects import ProjectService
from backend.services.executor import JobExecutor
from backend.services.webhooks import webhook_service
from backend.services.export_service import ExportService

# --- Composition Root ---
# Singleton services that power the engine

event_bus = InMemoryEventBus(cache=cache_service)
project_service = ProjectService(event_bus=event_bus)
job_executor = JobExecutor(cache_service=cache_service)

# Global Export Service (used for GIS tasks)
export_service = ExportService(
    db_path=Path(os.environ.get("LOCALAPPDATA", "")) / "sisRUA" / "projects.db"
)

def setup_event_bus():
    """Wire up global event subscriptions."""
    event_bus.subscribe("job_started", lambda p: webhook_service.broadcast("job_started", p))
    event_bus.subscribe("job_completed", lambda p: webhook_service.broadcast("job_completed", p))
    event_bus.subscribe("job_failed", lambda p: webhook_service.broadcast("job_failed", p))
    event_bus.subscribe("project_saved", lambda p: webhook_service.broadcast("project_saved", p))
    event_bus.subscribe("project_updated", lambda p: webhook_service.broadcast("project_updated", p))
