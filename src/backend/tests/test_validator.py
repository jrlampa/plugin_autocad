"""
Tests for GeometryValidator

Tests the geometry validation and auto-fix functionality.
"""

import pytest
from backend.gis_core.validator import GeometryValidator, validate_geojson, GeometryIssue


def test_valid_geometry():
    """Test that valid geometries pass without issues"""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "test1",
                "geometry": {
                    "type": "Point",
                    "coordinates": [-41.0, -21.0]
                },
                "properties": {}
            }
        ]
    }
    
    validator = GeometryValidator()
    cleaned, issues = validator.validate_and_fix(geojson)
    
    assert len(issues) == 0
    assert len(cleaned['features']) == 1


def test_invalid_polygon_auto_fix():
    """Test that invalid (self-intersecting) polygons are auto-fixed"""
    # Bow-tie polygon (self-intersecting)
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "invalid_poly",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0], [2, 2], [2, 0], [0, 2], [0, 0]  # Self-intersecting
                    ]]
                },
                "properties": {}
            }
        ]
    }
    
    validator = GeometryValidator()
    cleaned, issues = validator.validate_and_fix(geojson)
    
    # Should have found and fixed the issue
    topology_issues = [i for i in issues if i.issue_type == 'invalid_topology']
    assert len(topology_issues) > 0
    assert topology_issues[0].fixed == True
    
    # Feature should still be included (fixed)
    assert len(cleaned['features']) == 1


def test_complex_geometry_simplification():
    """Test that geometries with too many vertices are simplified"""
    # Create a line with many points
    coords = [[i * 0.001, 0] for i in range(15000)]  # 15000 points
    
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "complex_line",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {}
            }
        ]
    }
    
    validator = GeometryValidator(max_vertices=10000, simplify_tolerance=0.01)
    cleaned, issues = validator.validate_and_fix(geojson)
    
    # Should have detected complexity
    complexity_issues = [i for i in issues if i.issue_type == 'too_complex']
    assert len(complexity_issues) > 0
    assert complexity_issues[0].fixed == True
    
    # Geometry should be simplified
    from shapely.geometry import shape
    simplified_geom = shape(cleaned['features'][0]['geometry'])
    assert len(list(simplified_geom.coords)) < 15000


def test_duplicate_points_removal():
    """Test removal of consecutive duplicate points in LineStrings"""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "line_with_dupes",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [0, 0], [1, 1], [1, 1], [2, 2], [2, 2], [2, 2], [3, 3]
                    ]
                },
                "properties": {}
            }
        ]
    }
    
    validator = GeometryValidator()
    cleaned, issues = validator.validate_and_fix(geojson)
    
    # Should have detected duplicates
    dup_issues = [i for i in issues if i.issue_type == 'duplicate_points']
    assert len(dup_issues) > 0
    assert dup_issues[0].fixed == True
    assert "3 consecutive duplicate points" in dup_issues[0].description
    
    # Duplicates should be removed
    from shapely.geometry import shape
    line = shape(cleaned['features'][0]['geometry'])
    assert len(list(line.coords)) == 4  # [0,0], [1,1], [2,2], [3,3]


def test_out_of_bounds_detection():
    """Test detection of geometries outside specified bounds"""
    bounds = (-50, -30, -40, -20)  # min_lon, min_lat, max_lon, max_lat
    
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "out_of_bounds",
                "geometry": {
                    "type": "Point",
                    "coordinates": [-60, -25]  # Outside bounds
                },
                "properties": {}
            }
        ]
    }
    
    validator = GeometryValidator(bounds=bounds)
    cleaned, issues = validator.validate_and_fix(geojson)
    
    # Should detect out of bounds
    bounds_issues = [i for i in issues if i.issue_type == 'out_of_bounds']
    assert len(bounds_issues) > 0


def test_quality_report_generation():
    """Test quality report generation"""
    issues = [
        GeometryIssue("f1", "invalid_topology", "critical", "Self-intersecting", fixed=True),
        GeometryIssue("f2", "too_complex", "warning", "Too many vertices", fixed=True),
        GeometryIssue("f3", "duplicate_points", "info", "Duplicates found", fixed=True),
        GeometryIssue("f4", "invalid_topology", "critical", "Invalid ring", fixed=False),
    ]
    
    validator = GeometryValidator()
    report = validator.generate_report(issues)
    
    assert report['total_issues'] == 4
    assert report['fixed'] == 3
    assert report['unfixed'] == 1
    assert report['fix_rate'] == "75.0%"
    assert report['by_type']['invalid_topology'] == 2
    assert report['by_severity']['critical'] == 2


def test_validate_geojson_convenience():
    """Test the convenience function"""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [0, 0]
                },
                "properties": {}
            }
        ]
    }
    
    cleaned, report = validate_geojson(geojson)
    
    assert 'total_issues' in report
    assert len(cleaned['features']) == 1


def test_empty_featurecollection():
    """Test handling of empty FeatureCollections"""
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    validator = GeometryValidator()
    cleaned, issues = validator.validate_and_fix(geojson)
    
    assert len(issues) == 0
    assert len(cleaned['features']) == 0


def test_missing_features_key():
    """Test handling of GeoJSON without features key"""
    geojson = {
        "type": "FeatureCollection"
    }
    
    validator = GeometryValidator()
    cleaned, issues = validator.validate_and_fix(geojson)
    
    assert len(issues) == 0
