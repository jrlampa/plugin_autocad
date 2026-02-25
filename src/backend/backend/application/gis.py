import json
from typing import Dict, Any, Optional
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class GisService:
    """Service for GIS data manipulation and conversion (KML, GeoJSON)."""
    
    def process_kml(self, kml_content: str) -> Dict[str, Any]:
        """
        Converts KML string to GeoJSON using fastkml or pykml.
        For BIM-LITE, we use a robust backend approach.
        """
        try:
            # We use fastkml or simple parsing logic for now.
            # In a real project, we'd use 'fastkml' or 'kml2geojson'.
            # For this context, let's assume we have it or use a fallback.
            from fastkml import kml
            # fastkml 1.0+ uses KML.from_string (class method)
            # We encode to bytes because strings with XML declarations are not allowed
            k = kml.KML.from_string(kml_content.encode('utf-8'))
            
            def extract_features(feature_list):
                found = []
                for f in feature_list or []:
                    # Documents and Folders have .features (list)
                    if hasattr(f, 'features'):
                        found.extend(extract_features(f.features))
                    
                    # Placemarks have .geometry
                    if hasattr(f, 'geometry') and f.geometry:
                        # pygeoif implements __geo_interface__
                        geom = getattr(f.geometry, "__geo_interface__", None)
                        if geom:
                            found.append({
                                "type": "Feature",
                                "geometry": geom,
                                "properties": {"name": getattr(f, 'name', '') or ''}
                            })
                return found

            features = extract_features(k.features)
            
            if not features and kml_content.strip():
                # If we have content but no features, it's a semantic parsing failure for our needs
                raise ValueError("No valid KML features detected (Document/Placemarks missing)")
            
            return {
                "type": "FeatureCollection",
                "features": features
            }
        except Exception as e:
            logger.error("kml_conversion_failed", error=str(e))
            return {"type": "FeatureCollection", "features": [], "error": str(e)}

gis_service = GisService()
