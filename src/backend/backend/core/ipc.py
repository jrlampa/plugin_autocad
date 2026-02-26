"""Compatibility shim: re-exports backend.shared.ipc."""
from backend.shared.ipc import *  # noqa: F401, F403
from backend.shared.ipc import IpcServer, _WIN32_AVAILABLE  # noqa: F401
