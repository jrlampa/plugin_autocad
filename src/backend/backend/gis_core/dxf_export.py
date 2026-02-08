
import json
import logging
from pathlib import Path
from typing import List, Any, Dict, Optional
import ezdxf
from ezdxf.layouts import Modelspace
from shapely.geometry import shape, LineString, Point, Polygon, MultiLineString, MultiPolygon

logger = logging.getLogger(__name__)

# Default path to layers.json (adjust as needed for production)
# In standalone/dev mode, we look relative to the repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
LAYERS_JSON_PATH = REPO_ROOT / "bundle-template" / "sisRUA.bundle" / "Contents" / "Resources" / "layers.json"

class DxfExporter:
    def __init__(self, layers_config_path: Path = LAYERS_JSON_PATH):
        self.doc = ezdxf.new(dxfversion="R2010") # R2010 is widely compatible
        self.msp = self.doc.modelspace()
        self.layers_config = self._load_layers_config(layers_config_path)
        self._setup_layers()

    def _load_layers_config(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            logger.warning(f"layers.json not found at {path}. Using defaults.")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load layers.json: {e}")
            return {}

    def _setup_layers(self):
        """Creates layers in the DXF document based on valid ABNT/DNIT config."""
        highway_layers = self.layers_config.get("highway", {})
        
        for key, data in highway_layers.items():
            layer_name = data.get("layer", "0")
            aci_color = data.get("aci", 7)
            # ezdxf handles detailed layer properties
            if layer_name not in self.doc.layers:
                self.doc.layers.add(name=layer_name, color=aci_color)

    def _get_layer_for_feature(self, properties: Dict[str, Any]) -> str:
        """Determines the correct AutoCAD layer based on OSM tags."""
        highway = properties.get("highway")
        if not highway:
            return "0"
            
        # Check mapping
        mapping = self.layers_config.get("highway", {})
        if highway in mapping:
            return mapping[highway]["layer"]
            
        # Fallback for unmapped highways
        return mapping.get("unclassified", {}).get("layer", "0")

    def add_features(self, features: List[Any]):
        """
        Adds GeoJSON-like features (dicts with 'geometry' and 'properties') 
        or Objects with .geometry and .tags attributes.
        """
        for f in features:
            # Handle different feature object types (dict vs object)
            if isinstance(f, dict):
                geom = shape(f.get("geometry"))
                props = f.get("properties", {})
            else:
                # Assuming simple object structure from internal GIS core
                geom = getattr(f, "geometry", None)
                props = getattr(f, "tags", {})
                
            if geom is None:
                continue

            layer = self._get_layer_for_feature(props)
            self._add_geometry(geom, layer)

    def _add_geometry(self, geom, layer: str):
        if geom.is_empty:
            return

        if isinstance(geom, Point):
            self.msp.add_point(geom.coords[0], dxfattribs={'layer': layer})
            
        elif isinstance(geom, LineString):
            self.msp.add_lwpolyline(geom.coords, dxfattribs={'layer': layer})
            
        elif isinstance(geom, MultiLineString):
            for line in geom.geoms:
                self.msp.add_lwpolyline(line.coords, dxfattribs={'layer': layer})
                
        elif isinstance(geom, Polygon):
            # Draw exterior
            self.msp.add_lwpolyline(geom.exterior.coords, dxfattribs={'layer': layer, 'closed': True})
            # Draw interiors (holes) - treating as separate polylines for now
            for interior in geom.interiors:
                self.msp.add_lwpolyline(interior.coords, dxfattribs={'layer': layer, 'closed': True})
                
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                self._add_geometry(poly, layer)

    def save(self, output_path: Path):
        self.doc.saveas(output_path)
        logger.info(f"DXF saved to {output_path}")

    def get_stream(self):
        """Returns the DXF content as a string/bytes stream."""
        from io import StringIO
        stream = StringIO()
        self.doc.write(stream)
        return stream.getvalue()

