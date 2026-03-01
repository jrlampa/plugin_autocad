"""Compat layer for legacy imports.

Some older routers/tests import `backend.routes.deps`.
The canonical composition root lives in `backend.infrastructure.routes.deps`.
"""

from backend.infrastructure.routes.deps import *  # noqa: F401,F403
