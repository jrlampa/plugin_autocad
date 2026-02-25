"""
backend/domain/osm.py
Re-exporta o pipeline OSM de `backend.gis_core.osm`.

Expõe `prepare_osm_compute` e helpers internos no namespace
`backend.domain.osm` para consumo unificado pelos testes e
pela camada de aplicação.
"""
from backend.gis_core.osm import (
    prepare_osm_compute,
    _fetch_overpass_data,
    _parse_overpass_to_features,
    _OsmWayRow,
    _OsmNodeRow,
)

__all__ = [
    "prepare_osm_compute",
    "_fetch_overpass_data",
    "_parse_overpass_to_features",
    "_OsmWayRow",
    "_OsmNodeRow",
]
