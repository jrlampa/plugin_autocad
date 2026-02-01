from __future__ import annotations

import os
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure Matplotlib backend to 'Agg' BEFORE any other matplotlib imports
# this ensures thread-safety and avoids GUI-related memory leaks in headless environments.
try:
    import matplotlib
    matplotlib.use('Agg')
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

# --- Sentry SDK for Error Monitoring ---
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
        release=f"sisrua-backend@0.6.0",
        send_default_pii=False,  # Do not send personally identifiable information
    )


# --- New Imports from SoC ---
from backend.models import (
    PrepareOsmRequest, PrepareGeoJsonRequest, PrepareJobRequest,
    PrepareResponse, JobStatusResponse, ElevationQueryRequest, 
    ElevationProfileRequest, CadFeature, HealthResponse,
    ElevationPointResponse, ElevationProfileResponse, WebhookRegistrationRequest,
    InternalEvent
)
from backend.services.jobs import (
    job_store, init_job, update_job, check_cancellation, 
    get_job, cancel_job
)
from backend.services.webhooks import webhook_service
from backend.services.osm import prepare_osm_compute
from backend.services.geojson import prepare_geojson_compute
from backend.services.elevation import ElevationService # for tool endpoints
from backend.core.utils import sanitize_jsonable

AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN") or ""
AUTH_HEADER_NAME = "X-SisRua-Token"

