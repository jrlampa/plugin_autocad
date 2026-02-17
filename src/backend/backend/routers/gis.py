import logging
from fastapi import APIRouter, Header, HTTPException, Depends, Query
from backend.models import (
    ElevationQueryRequest, ElevationPointResponse, 
    ElevationProfileRequest, ElevationProfileResponse,
    PrepareOsmRequest, PrepareGeoJsonRequest, PrepareResponse
)
from backend.core.security import require_token
from backend.core.config import AUTH_HEADER_NAME
from backend.services.elevation import ElevationService
from backend.services.cache import cache_service
from backend.services.geocode import smart_geocode
from backend.gis_core.osm import prepare_osm_compute
from backend.services.geojson import prepare_geojson_compute

router = APIRouter(tags=["GIS Tools"])
logger = logging.getLogger(__name__)

@router.post("/api/v1/tools/elevation/query", response_model=ElevationPointResponse)
async def query_elevation(
    req: ElevationQueryRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Query numeric elevation (Z) at a single lat/lon point."""
    await require_token(x_sisrua_token)
    try:
        svc = ElevationService(cache=cache_service)
        z = svc.get_elevation_at_point(req.latitude, req.longitude)
        return ElevationPointResponse(latitude=req.latitude, longitude=req.longitude, elevation=z)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("elevation_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Error retrieving elevation data")

@router.post("/api/v1/tools/elevation/profile", response_model=ElevationProfileResponse)
async def query_profile(
    req: ElevationProfileRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Retrieve an elevation profile along a given path."""
    await require_token(x_sisrua_token)
    try:
        svc = ElevationService(cache=cache_service)
        coords = [(p[0], p[1]) for p in req.path]
        elevations = svc.get_elevation_profile(coords)
        return ElevationProfileResponse(elevations=elevations)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("elevation_profile_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Error generating elevation profile")

@router.get("/api/v1/tools/geocode")
async def geocode_tool(
    query: str = Query(..., min_length=2),
    _ = Depends(require_token)
):
    """Smart Geocoding Tool."""
    return smart_geocode(query)

@router.post("/api/v1/prepare/osm", response_model=PrepareResponse)
async def prepare_osm(
    req: PrepareOsmRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """OSM Geometry Processing & BIM-LITE Transformation."""
    await require_token(x_sisrua_token)
    elev_svc = ElevationService(cache=cache_service)
    return prepare_osm_compute(
        req.latitude, 
        req.longitude, 
        req.radius, 
        cache_service=cache_service,
        elevation_service=elev_svc
    )

@router.post("/api/v1/prepare/geojson", response_model=PrepareResponse)
async def prepare_geojson(
    req: PrepareGeoJsonRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Synchronous GeoJSON Processing & Projection."""
    await require_token(x_sisrua_token)
    return prepare_geojson_compute(req.geojson)
