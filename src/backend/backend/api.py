from __future__ import annotations

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Dict, Any, List, Tuple, Optional, Literal
import uuid
import os
import sys
import json
import hashlib
import threading
import math
from pathlib import Path

AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN") or ""
AUTH_HEADER_NAME = "X-SisRua-Token"

# Lock para proteger job_store contra race conditions
_job_store_lock = threading.Lock()

# Backend principal (produção): JSON → polylines.

def _require_token(x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    """
    Protege endpoints sensíveis contra chamadas externas na máquina do usuário.
    """
    if AUTH_TOKEN:
        if not x_sisrua_token or x_sisrua_token != AUTH_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")


class PrepareOsmRequest(BaseModel):
    latitude: float
    longitude: float
    radius: float


class PrepareGeoJsonRequest(BaseModel):
    geojson: Any  # pode vir como string JSON ou objeto GeoJSON

app = FastAPI()

# In-memory storage for job statuses and results. In a real application, this would be a database.
job_store: Dict[str, Dict[str, Any]] = {}


class PrepareJobRequest(BaseModel):
    kind: str  # "osm" | "geojson"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[float] = None
    geojson: Any | None = None


class CadFeature(BaseModel):
    feature_type: Literal["Polyline", "Point"] = "Polyline"  # Default to Polyline
    layer: Optional[str] = None
    name: Optional[str] = None
    highway: Optional[str] = None
    width_m: Optional[float] = None

    # For Polyline features
    coords_xy: Optional[List[List[float]]] = None

    # For Point features (blocks)
    insertion_point_xy: Optional[List[float]] = None
    block_name: Optional[str] = None
    block_filepath: Optional[str] = None
    rotation: Optional[float] = None
    scale: Optional[float] = None


class PrepareResponse(BaseModel):
    crs_out: Optional[str] = None
    features: List[CadFeature]
    cache_hit: Optional[bool] = None  # Indica se o resultado veio do cache


class JobStatusResponse(BaseModel):
    job_id: str
    kind: str
    status: str
    progress: float
    message: Optional[str] = None
    result: Optional[PrepareResponse] = None # Change type from Any to PrepareResponse
    error: Optional[str] = None

def _init_job(kind: str) -> str:
    job_id = str(uuid.uuid4())
    with _job_store_lock:
        job_store[job_id] = {
            "job_id": job_id,
            "kind": kind,
            "status": "queued",
            "progress": 0.0,
            "message": "Aguardando...",
            "result": None,
            "error": None,
        }
    return job_id


def _update_job(job_id: str, *, status: str | None = None, progress: float | None = None, message: str | None = None, result: Dict | None = None, error: str | None = None) -> None:
    with _job_store_lock:
        job = job_store.get(job_id)
        if not job:
            return
        if status is not None:
            job["status"] = status
        if progress is not None:
            job["progress"] = float(max(0.0, min(1.0, progress)))
        if message is not None:
            job["message"] = message
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error


def _cache_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    d = base / "sisRUA" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(parts: list[str]) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="ignore"))
        h.update(b"|")
    return h.hexdigest()

def _read_cache(key: str) -> Optional[dict]:
    try:
        path = _cache_dir() / f"{key}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return _sanitize_jsonable(data)
    except Exception:
        return None

def _write_cache(key: str, payload: dict) -> None:
    try:
        path = _cache_dir() / f"{key}.json"
        safe = _sanitize_jsonable(payload)
        path.write_text(json.dumps(safe, ensure_ascii=False), encoding="utf-8")
    except Exception:
        return

# Armazenamento simples em memória (jobs). Em produção, isso pode virar persistância.

