from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any, Dict

class HealthResponse(BaseModel):
    status: str = Field(..., description="Operational status of the API", example="ok")

class PrepareOsmRequest(BaseModel):
    latitude: float = Field(..., description="Target latitude (EPSG:4326)", example=-21.7634)
    longitude: float = Field(..., description="Target longitude (EPSG:4326)", example=-41.3235)
    radius: float = Field(..., description="Search radius in meters", example=500.0)

class PrepareGeoJsonRequest(BaseModel):
    geojson: Any = Field(..., description="GeoJSON string or object to process")

class PrepareJobRequest(BaseModel):
    kind: Literal["osm", "geojson"] = Field(..., description="Type of data preparation job")
    latitude: Optional[float] = Field(None, description="Required for kind='osm'")
    longitude: Optional[float] = Field(None, description="Required for kind='osm'")
    radius: Optional[float] = Field(None, description="Required for kind='osm'")
    geojson: Any | None = Field(None, description="Required for kind='geojson'")

class CadFeature(BaseModel):
    feature_type: Literal["Polyline", "Point"] = Field("Polyline", description="CAD entity type")
    layer: Optional[str] = Field(None, description="Target AutoCAD layer name")
    name: Optional[str] = Field(None, description="Display name for the feature")
    highway: Optional[str] = Field(None, description="OSM highway tag value")
    width_m: Optional[float] = Field(None, description="Estimated width in meters")

    # For Polyline features
    coords_xy: Optional[List[List[float]]] = Field(None, description="Coordinates in projected CRS (SIRGAS 2000)")

    # For Point features (blocks)
    insertion_point_xy: Optional[List[float]] = Field(None, description="Insertion point in projected CRS")
    block_name: Optional[str] = Field(None, description="Name of the AutoCAD block")
    block_filepath: Optional[str] = Field(None, description="Path to the block definition file")
    rotation: Optional[float] = Field(None, description="Rotation in radians")
    scale: Optional[float] = Field(None, description="Scale factor")

    # Phase 2 fields
    color: Optional[str] = Field(None, description="ACI color code or RGB string")
    elevation: Optional[float] = Field(None, description="Elevation (Z value) in meters")
    slope: Optional[float] = Field(None, description="Calculated slope percentage")

class PrepareResponse(BaseModel):
    crs_out: Optional[str] = Field(None, description="Projected Coordinate Reference System", example="EPSG:31983")
    features: List[CadFeature] = Field(..., description="List of CAD-ready features")
    cache_hit: Optional[bool] = Field(None, description="Indicates if the result was served from cache")

class JobStatusResponse(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    kind: str = Field(..., description="Job type (osm/geojson)")
    status: Literal["queued", "processing", "completed", "failed"] = Field(..., description="Current job execution status")
    progress: float = Field(..., description="Job progress from 0.0 to 1.0")
    message: Optional[str] = Field(None, description="Human-readable status message")
    result: Optional[PrepareResponse] = Field(None, description="Job result payload (only on completion)")
    error: Optional[str] = Field(None, description="Error detail if job failed")
    created_at: float = Field(..., description="Unix timestamp of job creation")
    updated_at: float = Field(..., description="Unix timestamp of last job update")

class ElevationQueryRequest(BaseModel):
    latitude: float = Field(..., description="Target latitude (EPSG:4326)")
    longitude: float = Field(..., description="Target longitude (EPSG:4326)")

class ElevationProfileRequest(BaseModel):
    path: List[List[float]] = Field(..., description="List of [lat, lon] points for the profile path")

class ElevationPointResponse(BaseModel):
    latitude: float = Field(..., description="Requested latitude")
    longitude: float = Field(..., description="Requested longitude")
    elevation: Optional[float] = Field(None, description="Elevation in meters (Z value)")

class ElevationProfileResponse(BaseModel):
    elevations: List[float] = Field(..., description="List of elevations in meters along the path")

class WebhookRegistrationRequest(BaseModel):
    url: str = Field(..., description="Target URL to receive webhook events", example="https://example.com/webhook")
    events: Optional[List[str]] = Field(None, description="Optional list of events to subscribe to (default: all)")
