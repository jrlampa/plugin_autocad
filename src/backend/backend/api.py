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

# In-memory storage for job statuses and results.
job_store: Dict[str, Dict[str, Any]] = {}
# Track which jobs have been requested to cancel
cancellation_tokens: Dict[str, bool] = {}


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


def _check_cancellation(job_id: str):
    if cancellation_tokens.get(job_id):
        raise  RuntimeError("CANCELLED")



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

def _norm_optional_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None

def _get_color_from_elevation(z: float, z_min: float, z_max: float) -> str:
    """
    Returns an AutoCAD Color Index (ACI) or RGB string based on elevation.
    Simple heatmap: Blue (low) -> Green -> Yellow -> Red (high).
    AutoCAD ACI:
    1 = Red
    2 = Yellow
    3 = Green
    4 = Cyan
    5 = Blue
    6 = Magenta
    """
    if z_max == z_min:
        return "255,255,255" # White
    
    ratio = (z - z_min) / (z_max - z_min)
    
    # Simple mapping to ACI for now (approximate)
    # Low (0.0) -> Blue (5)
    # Mid (0.5) -> Green (3)
    # High (1.0) -> Red (1)
    
    if ratio < 0.25: return "5" # Blue
    if ratio < 0.5: return "4" # Cyan
    if ratio < 0.75: return "3" # Green
    if ratio < 0.9: return "2" # Yellow
    return "1" # Red


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

        def check_cancel():
            _check_cancellation(job_id)

        check_cancel()

        if payload.kind == "osm":
            if payload.latitude is None or payload.longitude is None or payload.radius is None:
                raise ValueError("latitude/longitude/radius são obrigatórios para kind=osm")
            _update_job(job_id, progress=0.15, message="Baixando dados do OSM...")
            
            result = _prepare_osm_compute(payload.latitude, payload.longitude, payload.radius, check_cancel)
            
            check_cancel()
            _update_job(job_id, progress=0.95, message="Finalizando...")

        elif payload.kind == "geojson":
            if payload.geojson is None:
                raise ValueError("geojson é obrigatório para kind=geojson")
            _update_job(job_id, progress=0.2, message="Processando GeoJSON...")
            
            result = _prepare_geojson_compute(payload.geojson, check_cancel)
            
            check_cancel()
            _update_job(job_id, progress=0.95, message="Finalizando...")

        else:
            raise ValueError("kind inválido. Use 'osm' ou 'geojson'.")

        safe_result = PrepareResponse(**_sanitize_jsonable(result))
        _update_job(job_id, status="completed", progress=1.0, message="Concluído.", result=safe_result.model_dump())
    except RuntimeError as e:
        if str(e) == "CANCELLED":
            _update_job(job_id, status="failed", progress=1.0, message="Cancelado pelo usuário.", error="CANCELLED")
        else:
            _update_job(job_id, status="failed", progress=1.0, message="Falhou.", error=str(e))
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

