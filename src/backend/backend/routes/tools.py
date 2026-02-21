"""
backend/routes/tools.py
Router de ferramentas GIS (elevação SRTM, perfil de terreno).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth import require_token
from backend.core.logger import get_logger
from backend.models import (
    ElevationPointResponse,
    ElevationProfileRequest,
    ElevationProfileResponse,
    ElevationQueryRequest,
)
import backend.services.elevation as _elev_mod
from backend.routes.deps import cache_service

logger = get_logger(__name__)
router = APIRouter()


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