@app.get("/api/v1/auth/check")
async def auth_check(x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    _require_token(x_sisrua_token)
    return {"status": "ok"}

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


def _run_prepare_job_sync(job_id: str, payload: PrepareJobRequest) -> None:
    try:
        _update_job(job_id, status="processing", progress=0.05, message="Iniciando...")

        if payload.kind == "osm":
            if payload.latitude is None or payload.longitude is None or payload.radius is None:
                raise ValueError("latitude/longitude/radius são obrigatórios para kind=osm")
            _update_job(job_id, progress=0.15, message="Baixando dados do OSM...")
            result = _prepare_osm_compute(payload.latitude, payload.longitude, payload.radius)
            _update_job(job_id, progress=0.95, message="Finalizando...")
        elif payload.kind == "geojson":
            if payload.geojson is None:
                raise ValueError("geojson é obrigatório para kind=geojson")
            _update_job(job_id, progress=0.2, message="Processando GeoJSON...")
            result = _prepare_geojson_compute(payload.geojson)
            _update_job(job_id, progress=0.95, message="Finalizando...")
        else:
            raise ValueError("kind inválido. Use 'osm' ou 'geojson'.")

        safe_result = PrepareResponse(**_sanitize_jsonable(result)) # Ensure it's a PrepareResponse object
        _update_job(job_id, status="completed", progress=1.0, message="Concluído.", result=safe_result.model_dump()) # Use model_dump
    except Exception as e:
        _update_job(job_id, status="failed", progress=1.0, message="Falhou.", error=str(e))


@app.post("/api/v1/jobs/prepare")
async def create_prepare_job(payload: PrepareJobRequest, x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    _require_token(x_sisrua_token)
    job_id = _init_job(payload.kind)
    t = threading.Thread(target=_run_prepare_job_sync, args=(job_id, payload), daemon=True)
    t.start()
    with _job_store_lock:
        return job_store[job_id]


@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str, x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    _require_token(x_sisrua_token)
    with _job_store_lock:
        job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _utm_zone(longitude: float) -> int:
    """
    UTM zone: 1..60
    """
    zone = int((longitude + 180) // 6) + 1
    return max(1, min(60, zone))


def _sirgas2000_utm_epsg(latitude: float, longitude: float) -> int:
    """
    Para o Brasil (hemisfério sul), SIRGAS 2000 / UTM zona S segue a família EPSG:31960 + zona.
    Ex.: zona 24S → 31984.
    """
    zone = _utm_zone(longitude)
    # Roadmap do projeto assume SIRGAS 2000 / UTM.
    # Fórmula conhecida para zonas Sul: 31960 + zone.
    return 31960 + zone

def _to_linestrings(geom) -> List[Any]:
    # Import local para evitar puxar stack GIS pesada na importação do módulo (melhor para CI e startup).
    from shapely.geometry import LineString, MultiLineString  # type: ignore

    if geom is None:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return list(geom.geoms)
    return []

def _project_lines_to_xy(lines: List[Any], transformer: Any) -> List[List[List[float]]]:
    """
    Retorna lista de coordenadas [[x,y],...] por linha.
    """
    # Import local: evita custo de import no startup/testes que não precisam de OSM.
    from shapely.ops import transform as shapely_transform  # type: ignore

    out = []
    for line in lines:
        projected = shapely_transform(transformer.transform, line)
        coords = []
        for (x, y) in projected.coords:
            fx = float(x)
            fy = float(y)
            # Starlette/JSONResponse rejeita NaN/Inf (gera 500). Sanitizamos aqui.
            if not math.isfinite(fx) or not math.isfinite(fy):
                continue
            coords.append([fx, fy])
        if len(coords) >= 2:
            out.append(coords)
    return out

def _estimate_width_m(row: Any, highway: Optional[str]) -> Optional[float]:
    """
    Estima a largura em metros baseado no tipo de highway.
    Retorna None se não conseguir estimar.
    """
    if not highway:
        return None
    
    # Mapeamento básico de tipos de highway para larguras (em metros)
    width_map = {
        "residential": 5.0,
        "tertiary": 8.0,
        "secondary": 10.0,
        "primary": 12.0,
        "motorway": 20.0,
        "footway": 2.0,
        "cycleway": 3.0,
        "service": 4.0,
    }
    
    return width_map.get(highway, 6.0)  # Default 6.0m

def _norm_optional_str(v: Any) -> Optional[str]:
    """
    Normaliza valores vindos do pandas/osmnx para algo serializável em JSON.
    - Converte NaN/NA em None
    - Converte qualquer outro valor em string (mantém None)
    """
    if v is None:
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
    except Exception:
        pass
    # Muitos "missing values" acabam virando strings como "nan" dependendo do pipeline.
    try:
        s = str(v)
        if s.lower() == "nan":
            return None
        return s
    except Exception:
        return None

def _sanitize_jsonable(obj: Any) -> Any:
    """
    Garante que o payload é serializável como JSON estrito (sem NaN/Inf), evitando 500 em JSONResponse.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, BaseModel): # Handle Pydantic models
        return obj.model_dump(mode='json')
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            # chaves precisam ser string em JSON
            ks = str(k)
            out[ks] = _sanitize_jsonable(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_sanitize_jsonable(v) for v in obj]
    # fallback: tenta string
    try:
        return str(obj)
    except Exception:
        return None

def _prepare_osm_compute(latitude: float, longitude: float, radius: float) -> dict:
    # Import local: OSMnx/GeoPandas podem ser pesados; só precisamos disso ao executar OSM.
    import osmnx as ox  # type: ignore
    from pyproj import Transformer  # type: ignore

    key = _cache_key(["prepare_osm", f"{latitude:.6f}", f"{longitude:.6f}", str(int(radius))])
    cached = _read_cache(key)
    if cached is not None:
        # Retorna o cache com cache_hit marcado
        cached["cache_hit"] = True
        return cached

    epsg_out = _sirgas2000_utm_epsg(latitude, longitude)
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_out}", always_xy=True)

    try:
        graph = ox.graph_from_point((latitude, longitude), dist=radius, network_type="all")
        nodes, edges = ox.graph_to_gdfs(graph) # Get nodes as well
        edges = edges[edges.geometry.notna()]
    except Exception as e:
        # Tenta usar cache como fallback em caso de erro
        cached = _read_cache(key)
        if cached is not None:
            cached["cache_hit"] = True
            cached["cache_fallback_reason"] = str(e)
            return cached
        raise HTTPException(status_code=503, detail=f"Falha ao obter dados do OSM (sem cache local disponível). Detalhes: {e}")

    features: List[CadFeature] = [] # Changed type to CadFeature

    # Process Edges (Polylines) - existing logic
    for _, row in edges.iterrows():
        geom = row.geometry
        highway = row.get("highway")
        if isinstance(highway, list) and highway:
            highway = highway[0]
        name = row.get("name") if row.get("name") is not None else None
        highway = _norm_optional_str(highway)
        name = _norm_optional_str(name)
        width_m = _estimate_width_m(row, highway)

        lines = _to_linestrings(geom)
        for coords_xy in _project_lines_to_xy(lines, transformer):
            features.append(
                CadFeature(
                    feature_type="Polyline",
                    layer="SISRUA_OSM_VIAS",
                    name=name,
                    highway=highway,
                    width_m=width_m,
                    coords_xy=coords_xy,
                )
            )

    # Process Nodes (Points / Blocks) - new logic for FASE 1.5
    point_features_query = {
        "highway": ["street_light", "traffic_signals"],
        "power": ["pole", "tower"],
        "amenity": ["bench", "parking", "bus_stop"]
    }
    
    # Filter nodes based on tags that usually represent point features
    # Convert node geometries (points) to projected coordinates
    for _, node_row in nodes.iterrows():
        point_geom = node_row.geometry
        
        # Ensure it's a point and valid
        if point_geom is None or point_geom.geom_type != "Point":
            continue

        tags = node_row.to_dict() # Get all tags from the node
        
        block_name = None
        # Basic mapping logic from OSM tags to block types
        if tags.get("highway") == "street_light":
            block_name = "POSTE"
        elif tags.get("power") == "pole":
            block_name = "POSTE"
        elif tags.get("amenity") == "bench":
            block_name = "BANCO" # Example, would need BANCO_GENERICO.dxf
        # Add more mappings as needed for FASE 1.5

        if block_name:
            # Project the point coordinates
            x_proj, y_proj = transformer.transform(point_geom.x, point_geom.y)
            if math.isfinite(x_proj) and math.isfinite(y_proj):
                features.append(
                    CadFeature(
                        feature_type="Point",
                        layer="SISRUA_OSM_PONTOS", # Specific layer for OSM points/blocks
                        name=_norm_optional_str(tags.get("name")),
                        block_name=block_name,
                        # block_filepath will be resolved by C# plugin using blocks_mapping.json
                        insertion_point_xy=[x_proj, y_proj],
                        rotation=0.0, # Default rotation
                        scale=1.0 # Default scale
                    )
                )

    epsg_out = _sirgas2000_utm_epsg(latitude, longitude)
    payload = PrepareResponse(crs_out=f"EPSG:{epsg_out}", features=features)
    
    # Cache por conteúdo
    try:
        key = _cache_key(["prepare_osm", f"{latitude:.6f}", f"{longitude:.6f}", str(int(radius))])
        _write_cache(key, payload.model_dump())
        payload.cache_hit = False
    except Exception:
        pass
    
    return payload.model_dump()


@app.post("/api/v1/prepare/osm")
async def prepare_osm(req: PrepareOsmRequest, x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    """
    MVP (Fase 1): pega OSM em lat/lon (EPSG:4326), projeta para SIRGAS2000/UTM (zona automática)
    e devolve linhas prontas para o C# desenhar como Polyline.
    """
    _require_token(x_sisrua_token)
    return _prepare_osm_compute(req.latitude, req.longitude, req.radius)

def _prepare_geojson_compute(geo: Any) -> dict:
    from pyproj import Transformer  # type: ignore
    from shapely.geometry import LineString  # type: ignore

    if isinstance(geo, str):
        geo = json.loads(geo)

    # Encontrar um ponto de referância para detectar zona UTM
    def _first_lonlat(obj) -> Tuple[float, float]:
        if not obj:
            return (0.0, 0.0)
        if obj.get("type") == "FeatureCollection":
            feats = obj.get("features") or []
            for f in feats:
                g = f.get("geometry") or {}
                coords = g.get("coordinates")
                t = g.get("type")
                if t == "LineString" and coords and len(coords) > 0:
                    return float(coords[0][0]), float(coords[0][1])
                if t == "MultiLineString" and coords and len(coords) > 0 and len(coords[0]) > 0:
                    return float(coords[0][0][0]), float(coords[0][0][1])
        if obj.get("type") == "Feature":
            g = obj.get("geometry") or {}
            coords = g.get("coordinates")
            t = g.get("type")
            if t == "LineString" and coords and len(coords) > 0:
                return float(coords[0][0]), float(coords[0][1])
            if t == "MultiLineString" and coords and len(coords) > 0 and len(coords[0]) > 0:
                return float(coords[0][0][0]), float(coords[0][0][1])
        # fallback
        return (0.0, 0.0)

    lon0, lat0 = _first_lonlat(geo)
    if lon0 == 0.0 and lat0 == 0.0:
        raise HTTPException(status_code=400, detail="GeoJSON inválido: não foi possível extrair coordenadas.")

    epsg_out = _sirgas2000_utm_epsg(lat0, lon0)
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_out}", always_xy=True)

    features: List[CadFeature] = [] # Changed type to CadFeature

    def _emit_feature(layer: Optional[str], name: Optional[str], highway: Optional[str], coords_lonlat):
        if not coords_lonlat or len(coords_lonlat) < 2:
            return
        line = LineString([(float(x), float(y)) for (x, y) in coords_lonlat])
        coords_xy_list = _project_lines_to_xy([line], transformer)
        for coords_xy in coords_xy_list:
            features.append(
                CadFeature(
                    feature_type="Polyline", # Explicitly set feature_type
                    layer=layer or "SISRUA_GEOJSON",
                    name=name,
                    highway=highway,
                    coords_xy=coords_xy,
                )
            )

    t = geo.get("type")
    if t == "FeatureCollection":
        for f in geo.get("features") or []:
            props = f.get("properties") or {}
            geom = f.get("geometry") or {}
            gtype = geom.get("type")
            coords = geom.get("coordinates")
            layer = props.get("layer") or props.get("Layer")
            name = props.get("name")
            highway = props.get("highway")

            if gtype == "LineString":
                _emit_feature(layer, name, highway, coords)
            elif gtype == "MultiLineString":
                for part in coords or []:
                    _emit_feature(layer, name, highway, part)
            elif gtype == "Point": # Handle Point features from GeoJSON
                point_lonlat = coords
                if point_lonlat and len(point_lonlat) >= 2:
                    lon, lat = point_lonlat[0], point_lonlat[1]
                    # Project point
                    x_proj, y_proj = transformer.transform(lon, lat)
                    if math.isfinite(x_proj) and math.isfinite(y_proj):
                        block_name = props.get("block_name") or props.get("BlockName")
                        block_filepath = props.get("block_filepath") or props.get("BlockFilePath")
                        features.append(
                            CadFeature(
                                feature_type="Point",
                                layer=layer or "SISRUA_GEOJSON_POINT",
                                name=name,
                                block_name=_norm_optional_str(block_name),
                                block_filepath=_norm_optional_str(block_filepath),
                                insertion_point_xy=[x_proj, y_proj],
                                rotation=props.get("rotation"),
                                scale=props.get("scale"),
                            )
                        )

    elif t == "Feature":
        props = geo.get("properties") or {}
        geom = geo.get("geometry") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        layer = props.get("layer") or props.get("Layer")
        name = props.get("name")
        highway = props.get("highway")

        if gtype == "LineString":
            _emit_feature(layer, name, highway, coords)
        elif gtype == "MultiLineString":
            for part in coords or []:
                _emit_feature(layer, name, highway, part)
        elif gtype == "Point": # Handle Point features from GeoJSON
            point_lonlat = coords
            if point_lonlat and len(point_lonlat) >= 2:
                lon, lat = point_lonlat[0], point_lonlat[1]
                # Project point
                x_proj, y_proj = transformer.transform(lon, lat)
                if math.isfinite(x_proj) and math.isfinite(y_proj):
                    block_name = props.get("block_name") or props.get("BlockName")
                    block_filepath = props.get("block_filepath") or props.get("BlockFilePath")
                    features.append(
                        CadFeature(
                            feature_type="Point",
                            layer=layer or "SISRUA_GEOJSON_POINT",
                            name=name,
                            block_name=_norm_optional_str(block_name),
                            block_filepath=_norm_optional_str(block_filepath),
                            insertion_point_xy=[x_proj, y_proj],
                            rotation=props.get("rotation"),
                            scale=props.get("scale"),
                        )
                    )
    else:
        raise HTTPException(status_code=400, detail="GeoJSON não suportado. Use Feature/FeatureCollection com LineString/MultiLineString/Point.")

    payload = PrepareResponse(crs_out=f"EPSG:{epsg_out}", features=features)

    # Cache por conteúdo (ajuda em reimportações repetidas)
    try:
        raw = json.dumps(geo, sort_keys=True, ensure_ascii=False)
        key = _cache_key(["prepare_geojson", raw])
        _write_cache(key, payload.model_dump())
        payload.cache_hit = False # Add cache_hit attribute
    except Exception:
        pass

    return payload.model_dump()


@app.post("/api/v1/prepare/geojson")
async def prepare_geojson(req: PrepareGeoJsonRequest, x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    """
    MVP (Fase 1): recebe GeoJSON (EPSG:4326), projeta para SIRGAS2000/UTM (zona automática)
    e devolve linhas prontas para o C# desenhar como Polyline.
    """
    _require_token(x_sisrua_token)
    return _prepare_geojson_compute(req.geojson)

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
                    <h3>Para habilitar a UI completa (React)</h3>
                    <ol>
                      <li>Entre em <code>Contents/frontend</code></li>
                      <li>Rode <code>npm install</code> e <code>npm run build</code></li>
                      <li>Garanta que exista <code>Contents/frontend/dist/index.html</code></li>
                    </ol>

                    <script>
                      const statusEl = document.getElementById("status");
                      let geojsonText = null;

                      function log(msg) {
                        statusEl.textContent = (new Date().toLocaleTimeString()) + " - " + msg + "\n" + statusEl.textContent;
                      }

                      function postToCad(message) {
                        if (window.chrome && window.chrome.webview) {
                          window.chrome.webview.postMessage(message);
                          log("Mensagem enviada ao AutoCAD: " + JSON.stringify(message));
                        } else {
                          log("Sem host do AutoCAD (window.chrome.webview). Esta tela é para uso dentro do AutoCAD.");
                        }
                      }

                      document.getElementById("btnOsm").addEventListener("click", () => {
                        const latitude = Number(document.getElementById("lat").value);
                        const longitude = Number(document.getElementById("lon").value);
                        const radius = Number(document.getElementById("radius").value);
                        postToCad({ action: "GENERATE_OSM", data: { latitude, longitude, radius } });
                      });

                      document.getElementById("file").addEventListener("change", async (e) => {
                        const f = e.target.files && e.target.files[0];
                        if (!f) return;
                        geojsonText = await f.text();
                        log("Arquivo carregado: " + f.name);
                      });

                      document.getElementById("btnGeo").addEventListener("click", () => {
                        if (!geojsonText) {
                          log("Nenhum GeoJSON carregado.");
                          return;
                        }
                        postToCad({ action: "IMPORT_GEOJSON", data: geojsonText });
                      });

                      // Recebe mensagens do C# (drag & drop na paleta)
                      if (window.chrome && window.chrome.webview) {
                        window.chrome.webview.addEventListener("message", (event) => {
                          try {
                            if (typeof event.data === "string") {
                              const msg = JSON.parse(event.data);
                              if (msg.action === "FILE_DROPPED" && msg.data && msg.data.content) {
                                geojsonText = msg.data.content;
                                log("FILE_DROPPED recebido do AutoCAD: " + (msg.data.fileName || "(sem nome)"));
                              }
                            }
                          } catch (err) {
                            log("Erro ao processar mensagem do AutoCAD: " + err.message);
                          }
                        });
                      }
                    </script>
                  </body>
                </html>
                '''
            )


_maybe_mount_frontend()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
