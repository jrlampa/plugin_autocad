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

class ProjectCreateRequest(FrozenBaseModel):
    project_name: str = Field(..., min_length=1, max_length=255, description="Nome do projeto")
    crs_out: Optional[str] = Field("EPSG:31983", description="CRS de saída (padrão: SIRGAS 2000 Zona 23S)")

class ProjectUpdateRequest(FrozenBaseModel):
    version: int = Field(..., description="Current version of the project for optimistic locking")
    project_name: Optional[str] = Field(None, description="New project name")
    crs_out: Optional[str] = Field(None, description="New CRS")

class PrepareOsmRequest(FrozenBaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Target latitude (EPSG:4326)", json_schema_extra={"example": -21.7634})
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Target longitude (EPSG:4326)", json_schema_extra={"example": -41.3235})
    radius: float = Field(..., gt=0.0, le=5000.0, description="Search radius in meters (1–5000)", json_schema_extra={"example": 500.0})

class PrepareGeoJsonRequest(FrozenBaseModel):
    geojson: Any = Field(..., description="GeoJSON string or object to process")

class PrepareJobRequest(FrozenBaseModel):
    kind: Literal["osm", "geojson"] = Field(..., description="Type of data preparation job")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Required for kind='osm'")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Required for kind='osm'")
    radius: Optional[float] = Field(None, gt=0.0, le=5000.0, description="Required for kind='osm'")
    geojson: Any | None = Field(None, description="Required for kind='geojson'")

class CadFeature(BaseModel):
    feature_type: Literal["Polyline", "Point"] = Field("Polyline", description="CAD entity type")
    layer: str = Field("0", description="Target AutoCAD layer name")
    name: Optional[str] = Field(None, description="Display name for the feature")
    highway: Optional[str] = Field(None, description="OSM highway tag value")
    width_m: Optional[float] = Field(None, description="Estimated width in meters")

    # For Polyline features (2.5D: Z is stored in elevation field, not here)
    coords_xy: Optional[List[List[float]]] = Field(default_factory=list, description="2D Coordinates [X, Y] in projected CRS (SIRGAS 2000). 2.5D Architecture: Z is treated as an attribute.")

    # For Point features (blocks)
    insertion_point_xy: Optional[List[float]] = Field(default_factory=list, description="2D Insertion point [X, Y] in projected CRS. Z is treated as an attribute.")
    block_name: Optional[str] = Field(None, description="Name of the AutoCAD block")
    block_filepath: Optional[str] = Field(None, description="Path to the block definition file")
    rotation: float = Field(0.0, description="Rotation in radians")
    scale: float = Field(1.0, description="Scale factor")

    # Phase 2 fields
    color: Optional[str] = Field(None, description="ACI color code or RGB string")
    elevation: Optional[float] = Field(None, description="Elevation (Z value) in meters. Source of truth for 2.5D z-axis.")
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

class ElevationContoursRequest(FrozenBaseModel):
    """Bounding box e intervalo para geração de curvas de nível."""
    min_lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude mínima da área (EPSG:4326)")
    min_lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude mínima da área")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude máxima da área")
    max_lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude máxima da área")
    interval: float = Field(10.0, gt=0.0, le=1000.0, description="Intervalo de contorno em metros")

    @model_validator(mode="after")
    def validate_bounds(self) -> "ElevationContoursRequest":
        if self.max_lat <= self.min_lat:
            raise ValueError("max_lat deve ser maior que min_lat")
        if self.max_lon <= self.min_lon:
            raise ValueError("max_lon deve ser maior que min_lon")
        return self

class ContourLine(FrozenBaseModel):
    elevation: float = Field(..., description="Elevação da curva de nível em metros")
    geometry: List[List[float]] = Field(..., description="Lista de pares [lat, lon] formando a curva")

class ElevationContoursResponse(FrozenBaseModel):
    contours: List[ContourLine] = Field(..., description="Lista de curvas de nível")
    interval: float = Field(..., description="Intervalo de contorno utilizado em metros")
    count: int = Field(..., description="Total de curvas de nível geradas")

class WebhookRegistrationRequest(FrozenBaseModel):
    url: str = Field(..., description="Target URL to receive webhook events", json_schema_extra={"example": "https://example.com/webhook"})
    events: Optional[List[str]] = Field(None, description="Optional list of events to subscribe to (default: all)")

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        """Garante que a URL é HTTP/HTTPS e tem hostname para prevenir SSRF."""
        stripped = v.strip()
        if not stripped.lower().startswith(("http://", "https://")):
            raise ValueError("A URL do webhook deve começar com http:// ou https://")
        from urllib.parse import urlparse
        parsed = urlparse(stripped)
        if not parsed.netloc:
            raise ValueError("A URL do webhook deve conter um hostname válido")
        return stripped

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Sanitiza e valida entradas da lista de eventos."""
        if v is None:
            return v
        cleaned = []
        for evt in v:
            s = str(evt).strip()[:128]
            if s:
                cleaned.append(s)
        return cleaned if cleaned else None

class InternalEvent(FrozenBaseModel):
    event_type: str = Field(..., description="Type of the internal event", json_schema_extra={"example": "project_saved"})
    payload: Dict[str, Any] = Field(..., description="Event payload data")

class ProdistConfigRequest(FrozenBaseModel):
    """Configuração de norma ANEEL/PRODIST para o projeto atual."""
    ativa: bool = Field(..., description="True para ativar PRODIST, False para ABNT")
    concessionaria: str = Field(
        "Não informada",
        max_length=128,
        description="Nome da distribuidora de energia (ex.: 'Light S.A.')",
    )
    classe_tensao: str = Field(
        "MT",
        description="Classe de tensão: BT (baixa), MT (média) ou AT (alta)",
    )
    numero_processo: str = Field(
        "",
        max_length=64,
        description="Nº do processo ANEEL (opcional)",
    )

    @field_validator("classe_tensao")
    @classmethod
    def validate_classe_tensao(cls, v: str) -> str:
        allowed = {"BT", "MT", "AT"}
        upper = v.strip().upper()
        if upper not in allowed:
            raise ValueError(f"classe_tensao deve ser BT, MT ou AT. Recebido: {v!r}")
        return upper
