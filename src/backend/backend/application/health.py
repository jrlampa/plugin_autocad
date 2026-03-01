
import os
import time
from typing import Dict
from backend.domain.dto import ComponentHealth, DeepHealthResponse
from backend.application.cache import cache_service

# Exposto para compatibilidade com testes que patcham
# `backend.application.health.get_db_connection`.
from backend.shared.database import get_db_connection  # noqa: F401,E402

class HealthService:
    def check_health(self) -> DeepHealthResponse:
        start_time = time.time()
        components: Dict[str, ComponentHealth] = {}
        
        # 1. Database Check
        db_start = time.time()
        try:
            from backend.services import health as _health_compat

            db_get = get_db_connection
            # Se não está mockado/patchado no módulo local, preferir o compat
            # (muitos testes patcham backend.services.health.get_db_connection).
            if getattr(db_get, "__module__", "") == "backend.shared.database":
                db_get = _health_compat.get_db_connection

            with db_get() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    status = "up"
                    details = None
                else:
                    status = "down"
                    details = "SELECT 1 returned unexpected result"
        except Exception as e:
            status = "down"
            details = str(e)
        
        components["database"] = ComponentHealth(
            status=status, 
            details=details, 
            latency_ms=(time.time() - db_start) * 1000
        )
        
        # 2. Cache Check (Filesystem only)
        cache_start = time.time()
        try:
            from backend.services import health as _health_compat

            # Alguns testes patcham `backend.application.health.cache_service`.
            # Outros patcham `backend.services.health.cache_service`.
            _cache = cache_service
            if getattr(_cache, "__module__", "") == "backend.application.cache":
                _cache = _health_compat.cache_service

            test_key = "health_check_probe"
            test_val = {"ts": time.time()}
            _cache.set(test_key, test_val, ttl=10)
            retrieved = _cache.get(test_key)
            if retrieved and retrieved.get("ts") == test_val["ts"]:
                c_status = "up"
                c_details = "File-based cache"
            else:
                c_status = "degraded"
                c_details = "File write/read mismatch"
        except Exception as e:
            c_status = "down"
            c_details = str(e)
            
        components["cache"] = ComponentHealth(
            status=c_status,
            details=c_details,
            latency_ms=(time.time() - cache_start) * 1000
        )
        
        # 3. External Configuration Check (Static)
        ext_start = time.time()
        groq_set = bool(os.environ.get("GROQ_API_KEY"))
        opentopo_set = bool(os.environ.get("OPENTOPOGRAPHY_API_KEY"))
        
        components["external_apis"] = ComponentHealth(
            status="up" if (groq_set or opentopo_set) else "degraded",
            details=f"Groq: {'Set' if groq_set else 'Missing'}, OpenTopo: {'Set' if opentopo_set else 'OfflineMode'}",
            latency_ms=(time.time() - ext_start) * 1000
        )
        
        # 4. GIS Core Dependencies (C-Libraries)
        gis_start = time.time()
        gdal_status, proj_status = "down", "down"
        try:
            from osgeo import gdal
            gdal.UseExceptions()
            gdal_status = "up"
        except Exception: gdal_status = "down"
        
        try:
            import pyproj
            pyproj.Proj("EPSG:4326")
            proj_status = "up"
        except Exception: proj_status = "down"
        
        components["gis_core_deps"] = ComponentHealth(
            status="up" if (gdal_status == "up" and proj_status == "up") else "down",
            details=f"GDAL: {gdal_status}, PROJ: {proj_status}",
            latency_ms=(time.time() - gis_start) * 1000
        )
        
        total_latency = (time.time() - start_time) * 1000
        
        # Calculate overall status
        overall = "up"
        if any(c.status == "down" for c in components.values()):
            overall = "down"
        elif any(c.status == "degraded" for c in components.values()):
            overall = "degraded"

        return DeepHealthResponse(
            status=overall,
            components=components,
            system_latency_ms=total_latency
        )

health_service = HealthService()
