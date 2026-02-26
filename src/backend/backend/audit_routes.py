"""Compatibility shim: backend.audit_routes → backend.infrastructure.audit_routes."""
import sys
import importlib

# Register as alias so patches to backend.audit_routes.X affect the real module
_mod = importlib.import_module("backend.infrastructure.audit_routes")
sys.modules[__name__] = _mod
