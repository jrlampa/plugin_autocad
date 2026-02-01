from typing import Dict, Any, Optional
from backend.models import PrepareJobRequest, PrepareResponse
from backend.core.interfaces import IEventBus, ICache
from backend.services.jobs import update_job, check_cancellation
from backend.services.osm import prepare_osm_compute
from backend.services.geojson import prepare_geojson_compute
from backend.services.elevation import ElevationService
from backend.core.utils import sanitize_jsonable

class JobExecutor:
    def __init__(self, cache_service: ICache):
        self.cache_service = cache_service

    def execute_prepare_job(self, job_id: str, payload: PrepareJobRequest, event_bus: IEventBus) -> None:
        """
        Orchestrates the execution of a prepare job (OSM/GeoJSON).
        Updates job status via update_job and event_bus.
        """
        try:
            update_job(job_id, event_bus, status="processing", progress=0.05, message="Iniciando...")

            from backend.core.lifecycle import SHUTDOWN_EVENT

            def check_cancel():
                if SHUTDOWN_EVENT.is_set():
                    raise RuntimeError("SHUTDOWN")
                check_cancellation(job_id)

            check_cancel()

            result = None

            if payload.kind == "osm":
                if payload.latitude is None or payload.longitude is None or payload.radius is None:
                    raise ValueError("latitude/longitude/radius são obrigatórios para kind=osm")
                
                update_job(job_id, event_bus, progress=0.15, message="Baixando dados do OSM...")
                
                # Instantiate dependencies within the execution scope (or inject factory)
                elev_svc = ElevationService(cache=self.cache_service)
                
                result = prepare_osm_compute(
                    payload.latitude, 
                    payload.longitude, 
                    payload.radius, 
                    cache_service=self.cache_service,
                    elevation_service=elev_svc,
                    check_cancel=check_cancel
                )
                
                check_cancel()
                update_job(job_id, event_bus, progress=0.95, message="Finalizando...")

            elif payload.kind == "geojson":
                if payload.geojson is None:
                    raise ValueError("geojson é obrigatório para kind=geojson")
                    
                update_job(job_id, event_bus, progress=0.2, message="Processando GeoJSON...")
                
                result = prepare_geojson_compute(payload.geojson, check_cancel)
                
                check_cancel()
                update_job(job_id, event_bus, progress=0.95, message="Finalizando...")

            else:
                raise ValueError("kind inválido. Use 'osm' ou 'geojson'.")

            safe_result = PrepareResponse(**sanitize_jsonable(result))
            update_job(job_id, event_bus, status="completed", progress=1.0, message="Concluído.", result=safe_result.model_dump())
            
        except RuntimeError as e:
            if str(e) == "CANCELLED":
                update_job(job_id, event_bus, status="failed", progress=1.0, message="Cancelado pelo usuário.", error="CANCELLED")
            elif str(e) == "SHUTDOWN":
                update_job(job_id, event_bus, status="failed", progress=1.0, message="Servidor desligando.", error="SHUTDOWN")
            else:
                update_job(job_id, event_bus, status="failed", progress=1.0, message="Falhou.", error=str(e))
        except Exception as e:
            update_job(job_id, event_bus, status="failed", progress=1.0, message="Falhou.", error=str(e))
