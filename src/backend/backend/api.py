"""Compatibility shim: backend.api → backend.infrastructure.api."""
import sys
import importlib

# Register as alias so monkeypatch.setattr(backend.api, "ai_service", ...)
# affects the real module-level attributes.
_mod = importlib.import_module("backend.infrastructure.api")
sys.modules["backend.api"] = _mod

# Re-export primary symbols for convenience
from backend.infrastructure.api import app, AUTH_TOKEN  # noqa: F401
