from __future__ import annotations

from fastapi import FastAPI, HTTPException, Header
from typing import Dict, Any, List, Optional
import os
import sys
import threading
from pathlib import Path

# --- New Imports from SoC ---
from backend.models import (
    PrepareOsmRequest, PrepareGeoJsonRequest, PrepareJobRequest,
    PrepareResponse, JobStatusResponse, ElevationQueryRequest, 
    ElevationProfileRequest, CadFeature
)
from backend.services.jobs import (
    job_store, cancellation_tokens, init_job, update_job, check_cancellation, 
    get_job, cancel_job
)
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
    version="0.5.0",
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
    ]
)

# Instantiate independent service for tool endpoints (query/profile)
# Note: osm and geojson services use their own instances or imports.
elevation_tool_service = ElevationService()

@app.get("/api/v1/auth/check", tags=["Health"])
async def auth_check(x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    _require_token(x_sisrua_token)
    return {"status": "ok"}

@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {"status": "ok"}

def _run_prepare_job_sync(job_id: str, payload: PrepareJobRequest) -> None:
    try:
        update_job(job_id, status="processing", progress=0.05, message="Iniciando...")

        def check_cancel():
            check_cancellation(job_id)

        check_cancel()

        if payload.kind == "osm":
            if payload.latitude is None or payload.longitude is None or payload.radius is None:
                raise ValueError("latitude/longitude/radius são obrigatórios para kind=osm")
            update_job(job_id, progress=0.15, message="Baixando dados do OSM...")
            
            result = prepare_osm_compute(payload.latitude, payload.longitude, payload.radius, check_cancel)
            
            check_cancel()
            update_job(job_id, progress=0.95, message="Finalizando...")

        elif payload.kind == "geojson":
            if payload.geojson is None:
                raise ValueError("geojson é obrigatório para kind=geojson")
            update_job(job_id, progress=0.2, message="Processando GeoJSON...")
            
            result = prepare_geojson_compute(payload.geojson, check_cancel)
            
            check_cancel()
            update_job(job_id, progress=0.95, message="Finalizando...")

        else:
            raise ValueError("kind inválido. Use 'osm' ou 'geojson'.")

        safe_result = PrepareResponse(**sanitize_jsonable(result))
        update_job(job_id, status="completed", progress=1.0, message="Concluído.", result=safe_result.model_dump())
    except RuntimeError as e:
        if str(e) == "CANCELLED":
            update_job(job_id, status="failed", progress=1.0, message="Cancelado pelo usuário.", error="CANCELLED")
        else:
            update_job(job_id, status="failed", progress=1.0, message="Falhou.", error=str(e))
    except Exception as e:
        update_job(job_id, status="failed", progress=1.0, message="Falhou.", error=str(e))


@app.post("/api/v1/jobs/prepare", tags=["Jobs"])
async def create_prepare_job(
    payload: PrepareJobRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Start an asynchronous data preparation job (OSM or GeoJSON)."""
    _require_token(x_sisrua_token)
    job_id = init_job(payload.kind)
    t = threading.Thread(target=_run_prepare_job_sync, args=(job_id, payload), daemon=True)
    t.start()
    return get_job(job_id) # Using getter from service which is locked

@app.get("/api/v1/jobs/{job_id}", tags=["Jobs"])
async def get_job_endpoint(
    job_id: str,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Get the status and result of a job."""
    _require_token(x_sisrua_token)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.delete("/api/v1/jobs/{job_id}", tags=["Jobs"])
async def cancel_job_endpoint(
    job_id: str,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Cancel a running job."""
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
        
    return {"status": "ok"}

@app.post("/api/v1/tools/elevation/query", tags=["Tools"])
async def query_elevation(
    req: ElevationQueryRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Query elevation at a single point."""
    _require_token(x_sisrua_token)
    try:
        z = elevation_tool_service.get_elevation_at_point(req.latitude, req.longitude)
        return {"latitude": req.latitude, "longitude": req.longitude, "elevation": z}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/tools/elevation/profile", tags=["Tools"])
async def query_profile(
    req: ElevationProfileRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """Get elevation profile along a path."""
    _require_token(x_sisrua_token)
    try:
        # Convert list of lists to list of tuples for the service
        coords = [(p[0], p[1]) for p in req.path]
        elevations = elevation_tool_service.get_elevation_profile(coords)
        return {"elevations": elevations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/prepare/osm", tags=["Prepare"])
async def prepare_osm(
    req: PrepareOsmRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """
    MVP (Fase 1): pega OSM em lat/lon (EPSG:4326), projeta para SIRGAS2000/UTM (zona automática)
    e devolve linhas prontas para o C# desenhar como Polyline.
    """
    _require_token(x_sisrua_token)
    return prepare_osm_compute(req.latitude, req.longitude, req.radius)

@app.post("/api/v1/prepare/geojson", tags=["Prepare"])
async def prepare_geojson(
    req: PrepareGeoJsonRequest,
    x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)
):
    """
    MVP (Fase 1): recebe GeoJSON (EPSG:4326), projeta para SIRGAS2000/UTM (zona automática)
    e devolve linhas prontas para o C# desenhar como Polyline.
    """
    _require_token(x_sisrua_token)
    return prepare_geojson_compute(req.geojson)


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
