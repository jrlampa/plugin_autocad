import logging
from typing import Dict, Any
from fastapi import APIRouter, Header, HTTPException, Depends
from starlette.responses import Response
from backend.models import ProjectUpdateRequest
from backend.core.security import require_token
from backend.core.config import AUTH_HEADER_NAME
from backend.core.container import project_service, export_service, webhook_service
from backend.core.bus import InternalEvent

router = APIRouter(tags=["Projects"])
logger = logging.getLogger(__name__)

@router.put("/api/v1/projects/{project_id}")
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Update project metadata safely using Optimistic Locking."""
    await require_token(x_sisrua_token)
    try:
        updated = project_service.update_metadata(
            project_id=project_id,
            name=req.project_name,
            crs=req.crs_out,
            version=req.version
        )
        return updated
    except Exception as e:
        logger.error("update_project_failed", project_id=project_id, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/api/v1/events/emit")
async def emit_event(
    req: InternalEvent,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Internal endpoint for broadcasting system events."""
    await require_token(x_sisrua_token)
    webhook_service.broadcast(req.event_type, req.payload)
    return {"status": "event_broadcasted"}

@router.get("/api/v1/projects/{project_id}/export/gpkg")
async def export_geopackage(
    project_id: str,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Export project data to OGC GeoPackage format."""
    await require_token(x_sisrua_token)
    if not export_service:
         raise HTTPException(status_code=501, detail="Export service not configured")
         
    try:
        gpkg_binary = export_service.export_as_gpkg(project_id)
        return Response(
            content=gpkg_binary,
            media_type="application/geopackage+sqlite3",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}.gpkg"}
        )
    except Exception as e:
        logger.error("export_failed", project_id=project_id, error=str(e))
        raise HTTPException(status_code=404, detail="Project or data not found for export")
