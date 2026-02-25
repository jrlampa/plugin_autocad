"""Compatibility shim: re-exports backend.shared.database."""
from backend.shared.database import *  # noqa: F401, F403
from backend.shared.database import get_db_connection  # noqa: F401
