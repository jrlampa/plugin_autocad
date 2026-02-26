"""
Pacote backend do sisRUA.

Este arquivo existe para garantir que `backend.*` (ex.: `backend.api:app`)
seja importável de forma consistente quando iniciado via Uvicorn.

Registra aliases de compatibilidade retroativa (backend.X → backend.infrastructure.X)
para que patch("backend.X.func") funcione corretamente nos testes.
"""
from __future__ import annotations
import sys
import importlib

__version__ = "0.1.0"


def _register_alias(compat: str, real: str) -> None:
    """Registra compat → real em sys.modules sem importar imediatamente."""
    if compat not in sys.modules:
        try:
            mod = importlib.import_module(real)
            sys.modules[compat] = mod
        except Exception:
            pass  # Módulo opcional ou não disponível


# backend.audit_routes → backend.infrastructure.audit_routes
_register_alias("backend.audit_routes", "backend.infrastructure.audit_routes")

# backend.api → backend.infrastructure.api (já existe o shim em api.py)
# O shim em backend/api.py lida com isso via import normal
