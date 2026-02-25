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
from contextlib import asynccontextmanager
from starlette.responses import Response

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    HAS_SENTRY = True
except ImportError:
    HAS_SENTRY = False


from backend.shared.config import config
from backend.shared.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

# --- Token de autenticação (IPC) já garantido pelo config.py ---
AUTH_TOKEN = config.sisrua_auth_token

# --- Inicialização do Sentry (apenas se DSN configurado) ---
# --- Inicialização do Sentry (apenas se DSN configurado) ---
if HAS_SENTRY and config.sentry_dsn:
    try:
        sentry_sdk.init(
            dsn=config.sentry_dsn,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            traces_sample_rate=0.1,
            environment=config.environment,
            release="sisrua-backend@0.1.0",
            send_default_pii=False,
        )
    except Exception as e:
        logger.warning("sentry_init_failed", error=str(e))
else:
    logger.info("sentry_not_available", reason="Library not found")

from backend.infrastructure.lifecycle import start_background_tasks
from backend.infrastructure.middleware import add_trace_header, validate_origin, add_security_headers

@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup e shutdown gracioso (FastAPI 0.93+)."""
    # --- Startup ---
    start_background_tasks()

    if os.environ.get("SISRUA_TESTING") != "true":
        try:
            from backend.shared.ipc import IpcServer
            ipc_server = IpcServer(AUTH_TOKEN)
            ipc_server.start()
            print(f"[startup] IPC Server iniciado em {IpcServer.PIPE_NAME}")
        except (ImportError, Exception) as e:
            print(f"[startup] IPC Server indisponível ou falhou: {e}")

    print("[startup] sisRUA API pronta.")

    yield  # Aplicação em execução

    # --- Shutdown ---
    print("[shutdown] Encerrando serviços...")
    try:
        from backend.shared.lifecycle import SHUTDOWN_EVENT, job_registry
        SHUTDOWN_EVENT.set()
        job_registry.wait_for_completion(timeout=5.0)
    except Exception:
        pass
    print("[shutdown] Encerrado.")


# --- App FastAPI ---
app = FastAPI(
    title="sisRUA: The Urban Data Engine",
    version="0.1.0",
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
    lifespan=_lifespan,
)

app.middleware("http")(add_trace_header)
app.middleware("http")(validate_origin)
app.middleware("http")(add_security_headers)


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
    logger.info("telemetry_received", payload=payload)
    return {"status": "received"}


# --- Registro de Routers (SoC) ---
from backend.infrastructure.routes.health import router as health_router
from backend.infrastructure.routes.projects import router as projects_router
from backend.infrastructure.routes.jobs import router as jobs_router
from backend.infrastructure.routes.tools import router as tools_router
from backend.infrastructure.routes.ai_routes import router as ai_router
from backend.infrastructure.routes.prepare import router as prepare_router
from backend.infrastructure.routes.webhooks import router as webhooks_router
from backend.infrastructure.routes.enterprise import router as enterprise_router
from backend.infrastructure.routes.gis import router as gis_router
from backend.infrastructure.audit_routes import audit_bp as audit_router

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(jobs_router)
app.include_router(tools_router)
app.include_router(ai_router)
app.include_router(prepare_router)
app.include_router(webhooks_router)
app.include_router(enterprise_router)
app.include_router(gis_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api", tags=["Audit"])

# --- Exposição de serviços para compatibilidade com testes existentes ---
# Os testes acessam estes atributos via `backend.api.<service>`.
from backend.infrastructure.routes.deps import (
    ai_service,
    export_service,
)
from backend.application.webhooks import webhook_service


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
