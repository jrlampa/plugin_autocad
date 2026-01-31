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
        "footway": 2.0,
        "cycleway": 3.0,
        "service": 4.0,
    }
    
    return width_map.get(highway, 6.0)  # Default 6.0m
