from typing import List, Optional, Callable, Any
from fastapi import HTTPException
import math
from backend.domain.dto import CadFeature, PrepareResponse
from backend.shared.interfaces import ICache
from backend.shared.utils import (
    cache_key,
    norm_optional_str,
    to_linestrings,
    estimate_width_m,
    get_color_from_elevation,
    sanitize_jsonable,
    get_layer_name
)
from backend.domain.crs import sirgas2000_utm_epsg
from backend.shared.logger import get_logger
from backend.domain.topology import TopologyHealer
from backend.domain.geometry import apply_local_offset, snap_to_edge, get_bounding_offset
from backend.infrastructure.osm_client import OsmClient


def _fetch_overpass_data(latitude: float, longitude: float, radius: float, check_cancel: Callable = None) -> dict:
    """Wrapper de módulo para OsmClient.fetch_overpass_data — permite patch em testes."""
    return OsmClient.fetch_overpass_data(latitude, longitude, radius, check_cancel)


def _parse_overpass_to_features(data: dict, epsg_out: int) -> tuple:
    """Wrapper de módulo para OsmParser.parse_to_features — permite patch em testes."""
    return OsmParser.parse_to_features(data, epsg_out)
from backend.domain.osm_parser import OsmParser, OsmWayRow, OsmNodeRow

# Aliases com underscore para retrocompatibilidade com testes legados
_OsmWayRow = OsmWayRow
_OsmNodeRow = OsmNodeRow

logger = get_logger(__name__)

MAX_RADIUS_M = 5000.0

def prepare_osm_compute(
    latitude: float, 
    longitude: float, 
    radius: float, 
    cache_service: ICache = None,
    elevation_service: Any = None,
    check_cancel: Callable = None
) -> PrepareResponse:
    # 0. Validate Inputs (Security & DoS Protection)
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates.")
    
    if radius <= 0:
        raise HTTPException(status_code=400, detail="Radius must be positive.")
    
    if radius > MAX_RADIUS_M:
        logger.warning("security_radius_exceeded", requested=radius, allowed=MAX_RADIUS_M)
        raise HTTPException(status_code=400, detail=f"Radius too large. Max allowed: {MAX_RADIUS_M}m")

    # 1. Check Cache
    if check_cancel: check_cancel()
    
    from pyproj import Transformer

    key = cache_key(["prepare_osm", f"{latitude:.6f}", f"{longitude:.6f}", str(int(radius))])
    cached = cache_service.get(key)
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    epsg_out = sirgas2000_utm_epsg(latitude, longitude)
    
    try:
        # 1. Fetch data from Overpass via Modular Client
        raw_data = _fetch_overpass_data(latitude, longitude, radius, check_cancel)
        
        # 2. Parse and Project via Modular Parser
        nodes_list, edges_list = OsmParser.parse_to_features(raw_data, epsg_out)
        
    except Exception as e:
        cached = cache_service.get(key)
        if cached is not None:
            cached["cache_hit"] = True
            cached["cache_fallback_reason"] = str(e)
            return cached
        raise HTTPException(status_code=503, detail=f"Falha ao obter dados do OSM. Detalhes: {str(e)}")

    if check_cancel: check_cancel()
    
    features: List[CadFeature] = [] 

    # Process Edges (Polylines)
    for row in edges_list:
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
                # Capture all original properties for BIM-LITE portability
                props = sanitize_jsonable(row._asdict())
                
                # Smart Layer Mapping (Brazilian Norms)
                layer = get_layer_name(props, default="SISRUA_Vias_Locais")
                
                features.append(
                    CadFeature(
                        feature_type="Polyline",
                        layer=layer,
                        name=name,
                        highway=highway,
                        width_m=width_m,
                        coords_xy=coords_xy,
                        original_geojson_properties=props
                    )
                )

    # Process Nodes (Points / Blocks)
    for row in nodes_list:
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
        # Mapeamento de ativos urbanos OSM para blocos CAD.
        # Dados estruturados (Poste, Hidrante, Bueiro) são persistidos no banco local
        # para enriquecimento BIM-LITE e auditoria de infraestrutura urbana.

        # Mapeamento de Ativos Urbanos para Blocos CAD
        asset_mapping = {
            "street_light": "POSTE_ILUMINACAO",
            "pole": "POSTE_ENERGIA",
            "fire_hydrant": "HIDRANTE",
            "bench": "MOBILIARIO_BANCO",
            "waste_basket": "MOBILIARIO_LIXEIRA",
            "manhole": "INFRA_BUEIRO",
            "tree": "VEGETACAO_ARVORE",
            "bus_stop": "TRANSPORTE_PARADA_ONIBUS",
            "traffic_signals": "SINALIZACAO_SEMAFORO",
            "crossing": "SINALIZACAO_FAIXA"
        }

        # Verifica tags comuns
        search_tags = ["highway", "power", "amenity", "emergency", "man_made", "natural", "public_transport"]
        props = sanitize_jsonable(row._asdict())
        
        for tag in search_tags:
            val = props.get(tag)
            if isinstance(val, list) and val: val = val[0]
            if val in asset_mapping:
                block_name = asset_mapping[val]
                break
        
        if block_name:
            x, y = point_geom.x, point_geom.y
            if math.isfinite(x) and math.isfinite(y):
                # Smart Layer Mapping for Assets
                layer = get_layer_name(props, default="SISRUA_Infraestrutura_Pontos")
                
                features.append(
                    CadFeature(
                        feature_type="Point",
                        layer=layer,
                        name=norm_optional_str(props.get("name")),
                        block_name=block_name,
                        insertion_point_xy=[float(x), float(y)],
                        rotation=0.0, 
                        scale=1.0,
                        original_geojson_properties=props
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
        logger.error("elevation_injection_failed", error=str(ex))

    # HEAL TOPOLOGY (Proprietary IP)
    healer = TopologyHealer()
    features = healer.heal_network(features)
    
    # PRECISION HARDENING: Local Offset Strategy
    # Using the first point as origin to keep coordinates near [0,0]
    origin_x, origin_y = get_bounding_offset(features)
    
    for f in features:
        # Brand Signature (Invisible Metadata)
        f.original_geojson_properties["sys_sisrua_integrity"] = healer.get_integrity_signature(features)
        f.original_geojson_properties["sys_sisrua_origin"] = [origin_x, origin_y]
        
        if f.feature_type == "Polyline" and f.coords_xy:
            # Shift to local origin
            local_coords = apply_local_offset(f.coords_xy, origin_x, origin_y)
            # Deterministic Snap-on-Edge
            f.coords_xy = snap_to_edge(local_coords)
            
        elif f.feature_type == "Point" and f.insertion_point_xy:
            # Shift point to local origin
            f.insertion_point_xy = [f.insertion_point_xy[0] - origin_x, f.insertion_point_xy[1] - origin_y]

    # BIM-LITE: Offload geometric cleaning to backend for SaaS scalability
    from backend.shared.utils import clean_geometry
    features = clean_geometry(features)

    payload = PrepareResponse(crs_out=f"EPSG:{epsg_out}", features=features)
    
    # Cache
    try:
        cache_service.set(key, payload.model_dump())
        payload.cache_hit = False
    except Exception:
        pass
    
    return payload.model_dump()
