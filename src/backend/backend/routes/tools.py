"""
backend/routes/tools.py
Router de ferramentas GIS (geocodificação, elevação SRTM, perfil de terreno).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.core.auth import require_token
from backend.core.logger import get_logger
from backend.models import (
    ElevationPointResponse,
    ElevationProfileRequest,
    ElevationProfileResponse,
    ElevationQueryRequest,
)
import backend.services.elevation as _elev_mod
import backend.services.geocode as _geocode_mod
from backend.routes.deps import cache_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/v1/tools/geocode", tags=["Tools"])
async def geocode_query(
    query: str = Query(..., min_length=1, max_length=200, description="Endereço, Lat/Lon ou UTM"),
    _: None = Depends(require_token),
):
    """
    Geocodifica um texto de entrada em coordenadas geográficas (EPSG:4326).

    Estratégia (custo zero, em ordem de prioridade):
      1. Coordenadas decimais diretas — ex.: ``-22.15018, -42.92185``
      2. Coordenadas UTM SIRGAS 2000  — ex.: ``23K 788547 7634925``
      3. Endereço por Nominatim/OSM   — ex.: ``Rua das Flores, Nova Friburgo``

    Returns:
        ``{ latitude, longitude, source, display_name? }``
    """
    result = _geocode_mod.geocode(query)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Não foi possível geocodificar: {query!r}",
        )
    return result


@router.post(
    "/api/v1/tools/elevation/query",
    tags=["Tools"],
    response_model=ElevationPointResponse,
)
async def query_elevation(
    req: ElevationQueryRequest,
    _: None = Depends(require_token),
):
    """Consulta a elevação (Z) num único ponto lat/lon via SRTM (offline-first)."""
    try:
        svc = _elev_mod.ElevationService(cache=cache_service)
        z = svc.get_elevation_at_point(req.latitude, req.longitude)
        return ElevationPointResponse(
            latitude=req.latitude, longitude=req.longitude, elevation=z
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("elevation_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao obter elevação.")


@router.post(
    "/api/v1/tools/elevation/profile",
    tags=["Tools"],
    response_model=ElevationProfileResponse,
)
async def query_profile(
    req: ElevationProfileRequest,
    _: None = Depends(require_token),
):
    """Retorna o perfil de elevação (lista de Z) ao longo de um caminho."""
    try:
        svc = _elev_mod.ElevationService(cache=cache_service)
        coords = [(p[0], p[1]) for p in req.path]
        elevations = svc.get_elevation_profile(coords)
        return ElevationProfileResponse(elevations=elevations)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("elevation_profile_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao gerar perfil de elevação.")