@app.delete("/api/v1/jobs/{job_id}")
async def cancel_job(job_id: str, x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    _require_token(x_sisrua_token)
    with _job_store_lock:
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # If already finished, do nothing
        if job["status"] in ("completed", "failed"):
            return {"status": "ok", "message": "Job already finished"}
            
        cancellation_tokens[job_id] = True
        job["status"] = "failed"
        job["message"] = "Cancelamento solicitado..."
        job["error"] = "CANCELLED"
    return {"status": "ok"}





from backend.services.crs import sirgas2000_utm_epsg
from backend.services.elevation import ElevationService

elevation_service = ElevationService()

class ElevationQueryRequest(BaseModel):
    latitude: float
    longitude: float

class ElevationProfileRequest(BaseModel):
    path: List[List[float]] # [[lat, lon], [lat, lon], ...]

@app.post("/api/v1/tools/elevation/query")
async def query_elevation(req: ElevationQueryRequest, x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    _require_token(x_sisrua_token)
    try:
        z = elevation_service.get_elevation_at_point(req.latitude, req.longitude)
        return {"latitude": req.latitude, "longitude": req.longitude, "elevation": z}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/tools/elevation/profile")
async def query_profile(req: ElevationProfileRequest, x_sisrua_token: str | None = Header(default=None, alias=AUTH_HEADER_NAME)):
    _require_token(x_sisrua_token)
    try:
        # Convert list of lists to list of tuples for the service
        coords = [(p[0], p[1]) for p in req.path]
        elevations = elevation_service.get_elevation_profile(coords)
        return {"elevations": elevations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

def _prepare_osm_compute(latitude: float, longitude: float, radius: float, check_cancel: callable = None) -> dict:
    if check_cancel: check_cancel()
    
    # Import local: OSMnx/GeoPandas podem ser pesados; só precisamos disso ao executar OSM.
    import osmnx as ox  # type: ignore

    if check_cancel: check_cancel()

    key = _cache_key(["prepare_osm", f"{latitude:.6f}", f"{longitude:.6f}", str(int(radius))])
    cached = _read_cache(key)
    if cached is not None:
        # Retorna o cache com cache_hit marcado
        cached["cache_hit"] = True
        return cached

    epsg_out = sirgas2000_utm_epsg(latitude, longitude)
    
    try:
        if check_cancel: check_cancel()
        graph = ox.graph_from_point((latitude, longitude), dist=radius, network_type="all")
        if check_cancel: check_cancel()
        
        # Optimization: Project graph using OSMnx (vectorized) directly to SIRGAS 2000
        graph = ox.project_graph(graph, to_crs=f"EPSG:{epsg_out}")
        nodes, edges = ox.graph_to_gdfs(graph) 
        edges = edges[edges.geometry.notna()]
    except Exception as e:
        # Tenta usar cache como fallback em caso de erro
        cached = _read_cache(key)
        if cached is not None:
            cached["cache_hit"] = True
            cached["cache_fallback_reason"] = str(e)
            return cached
        raise HTTPException(status_code=503, detail=f"Falha ao obter dados do OSM (sem cache local disponível). Detalhes: {str(e)}")

    if check_cancel: check_cancel()
    
    features: List[CadFeature] = [] # Changed type to CadFeature

    # Process Edges (Polylines) - optimized with itertuples
    # We create a simple dictionary of standard columns to avoid AttributeError if they are missing
    
    for row in edges.itertuples(index=False):
        # Periodic cancel check
        if len(features) % 100 == 0 and check_cancel:
            check_cancel()

        geom = row.geometry
        # Handle tags safely
        highway = getattr(row, "highway", None)
        if isinstance(highway, list) and highway:
            highway = highway[0]
        name = getattr(row, "name", None)
        
        highway = _norm_optional_str(highway)
        name = _norm_optional_str(name)
        
        width_m = _estimate_width_m(None, highway)

        lines = _to_linestrings(geom)
        for line in lines:
            # Geometries are already projected in meters!
            coords_xy = []
            for x, y in line.coords:
                if math.isfinite(x) and math.isfinite(y):
                    coords_xy.append([float(x), float(y)])
            
            if len(coords_xy) >= 2:
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
    for row in nodes.itertuples(index=False):
        if len(features) % 100 == 0 and check_cancel:
             check_cancel()

        point_geom = row.geometry
        
        # Ensure it's a point and valid
        if point_geom is None or point_geom.geom_type != "Point":
            continue

        # Extract tags from namedtuple attributes
        # getattr(row, "key", None)
        highway_tag = getattr(row, "highway", None)
        power_tag = getattr(row, "power", None)
        amenity_tag = getattr(row, "amenity", None)
        name_tag = getattr(row, "name", None)

        block_name = None
        # Basic mapping logic from OSM tags to block types
        if highway_tag == "street_light":
            block_name = "POSTE"
        elif power_tag == "pole":
            block_name = "POSTE"
        elif amenity_tag == "bench":
            block_name = "BANCO"
        
        if block_name:
            # Point is already projected in meters
            x, y = point_geom.x, point_geom.y
            if math.isfinite(x) and math.isfinite(y):
                features.append(
                    CadFeature(
                        feature_type="Point",
                        layer="SISRUA_OSM_PONTOS",
                        name=_norm_optional_str(name_tag),
                        block_name=block_name,
                        insertion_point_xy=[float(x), float(y)],
                        rotation=0.0, 
                        scale=1.0 
                    )
                )

    # INJECT ELEVATION DATA (Phase 2)
    try:
        if check_cancel: check_cancel()
        
        # Filter for features that need elevation (Polylines and Points)
        # Note: elevation service needs lat/lon. 
        # But features are currently in UTM/SIRGAS 2000 (projected).
        # We need to reproject minimal points back to lat/lon for SRTM query?
        # OR: query SRTM using bounds before projection?
        # Better: use the transformer to reverse project sample points.
        
        from pyproj import Transformer
        # Back to LatLon for elevation query
        reverse_transformer = Transformer.from_crs(f"EPSG:{epsg_out}", "EPSG:4326", always_xy=True)
        
        # collect sample points
        query_points_xy = []
        feature_indices = []
        
        for i, f in enumerate(features):
            if f.FeatureType == "Polyline" and f.coords_xy and len(f.coords_xy) > 0:
                # Use first point for basic 2.5D elevation
                query_points_xy.append(f.coords_xy[0])
                feature_indices.append(i)
            elif f.FeatureType == "Point" and f.insertion_point_xy:
                query_points_xy.append(f.insertion_point_xy)
                feature_indices.append(i)

        if query_points_xy:
            # Reproject to lat/lon
            lonlat_points = list(reverse_transformer.itransform(query_points_xy))
            # Format as (lat, lon) for elevation service
            latlon_query = [(p[1], p[0]) for p in lonlat_points]
            
            # Batch query
            elevations = elevation_service.get_elevation_profile(latlon_query)
            
            # Assign back
            z_values = []
            for idx, elev in zip(feature_indices, elevations):
                if elev is not None:
                     features[idx].elevation = elev
                     z_values.append(elev)
            
            # Calculate Slope & Color
            if z_values:
                z_min, z_max = min(z_values), max(z_values)
                
                for f in features:
                    if f.elevation is not None:
                        f.color = _get_color_from_elevation(f.elevation, z_min, z_max)
                        
                    if f.FeatureType == "Polyline" and f.coords_xy and len(f.coords_xy) >= 2 and f.elevation is not None:
                        # Simple slope: (Z_end - Z_start) / Length? 
                        # Or just slope of the terrain at that point?
                        # Let's use the single Z for the whole feature (flat 2.5D) for now as defined in Models.
                        # If we want 3D polylines (varying Z), we need Z per vertex.
                        # Current implementation sets one Z for the object. 
                        # So slope is 0 for the object itself unless it's a 3D Polyline.
                        # For Phase 2, let's keep it simple: Color is more important.
                        pass

        # GENERATE CONTOURS
        if check_cancel: check_cancel()
        
        # Determine bounds (lat/lon)
        # s, n, w, e were inputs. We can reuse them.
        contours = elevation_service.get_contours(latitude - 0.02, longitude - 0.02, latitude + 0.02, longitude + 0.02)
        
        # Project contours to UTM
        # Transformer is reusable? We need LatLon -> UTM
        # epsg_out is defined earlier.
        from pyproj import Transformer
        forward_transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_out}", always_xy=True)
        
        for c in contours:
            geom_latlon = c['geometry']
            elev = c['elevation']
            
            # Reproject list of (lat, lon) -> (x, y)
            # Note: geometry is (lat, lon). Transformer needs (lon, lat) usually for x, y
            lonlat_list = [(p[1], p[0]) for p in geom_latlon]
            
            x_out, y_out = [], []
            for lon, lat in lonlat_list:
                xx, yy = forward_transformer.transform(lon, lat)
                x_out.append(xx)
                y_out.append(yy)
            
            coords_utm = [[x, y] for x, y in zip(x_out, y_out)]
            
            if len(coords_utm) >= 2:
                features.append(
                    CadFeature(
                        feature_type="Polyline",
                        layer="SISRUA_CURVAS_NIVEL",
                        name=f"Curva {int(elev)}m",
                        coords_xy=coords_utm,
                        elevation=elev,
                        color=_get_color_from_elevation(elev, z_min if 'z_min' in locals() else elev, z_max if 'z_max' in locals() else elev)
                    )
                )

    except Exception as e:
        print(f"Error injecting elevation data: {e}")
        # Non-critical, continue without elevation
        pass


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

def _prepare_geojson_compute(geo: Any, check_cancel: callable = None) -> dict:
    if check_cancel: check_cancel()
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

    epsg_out = sirgas2000_utm_epsg(lat0, lon0)
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
                    x_proj, y_proj = transformer.transform(lon, lat)
                    if math.isfinite(x_proj) and math.isfinite(y_proj):
                        if len(features) % 50 == 0 and check_cancel: check_cancel()
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
                    )
                    
    # INJECT ELEVATION DATA (Phase 2)
    # Similar logic to OSM but points are already in lat/lon here? 
    # NO: features are in UTM now (projected above).
    # But we have original coords in 'coords' or 'point_lonlat' in the loop.
    # Re-using the reverse projection approach is cleaner than passing data around.
    
    try:
        if check_cancel: check_cancel()
        
        # We need to reverse calculate or if we can access the original lat/lon?
        # For uniformity, let's reverse project from features.
        from pyproj import Transformer
        reverse_transformer = Transformer.from_crs(f"EPSG:{epsg_out}", "EPSG:4326", always_xy=True)
        
        query_points_xy = []
        feature_indices = []
        
        for i, f in enumerate(features):
            if f.FeatureType == "Polyline" and f.coords_xy and len(f.coords_xy) > 0:
                query_points_xy.append(f.coords_xy[0])
                feature_indices.append(i)
            elif f.FeatureType == "Point" and f.insertion_point_xy:
                query_points_xy.append(f.insertion_point_xy)
                feature_indices.append(i)

        if query_points_xy:
            if check_cancel: check_cancel()
            lonlat_points = list(reverse_transformer.itransform(query_points_xy))
            latlon_query = [(p[1], p[0]) for p in lonlat_points]
            
            # Batch query
            elevations = elevation_service.get_elevation_profile(latlon_query)
            
            for idx, elev in zip(feature_indices, elevations):
                if elev is not None:
                     features[idx].elevation = elev

    except Exception as e:
        print(f"Error injecting elevation data for GeoJSON: {e}")
        pass
    
    if check_cancel: check_cancel()

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
                              if (msg.action === "FILE_DROPPED_GEOJSON" && msg.data && msg.data.content) {
                                geojsonText = msg.data.content;
                                log("FILE_DROPPED_GEOJSON recebido do AutoCAD: " + (msg.data.fileName || "(sem nome)"));
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
