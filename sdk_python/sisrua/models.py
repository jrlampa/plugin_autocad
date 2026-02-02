from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime

class CadFeature(BaseModel):
    feature_type: Optional[str] = Field(None)
    layer: Optional[Any] = Field(None)
    name: Optional[Any] = Field(None)
    highway: Optional[Any] = Field(None)
    width_m: Optional[Any] = Field(None)
    coords_xy: Optional[Any] = Field(None)
    insertion_point_xy: Optional[Any] = Field(None)
    block_name: Optional[Any] = Field(None)
    block_filepath: Optional[Any] = Field(None)
    rotation: Optional[Any] = Field(None)
    scale: Optional[Any] = Field(None)
    color: Optional[Any] = Field(None)
    elevation: Optional[Any] = Field(None)
    slope: Optional[Any] = Field(None)

class ChatRequest(BaseModel):
    message: str = Field(...)
    context: Optional[Any] = Field(None)
    job_id: Optional[Any] = Field(None)

class ChatResponse(BaseModel):
    response: str = Field(...)

class ComponentHealth(BaseModel):
    status: str = Field(...)
    details: Optional[Any] = Field(None)
    latency_ms: Optional[Any] = Field(None)

class DeepHealthResponse(BaseModel):
    status: str = Field(...)
    components: Any = Field(...)
    system_latency_ms: float = Field(...)

class ElevationPointResponse(BaseModel):
    latitude: float = Field(...)
    longitude: float = Field(...)
    elevation: Optional[Any] = Field(None)

class ElevationProfileRequest(BaseModel):
    path: List[Any] = Field(...)

class ElevationProfileResponse(BaseModel):
    elevations: List[Any] = Field(...)

class ElevationQueryRequest(BaseModel):
    latitude: float = Field(...)
    longitude: float = Field(...)

class HTTPValidationError(BaseModel):
    detail: Optional[List[Any]] = Field(None)

class HealthResponse(BaseModel):
    status: str = Field(...)

class InternalEvent(BaseModel):
    event_type: str = Field(...)
    payload: Any = Field(...)

class JobStatusResponse(BaseModel):
    job_id: str = Field(...)
    kind: str = Field(...)
    status: str = Field(...)
    progress: float = Field(...)
    message: Optional[Any] = Field(None)
    result: Optional[Any] = Field(None)
    error: Optional[Any] = Field(None)
    created_at: float = Field(...)
    updated_at: float = Field(...)

class PrepareGeoJsonRequest(BaseModel):
    geojson: Any = Field(...)

class PrepareJobRequest(BaseModel):
    kind: str = Field(...)
    latitude: Optional[Any] = Field(None)
    longitude: Optional[Any] = Field(None)
    radius: Optional[Any] = Field(None)
    geojson: Optional[Any] = Field(None)

class PrepareOsmRequest(BaseModel):
    latitude: float = Field(...)
    longitude: float = Field(...)
    radius: float = Field(...)

class PrepareResponse(BaseModel):
    crs_out: Optional[Any] = Field(None)
    features: List[Any] = Field(...)
    cache_hit: Optional[Any] = Field(None)

class ProjectUpdateRequest(BaseModel):
    version: int = Field(...)
    project_name: Optional[Any] = Field(None)
    crs_out: Optional[Any] = Field(None)

class ValidationError(BaseModel):
    loc: List[Any] = Field(...)
    msg: str = Field(...)
    type: str = Field(...)

class WebhookRegistrationRequest(BaseModel):
    url: str = Field(...)
    events: Optional[Any] = Field(None)

