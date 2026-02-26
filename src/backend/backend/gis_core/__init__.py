"""
backend/gis_core — Módulos de integração GIS (IBGE, INEA) e aliases de compatibilidade.

Registra aliases de retrocompatibilidade em sys.modules para que
patch("backend.gis_core.osm.func") e patch("backend.gis_core.osm_client.Cls")
apontem para os módulos reais (backend.domain.osm e backend.infrastructure.osm_client).
"""
from __future__ import annotations

import sys
import importlib


def _register_alias(compat: str, real: str) -> None:
    if compat not in sys.modules:
        try:
            mod = importlib.import_module(real)
            sys.modules[compat] = mod
        except Exception:
            pass


_ALIASES = (
    ("backend.gis_core.osm",        "backend.domain.osm"),
    ("backend.gis_core.osm_client", "backend.infrastructure.osm_client"),
    ("backend.gis_core.crs",        "backend.domain.crs"),
)

for _compat, _real in _ALIASES:
    _register_alias(_compat, _real)
