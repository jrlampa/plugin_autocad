import math
from typing import List, Optional, Callable
from fastapi import HTTPException
from backend.models import CadFeature, PrepareResponse  # Importing from models
from backend.core.utils import (
    cache_key,
    norm_optional_str,
    to_linestrings,
    estimate_width_m,
    get_color_from_elevation,
    sanitize_jsonable
)
from backend.services.cache import cache_service
from backend.services.crs import sirgas2000_utm_epsg

def prepare_osm_compute(latitude: float, longitude: float, radius: float, check_cancel: Callable[[], None] = None) -> dict:
    if check_cancel: check_cancel()
    
    # Deferred heavy imports
    import osmnx as ox  # type: ignore
    from pyproj import Transformer
    from backend.services.elevation import ElevationService
    elevation_service = ElevationService()

    if check_cancel: check_cancel()

    key = cache_key(["prepare_osm", f"{latitude:.6f}", f"{longitude:.6f}", str(int(radius))])
    cached = cache_service.get(key)
    if cached is not None:
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
        cached = cache_service.get(key)
        if cached is not None:
            cached["cache_hit"] = True
            cached["cache_fallback_reason"] = str(e)
            return cached
        raise HTTPException(status_code=503, detail=f"Falha ao obter dados do OSM (sem cache local disponível). Detalhes: {str(e)}")

    if check_cancel: check_cancel()
    
    features: List[CadFeature] = [] 

    # Process Edges (Polylines)
    for row in edges.itertuples(index=False):
        if len(features) % 100 == 0 and check_cancel:
            check_cancel()

        geom = row.geometry
        highway = getattr(row, "highway", None)
        if isinstance(highway, list) and highway:
            highway = highway[0]
        name = getattr(row, "name", None)
        
        highway = norm_optional_str(highway)
        name = norm_optional_str(name)
        
        width_m = estimate_width_m(None, highway)

        lines = to_linestrings(geom)
        for line in lines:
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

    # Process Nodes (Points / Blocks)
    for row in nodes.itertuples(index=False):
        if len(features) % 100 == 0 and check_cancel:
             check_cancel()

        point_geom = row.geometry
        if point_geom is None or point_geom.geom_type != "Point":
            continue

        highway_tag = getattr(row, "highway", None)
        power_tag = getattr(row, "power", None)
        amenity_tag = getattr(row, "amenity", None)
        name_tag = getattr(row, "name", None)

        block_name = None
        if highway_tag == "street_light":
            block_name = "POSTE"
        elif power_tag == "pole":
            block_name = "POSTE"
        elif amenity_tag == "bench":
            block_name = "BANCO"
        
        if block_name:
            x, y = point_geom.x, point_geom.y
            if math.isfinite(x) and math.isfinite(y):
                features.append(
                    CadFeature(
                        feature_type="Point",
                        layer="SISRUA_OSM_PONTOS",
                        name=norm_optional_str(name_tag),
                        block_name=block_name,
                        insertion_point_xy=[float(x), float(y)],
                        rotation=0.0, 
                        scale=1.0 
                    )
                )

    # INJECT ELEVATION DATA
    try:
        if check_cancel: check_cancel()
        
        reverse_transformer = Transformer.from_crs(f"EPSG:{epsg_out}", "EPSG:4326", always_xy=True)
        forward_transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_out}", always_xy=True)
        
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
            lonlat_points = list(reverse_transformer.itransform(query_points_xy))
            latlon_query = [(p[1], p[0]) for p in lonlat_points]
            
            elevations = elevation_service.get_elevation_profile(latlon_query)
            
            z_values = []
            for idx, elev in zip(feature_indices, elevations):
                if elev is not None:
                     features[idx].elevation = elev
                     z_values.append(elev)
            
            if z_values:
                z_min, z_max = min(z_values), max(z_values)
                for f in features:
                    if f.elevation is not None:
                        f.color = get_color_from_elevation(f.elevation, z_min, z_max)

        # GENERATE CONTOURS
        if check_cancel: check_cancel()
        
        contours = elevation_service.get_contours(latitude - 0.02, longitude - 0.02, latitude + 0.02, longitude + 0.02)
        
        for c in contours:
            geom_latlon = c['geometry']
            elev = c['elevation']
            
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
                        color=get_color_from_elevation(elev, z_min if 'z_min' in locals() else elev, z_max if 'z_max' in locals() else elev)
                    )
                )

    except Exception as ex:
        print(f"Error injecting elevation in OSM compute: {ex}")

    payload = PrepareResponse(crs_out=f"EPSG:{epsg_out}", features=features)
    
    # Cache
    try:
        cache_service.set(key, payload.model_dump())
        payload.cache_hit = False
    except Exception:
        pass
    
    return payload.model_dump()
