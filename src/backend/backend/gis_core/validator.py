"""
Geometry Validation and Auto-Fix Module

Validates and automatically fixes common geometry issues in GeoJSON data:
- Self-intersections
- Invalid topology
- Out-of-bounds coordinates
- Too many vertices (simplification)
- Duplicate points

Part of Implementation #5 from Fullstack Analysis.
"""

from typing import Dict, List, Tuple, Optional, Any
import logging
from shapely.geometry import shape, mapping, Point, LineString, Polygon, MultiPolygon
from shapely.validation import explain_validity
from shapely.ops import unary_union
from shapely import is_valid, make_valid, simplify

logger = logging.getLogger(__name__)


class GeometryIssue:
    """Represents a geometry validation issue"""
    
    def __init__(self, feature_id: str, issue_type: str, severity: str, description: str, fixed: bool = False):
        self.feature_id = feature_id
        self.issue_type = issue_type  # 'invalid_topology', 'out_of_bounds', 'too_complex', 'duplicate_points'
        self.severity = severity  # 'critical', 'warning', 'info'
        self.description = description
        self.fixed = fixed
    
    def to_dict(self) -> Dict:
        return {
            'feature_id': self.feature_id,
            'type': self.issue_type,
            'severity': self.severity,
            'description': self.description,
            'fixed': self.fixed
        }


