import geopandas as gpd
from shapely.geometry import Point, LineString
from typing import Dict, Any, List, Tuple

class SpatialAuditEngine:
    @staticmethod
    def run_spatial_audit(gdf: gpd.GeoDataFrame) -> Tuple[Dict[str, Any], gpd.GeoDataFrame]:
        """
        Performs GIS audit on the GeoDataFrame.
        Returns: (summary_dict, analysis_gdf)
        """
        if gdf.empty:
            return {}, gpd.GeoDataFrame(columns=['geometry'], crs=gdf.crs)

        # Robust column identification
        def get_series(col_name):
            return gdf[col_name] if col_name in gdf.columns else gpd.pd.Series([None] * len(gdf))

        # Filtering Categories
        power_lines = gdf[
            ((get_series('power') == 'line') | (get_series('feature_type') == 'power_line')) & 
            gdf.geometry.type.isin(['LineString', 'MultiLineString'])
        ]
        
        buildings = gdf[
            (get_series('building').notnull()) | (get_series('feature_type') == 'building')
        ]
        
        lamps = gdf[
            (get_series('highway') == 'street_lamp') | (get_series('feature_type') == 'lamp')
        ]
        
        roads = gdf[get_series('highway').notnull()]

        analysis_features = []
        violations_count = 0
        violations_list = []
        
        # 1. Proximity Audit (Buffers)
        # Check buildings within 5m of power lines
        if not power_lines.empty and not buildings.empty:
            # We work in projected CRS (SIRGAS 2000), so units are in meters
            for idx_p, p_line in power_lines.iterrows():
                buffer_geom = p_line.geometry.buffer(5.0)
                for idx_b, building in buildings.iterrows():
                    if buffer_geom.intersects(building.geometry):
                        violations_count += 1
                        
                        # Get centroid for reporting
                        centroid = building.geometry.centroid
                        
                        violations_list.append({
                            "type": "proximity_violation",
                            "severity": "high",
                            "description": f"Building near Power Line (Distance < 5m)",
                            "coords": [float(centroid.x), float(centroid.y)]
                        })
            
            # Create visualization features for the audit
            # (In a real audit we might add the actual buffer polygons to the CAD)
            
        # 2. Lighting Audit (Coverage)
        coverage_score = 0
        if not roads.empty:
            total_road_length = roads.geometry.length.sum()
            # Ideal: 1 lamp every 30m
            ideal_lamps_count = total_road_length / 30.0
            actual_lamps_count = len(lamps)
            
            if ideal_lamps_count > 0:
                coverage_score = min(100, int((actual_lamps_count / ideal_lamps_count) * 100))

        summary = {
            "violations_count": int(violations_count),
            "proximity_alerts": violations_list,
            "lighting_score": float(coverage_score / 100.0),
            "stats": {
                "power_lines": len(power_lines),
                "buildings": len(buildings),
                "lamps": len(lamps)
            }
        }

        return summary, gpd.GeoDataFrame(columns=['geometry'], crs=gdf.crs) # Analysis GDF placeholder
