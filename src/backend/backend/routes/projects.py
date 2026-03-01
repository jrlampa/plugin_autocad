"""Legacy compatibility layer for `backend.routes.projects`.

Canonical implementation: backend.infrastructure.routes.projects
"""

from backend.infrastructure.routes.projects import router  # noqa: F401

# Legacy tests expect project_service here
from backend.infrastructure.routes.deps import project_service  # noqa: F401
