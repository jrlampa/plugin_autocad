import sys
import os
import unittest
import shutil
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path
import math

# Add src/backend to python path
sys.path.append(os.path.join(os.getcwd(), 'src', 'backend'))

from backend.services.elevation import ElevationService
from backend.api import _get_color_from_elevation

try:
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None

class TestBackendPhase2(unittest.TestCase):
    
    def setUp(self):
        # Setup mock elevation service
        self.service = ElevationService()
        self.cache_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'sisRUA' / 'cache' / 'elevation'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a dummy GeoTIFF for testing
        self.dummy_tif = self.cache_dir / "test_synthetic.tif"
        self._create_dummy_tif(self.dummy_tif)

    def _create_dummy_tif(self, path):
        if not rasterio:
            return
            
        # Create a 100x100 grid representing a hill
        # Lat/Lon area: -20.44 to -20.43 (approx 1km)
        transform = from_origin(-41.80, -20.43, 0.0001, 0.0001)
        
        # Array 100x100
        x = np.linspace(-1, 1, 100)
        y = np.linspace(-1, 1, 100)
        X, Y = np.meshgrid(x, y)
        Z = 500 * np.exp(-(X**2 + Y**2)) # Gaussian hill, max 500m
        Z = Z.astype(rasterio.float32)

        with rasterio.open(
            path,
            'w',
            driver='GTiff',
            height=Z.shape[0],
            width=Z.shape[1],
            count=1,
            dtype=Z.dtype,
            crs='+proj=latlong',
            transform=transform,
        ) as dst:
            dst.write(Z, 1)

    def tearDown(self):
        # Cleanup
        if self.dummy_tif.exists():
            try:
                self.dummy_tif.unlink()
            except:
                pass

    def test_color_logic(self):
        self.assertEqual(_get_color_from_elevation(0, 0, 100), "5") 
        self.assertEqual(_get_color_from_elevation(100, 0, 100), "1")
        self.assertEqual(_get_color_from_elevation(50, 0, 100), "3")
        self.assertEqual(_get_color_from_elevation(50, 50, 50), "255,255,255")

    @patch('backend.services.elevation.ElevationService.get_elevation_grid')
    def test_elevation_point_query(self, mock_get_grid):
        if not rasterio:
            self.skipTest("Rasterio not installed")
            
        # Mock get_elevation_grid to return our dummy tif
        mock_get_grid.return_value = self.dummy_tif
        
        # Center of the hill (-20.435, -41.795) - heavily approximate coords
        # Our transform started at -41.80, -20.43
        # pixel size 0.0001. 100 pixels = 0.01 deg.
        # So covers -41.80 to -41.79, and -20.43 to -20.44 (going down/up?)
        # from_origin(west, north, xsize, ysize).
        # Bounds: West -41.80. North -20.43.
        # East = -41.80 + 0.01 = -41.79.
        # South = -20.43 - 0.01 = -20.44.
        
        # Query center: -41.795, -20.435
        lat, lon = -20.435, -41.795
        
        z = self.service.get_elevation_at_point(lat, lon)
        print(f"Sampled Z: {z}")
        
        self.assertIsNotNone(z)
        # Should be near max (500)
        self.assertTrue(300 < z < 550)

    @patch('backend.services.elevation.ElevationService.get_elevation_grid')
    def test_contours_generation(self, mock_get_grid):
        if not rasterio:
            self.skipTest("Rasterio not installed")
            
        mock_get_grid.return_value = self.dummy_tif
        
        # Request contours for the whole area
        min_lat, max_lat = -20.44, -20.43
        min_lon, max_lon = -41.80, -41.79
        
        contours = self.service.get_contours(min_lat, min_lon, max_lat, max_lon, interval=100.0)
        
        print(f"Generated {len(contours)} contour sets")
        self.assertTrue(len(contours) > 0)
        
        sample = contours[0]
        self.assertIn('elevation', sample)
        self.assertIn('geometry', sample)
        
        # Check Z values roughly match interval
        elevs = [c['elevation'] for c in contours]
        print(f"Contour levels: {sorted(list(set(elevs)))}")
        self.assertIn(100.0, elevs)
        self.assertIn(200.0, elevs)

if __name__ == '__main__':
    unittest.main()
