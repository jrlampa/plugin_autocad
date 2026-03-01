"""Legacy compatibility layer for `backend.routes.jobs`.

Canonical implementation: backend.infrastructure.routes.jobs
"""

from backend.infrastructure.routes.jobs import router  # noqa: F401

# Legacy tests patch these helpers directly on backend.routes.jobs
from backend.application.jobs import init_job, get_job, cancel_job  # noqa: F401
