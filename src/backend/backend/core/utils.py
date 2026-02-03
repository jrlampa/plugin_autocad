import os
import hashlib
import json
import math
from pathlib import Path
from typing import Optional, Any, List, Dict
from pydantic import BaseModel

def cache_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    d = base / "sisRUA" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d

def cache_key(parts: list[str]) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="ignore"))
        h.update(b"|")
    return h.hexdigest()

def norm_optional_str(val: Any) -> str | None:
    if val is None:
        return None
    try:
        if isinstance(val, float) and math.isnan(val):
            return None
    except Exception:
        pass
    try:
        s = str(val).strip()
        if s.lower() == "nan":
            return None
        return s if s else None
    except Exception:
        return None

def sanitize_jsonable(obj: Any) -> Any:
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
            ks = str(k)
            out[ks] = sanitize_jsonable(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [sanitize_jsonable(v) for v in obj]
    try:
        return str(obj)
    except Exception:
        return None

def get_color_from_elevation(z: float, z_min: float, z_max: float) -> str:
    if z_max == z_min:
        return "255,255,255" # White
    
    ratio = (z - z_min) / (z_max - z_min)
    if ratio < 0.25: return "5" # Blue
    if ratio < 0.5: return "4" # Cyan
    if ratio < 0.75: return "3" # Green
    if ratio < 0.9: return "2" # Yellow
    return "1" # Red

def to_linestrings(geom) -> List[Any]:
    from shapely.geometry import LineString, MultiLineString  # type: ignore

    if geom is None:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return list(geom.geoms)
    return []

def project_lines_to_xy(lines: List[Any], transformer: Any) -> List[List[List[float]]]:
    from shapely.ops import transform as shapely_transform  # type: ignore

    out = []
    for line in lines:
        projected = shapely_transform(transformer.transform, line)
        coords = []
        for (x, y) in projected.coords:
            fx = float(x)
            fy = float(y)
            if not math.isfinite(fx) or not math.isfinite(fy):
                continue
            coords.append([fx, fy])
        if len(coords) >= 2:
            out.append(coords)
    return out

def estimate_width_m(row: Any, highway: Optional[str]) -> Optional[float]:
    if not highway:
        return None
    
    width_map = {
        "residential": 5.0,
        "tertiary": 8.0,
        "secondary": 10.0,
        "primary": 12.0,
        "motorway": 20.0,
        "trunk": 18.0,
        "footway": 2.0,
        "cycleway": 3.0,
        "service": 4.0,
    }
    
    return width_map.get(highway, 6.0)  # Default 6.0m

def get_layer_config() -> Dict[str, Any]:
    """
    Carrega a configuração de layers (Normas Brasileiras).
    Busca dinamicamente no repo ou no bundle.
    """
    current_file = Path(__file__).resolve()
    repo_root = current_file.parent.parent.parent.parent
    
    # 1. Tenta no bundle-template (Desenvolvimento)
    layers_path = repo_root / "bundle-template" / "sisRUA.bundle" / "Contents" / "Resources" / "layers.json"
    
    if not layers_path.exists():
        # 2. Tenta no layout de produção (Contents/Resources)
        layers_path = current_file.parent.parent / "Resources" / "layers.json"
        
    if layers_path.exists():
        try:
            with open(layers_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    # Fallback Hardcoded (Normas Brasileiras simplificadas)
    return {
        "highway": {
            "motorway": { "layer": "SISRUA_Vias_Expressas", "aci": 1 },
            "trunk": { "layer": "SISRUA_Vias_Arteriais_Trunk", "aci": 2 },
            "primary": { "layer": "SISRUA_Vias_Arteriais", "aci": 3 },
            "secondary": { "layer": "SISRUA_Vias_Coletoras", "aci": 4 },
            "tertiary": { "layer": "SISRUA_Vias_Locais_Principais", "aci": 5 },
            "residential": { "layer": "SISRUA_Vias_Locais", "aci": 7 },
            "service": { "layer": "SISRUA_Vias_Servico", "aci": 8 },
            "pedestrian": { "layer": "SISRUA_Vias_Pedestres", "aci": 140 },
            "footway": { "layer": "SISRUA_Vias_Pedestres", "aci": 140 }
        }
    }

def get_layer_name(tags: Dict[str, Any], default: str = "SISRUA_DEFAULT") -> str:
    """
    Mapeia tags do OSM/GeoJSON para layers seguindo normas brasileiras.
    Diferencial sisRUA: O dado já sai classificado para o engenheiro.
    """
    config = get_layer_config()
    
    # Ordem de prioridade para classificação
    keys_to_check = ["highway", "power", "amenity", "railway", "waterway"]
    
    for key in keys_to_check:
        val = tags.get(key)
        if isinstance(val, list) and val: val = val[0]
        val = norm_optional_str(val)
        
        if val and key in config and val in config[key]:
            return config[key][val]["layer"]
            
    return default

def clean_geometry(features: List[Any], tolerance: float = 0.1) -> List[Any]:
    """
    Realiza limpeza geométrica (deduplicação e simplificação) no backend.
    """
    from shapely.geometry import LineString # type: ignore
    
    seen_hashes = set()
    cleaned = []
    
    for f in features:
        # Deduplicação via Hash (Geometria + Atributos)
        # Usamos uma string estável para o hash
        geom_key = str(f.coords_xy) if f.feature_type == "Polyline" else str(f.insertion_point_xy)
        attr_key = f"{f.layer}|{f.name}|{f.highway}"
        h = hashlib.sha256(f"{geom_key}|{attr_key}".encode("utf-8")).hexdigest()
        
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        
        # Simplificação (apenas para Polylines)
        if f.feature_type == "Polyline" and f.coords_xy and len(f.coords_xy) > 2:
            try:
                ls = LineString(f.coords_xy)
                simplified = ls.simplify(tolerance, preserve_topology=True)
                # Convert back to list of lists
                f.coords_xy = [[float(x), float(y)] for x, y in simplified.coords]
            except Exception:
                pass # Mantém original se falhar
        
        cleaned.append(f)
        
    return cleaned
