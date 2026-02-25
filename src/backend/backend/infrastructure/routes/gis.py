from fastapi import APIRouter, Depends, HTTPException, Body
from backend.application.gis import gis_service
from backend.shared.auth import require_token
from typing import Dict, Any

router = APIRouter(prefix="/gis", tags=["GIS"])

@router.post("/convert/kml", dependencies=[Depends(require_token)])
async def convert_kml(payload: Dict[str, Any] = Body(...)):
    """Converts KML content to GeoJSON."""
    kml_content = payload.get("content")
    if not kml_content:
        raise HTTPException(status_code=400, detail="Missing KML content")
        
    result = gis_service.process_kml(kml_content)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
        
    return result
