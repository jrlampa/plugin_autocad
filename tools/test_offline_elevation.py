import unittest
import os
import sys
import shutil
import numpy as np
import rasterio
from rasterio.transform import from_origin
from pathlib import Path
from unittest.mock import patch, MagicMock

# Fix path
sys.path.append(os.path.abspath("src/backend"))

from backend.services.elevation import ElevationService
from backend.services.cache import CacheService

class TestOfflineElevation(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_dem_lib")
        self.test_dir.mkdir(exist_ok=True)
        os.environ["SISRUA_DEM_LIBRARY"] = str(self.test_dir)
        
        # Create a dummy GeoTIFF covering lat 0-1, lon 0-1
        self.tif_path = self.test_dir / "test_tile.tif"
        
        arr = np.array([[100.0, 100.0], [100.0, 100.0]])
        transform = from_origin(0.0, 1.0, 0.5, 0.5) # West, North, xres, yres
        
        with rasterio.open(
            self.tif_path,
            'w',
            driver='GTiff',
            height=2,
            width=2,
            count=1,
            dtype=arr.dtype,
            crs='+proj=latlong',
            transform=transform,
        ) as dst:
            dst.write(arr, 1)

        self.cache = CacheService() # Assuming simple dict or file cache
        # Mock CacheService slightly if it relies on disk
        self.cache.get = MagicMock(return_value=None)
        self.cache.set = MagicMock()

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        del os.environ["SISRUA_DEM_LIBRARY"]

    @patch('requests.get')
    def test_offline_fallback(self, mock_get):
        print("--- Testing Offline Elevation ---")
        # Simulate network failure
        mock_get.side_effect = Exception("No Internet Connection")
        
        svc = ElevationService(self.cache)
        
        # Query point inside our TIF (0.25, 0.75) -> center of top-left pixel
        # Origin is (0, 1). x=0.25 (col 0), y=0.75 (row 0)
        lat = 0.75
        lon = 0.25
        
        print(f"Querying Lat: {lat}, Lon: {lon} (Simulated Offline)")
        elev = svc.get_elevation_at_point(lat, lon)
        
        print(f"Result: {elev}")
        
        self.assertEqual(elev, 100.0)
        print("[PASS] Retrieved elevation from local file despite network failure.")

if __name__ == "__main__":
    unittest.main()
