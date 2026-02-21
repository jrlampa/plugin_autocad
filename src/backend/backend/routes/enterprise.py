"""
backend/routes/enterprise.py
Router enterprise: exportação (GeoJSON/GeoPackage), sincronização e gestão do servidor.
"""
from __future__ import annotations

import os
import signal
import threading
import time

from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth import require_token
from backend.core.logger import get_logger
from backend.models import HealthResponse
from backend.services.projects import NotFoundError

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/v1/export/geopackage/{project_id}", tags=["Enterprise"])
async def export_geopackage(
    project_id: str,
    _: None = Depends(require_token),
):
    """
    Exporta projeto completo no formato OGC GeoPackage (.gpkg).
    Garante interoperabilidade com ArcGIS, QGIS e Digital Twins corporativos.
    """
    from fastapi.responses import FileResponse
    import backend.api as _api
    try:
        path = _api.export_service.export_project_to_geopackage(project_id)
        return FileResponse(
            path=str(path),
            media_type="application/geopackage+sqlite3",
            filename=f"sisrua_{project_id}.gpkg",
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("export_geopackage_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao exportar GeoPackage: {e}")


@router.get("/api/v1/export/dxf/{project_id}", tags=["Enterprise"])
async def export_dxf(
    project_id: str,
    escala: int = 1_000,
    _: None = Depends(require_token),
):
    """
    Exporta projeto como arquivo DXF R2010 com metadados ABNT.

    Princípio 2.5D: elevação preservada como XDATA (não como coordenada Z).
    Conformidade: ABNT NBR 14166:1998 e NBR 13133:2021.

    Args:
        project_id: ID do projeto a exportar.
        escala: Escala cartográfica ABNT (padrão: 1000 = 1:1.000).
    """
    from fastapi.responses import FileResponse
    import backend.api as _api
    try:
        path = _api.export_service.export_project_to_dxf(project_id, escala=escala)
        return FileResponse(
            path=str(path),
            media_type="application/dxf",
            filename=f"sisrua_{project_id}.dxf",
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("export_dxf_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao exportar DXF: {e}")



@router.get("/api/v1/export/geojson/{project_id}", tags=["Enterprise"])
async def export_geojson(
    project_id: str,
    _: None = Depends(require_token),
):
    """
    Exporta projeto completo no formato GeoJSON.
    Portabilidade total para ferramentas web e análise espacial leve.
    """
    from fastapi.responses import FileResponse
    import backend.api as _api
    try:
        path = _api.export_service.export_project_to_geojson(project_id)
        return FileResponse(
            path=str(path),
            media_type="application/geo+json",
            filename=f"sisrua_{project_id}.geojson",
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("export_geojson_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao exportar GeoJSON: {e}")


@router.post("/api/v1/sync/cloud", tags=["Enterprise"])
async def sync_to_cloud(_: None = Depends(require_token)):
    """
    Interface de sincronização cloud (Enterprise).

    Quando `SISRUA_CLOUD_URL` não está configurada, retorna estatísticas locais reais
    e informa que a sincronização cloud está desativada.
    Quando configurada, esta rota seria o ponto de entrada para replicação remota.
    """
    cloud_url = os.environ.get("SISRUA_CLOUD_URL")

    # Coleta estatísticas reais do banco de dados local
    local_stats = _get_local_stats()

    if not cloud_url:
        return {
            "status": "local_only",
            "message": "Sincronização cloud não configurada. Defina SISRUA_CLOUD_URL para ativar.",
            "local_projects": local_stats["projects"],
            "local_features": local_stats["features"],
            "timestamp": time.time(),
        }

    # Ponto de extensão: integração com nó cloud real quando SISRUA_CLOUD_URL for definida.
    # A implementação deve usar um cliente HTTP com retry + circuit breaker.
    logger.info("cloud_sync_requested", cloud_url=cloud_url, **local_stats)
    return {
        "status": "pending",
        "message": "Sincronização cloud ainda não implementada para este nó.",
        "local_projects": local_stats["projects"],
        "local_features": local_stats["features"],
        "cloud_url": cloud_url,
        "timestamp": time.time(),
    }


def _get_local_stats() -> dict:
    """Consulta o banco SQLite local para obter contagens reais."""
    try:
        from backend.core.database import get_db_connection

        conn = get_db_connection()
        try:
            projects = conn.execute("SELECT COUNT(*) FROM Projects").fetchone()[0]
            features = conn.execute("SELECT COUNT(*) FROM CadFeatures").fetchone()[0]
            return {"projects": projects, "features": features}
        finally:
            conn.close()
    except Exception as e:
        logger.warning("local_stats_unavailable", error=str(e))
        return {"projects": 0, "features": 0}


@router.post(
    "/api/v1/management/shutdown",
    tags=["Infrastructure"],
    response_model=HealthResponse,
)
async def shutdown_server(_: None = Depends(require_token)):
    """
    **Desligamento gracioso**: solicita ao servidor que se encerre.
    Usado pelo plugin para parar o backend sem kill forçado.
    Requer Master Token.
    """

    def self_terminate():
        time.sleep(1.0)
        logger.warning("api_shutdown_requested_by_client")
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=self_terminate, daemon=True).start()
    return HealthResponse(status="shutting_down")
