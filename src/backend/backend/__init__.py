"""
Pacote backend do sisRUA.

Este arquivo existe para garantir que `backend.*` (ex.: `backend.api:app`)
seja importável de forma consistente quando iniciado via Uvicorn.
"""

__version__ = "0.1.0"

from backend import audit_routes as audit_routes  # noqa: F401
