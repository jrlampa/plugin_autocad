"""
backend/services — Aliases de compatibilidade retroativa.

Registra backend.services.X como alias de backend.application.X em sys.modules,
garantindo que patch("backend.services.X.func") funcione corretamente nos testes.
Também expõe os módulos como atributos do pacote para pytest monkeypatch.
"""
from __future__ import annotations

import sys
import importlib
import types


def _register_alias(compat: str, real: str) -> types.ModuleType:
    if compat not in sys.modules:
        try:
            mod = importlib.import_module(real)
            sys.modules[compat] = mod
        except Exception:
            return None
    return sys.modules.get(compat)


_ALIASES = (
    ("backend.services.ai",            "backend.application.ai"),
    ("backend.services.cache",         "backend.application.cache"),
    ("backend.services.dxf_export",    "backend.application.dxf_export"),
    ("backend.services.elevation",     "backend.application.elevation"),
    ("backend.services.executor",      "backend.application.executor"),
    ("backend.services.export_service","backend.application.export_service"),
    ("backend.services.geocode",       "backend.application.geocode"),
    ("backend.services.geojson",       "backend.application.geojson"),
    ("backend.services.gis",           "backend.application.gis"),
    ("backend.services.health",        "backend.application.health"),
    ("backend.services.housekeeper",   "backend.application.housekeeper"),
    ("backend.services.jobs",          "backend.application.jobs"),
    ("backend.services.projects",      "backend.application.projects"),
    ("backend.services.webhooks",      "backend.application.webhooks"),
)

_self = sys.modules[__name__]
for _compat, _real in _ALIASES:
    mod = _register_alias(_compat, _real)
    if mod is not None:
        # Expõe como atributo do pacote para que monkeypatch.setattr funcione
        _short = _compat.split(".")[-1]
        setattr(_self, _short, mod)
