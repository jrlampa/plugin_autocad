"""
backend/routes/enterprise.py
Router enterprise: exportação (GeoJSON/GeoPackage), sincronização e gestão do servidor.
Inclui endpoints ANEEL/PRODIST para configuração de normas da concessionária.
"""
from __future__ import annotations

import os
import signal
import threading
import time

from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth import require_token
from backend.core.logger import get_logger
from backend.models import HealthResponse, ProdistConfigRequest
from backend.services.projects import NotFoundError

logger = get_logger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Estado em memória da norma ativa (persiste durante a execução do processo)
# Thread-safe via _norma_lock. Em produção: usar Redis ou DB para persistência.
# ---------------------------------------------------------------------------
_norma_lock = threading.Lock()
_norma_config: dict = {
    "ativa": "ABNT",            # "ABNT" ou "PRODIST"
    "concessionaria": "",
    "classe_tensao": "MT",
    "numero_processo": "",
    "toast": None,              # Mensagem toast para o frontend
}


# ---------------------------------------------------------------------------
# Endpoints ANEEL/PRODIST
# ---------------------------------------------------------------------------

@router.get("/api/v1/normas/ativas", tags=["Normas"])
async def get_norma_ativa(_: None = Depends(require_token)):
    """
    Retorna a norma técnica ativa para o projeto corrente.

    Quando a norma é PRODIST, o campo `toast` contém a mensagem de
    notificação que o frontend deve exibir ao usuário (substituição de ABNT).

    Responses:
        200: Configuração atual da norma ativa.
    """
    from backend.gis_core.prodist import TOAST_NORMA_OVERRIDE
    with _norma_lock:
        config = dict(_norma_config)
    if config["ativa"] == "PRODIST" and not config["toast"]:
        config["toast"] = TOAST_NORMA_OVERRIDE
    return config


@router.post("/api/v1/normas/config", tags=["Normas"])
async def set_norma_config(
    req: ProdistConfigRequest,
    _: None = Depends(require_token),
):
    """
    Configura a norma técnica ativa para o projeto corrente.

    Quando `ativa=true`, ativa ANEEL/PRODIST e define a mensagem toast
    informando que as regras ABNT foram substituídas pelas regras da
    concessionária (PRODIST Módulo 1 §4).

    Quando `ativa=false`, restaura ABNT como norma padrão.

    Args:
        req: Configuração PRODIST (concessionária, classe de tensão).
    """
    from backend.gis_core.prodist import (
        TensaoClasse,
        buffer_de_seguranca_m,
        faixa_servidao_m,
        TOAST_NORMA_OVERRIDE,
        TOAST_NORMA_ABNT_RESTAURADA,
    )

    if req.ativa:
        try:
            classe = TensaoClasse(req.classe_tensao)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"classe_tensao inválida: {req.classe_tensao!r}. Use BT, MT ou AT.",
            )
        with _norma_lock:
            _norma_config["ativa"] = "PRODIST"
            _norma_config["concessionaria"] = req.concessionaria
            _norma_config["classe_tensao"] = req.classe_tensao
            _norma_config["numero_processo"] = req.numero_processo
            _norma_config["toast"] = TOAST_NORMA_OVERRIDE
        logger.info(
            "norma_prodist_ativada",
            concessionaria=req.concessionaria,
            classe_tensao=req.classe_tensao,
        )
        return {
            "norma_ativa": "PRODIST",
            "concessionaria": req.concessionaria,
            "classe_tensao": req.classe_tensao,
            "buffer_seguranca_m": buffer_de_seguranca_m(classe),
            "faixa_servidao_m": faixa_servidao_m(classe),
            "toast": TOAST_NORMA_OVERRIDE,
            "abnt_substituida": True,
        }
    else:
        with _norma_lock:
            _norma_config["ativa"] = "ABNT"
            _norma_config["concessionaria"] = ""
            _norma_config["classe_tensao"] = "MT"
            _norma_config["numero_processo"] = ""
            _norma_config["toast"] = None
        logger.info("norma_abnt_restaurada")
        return {
            "norma_ativa": "ABNT",
            "toast": TOAST_NORMA_ABNT_RESTAURADA,
            "abnt_substituida": False,
        }


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


@router.get("/api/v1/export/dxf-prodist/{project_id}", tags=["Enterprise"])
async def export_dxf_prodist(
    project_id: str,
    include_buffers: bool = True,
    _: None = Depends(require_token),
):
    """
    Exporta projeto como DXF R2010 com metadados ANEEL/PRODIST.

    Quando `include_buffers=true` (padrão), gera faixas de segurança
    geométricas (polígonos) conforme NR-10:2016 e PRODIST Módulo 3 §3.4
    nas camadas SISRUA_ANEEL_BUFFER_BT/MT/AT.

    A norma ANEEL/PRODIST é lida da configuração ativa do servidor
    (definida via POST /api/v1/normas/config). Se a norma ativa for ABNT,
    retorna erro 409 orientando o usuário a ativar PRODIST primeiro.

    Args:
        project_id:      ID do projeto a exportar.
        include_buffers: Inclui faixas de segurança (padrão: true).
    """
    from fastapi.responses import FileResponse
    from backend.gis_core.prodist import build_prodist_metadata, TensaoClasse
    import backend.api as _api

    with _norma_lock:
        config = dict(_norma_config)

    if config.get("ativa") != "PRODIST":
        raise HTTPException(
            status_code=409,
            detail=(
                "Norma ANEEL/PRODIST não está ativa. "
                "Ative via POST /api/v1/normas/config antes de exportar."
            ),
        )

    try:
        classe = TensaoClasse(config["classe_tensao"])
    except ValueError:
        classe = TensaoClasse.MT

    prodist_meta = build_prodist_metadata(
        concessionaria=config.get("concessionaria", "Não informada"),
        classe_tensao=classe,
        numero_processo=config.get("numero_processo", ""),
    )

    try:
        path = _api.export_service.export_project_to_dxf(
            project_id,
            prodist_metadata=prodist_meta,
            include_prodist_buffers=include_buffers,
        )
        return FileResponse(
            path=str(path),
            media_type="application/dxf",
            filename=f"sisrua_{project_id}_prodist.dxf",
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("export_dxf_prodist_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao exportar DXF PRODIST: {e}")


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
