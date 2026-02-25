"""
backend/domain/geometry.py
Re-exporta funções de geometria GIS de `backend.gis_core.geometry`.

Expõe a API de geometria no namespace `backend.domain.geometry`
sem duplicar implementações.
"""
from backend.gis_core.geometry import (
    apply_local_offset,
    snap_to_edge,
    get_bounding_offset,
    generate_street_curbs,
)

__all__ = [
    "apply_local_offset",
    "snap_to_edge",
    "get_bounding_offset",
    "generate_street_curbs",
]
