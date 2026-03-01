"""Legacy compatibility layer for `backend.core.ipc`.

Canonical implementation: backend.shared.ipc
"""

import backend.shared.ipc as _ipc

IpcServer = _ipc.IpcServer  # noqa: F401
_WIN32_AVAILABLE = getattr(_ipc, "_WIN32_AVAILABLE", False)

# Re-export public names for convenience
from backend.shared.ipc import *  # noqa: F401,F403
