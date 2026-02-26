"""
backend/core — Camada de compatibilidade retroativa.

Registra os submódulos de backend.core como aliases dos módulos em
backend.shared, de forma que patch("backend.core.X.func") e
patch("backend.shared.X.func") afetam o mesmo objeto de módulo.
"""
from __future__ import annotations

import sys
import importlib
from typing import Tuple


def _register_alias(core_path: str, shared_path: str) -> None:
    """Importa shared_path e registra como core_path em sys.modules."""
    if core_path not in sys.modules:
        mod = importlib.import_module(shared_path)
        sys.modules[core_path] = mod


# Mapeamento: backend.core.X → backend.shared.X
_ALIASES: Tuple[Tuple[str, str], ...] = (
    ("backend.core.audit",          "backend.shared.audit"),
    ("backend.core.auth",           "backend.shared.auth"),
    ("backend.core.bus",            "backend.shared.bus"),
    ("backend.core.circuit_breaker","backend.shared.circuit_breaker"),
    ("backend.core.config",         "backend.shared.config"),
    ("backend.core.database",       "backend.shared.database"),
    ("backend.core.ipc",            "backend.shared.ipc"),
    ("backend.core.interfaces",     "backend.shared.interfaces"),
    ("backend.core.lifecycle",      "backend.shared.lifecycle"),
    ("backend.core.logger",         "backend.shared.logger"),
    ("backend.core.migrations",     "backend.shared.migrations"),
    ("backend.core.rate_limit",     "backend.shared.rate_limit"),
    ("backend.core.retry",          "backend.shared.retry"),
    ("backend.core.utils",          "backend.shared.utils"),
)

for _core_path, _shared_path in _ALIASES:
    _register_alias(_core_path, _shared_path)