def _require_token(x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    """
    Protege endpoints sensíveis contra chamadas externas na máquina do usuário.
    """
    if AUTH_TOKEN:
        if not x_sisrua_token or x_sisrua_token != AUTH_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")

app = FastAPI(
    title="sisRUA API",
    version="0.6.0",
    description="""
**sisRUA** - Generative Urban Design System for AutoCAD.

This API powers the AutoCAD plugin for:
- Fetching and projecting **OpenStreetMap** data
- Processing **GeoJSON** files for CAD import
- Providing **elevation data** from SRTM sources
- Managing **asynchronous jobs** for long-running operations

## Authentication
Protected endpoints require the `X-SisRua-Token` header.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Jobs", "description": "Asynchronous job management"},
        {"name": "Prepare", "description": "Data preparation (OSM/GeoJSON)"},
        {"name": "Tools", "description": "Utility tools (elevation, etc.)"},
        {"name": "Webhooks", "description": "Dynamic webhook registration"},
    ]
)

# --- CORS Middleware ---
# Allows requests from the WebView2 control (localhost origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:4173",  # Vite preview
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-SisRua-Token"],
)

# --- Security Headers Middleware ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Adds security headers to all responses efficiently."""
    response = await call_next(request)
    
    # Prevent XSS attacks
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # Content Security Policy (relaxed for WebView2 compatibility)
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# --- Warm-up logic (Internal performance) ---
@app.on_event("startup")
async def startup_event():
    """Warms up the environment to reduce latency on first user request."""
    # Start background cleanup thread for jobs
    def run_cleanup():
        from backend.services.jobs import cleanup_expired_jobs
        while True:
            try:
                count = cleanup_expired_jobs(max_age_seconds=3600)
                if count > 0:
                    print(f"[cleanup] Removed {count} expired jobs.")
            except Exception as e:
                print(f"[cleanup] Error: {e}")
            time.sleep(600) # Run every 10 minutes

    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()

    # Pre-calculate or pre-import anything that doesn't depend on heavy GIS libs
    # (Heavy GIS libs are deferred to usage time now)
    print("[startup] sisRUA API ready.")



@app.get("/api/v1/auth/check", tags=["Health"], response_model=HealthResponse)
async def auth_check(x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    """Check if the provided authentication token is valid."""
    _require_token(x_sisrua_token)
    return HealthResponse(status="ok")

@app.get("/api/v1/health", tags=["Health"], response_model=HealthResponse)
async def health():
    """Simple health check to verify the API server is up and running."""
    return HealthResponse(status="ok")

from backend.services.cache import cache_service
from backend.core.bus import InMemoryEventBus

# --- Composition Root ---
event_bus = InMemoryEventBus(cache=cache_service)

# Wiring: WebhookService listens to events
def webhook_adapter(payload: Dict[str, Any]):
    # Since payload isn't carrying the 'type' directly in a clean way for broadcast in this naive implementation,
    # we might need to assume the event that triggered this IS the type, or pass it via closure.
    # Ideally, we subscribe specific events to specific broadcasts.
    pass

# Direct subscriptions for known job events
event_bus.subscribe("job_started", lambda p: webhook_service.broadcast("job_started", p))
event_bus.subscribe("job_completed", lambda p: webhook_service.broadcast("job_completed", p))
event_bus.subscribe("job_failed", lambda p: webhook_service.broadcast("job_failed", p))
event_bus.subscribe("project_saved", lambda p: webhook_service.broadcast("project_saved", p))

def _run_prepare_job_sync(job_id: str, payload: PrepareJobRequest) -> None:
    try:
        # Dependency Injection: Pass event_bus
        update_job(job_id, event_bus, status="processing", progress=0.05, message="Iniciando...")

        def check_cancel():
            check_cancellation(job_id)

        check_cancel()

        if payload.kind == "osm":
            if payload.latitude is None or payload.longitude is None or payload.radius is None:
                raise ValueError("latitude/longitude/radius são obrigatórios para kind=osm")
            update_job(job_id, event_bus, progress=0.15, message="Baixando dados do OSM...")
            
            # Instantiate services with dependencies
            elev_svc = ElevationService(cache=cache_service)
            
            result = prepare_osm_compute(
                payload.latitude, 
                payload.longitude, 
                payload.radius, 
                cache_service=cache_service,
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
        else:
            update_job(job_id, event_bus, status="failed", progress=1.0, message="Falhou.", error=str(e))
    except Exception as e:
        update_job(job_id, event_bus, status="failed", progress=1.0, message="Falhou.", error=str(e))


@app.post("/api/v1/jobs/prepare", tags=["Jobs"], response_model=JobStatusResponse)
async def create_prepare_job(
    payload: PrepareJobRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Start an asynchronous data preparation job (OSM or GeoJSON). returns the initial job status."""
    _require_token(x_sisrua_token)
    job_id = init_job(payload.kind)
    t = threading.Thread(target=_run_prepare_job_sync, args=(job_id, payload), daemon=True)
    t.start()
    return get_job(job_id) # Using getter from service which is locked

@app.get("/api/v1/jobs/{job_id}", tags=["Jobs"], response_model=JobStatusResponse)
async def get_job_endpoint(
    job_id: str,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Retrieve the current status, progress, and result (if completed) of a job."""
    _require_token(x_sisrua_token)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.delete("/api/v1/jobs/{job_id}", tags=["Jobs"], response_model=HealthResponse)
async def cancel_job_endpoint(
    job_id: str,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Request cancellation of a running job."""
    _require_token(x_sisrua_token)
    
    # Use service method
    cancelled = cancel_job(job_id)
    if not cancelled:
        # Check if it was because it wasn't found or because it was already done
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        # if found but return false, it means it was already done, which counts as success/ignored?
        # api spec says if already finished do nothing and return ok.
        
    return HealthResponse(status="ok")

@app.post("/api/v1/tools/elevation/query", tags=["Tools"], response_model=ElevationPointResponse)
async def query_elevation(
    req: ElevationQueryRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Query numeric elevation (Z) at a single lat/lon point."""
    _require_token(x_sisrua_token)
    try:
        from backend.services.elevation import ElevationService
        svc = ElevationService(cache=cache_service)
        z = svc.get_elevation_at_point(req.latitude, req.longitude)
        return ElevationPointResponse(latitude=req.latitude, longitude=req.longitude, elevation=z)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/tools/elevation/profile", tags=["Tools"], response_model=ElevationProfileResponse)
async def query_profile(
    req: ElevationProfileRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Retrieve an elevation profile (list of Z values) along a given path."""
    _require_token(x_sisrua_token)
    try:
        from backend.services.elevation import ElevationService
        svc = ElevationService(cache=cache_service)
        # Convert list of lists to list of tuples for the service
        coords = [(p[0], p[1]) for p in req.path]
        elevations = svc.get_elevation_profile(coords)
        return ElevationProfileResponse(elevations=elevations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/prepare/osm", tags=["Prepare"], response_model=PrepareResponse)
async def prepare_osm(
    req: PrepareOsmRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """
    Synchronous OSM data preparation. 
    Downloads OSM data in lat/lon (EPSG:4326), projects to SIRGAS 2000 UTM, 
    and returns a list of CAD-ready features.
    """
    _require_token(x_sisrua_token)
    from backend.services.elevation import ElevationService
    elev_svc = ElevationService(cache=cache_service)
    return prepare_osm_compute(
        req.latitude, 
        req.longitude, 
        req.radius, 
        cache_service=cache_service,
        elevation_service=elev_svc
    )

@app.post("/api/v1/prepare/geojson", tags=["Prepare"], response_model=PrepareResponse)
async def prepare_geojson(
    req: PrepareGeoJsonRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """
    Synchronous GeoJSON data preparation.
    Accepts GeoJSON (EPSG:4326), projects to SIRGAS 2000 UTM, 
    and returns a list of CAD-ready features.
    """
    _require_token(x_sisrua_token)
    return prepare_geojson_compute(req.geojson)

@app.post("/api/v1/webhooks/register", tags=["Webhooks"], response_model=HealthResponse)
async def register_webhook(
    req: WebhookRegistrationRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Register a new URL to receive system events via webhook."""
    _require_token(x_sisrua_token)
    webhook_service.register_url(req.url)
    return HealthResponse(status="ok")

@app.post("/api/v1/events/emit", tags=["Webhooks"], response_model=HealthResponse)
async def emit_event(
    req: InternalEvent,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """
    Internal endpoint for the AutoCAD plugin to emit events for webhook broadcasting.
    e.g. project_saved, project_loaded.
    """
    _require_token(x_sisrua_token)
    webhook_service.broadcast(req.event_type, req.payload)
    return HealthResponse(status="ok")


def _maybe_mount_frontend():
    """
    Serve o frontend em '/' (WebView2 navega para http://localhost:8000).
    Mantém as rotas de API em /api/v1/**.
    """
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    # Quando empacotado (ex.: PyInstaller), __file__ pode apontar para uma pasta temporária (MEIPASS).
    # Preferimos resolver o caminho do bundle via executável.
    if getattr(sys, "frozen", False):
        contents_dir = Path(sys.executable).resolve().parent.parent
    else:
        contents_dir = Path(__file__).resolve().parent.parent
    dist_dir = contents_dir / "frontend" / "dist"

    if dist_dir.exists() and (dist_dir / "index.html").exists():
        # Importante: montar após as rotas de API, para não interceptar /api/v1/*
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
    else:
        @app.get("/", response_class=HTMLResponse)
        async def root():
            return HTMLResponse(
                '''
                <html>
                  <head><title>sisRUA</title></head>
                  <body style="font-family: Arial; padding: 24px; max-width: 980px; margin: 0 auto;">
                    <h2>sisRUA (modo mínimo)</h2>
                    <p>
                      O backend está rodando, mas não há build do frontend em <code>Contents/frontend/dist</code>.
                      Esta tela mínima permite testar o MVP dentro do AutoCAD enquanto você não gera o build do React.
                    </p>

                    <h3>Gerar ruas via OSM</h3>
                    <div style="display:flex; gap:12px; flex-wrap: wrap; align-items: end;">
                      <div>
                        <label>Latitude</label><br/>
                        <input id="lat" value="-21.7634" style="width:180px; padding:8px;"/>
                      </div>
                      <div>
                        <label>Longitude</label><br/>
                        <input id="lon" value="-41.3235" style="width:180px; padding:8px;"/>
                      </div>
                      <div>
                        <label>Raio (m)</label><br/>
                        <input id="radius" value="500" style="width:140px; padding:8px;"/>
                      </div>
                      <button id="btnOsm" style="padding:10px 14px; font-weight:700;">GERAR OSM → CAD</button>
                    </div>

                    <h3 style="margin-top:24px;">Importar GeoJSON</h3>
                    <p>Selecione um arquivo GeoJSON, ou arraste-o na paleta (o C# envia via FILE_DROPPED).</p>
                    <div style="display:flex; gap:12px; flex-wrap: wrap; align-items: center;">
                      <input id="file" type="file" accept=".json,.geojson" />
                      <button id="btnGeo" style="padding:10px 14px; font-weight:700;">IMPORTAR GEOJSON → CAD</button>
                    </div>
                    <pre id="status" style="margin-top:18px; padding:12px; background:#f4f4f4; border:1px solid #ddd; white-space: pre-wrap;"></pre>

                    <hr style="margin:24px 0;"/>
                    
                    <script>
                      const TOKEN = ""; // Se precisar, injete aqui via backend
                      
                      async function callApi(url, method, body) {
                         const headers = { "Content-Type": "application/json" };
                         if (TOKEN) headers["X-SisRua-Token"] = TOKEN;
                         const res = await fetch(url, { method, headers, body: JSON.stringify(body) });
                         return await res.json();
                      }

                      document.getElementById("btnOsm").onclick = async () => {
                        const lat = parseFloat(document.getElementById("lat").value);
                        const lon = parseFloat(document.getElementById("lon").value);
                        const radius = parseFloat(document.getElementById("radius").value);
                        document.getElementById("status").textContent = "Enviando job...";
                        try {
                           const job = await callApi("/api/v1/jobs/prepare", "POST", { kind: "osm", latitude: lat, longitude: lon, radius });
                           pollJob(job.job_id);
                        } catch(e) { document.getElementById("status").textContent = "Erro: " + e; }
                      };

                      async function pollJob(jobId) {
                         const statusEl = document.getElementById("status");
                         statusEl.textContent = `Job ${jobId}: aguardando...`;
                         while(true) {
                            await new Promise(r => setTimeout(r, 1000));
                            const info = await callApi(`/api/v1/jobs/${jobId}`, "GET");
                            statusEl.textContent = `Job ${jobId}: ${info.status} (${(info.progress*100).toFixed(0)}%) - ${info.message}`;
                            if (info.status === "completed" || info.status === "failed") break;
                         }
                      }
                    </script>
                  </body>
                </html>
                '''
            )

_maybe_mount_frontend()

# Para rodar com: python -m api
if __name__ == "__main__":
    import uvicorn
    # Em dev, recarrega e roda na 8000
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=True)
