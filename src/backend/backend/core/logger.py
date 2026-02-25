"""Compatibility shim: re-exports backend.shared.logger."""
from backend.shared.logger import *  # noqa: F401, F403
from backend.shared.logger import get_logger, configure_logging  # noqa: F401
