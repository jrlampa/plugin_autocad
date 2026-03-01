"""Legacy compatibility layer for `backend.audit_routes`.

Canonical implementation: backend.infrastructure.audit_routes
"""

from backend.infrastructure.audit_routes import *  # noqa: F401,F403

# Legacy tests patch `backend.audit_routes.get_db_connection`.
from backend.shared.database import get_db_connection  # noqa: F401,E402
