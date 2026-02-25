"""
backend/domain/dto.py
Re-exporta todos os DTOs/modelos Pydantic de `backend.models`.

Mantém compatibilidade com importações do namespace `backend.domain.dto`
sem duplicar definições.
"""
from backend.models import (
    FrozenBaseModel,
    HealthResponse,
    ComponentHealth,
    DeepHealthResponse,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    PrepareOsmRequest,
    PrepareGeoJsonRequest,
    PrepareJobRequest,
    CadFeature,
    PrepareResponse,
    JobStatusResponse,
    ElevationQueryRequest,
    ElevationProfileRequest,
    ElevationPointResponse,
    ElevationProfileResponse,
    ElevationContoursRequest,
    ContourLine,
    ElevationContoursResponse,
    WebhookRegistrationRequest,
    InternalEvent,
    PrepareIbgeRequest,
    PrepareIneaRequest,
    ProdistConfigRequest,
)

__all__ = [
    "FrozenBaseModel",
    "HealthResponse",
    "ComponentHealth",
    "DeepHealthResponse",
    "ProjectCreateRequest",
    "ProjectUpdateRequest",
    "PrepareOsmRequest",
    "PrepareGeoJsonRequest",
    "PrepareJobRequest",
    "CadFeature",
    "PrepareResponse",
    "JobStatusResponse",
    "ElevationQueryRequest",
    "ElevationProfileRequest",
    "ElevationPointResponse",
    "ElevationProfileResponse",
    "ElevationContoursRequest",
    "ContourLine",
    "ElevationContoursResponse",
    "WebhookRegistrationRequest",
    "InternalEvent",
    "PrepareIbgeRequest",
    "PrepareIneaRequest",
    "ProdistConfigRequest",
]
