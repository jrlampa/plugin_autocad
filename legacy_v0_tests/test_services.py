import unittest
from backend.services.crs import utm_zone, sirgas2000_utm_epsg
from backend.services.elevation import ElevationService
from unittest.mock import patch, MagicMock
from pathlib import Path
import shutil
import os
import requests

class TestCrsService(unittest.TestCase):
    def test_utm_zone_clamping(self):
        self.assertEqual(utm_zone(-185), 1)
        self.assertEqual(utm_zone(185), 60)
        self.assertEqual(utm_zone(0), 31)
        self.assertEqual(utm_zone(-45), 23)

    def test_sirgas2000_utm_epsg(self):
        # Zone 23 is -48 to -42. -45 is in zone 23.
        # 31960 + 23 = 31983
        self.assertEqual(sirgas2000_utm_epsg(-20, -45), 31983)

class TestElevationServiceExtra(unittest.TestCase):
    def setUp(self):
        self.cache_dir = Path("test_cache_services")
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.service = ElevationService(cache_dir=str(self.cache_dir))

    def tearDown(self):
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

    @patch('requests.get')
    def test_download_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        mock_get.return_value = mock_response
        
        # res should be None because of the try-except return None in elevation.py
        res = self.service.get_elevation_at_point(0, 0)
        self.assertIsNone(res)

    @patch('backend.services.elevation.ElevationService.get_elevation_grid')
    def test_get_elevation_at_point_cached(self, mock_grid):
        # This is more for structure since testing rasterio.open needs a real file
        mock_grid.return_value = None # Simulate failure
        res = self.service.get_elevation_at_point(0, 0)
        self.assertIsNone(res)

if __name__ == '__main__':
    unittest.main()
