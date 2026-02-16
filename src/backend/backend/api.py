from __future__ import annotations

import os
import sys
import signal
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure Matplotlib backend to 'Agg' BEFORE any other matplotlib imports
try:
    import matplotlib
    matplotlib.use('Agg')
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Header, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

# --- Sentry SDK for Error Monitoring ---
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

# --- Metrics / Logging v2 ---
import uuid
import structlog
from backend.core.logger import configure_logging, get_logger, set_trace_id

configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="sisRUA: The Urban Data Engine",
    version="1.1.0",
    description="""
**sisRUA** is a professional-grade Urban Geometry & Intelligence Engine.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "sisRUA Enterprise Support",
        "url": "https://sisrua.com/support",
    },
    openapi_tags=[
        {"name": "Urban Data", "description": "Core geometry and data preparation services"},
        {"name": "Intelligence", "description": "AI and predictive design services"},
        {"name": "Infrastructure", "description": "Global health, jobs, and audit services"},
    ]
)

# Middleware for Audit Logging (Trace ID)
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    trace_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    set_trace_id(trace_id)
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = trace_id
    logger.info("request_processed", 
                method=request.method, 
                path=request.url.path, 
                status_code=response.status_code, 
                duration=process_time)
    return response

SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
        release=f"sisrua-backend@0.7.0",
        send_default_pii=False,
    )

# --- Core Dependencies ---
from fastapi import Depends
from backend.core.config import AUTH_TOKEN, AUTH_HEADER_NAME
from backend.core.security import is_valid_session, require_token
from backend.core.container import setup_event_bus

# --- Strict Origin Middleware ---
# Permite file:// e qualquer porta local para WebView2
# Security Note: In production, restrict this to specific domains
# For plugin use (WebView2), we allow localhost and file:// protocol
ALLOWED_ORIGINS = ["*"]  # Development/Plugin mode: permissive for WebView2
# Production example: ALLOWED_ORIGINS = ["https://sisrua.example.com", "https://app.sisrua.com"]

@app.middleware("http")
async def validate_origin(request: Request, call_next):
    """ISO 27001: Strict Origin Validation."""
    try:
        if request.url.path in ["/api/v1/health", "/health", "/docs", "/openapi.json", "/"]:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        is_local = client_host in ("127.0.0.1", "localhost", "::1", "unknown")
        token = request.headers.get(AUTH_HEADER_NAME)
        has_valid_auth = (token == AUTH_TOKEN) or (token and is_valid_session(token))

        if is_local or has_valid_auth or request.base_url.hostname == "testserver":
            return await call_next(request)

        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")
        
        if not origin and not referer and request.url.path.startswith("/api/v1"):
            logger.warning("security_violation_no_origin", path=request.url.path, client=client_host)
            return Response("Forbidden: Strict Origin Required", status_code=403)
                
        if origin:
            if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
                 return await call_next(request)
            if origin not in ALLOWED_ORIGINS:
                logger.warning("security_violation_invalid_origin", origin=origin, client=client_host)
                return Response("Forbidden: Invalid Origin", status_code=403)
            
        return await call_next(request)
    except Exception as e:
        logger.error("middleware_origin_validation_failed", error=str(e), path=request.url.path)
        # Fallback to next to avoid infinite loading on health check if something crashes
        return await call_next(request)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PUT"],
    allow_headers=["*"],
    expose_headers=["X-SisRua-Token", "X-Request-ID"],
)

# --- Security Headers Middleware ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://*.tile.openstreetmap.org https://mt1.google.com https://*.basemaps.cartocdn.com; "
        "connect-src 'self' https://*.ingest.sentry.io; "
        "object-src 'none';"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# --- App Lifecycle ---
@app.on_event("startup")
async def startup_event():
    setup_event_bus()
    
    def run_cleanup():
        from backend.services.jobs import cleanup_expired_jobs
        while True:
            try:
                cleanup_expired_jobs(max_age_seconds=3600)
            except Exception as e:
                logger.error("job_cleanup_failed", error=str(e))
            time.sleep(600)

    threading.Thread(target=run_cleanup, daemon=True).start()

    def run_housekeeping():
        from backend.services.housekeeper import housekeeper_service
        targets = [Path("logs").resolve(), Path("cache").resolve()]
        try:
            housekeeper_service.run_daily_cleanup([t for t in targets if t.exists()])
        except Exception as e:
            logger.error("housekeeper_failed", error=str(e))

    threading.Thread(target=run_housekeeping, daemon=True).start()

    if os.environ.get("SISRUA_TESTING") != "true":
        try:
            from backend.core.ipc import IpcServer
            IpcServer(AUTH_TOKEN).start()
        except:
            pass

    logger.info("api_started")

@app.on_event("shutdown")
async def shutdown_event():
    from backend.core.lifecycle import SHUTDOWN_EVENT, job_registry
    SHUTDOWN_EVENT.set()
    job_registry.wait_for_completion(timeout=10.0)

# --- Router Registration ---
from backend.routers import (
    health, auth, jobs, gis, projects, ai, webhooks, audit
)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(gis.router)
app.include_router(projects.router)
app.include_router(ai.router)
app.include_router(webhooks.router)

app.include_router(audit.router, prefix="/api")

@app.post("/api/v1/management/shutdown", tags=["Infrastructure"])
async def shutdown_server(_ = Depends(require_token)):
    def self_terminate():
        time.sleep(1.0)
        os.kill(os.getpid(), 2) # SIGINT

    threading.Thread(target=self_terminate, daemon=True).start()
    return {"status": "shutting_down"}

# --- Static Frontend Serving ---
def _maybe_mount_frontend():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse
    
    # Path resolution logic: search in sibling and parent directories
    candidates = [
        Path(__file__).parent.parent / "frontend" / "dist", # sibling 'frontend' in repo
        Path(__file__).parent.parent.parent / "frontend" / "dist", # repo structure parent/src/frontend
        Path(sys.executable).parent / "frontend" / "dist", # relative to exe in bundle
    ]
    
    # Check MEIPASS for pyinstaller
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "frontend" / "dist")

    dist_dir = None
    for cand in candidates:
        if cand.exists() and (cand / "index.html").exists():
            dist_dir = cand
            break

    if dist_dir:
        logger.info("mounting_frontend", path=str(dist_dir))
        app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")
        @app.get("/", response_class=HTMLResponse)
        async def root():
            return (dist_dir / "index.html").read_text()
    else:
        logger.warning("frontend_dist_not_found", searched_paths=[str(p) for p in candidates])

_maybe_mount_frontend()
