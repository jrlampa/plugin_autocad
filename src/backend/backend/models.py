from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional, Literal, Any, Dict

class PrepareOsmRequest(BaseModel):
    latitude: float
    longitude: float
    radius: float

class PrepareGeoJsonRequest(BaseModel):
    geojson: Any  # pode vir como string JSON ou objeto GeoJSON

class PrepareJobRequest(BaseModel):
    kind: str  # "osm" | "geojson"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[float] = None
    geojson: Any | None = None

class CadFeature(BaseModel):
    feature_type: Literal["Polyline", "Point"] = "Polyline"  # Default to Polyline
    layer: Optional[str] = None
    name: Optional[str] = None
    highway: Optional[str] = None
    width_m: Optional[float] = None

    # For Polyline features
    coords_xy: Optional[List[List[float]]] = None

    # For Point features (blocks)
    insertion_point_xy: Optional[List[float]] = None
    block_name: Optional[str] = None
    block_filepath: Optional[str] = None
    rotation: Optional[float] = None
    scale: Optional[float] = None

    # Phase 2 fields
    color: Optional[str] = None
    elevation: Optional[float] = None
    slope: Optional[float] = None

class PrepareResponse(BaseModel):
    crs_out: Optional[str] = None
    features: List[CadFeature]
    cache_hit: Optional[bool] = None  # Indica se o resultado veio do cache

class JobStatusResponse(BaseModel):
    job_id: str
    kind: str
    status: str
    progress: float
    message: Optional[str] = None
    result: Optional[PrepareResponse] = None 
    error: Optional[str] = None

class ElevationQueryRequest(BaseModel):
    latitude: float
    longitude: float

class ElevationProfileRequest(BaseModel):
    path: List[List[float]] # [[lat, lon], [lat, lon], ...]
