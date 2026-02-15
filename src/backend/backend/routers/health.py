from fastapi import APIRouter, Header, Depends
from backend.models import HealthResponse, DeepHealthResponse
from backend.services.health import health_service
from backend.core.security import require_token
from backend.core.config import AUTH_HEADER_NAME

router = APIRouter(tags=["Health"])

@router.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Verifica se a API está online."""
    return HealthResponse(status="ok")

@router.get("/health", include_in_schema=False)
async def health_check_legacy():
    """Fallback para versões antigas do plugin ou monitoramento simples."""
    return {"status": "ok"}

@router.get("/api/v1/health/detailed", response_model=DeepHealthResponse)
async def health_detailed(x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    """Deep health check verifying DB, Cache, and Configuration."""
    # Note: validation is handled inside the service if needed, 
    # but here we just pass the header for tracing/audit.
    return await health_service.get_deep_health()
