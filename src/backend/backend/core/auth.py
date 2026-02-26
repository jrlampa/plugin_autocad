"""Compatibility shim: re-exports backend.shared.auth."""
from backend.shared.auth import *  # noqa: F401, F403
from backend.shared.auth import require_token  # noqa: F401
