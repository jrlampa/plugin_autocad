import sys
import os
import unittest
import shutil
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path
import math
import pandas as pd
from typing import Optional, List, Any, Tuple
from shapely.geometry import LineString, Point, MultiLineString

# Add src/backend to python path
sys.path.append(os.path.join(os.getcwd(), 'src', 'backend'))

from backend.services.elevation import ElevationService
from backend.core.utils import (
    get_color_from_elevation, 
    estimate_width_m, 
    norm_optional_str, 
    to_linestrings,
    sanitize_jsonable,
    read_cache, 
    write_cache
)
from backend.services.osm import prepare_osm_compute
from backend.services.geojson import prepare_geojson_compute
from backend.models import CadFeature

try:
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None

class TestBackendComprehensive(unittest.TestCase):
    
    def setUp(self):
        self.cache_dir = Path("test_cache_comprehensive")
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.service = ElevationService(cache_dir=str(self.cache_dir))
        
        self.dummy_tif = self.cache_dir / "test_comp.tif"
        self._create_dummy_tif(self.dummy_tif)

    def _create_dummy_tif(self, path):
        if not rasterio: return
        transform = from_origin(-41.02, -20.98, 0.004, 0.004) # Covers a small area
        # Data with a gradient to ensure contours are generated
        data = np.zeros((20, 20), dtype=rasterio.float32)
        for r in range(20):
            for c in range(20):
                data[r, c] = 100.0 + (r + c) * 5.0
        
        with rasterio.open(path, 'w', driver='GTiff', height=20, width=20, count=1,
                          dtype=rasterio.float32, crs=None, transform=transform) as dst:
            dst.write(data, 1)

    def tearDown(self):
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

    def test_elevation_profile_integration(self):
        if not rasterio: self.skipTest("No rasterio")
        with patch.object(ElevationService, 'get_elevation_grid', return_value=self.dummy_tif):
            coords = [(-21.0, -41.0), (-21.004, -41.004)]
            elevations = self.service.get_elevation_profile(coords)
            self.assertEqual(len(elevations), 2)

    def test_contours_integration_real(self):
        if not rasterio: self.skipTest("No rasterio")
        with patch.object(ElevationService, 'get_elevation_grid', return_value=self.dummy_tif):
            # Query bounds covering the TIF
            contours = self.service.get_contours(-21.02, -41.02, -20.98, -40.98, interval=10.0)
            self.assertTrue(len(contours) > 0)
            self.assertIn('elevation', contours[0])

    def test_geojson_mega_test(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[-41, -21], [-41.01, -21.01]]},
                    "properties": {"name": "L1", "highway": "primary"}
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "MultiLineString", "coordinates": [[[-41.02, -21.02], [-41.03, -21.03]]]},
                    "properties": {"name": "ML1", "layer": "MY_LAYER"}
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-41.04, -21.04]},
                    "properties": {"name": "P1", "block_name": "POSTE", "rotation": 45}
                }
            ]
        }
        # Patching backend.services.geojson.ElevationService to mock its method
        with patch('backend.services.geojson.ElevationService') as MockService:
             MockService.return_value.get_elevation_profile.return_value = [100.0, 100.0, 100.0, 100.0]
             result = prepare_geojson_compute(geojson)
             self.assertEqual(len(result["features"]), 3)
             # Verify Point properties
             p = next(f for f in result["features"] if f["feature_type"] == "Point")
             self.assertEqual(p["block_name"], "POSTE")
             self.assertEqual(p["rotation"], 45)

    def test_geojson_single_feature_point(self):
        geo = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-41, -21]},
            "properties": {"name": "Single Point"}
        }
        # Don't strictly need to patch elevation if it fails gracefully
        res = prepare_geojson_compute(geo)
        self.assertEqual(len(res["features"]), 1)

    @patch('backend.services.osm.read_cache', return_value=None)
    @patch('backend.services.osm.write_cache')
    @patch('osmnx.graph_from_point')
    @patch('osmnx.project_graph')
    @patch('osmnx.graph_to_gdfs')
    @patch('backend.services.osm.elevation_service') # It's a global instance in osm.py
    def test_osm_compute_full(self, mock_elev, mock_gdfs, mock_proj, mock_from_pt, mock_write, mock_read):
        mock_from_pt.return_value = MagicMock()
        mock_proj.return_value = MagicMock()
        
        edges_df = pd.DataFrame({
            'geometry': [LineString([(0,0), (1,1)])],
            'highway': [['residential']], 
            'name': ['Street 1']
        })
        edges_df.crs = "EPSG:31983"
        nodes_df = pd.DataFrame({
            'geometry': [Point(0,0)],
            'amenity': ['bench']
        })
        nodes_df.crs = "EPSG:31983"
        mock_gdfs.return_value = (nodes_df, edges_df)
        mock_elev.get_elevation_profile.return_value = [100.0, 100.0]
        mock_elev.get_contours.return_value = [
            {'elevation': 100.0, 'geometry': [(-21.0, -41.0), (-21.01, -41.01)]}
        ]
        
        result = prepare_osm_compute(-21, -41, 100)
        self.assertTrue(any(f["layer"] == "SISRUA_CURVAS_NIVEL" for f in result["features"]))

    def test_to_linestrings_unsupported(self):
        # Should return empty for unsupported geometry types like Point if passed to to_linestrings
        self.assertEqual(to_linestrings(Point(0,0)), [])

    def test_norm_optional_str_complex(self):
        self.assertEqual(norm_optional_str("test"), "test")
        self.assertEqual(norm_optional_str(123), "123")
        self.assertIsNone(norm_optional_str(None))

    @patch('backend.services.osm.read_cache', return_value=None)
    @patch('backend.services.osm.write_cache')
    @patch('osmnx.graph_from_point')
    @patch('osmnx.project_graph')
    @patch('osmnx.graph_to_gdfs')
    @patch('backend.services.osm.elevation_service')
    def test_osm_compute_elevation_fail(self, mock_elev, mock_gdfs, mock_proj, mock_from_pt, mock_write, mock_read):
        mock_from_pt.return_value = MagicMock()
        mock_proj.return_value = MagicMock()
        mock_gdfs.return_value = (pd.DataFrame({'geometry':[Point(0,0)]}), pd.DataFrame({'geometry':[LineString([(0,0),(1,1)])]}))
        mock_elev.get_elevation_profile.side_effect = Exception("Simulated Fail")
        
        # Should not raise, just continue gracefully
        result = prepare_osm_compute(0, 0, 100)
        self.assertTrue(len(result["features"]) > 0)

    @patch('backend.services.osm.read_cache')
    @patch('osmnx.graph_from_point', side_effect=Exception("OSM Down"))
    def test_osm_compute_fallback_to_cache(self, mock_ox, mock_read):
        mock_read.return_value = {"features": [{"name": "Cached Street"}], "cache_hit": True}
        result = prepare_osm_compute(0, 0, 100)
        self.assertEqual(result["features"][0]["name"], "Cached Street")
        self.assertTrue(result["cache_hit"])

    def test_elevation_at_point_fail_coverage(self):
        with patch.object(ElevationService, 'get_elevation_grid', return_value=None):
            elev = self.service.get_elevation_at_point(-21.0, -41.0)
            self.assertIsNone(elev)
