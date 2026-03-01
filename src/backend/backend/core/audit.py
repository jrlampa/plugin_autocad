"""Legacy compatibility layer for `backend.core.audit`.

Canonical implementation: backend.shared.audit
"""

from backend.shared.database import get_db_connection  # noqa: F401
from backend.shared.audit import *  # noqa: F401,F403
