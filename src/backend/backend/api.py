"""
backend/api.py
Ponto de entrada da API FastAPI do sisRUA.
Responsabilidade: criação do app, middleware e registro de routers.
A lógica de negócio fica em backend/routes/*.
"""
from __future__ import annotations

import os
import sys
import time
import threading
import uuid
from pathlib import Path
from typing import Dict, Any

# Configurar Matplotlib antes de qualquer importação para evitar memory leaks em headless
try:
    import matplotlib
    matplotlib.use('Agg')
except ImportError:
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

import structlog
from backend.core.logger import configure_logging, get_logger, set_trace_id

configure_logging()
logger = get_logger(__name__)

# --- Garantir token de autenticação (IPC) ---
# Se não definido no ambiente, gera um aleatório e persiste no env do processo.
AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN")
if not AUTH_TOKEN:
    AUTH_TOKEN = uuid.uuid4().hex
    os.environ["SISRUA_AUTH_TOKEN"] = AUTH_TOKEN

# --- Inicialização do Sentry (apenas se DSN configurado) ---
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
        release="sisrua-backend@1.1.0",
        send_default_pii=False,
    )

# --- App FastAPI ---
app = FastAPI(
    title="sisRUA: The Urban Data Engine",
    version="1.1.0",
    description="""
**sisRUA** é um motor profissional de geometria urbana e inteligência GIS.

Serviços principais:
- **Processamento OSM** autônomo com projeção de alta precisão
- **Transformação GeoJSON → BIM-LITE** para AutoCAD/BricsCAD
- **Perfil de Elevação Topográfica** (SRTM/Lidar, offline-first)
- **Renderização CAD desacoplada** com suporte a 2.5D

API projetada para fluxos de trabalho de design urbano enterprise,
com portabilidade total de dados e conformidade ISO 27001.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "sisRUA Enterprise Support", "url": "https://sisrua.com/support"},
    openapi_tags=[
        {"name": "Urban Data", "description": "Serviços de geometria e preparação de dados"},
        {"name": "AI", "description": "Assistente inteligente"},
        {"name": "Infrastructure", "description": "Saúde, jobs e auditoria"},
    ],
)

# --- Middleware: Trace ID e audit log ---
@app.middleware("http")
async def add_trace_header(request: Request, call_next):
    trace_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    set_trace_id(trace_id)
    structlog.contextvars.bind_contextvars(trace_id=trace_id)

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    response.headers["X-Request-ID"] = trace_id
    logger.info(
        "request_processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=process_time,
    )
    return response


# --- Middleware: Validação de Origem (ISO 27001) ---
from backend.core.auth import AUTH_HEADER_NAME, is_valid_session, _get_master_token

ALLOWED_ORIGINS = {
    "http://localhost:8000", "http://127.0.0.1:8000",
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:4173",
}

_PUBLIC_PATHS = {"/api/v1/health", "/health", "/docs", "/openapi.json", "/"}


@app.middleware("http")
async def validate_origin(request: Request, call_next):
    """ISO 27001: Bloqueio de origens externas e requisições suspeitas."""
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    client_host = request.client.host if request.client else "unknown"
    is_local = client_host in ("127.0.0.1", "localhost", "::1", "unknown")

    token = request.headers.get(AUTH_HEADER_NAME)
    master = _get_master_token()
    has_valid_auth = (token == master) or bool(token and is_valid_session(token))

    if is_local or has_valid_auth:
        return await call_next(request)

    # Permite TestClient interno
    if request.base_url.hostname == "testserver":
        return await call_next(request)

    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")

    if not origin and not referer and request.url.path.startswith("/api/v1"):
        logger.warning(
            "security_violation_no_origin",
            path=request.url.path,
            client=client_host,
            has_token=bool(token),
        )
        return Response("Forbidden: Strict Origin Required", status_code=403)

    if origin:
        if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
            return await call_next(request)
        if origin not in ALLOWED_ORIGINS:
            logger.warning("security_violation_invalid_origin", origin=origin, client=client_host)
            return Response("Forbidden: Invalid Origin", status_code=403)

    return await call_next(request)


# --- Middleware: Cabeçalhos de Segurança ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Adiciona cabeçalhos de segurança HTTP a todas as respostas."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://*.tile.openstreetmap.org https://mt1.google.com "
        "https://*.basemaps.cartocdn.com; "
        "connect-src 'self' https://*.ingest.sentry.io; "
        "object-src 'none';"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-SisRua-Token"],
)


# --- Telemetria (recebe do plugin, sem autenticação necessária) ---
@app.post("/api/v1/audit/telemetry", tags=["Audit"])
async def receive_telemetry(payload: Dict[str, Any]):
    """Recebe telemetria silenciosa do plugin para monitoramento e auto-healing."""
    logger.info("telemetry_received", **payload)
    return {"status": "received"}


# --- Startup ---
@app.on_event("startup")
async def startup_event():
    """Inicializa serviços de background (cleanup, housekeeping, IPC)."""

    def run_cleanup():
        from backend.services.jobs import cleanup_expired_jobs
        while True:
            try:
                count = cleanup_expired_jobs(max_age_seconds=3600)
                if count > 0:
                    print(f"[cleanup] {count} jobs expirados removidos.")
            except Exception as e:
                print(f"[cleanup] Erro: {e}")
            time.sleep(600)

    threading.Thread(target=run_cleanup, daemon=True).start()

    def run_housekeeping():
        try:
            from backend.services.housekeeper import housekeeper_service
            targets = []
            for name in ("logs", "cache"):
                d = Path(name).resolve()
                if d.exists():
                    targets.append(d)
            housekeeper_service.run_daily_cleanup(targets)
        except Exception as e:
            print(f"[housekeeper] Erro: {e}")

    threading.Thread(target=run_housekeeping, daemon=True).start()

    if os.environ.get("SISRUA_TESTING") != "true":
        try:
            from backend.core.ipc import IpcServer
            ipc_server = IpcServer(AUTH_TOKEN)
            ipc_server.start()
            print(f"[startup] IPC Server iniciado em {IpcServer.PIPE_NAME}")
        except ImportError:
            print("[startup] Aviso: pywin32 não instalado, IPC desativado.")
        except Exception as e:
            print(f"[startup] IPC Server falhou: {e}")

    print("[startup] sisRUA API pronta.")


# --- Shutdown ---
@app.on_event("shutdown")
async def shutdown_event():
    """Encerramento gracioso: sinaliza jobs ativos e aguarda conclusão."""
    print("[shutdown] Encerrando serviços...")
    from backend.core.lifecycle import SHUTDOWN_EVENT, job_registry
    SHUTDOWN_EVENT.set()
    job_registry.wait_for_completion(timeout=10.0)
    print("[shutdown] Encerrado.")


# --- Registro de Routers (SoC) ---
from backend.routes.health import router as health_router
from backend.routes.projects import router as projects_router
from backend.routes.jobs import router as jobs_router
from backend.routes.tools import router as tools_router
from backend.routes.ai_routes import router as ai_router
from backend.routes.prepare import router as prepare_router
from backend.routes.webhooks import router as webhooks_router
from backend.routes.enterprise import router as enterprise_router
from backend.audit_routes import audit_bp

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(jobs_router)
app.include_router(tools_router)
app.include_router(ai_router)
app.include_router(prepare_router)
app.include_router(webhooks_router)
app.include_router(enterprise_router)
app.include_router(audit_bp, prefix="/api", tags=["Audit"])

# --- Exposição de serviços para compatibilidade com testes existentes ---
# Os testes acessam estes atributos via `backend.api.<service>`.
from backend.routes.deps import (
    ai_service,
    export_service,
)
from backend.services.webhooks import webhook_service


# --- Montagem do Frontend Estático ---
def _maybe_mount_frontend():
    """
    Serve o frontend React em '/' (WebView2 navega para http://localhost:8000).
    As rotas /api/v1/* têm precedência sobre os arquivos estáticos.
    """
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    dist_dir: Path | None = None

    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            candidate = Path(sys._MEIPASS) / "frontend" / "dist"
            if candidate.exists():
                dist_dir = candidate
        if not dist_dir:
            dist_dir = Path(sys.executable).resolve().parent.parent / "frontend" / "dist"
    else:
        current_file = Path(__file__).resolve()
        repo_src = current_file.parent.parent.parent
        dist_dir = repo_src / "frontend" / "dist"

    if dist_dir and not dist_dir.exists():
        dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"

    if dist_dir and dist_dir.exists() and (dist_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
    else:
        @app.get("/", response_class=HTMLResponse)
        async def root():
            return HTMLResponse(
                """
                <html>
                  <head>
                    <title>sisRUA - Build Necessário</title>
                    <style>
                      body{font-family:Segoe UI,Arial,sans-serif;background:#0f172a;
                           color:#f8fafc;padding:40px;text-align:center}
                      .card{border:1px solid #1e293b;padding:24px;border-radius:8px;
                            max-width:600px;margin:0 auto;background:#1e293b}
                      code{background:#334155;padding:2px 4px;border-radius:4px}
                      h2{color:#3b82f6}
                    </style>
                  </head>
                  <body>
                    <div class="card">
                      <h2>Build do Frontend Não Encontrado</h2>
                      <p>O backend está pronto, mas os arquivos estáticos do React não foram detectados.</p>
                      <p>Para o AutoCAD Plugin funcionar corretamente:</p>
                      <p>1. Acesse <code>src/frontend</code><br/>2. Execute <code>npm run build</code></p>
                      <hr style="border:0;border-top:1px solid #334155;margin:20px 0"/>
                      <p style="font-size:0.85em;color:#94a3b8">
                        sisRUA v1.1 — Modo Backend Apenas
                      </p>
                    </div>
                  </body>
                </html>
                """
            )


_maybe_mount_frontend()

# Para execução direta: python -m backend.api
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=True)
