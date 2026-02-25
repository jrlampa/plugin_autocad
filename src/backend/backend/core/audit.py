"""Compatibility shim: re-exports backend.shared.audit."""
from backend.shared.audit import AuditLogger, get_audit_logger  # noqa: F401
from backend.shared.database import get_db_connection  # noqa: F401
