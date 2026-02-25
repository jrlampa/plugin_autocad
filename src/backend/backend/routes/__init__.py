"""
backend/routes — Aliases de compatibilidade retroativa.

Registra backend.routes.X como alias de backend.infrastructure.routes.X em sys.modules,
garantindo que patch("backend.routes.X.func") funcione corretamente nos testes.
Também expõe os módulos como atributos do pacote para pytest monkeypatch.
"""
from __future__ import annotations

import sys
import importlib
import types


def _register_route_alias(compat: str, infra: str) -> types.ModuleType:
    if compat not in sys.modules:
        try:
            mod = importlib.import_module(infra)
            sys.modules[compat] = mod
        except Exception:
            return None
    return sys.modules.get(compat)


_ROUTE_ALIASES = (
    ("backend.routes.prepare",    "backend.infrastructure.routes.prepare"),
    ("backend.routes.enterprise", "backend.infrastructure.routes.enterprise"),
    ("backend.routes.projects",   "backend.infrastructure.routes.projects"),
    ("backend.routes.jobs",       "backend.infrastructure.routes.jobs"),
    ("backend.routes.tools",      "backend.infrastructure.routes.tools"),
    ("backend.routes.health",     "backend.infrastructure.routes.health"),
    ("backend.routes.webhooks",   "backend.infrastructure.routes.webhooks"),
    ("backend.routes.ai",         "backend.infrastructure.routes.ai_routes"),
    ("backend.routes.deps",       "backend.infrastructure.routes.deps"),
)

_self = sys.modules[__name__]
for _compat, _infra in _ROUTE_ALIASES:
    mod = _register_route_alias(_compat, _infra)
    if mod is not None:
        _short = _compat.split(".")[-1]
        setattr(_self, _short, mod)
