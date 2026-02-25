"""Compatibility shim: re-exports backend.shared.lifecycle."""
from backend.shared.lifecycle import SHUTDOWN_EVENT, ActiveJobRegistry, job_registry  # noqa: F401
