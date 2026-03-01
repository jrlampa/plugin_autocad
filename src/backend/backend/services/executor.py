"""Legacy compatibility layer for `backend.services.executor`.

Canonical implementation: backend.application.executor
"""

from backend.application.executor import *  # noqa: F401,F403

# Legacy tests patch `backend.services.executor.update_job` / `check_cancellation`.
# Expose them here so code can call through this module.
from backend.application.jobs import update_job, check_cancellation  # noqa: F401,E402
