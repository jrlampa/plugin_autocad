from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import List, Optional, Literal, Any, Dict

class FrozenBaseModel(BaseModel):
    model_config = ConfigDict(frozen=True)

class HealthResponse(FrozenBaseModel):
    status: str = Field(..., description="Operational status of the API", json_schema_extra={"example": "ok"})

class ComponentHealth(FrozenBaseModel):
    status: Literal["up", "down", "degraded"] = Field(..., description="Status of the specific component")
    details: Optional[str] = Field(None, description="Error message or metadata")
    latency_ms: Optional[float] = Field(None, description="Response time in milliseconds")

class DeepHealthResponse(HealthResponse):
    components: Dict[str, ComponentHealth] = Field(..., description="Health status of internal dependencies")
    system_latency_ms: float = Field(..., description="Total time taken to perform health check")

class ProjectUpdateRequest(FrozenBaseModel):
    version: int = Field(..., description="Current version of the project for optimistic locking")
    project_name: Optional[str] = Field(None, description="New project name")
    crs_out: Optional[str] = Field(None, description="New CRS")

class PrepareOsmRequest(FrozenBaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Target latitude (EPSG:4326)", json_schema_extra={"example": -21.7634})
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Target longitude (EPSG:4326)", json_schema_extra={"example": -41.3235})
    radius: float = Field(..., gt=0.0, le=50000.0, description="Search radius in meters (1–50000)", json_schema_extra={"example": 500.0})

class PrepareGeoJsonRequest(FrozenBaseModel):
    geojson: Any = Field(..., description="GeoJSON string or object to process")

class PrepareJobRequest(FrozenBaseModel):
    kind: Literal["osm", "geojson"] = Field(..., description="Type of data preparation job")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Required for kind='osm'")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Required for kind='osm'")
    radius: Optional[float] = Field(None, gt=0.0, le=50000.0, description="Required for kind='osm'")
    geojson: Any | None = Field(None, description="Required for kind='geojson'")

class CadFeature(BaseModel):
    feature_type: Literal["Polyline", "Point"] = Field("Polyline", description="CAD entity type")
    layer: str = Field("0", description="Target AutoCAD layer name")
    name: Optional[str] = Field(None, description="Display name for the feature")
    highway: Optional[str] = Field(None, description="OSM highway tag value")
    width_m: Optional[float] = Field(None, description="Estimated width in meters")

    # For Polyline features
    coords_xy: Optional[List[List[float]]] = Field(default_factory=list, description="Coordinates in projected CRS (SIRGAS 2000)")

    # For Point features (blocks)
    insertion_point_xy: Optional[List[float]] = Field(default_factory=list, description="Insertion point in projected CRS")
    block_name: Optional[str] = Field(None, description="Name of the AutoCAD block")
    block_filepath: Optional[str] = Field(None, description="Path to the block definition file")
    rotation: float = Field(0.0, description="Rotation in radians")
    scale: float = Field(1.0, description="Scale factor")

    # Phase 2 fields
    color: Optional[str] = Field(None, description="ACI color code or RGB string")
    elevation: Optional[float] = Field(None, description="Elevation (Z value) in meters")
    slope: Optional[float] = Field(None, description="Calculated slope percentage")
    original_geojson_properties: Dict[str, Any] = Field(default_factory=dict, description="Original GeoJSON properties for portability")

class PrepareResponse(FrozenBaseModel):
    crs_out: Optional[str] = Field(None, description="Projected Coordinate Reference System", json_schema_extra={"example": "EPSG:31983"})
    features: List[CadFeature] = Field(..., description="List of CAD-ready features")
    cache_hit: Optional[bool] = Field(None, description="Indicates if the result was served from cache")

class JobStatusResponse(FrozenBaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    kind: str = Field(..., description="Job type (osm/geojson)")
    status: Literal["queued", "processing", "completed", "failed"] = Field(..., description="Current job execution status")
    progress: float = Field(..., description="Job progress from 0.0 to 1.0")
    message: Optional[str] = Field(None, description="Human-readable status message")
    result: Optional[PrepareResponse] = Field(None, description="Job result payload (only on completion)")
    error: Optional[str] = Field(None, description="Error detail if job failed")
    created_at: float = Field(..., description="Unix timestamp of job creation")
    updated_at: float = Field(..., description="Unix timestamp of last job update")

class ElevationQueryRequest(FrozenBaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Target latitude (EPSG:4326)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Target longitude (EPSG:4326)")

class ElevationProfileRequest(FrozenBaseModel):
    path: List[List[float]] = Field(..., min_length=2, description="List of [lat, lon] points for the profile path")

    @field_validator("path")
    @classmethod
    def validate_path_coordinates(cls, v: List[List[float]]) -> List[List[float]]:
        for point in v:
            if len(point) < 2:
                raise ValueError("Cada ponto deve ter pelo menos [lat, lon].")
            lat, lon = point[0], point[1]
            if not (-90.0 <= lat <= 90.0):
                raise ValueError(f"Latitude inválida: {lat}. Deve estar entre -90 e 90.")
            if not (-180.0 <= lon <= 180.0):
                raise ValueError(f"Longitude inválida: {lon}. Deve estar entre -180 e 180.")
        return v

class ElevationPointResponse(FrozenBaseModel):
    latitude: float = Field(..., description="Requested latitude")
    longitude: float = Field(..., description="Requested longitude")
    elevation: Optional[float] = Field(None, description="Elevation in meters (Z value)")

class ElevationProfileResponse(FrozenBaseModel):
    elevations: List[float] = Field(..., description="List of elevations in meters along the path")

class WebhookRegistrationRequest(FrozenBaseModel):
    url: str = Field(..., description="Target URL to receive webhook events", json_schema_extra={"example": "https://example.com/webhook"})
    events: Optional[List[str]] = Field(None, description="Optional list of events to subscribe to (default: all)")

class InternalEvent(FrozenBaseModel):
    event_type: str = Field(..., description="Type of the internal event", json_schema_extra={"example": "project_saved"})
    payload: Dict[str, Any] = Field(..., description="Event payload data")
