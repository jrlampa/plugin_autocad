"""
backend/routes/prepare.py
Router de preparação de dados GIS: OSM síncrono e GeoJSON.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth import require_token
from backend.gis_core.osm import prepare_osm_compute
from backend.models import PrepareGeoJsonRequest, PrepareOsmRequest, PrepareResponse
from backend.routes.deps import cache_service
from backend.services.elevation import ElevationService
from backend.services.geojson import prepare_geojson_compute

router = APIRouter()


@router.post("/api/v1/prepare/osm", tags=["Urban Data"], response_model=PrepareResponse)
async def prepare_osm(
    req: PrepareOsmRequest,
    _: None = Depends(require_token),
):
    """
    **Aquisição Enterprise**: processamento OSM de alto desempenho.
    Busca dados via Overpass, projeta para SIRGAS 2000 UTM,
    sana a topologia e retorna features prontas para CAD/BIM-LITE.
    """
    elev_svc = ElevationService(cache=cache_service)
    return prepare_osm_compute(
        req.latitude,
        req.longitude,
        req.radius,
        cache_service=cache_service,
        elevation_service=elev_svc,
    )


@router.post("/api/v1/prepare/geojson", tags=["Prepare"], response_model=PrepareResponse)
async def prepare_geojson(
    req: PrepareGeoJsonRequest,
    _: None = Depends(require_token),
):
    """
    Preparação síncrona de GeoJSON.
    Aceita EPSG:4326, projeta para SIRGAS 2000 UTM e retorna features CAD.
    """
    return prepare_geojson_compute(req.geojson)
