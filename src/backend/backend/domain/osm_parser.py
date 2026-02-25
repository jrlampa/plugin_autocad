from typing import List, Tuple, Any, Optional
from pyproj import Transformer
from shapely.geometry import LineString, Point
from backend.shared.logger import get_logger

logger = get_logger(__name__)

def _sanitize_tags(tags: dict) -> dict:
    """
    Cleans OSM tags for CAD/BIM use:
    - Truncates keys/values to 255 chars (XData limit)
    - Strips excessive whitespace
    - Basic HTML tag removal
    """
    import re
    html_regex = re.compile(r'<[^>]*>')
    sanitized = {}
    for k, v in tags.items():
        if not isinstance(k, str) or not v:
            continue

        s_k = html_regex.sub("", k).strip()[:255]
        s_v = str(v)
        s_v = html_regex.sub("", s_v).strip()[:255]

        # Remove control characters
        s_v = "".join(char for char in s_v if ord(char) >= 32)

        if s_k:
            sanitized[s_k] = s_v
    return sanitized


class OsmWayRow:
    """Projected OSM way representation."""

    __slots__ = ("geometry", "highway", "name", "tags")

    def __init__(self, way: dict, projected_geom: Any) -> None:
        tags = _sanitize_tags(way.get("tags", {}))
        self.geometry = projected_geom
        self.highway: Optional[str] = tags.get("highway")
        self.name: Optional[str] = tags.get("name")
        self.tags: dict = tags

    def _asdict(self) -> dict:
        return self.tags


class OsmNodeRow:
    """Projected OSM node representation."""

    __slots__ = ("geometry", "highway", "power", "amenity", "name", "tags")

    def __init__(self, node: dict, proj_x: float, proj_y: float) -> None:
        tags = _sanitize_tags(node.get("tags", {}))
        self.geometry = Point(proj_x, proj_y)
        self.highway: Optional[str] = tags.get("highway")
        self.power: Optional[str] = tags.get("power")
        self.amenity: Optional[str] = tags.get("amenity")
        self.name: Optional[str] = tags.get("name")
        self.tags: dict = tags

    def _asdict(self) -> dict:
        return self.tags


class OsmParser:
    """
    Responsibility: Parsing raw Overpass JSON into projected GIS geometry.
    """
    
    @staticmethod
    def parse_to_features(data: dict, epsg_out: int) -> Tuple[List[OsmNodeRow], List[OsmWayRow]]:
        elements = data.get("elements", [])
        nodes_lookup = {n["id"]: n for n in elements if n["type"] == "node"}
        ways = [w for w in elements if w["type"] == "way"]

        transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_out}", always_xy=True)

        # Optimization: Map all coordinates to a single list for batch transformation
        all_lons = []
        all_lats = []
        
        # Collect from ways
        way_node_indices = []
        for way in ways:
            node_ids = way.get("nodes", [])
            way_node_indices.append(len(all_lons))
            for nid in node_ids:
                n = nodes_lookup.get(nid)
                if n:
                    all_lons.append(n["lon"])
                    all_lats.append(n["lat"])
        way_node_indices.append(len(all_lons)) # end marker

        # Collect from standalone nodes
        standalone_nodes = [n for n in nodes_lookup.values() if n.get("tags")]
        node_start_idx = len(all_lons)
        for n in standalone_nodes:
            all_lons.append(n["lon"])
            all_lats.append(n["lat"])

        # Batch Transform! (This is where the speedup happens)
        if not all_lons:
            return [], []
            
        proj_x, proj_y = transformer.transform(all_lons, all_lats)

        parsed_edges = []
        parsed_nodes = []
        
        # Re-map batch results to Ways
        for i, way in enumerate(ways):
            start = way_node_indices[i]
            end = way_node_indices[i+1]
            if end - start < 2: continue
            
            coords = list(zip(proj_x[start:end], proj_y[start:end]))
            projected_geom = LineString(coords)
            parsed_edges.append(OsmWayRow(way, projected_geom))

        # Re-map batch results to Nodes
        for i, n in enumerate(standalone_nodes):
            idx = node_start_idx + i
            parsed_nodes.append(OsmNodeRow(n, proj_x[idx], proj_y[idx]))
            
        return parsed_nodes, parsed_edges
