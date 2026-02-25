"""
backend/routes/prepare.py
Router de preparação de dados GIS: OSM síncrono, GeoJSON, IBGE e INEA.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth import require_token
from backend.gis_core.osm import prepare_osm_compute
from backend.gis_core.ibge import prepare_ibge_compute
from backend.gis_core.inea import prepare_inea_compute
from backend.models import (
    PrepareGeoJsonRequest,
    PrepareIbgeRequest,
    PrepareIneaRequest,
    PrepareOsmRequest,
    PrepareResponse,
)
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


@router.post("/api/v1/prepare/ibge", tags=["Urban Data"], response_model=PrepareResponse)
async def prepare_ibge(
    req: PrepareIbgeRequest,
    _: None = Depends(require_token),
):
    """
    **Malha Municipal IBGE**: baixa e projeta o limite geográfico de um município
    a partir da API gratuita do IBGE (Malhas Geográficas v3).

    Retorna feições Polyline representando o contorno municipal, prontas
    para inserção no desenho AutoCAD como referência cadastral (NBR 14166).
    """
    return prepare_ibge_compute(
        nome_municipio=req.nome_municipio,
        uf=req.uf,
        cache_service=cache_service,
    )


@router.post("/api/v1/prepare/inea", tags=["Urban Data"], response_model=PrepareResponse)
async def prepare_inea(
    req: PrepareIneaRequest,
    _: None = Depends(require_token),
):
    """
    **Feições Ambientais INEA-RJ**: obtém dados geoespaciais do Instituto
    Estadual do Ambiente do Rio de Janeiro via WFS público (GeoServer).

    Tipos disponíveis: `hidrografia`, `bacias`, `unidades_conservacao`, `manguezais`.
    Suporta filtro por bounding box para consultas localizadas.
    """
    bbox = tuple(req.bbox) if req.bbox else None
    return prepare_inea_compute(
        typename=req.typename,
        bbox=bbox,
        cache_service=cache_service,
    )
