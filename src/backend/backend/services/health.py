
import os
import time
from typing import Dict
from backend.models import ComponentHealth, DeepHealthResponse
from backend.core.database import get_db_connection
from backend.services.cache import cache_service

class HealthService:
    def check_health(self) -> DeepHealthResponse:
        start_time = time.time()
        components: Dict[str, ComponentHealth] = {}
        
        # 1. Database Check
        db_start = time.time()
        try:
            with get_db_connection() as conn:
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
            test_key = "health_check_probe"
            test_val = {"ts": time.time()}
            cache_service.set(test_key, test_val, ttl=10)
            retrieved = cache_service.get(test_key)
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
        
        return DeepHealthResponse(
            status=overall,
            components=components,
            system_latency_ms=total_latency
        )

health_service = HealthService()
