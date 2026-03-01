"""Legacy compatibility layer for `backend.services.health`.

Canonical implementation: backend.application.health
"""

from backend.shared.database import get_db_connection  # noqa: F401
from backend.application.health import HealthService, health_service, cache_service  # noqa: F401