class GeometryValidator:
    """
    Validates and fixes geometries in GeoJSON data.
    
    Usage:
        validator = GeometryValidator(max_vertices=10000, tolerance=0.001)
        cleaned_geojson, issues = validator.validate_and_fix(geojson)
        report = validator.generate_report(issues)
    """
    
    def __init__(self, 
                 max_vertices: int = 10000,
                 simplify_tolerance: float = 0.001,
                 bounds: Optional[Tuple[float, float, float, float]] = None):
        """
        Args:
            max_vertices: Maximum allowed vertices per feature (triggers simplification)
            simplify_tolerance: Douglas-Peucker tolerance for simplification
            bounds: Optional (min_lon, min_lat, max_lon, max_lat) bounds
        """
        self.max_vertices = max_vertices
        self.simplify_tolerance = simplify_tolerance
        self.bounds = bounds
        
    def validate_and_fix(self, geojson: Dict) -> Tuple[Dict, List[GeometryIssue]]:
        """
        Validates and fixes all features in a GeoJSON FeatureCollection.
        
        Returns:
            Tuple of (cleaned_geojson, list_of_issues)
        """
        if 'features' not in geojson:
            logger.warning("GeoJSON has no 'features' key")
            return geojson, []
        
        issues: List[GeometryIssue] = []
        cleaned_features = []
        
        for idx, feature in enumerate(geojson['features']):
            feature_id = feature.get('id', f"feature_{idx}")
            
            try:
                geom = shape(feature['geometry'])
                
                # Validation steps
                feature_issues = []
                
                # 1. Topology validation
                if not is_valid(geom):
                    reason = explain_validity(geom)
                    feature_issues.append(GeometryIssue(
                        feature_id, 'invalid_topology', 'critical',
                        f"Invalid geometry: {reason}", fixed=False
                    ))
                    # Auto-fix with buffer(0) or make_valid
                    try:
                        geom = make_valid(geom)
                        feature_issues[-1].fixed = True
                        logger.info(f"Fixed invalid geometry for {feature_id}")
                    except Exception as e:
                        logger.error(f"Could not fix geometry for {feature_id}: {e}")
                        continue  # Skip this feature
                
                # 2. Bounds validation
                if self.bounds:
                    if not self._check_bounds(geom):
                        feature_issues.append(GeometryIssue(
                            feature_id, 'out_of_bounds', 'warning',
                            f"Geometry outside bounds {self.bounds}", fixed=False
                        ))
                        # Could clip here if needed
                
                # 3. Complexity check (vertex count)
                vertex_count = self._count_vertices(geom)
                if vertex_count > self.max_vertices:
                    feature_issues.append(GeometryIssue(
                        feature_id, 'too_complex', 'warning',
                        f"{vertex_count} vertices (max: {self.max_vertices})", fixed=False
                    ))
                    # Simplify
                    try:
                        original_area = geom.area if hasattr(geom, 'area') else 0
                        geom = simplify(geom, tolerance=self.simplify_tolerance, preserve_topology=True)
                        new_count = self._count_vertices(geom)
                        new_area = geom.area if hasattr(geom, 'area') else 0
                        
                        area_diff = abs(original_area - new_area) / original_area * 100 if original_area > 0 else 0
                        
                        feature_issues[-1].fixed = True
                        feature_issues[-1].description += f" → simplified to {new_count} vertices (area change: {area_diff:.2f}%)"
                        logger.info(f"Simplified {feature_id}: {vertex_count} → {new_count} vertices")
                    except Exception as e:
                        logger.error(f"Could not simplify {feature_id}: {e}")
                
                # 4. Duplicate points check (for LineStrings)
                if isinstance(geom, LineString):
                    coords = list(geom.coords)
                    unique_coords = []
                    duplicates = 0
                    for i, coord in enumerate(coords):
                        if i == 0 or coord != coords[i-1]:
                            unique_coords.append(coord)
                        else:
                            duplicates += 1
                    
                    if duplicates > 0:
                        feature_issues.append(GeometryIssue(
                            feature_id, 'duplicate_points', 'info',
                            f"Removed {duplicates} consecutive duplicate points", fixed=True
                        ))
                        geom = LineString(unique_coords)
                
                # Update feature geometry
                feature['geometry'] = mapping(geom)
                cleaned_features.append(feature)
                issues.extend(feature_issues)
                
            except Exception as e:
                logger.error(f"Error processing feature {feature_id}: {e}")
                issues.append(GeometryIssue(
                    feature_id, 'processing_error', 'critical',
                    f"Could not process: {str(e)}", fixed=False
                ))
        
        cleaned_geojson = {**geojson, 'features': cleaned_features}
        return cleaned_geojson, issues
    
    def _check_bounds(self, geom) -> bool:
        """Check if geometry is within bounds"""
        if not self.bounds:
            return True
        min_lon, min_lat, max_lon, max_lat = self.bounds
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        return (bounds[0] >= min_lon and bounds[1] >= min_lat and
                bounds[2] <= max_lon and bounds[3] <= max_lat)
    
    def _count_vertices(self, geom) -> int:
        """Count total vertices in a geometry"""
        if isinstance(geom, Point):
            return 1
        elif isinstance(geom, LineString):
            return len(geom.coords)
        elif isinstance(geom, Polygon):
            count = len(geom.exterior.coords)
            for interior in geom.interiors:
                count += len(interior.coords)
            return count
        elif isinstance(geom, (MultiPolygon,)):
            return sum(self._count_vertices(g) for g in geom.geoms)
        else:
            # For other geometry types
            try:
                return len(list(geom.coords))
            except:
                return 0
    
    def generate_report(self, issues: List[GeometryIssue]) -> Dict:
        """
        Generate a quality report from validation issues.
        
        Returns:
            Dict with statistics and issue breakdown
        """
        total = len(issues)
        if total == 0:
            return {
                'total_issues': 0,
                'summary': 'All geometries are valid ✓',
                'by_type': {},
                'by_severity': {},
                'fixed': 0,
                'unfixed': 0
            }
        
        by_type = {}
        by_severity = {}
        fixed_count = 0
        
        for issue in issues:
            # Count by type
            by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1
            
            # Count by severity
            by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
            
            # Count fixed
            if issue.fixed:
                fixed_count += 1
        
        return {
            'total_issues': total,
            'fixed': fixed_count,
            'unfixed': total - fixed_count,
            'fix_rate': f"{(fixed_count / total * 100):.1f}%" if total > 0 else "0%",
            'by_type': by_type,
            'by_severity': by_severity,
            'issues': [issue.to_dict() for issue in issues]
        }


def validate_geojson(geojson: Dict, 
                    max_vertices: int = 10000,
                    simplify_tolerance: float = 0.001,
                    bounds: Optional[Tuple[float, float, float, float]] = None) -> Tuple[Dict, Dict]:
    """
    Convenience function to validate and fix a GeoJSON.
    
    Returns:
        Tuple of (cleaned_geojson, quality_report)
    """
    validator = GeometryValidator(max_vertices, simplify_tolerance, bounds)
    cleaned, issues = validator.validate_and_fix(geojson)
    report = validator.generate_report(issues)
    return cleaned, report
