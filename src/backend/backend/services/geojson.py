import json
import math
from typing import List, Tuple, Optional, Any, Callable, Dict
from fastapi import HTTPException
from backend.models import CadFeature, PrepareResponse # Models
from backend.core.utils import norm_optional_str, project_lines_to_xy, sanitize_jsonable
from backend.services.crs import sirgas2000_utm_epsg
from backend.services.elevation import ElevationService

def first_lonlat(obj) -> Tuple[float, float]:
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
            if t == "Point" and coords and len(coords) >= 2:
                return float(coords[0]), float(coords[1])
    if obj.get("type") == "Feature":
        g = obj.get("geometry") or {}
        coords = g.get("coordinates")
        t = g.get("type")
        if t == "LineString" and coords and len(coords) > 0:
            return float(coords[0][0]), float(coords[0][1])
        if t == "MultiLineString" and coords and len(coords) > 0 and len(coords[0]) > 0:
            return float(coords[0][0][0]), float(coords[0][0][1])
        if t == "Point" and coords and len(coords) >= 2:
            return float(coords[0]), float(coords[1])
    # fallback
    return (0.0, 0.0)

def prepare_geojson_compute(geo: Any, check_cancel: Callable[[], None] = None) -> dict:
    if check_cancel: check_cancel()
    from pyproj import Transformer  # type: ignore
    from shapely.geometry import LineString  # type: ignore

    if isinstance(geo, str):
        geo = json.loads(geo)

    lon0, lat0 = first_lonlat(geo)
    if lon0 == 0.0 and lat0 == 0.0:
        raise HTTPException(status_code=400, detail="GeoJSON inválido: não foi possível extrair coordenadas.")

    epsg_out = sirgas2000_utm_epsg(lat0, lon0)
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_out}", always_xy=True)

    features: List[CadFeature] = [] 

    def _emit_feature(layer: Optional[str], name: Optional[str], highway: Optional[str], coords_lonlat):
        if not coords_lonlat or len(coords_lonlat) < 2:
            return
        line = LineString([(float(x), float(y)) for (x, y) in coords_lonlat])
        coords_xy_list = project_lines_to_xy([line], transformer)
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
    
    def process_feature(props, geom):
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
        elif gtype == "Point": 
            point_lonlat = coords
            if point_lonlat and len(point_lonlat) >= 2:
                lon, lat = point_lonlat[0], point_lonlat[1]
                # Project point
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
                            block_name=norm_optional_str(block_name),
                            block_filepath=norm_optional_str(block_filepath),
                            insertion_point_xy=[x_proj, y_proj],
                            rotation=props.get("rotation"),
                            scale=props.get("scale"),
                        )
                    )

    if t == "FeatureCollection":
        for f in geo.get("features") or []:
            props = f.get("properties") or {}
            geom = f.get("geometry") or {}
            process_feature(props, geom)

    elif t == "Feature":
        props = geo.get("properties") or {}
        geom = geo.get("geometry") or {}
        process_feature(props, geom)
        
    else:
        raise HTTPException(status_code=400, detail="GeoJSON não suportado. Use Feature/FeatureCollection com LineString/MultiLineString/Point.")

    # INJECT ELEVATION DATA
    try:
        if check_cancel: check_cancel()
        
        # We need to reverse calculate or if we can access the original lat/lon?
        # For uniformity, let's reverse project from features.
        from pyproj import Transformer
        reverse_transformer = Transformer.from_crs(f"EPSG:{epsg_out}", "EPSG:4326", always_xy=True)
        
        query_points_xy = []
        feature_indices = []
        
        for i, f in enumerate(features):
            if f.feature_type == "Polyline" and f.coords_xy and len(f.coords_xy) > 0:
                query_points_xy.append(f.coords_xy[0])
                feature_indices.append(i)
            elif f.feature_type == "Point" and f.insertion_point_xy:
                query_points_xy.append(f.insertion_point_xy)
                feature_indices.append(i)

        if query_points_xy:
            if check_cancel: check_cancel()
            lonlat_points = list(reverse_transformer.itransform(query_points_xy))
            latlon_query = [(p[1], p[0]) for p in lonlat_points]
            
            # Batch query
            # Instantiate simplified service if not passed? 
            # In osm.py we instantiated a global one. Let's do same here for now.
            elevations = ElevationService().get_elevation_profile(latlon_query)
            
            for idx, elev in zip(feature_indices, elevations):
                if elev is not None:
                     features[idx].elevation = elev

    except Exception as e:
        print(f"Error injecting elevation data for GeoJSON: {e}")
        pass
    
    if check_cancel: check_cancel()

    payload = PrepareResponse(crs_out=f"EPSG:{epsg_out}", features=features)

    # Cache por conteúdo (ajuda em reimportações repetidas)
    try:
        raw = json.dumps(geo, sort_keys=True, ensure_ascii=False)
        from backend.core.utils import cache_key, write_cache
        key = cache_key(["prepare_geojson", raw])
        write_cache(key, payload.model_dump())
        payload.cache_hit = False 
    except Exception:
        pass
    
    return payload.model_dump()
