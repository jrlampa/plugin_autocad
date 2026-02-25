"""
backend/routes/tools.py
Router de ferramentas GIS (geocodificação, elevação SRTM, perfil de terreno).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.shared.auth import require_token
from backend.shared.logger import get_logger
from backend.domain.dto import (
    ContourLine,
    ElevationContoursRequest,
    ElevationContoursResponse,
    ElevationPointResponse,
    ElevationProfileRequest,
    ElevationProfileResponse,
    ElevationQueryRequest,
)
import backend.application.elevation as _elev_mod
import backend.application.geocode as _geocode_mod
from backend.infrastructure.routes.deps import cache_service

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


@router.post(
    "/api/v1/tools/elevation/contours",
    tags=["Tools"],
    response_model=ElevationContoursResponse,
)
async def get_elevation_contours(
    req: ElevationContoursRequest,
    _: None = Depends(require_token),
):
    """
    Gera curvas de nível (isolinhas de elevação) para uma área delimitada (bounding box).

    Útil para visualização de terreno em projetos de urbanização,
    drenagem pluvial e análise de declividade (ABNT NBR 14166:1998).

    Os dados de elevação SRTM são obtidos offline-first via cache local.
    A geração de isolinhas usa scikit-image (dependência de produção; instalada
    via ``requirements.txt``). Em ambiente CI, o método é mockado pelos testes.
    Quando scikit-image não está disponível, o endpoint retorna lista vazia.

    Args:
        req: Bounding box (min/max lat/lon) e intervalo de contorno em metros.

    Returns:
        Lista de curvas de nível com elevação e geometria em EPSG:4326.
    """
    try:
        svc = _elev_mod.ElevationService(cache=cache_service)
        raw = svc.get_contours(
            req.min_lat, req.min_lon, req.max_lat, req.max_lon,
            interval=req.interval,
        )
        contours = [
            ContourLine(elevation=c["elevation"], geometry=c["geometry"])
            for c in raw
        ]
        return ElevationContoursResponse(
            contours=contours,
            interval=req.interval,
            count=len(contours),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("elevation_contours_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao gerar curvas de nível.")
