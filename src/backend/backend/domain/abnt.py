"""
backend/domain/abnt.py
Re-exporta metadados e validações ABNT de `backend.gis_core.abnt`.
"""
from backend.gis_core.abnt import (
    ABNT_ESCALAS_CADASTRAIS,
    AbntDrawingMetadata,
    validate_utm_coordinates,
    nearest_abnt_escala,
    build_default_metadata,
)

__all__ = [
    "ABNT_ESCALAS_CADASTRAIS",
    "AbntDrawingMetadata",
    "validate_utm_coordinates",
    "nearest_abnt_escala",
    "build_default_metadata",
]
