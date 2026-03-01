"""Legacy compatibility layer for tests importing `backend.services.projects`.

Canonical implementation:
- backend.application.projects.ProjectService
- backend.shared.database.get_db_connection
"""

from backend.shared.database import get_db_connection  # noqa: F401
