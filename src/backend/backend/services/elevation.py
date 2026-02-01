import os
import requests
from pathlib import Path
import hashlib
from typing import Optional, List, Any, Tuple
import math


CACHE_DIR_DEFAULT = Path(os.environ.get('LOCALAPPDATA', '')) / 'sisRUA' / 'cache' / 'elevation'

from backend.core.interfaces import ICache
from backend.core.circuit_breaker import CircuitBreaker

class ElevationService:
    def __init__(self, cache: ICache, cache_dir: Optional[str] = None):
        # OpenTopography API base URL for SRTMGL3 (90m resolution) or SRTMGL1 (30m)
        self.base_url = "https://portal.opentopography.org/API/globaldem"
        self.api_key = os.environ.get("OPENTOPOGRAPHY_API_KEY")
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR_DEFAULT
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = cache
        
    def _get_cache_path(self, bounds):
        """Generates a cache filename based on bounds."""
        bounds_str = f"{bounds[0]}_{bounds[1]}_{bounds[2]}_{bounds[3]}"
        hash_digest = hashlib.md5(bounds_str.encode()).hexdigest()
        return self.cache_dir / f"srtm_{hash_digest}.tif"

    def _find_local_coverage(self, s, n, w, e) -> Optional[Path]:
        """
        Searches for a local GeoTIFF that covers the requested bounds.
        Scans SISRUA_DEM_LIBRARY and the cache directory.
        """
        search_paths = [self.cache_dir]
        lib_path = os.environ.get("SISRUA_DEM_LIBRARY")
        if lib_path:
            search_paths.append(Path(lib_path))
            
        import rasterio
        
        for base_dir in search_paths:
            if not base_dir.exists(): continue
            
            # Simple scan (could be optimized with an index)
            for tif in base_dir.glob("*.tif"):
                try:
                    with rasterio.open(tif) as src:
                        # Check if bounds overlap significantly or contain the request
                        # src.bounds = (left, bottom, right, top) i.e. (w, s, e, n)
                        if (src.bounds.left <= w and src.bounds.right >= e and
                            src.bounds.bottom <= s and src.bounds.top >= n):
                            return tif
                except:
                    continue
        return None

    def get_elevation_grid(self, min_lat, min_lon, max_lat, max_lon):
        """
        Downloads or retrieves cached elevation grid (GeoTIFF) for the specified bounding box.
        Fallback to local library if offline.
        """
        # Add a small buffer to avoid edge issues
        buffer = 0.01 
        s, n = min_lat - buffer, max_lat + buffer
        w, e = min_lon - buffer, max_lon + buffer
        
        # Round to 2 decimals to improve cache hit rate for slightly different queries
        s, n, w, e = round(s, 2), round(n, 2), round(w, 2), round(e, 2)
        
        bounds = (s, n, w, e)
        cache_path = self._get_cache_path(bounds)
        
        if cache_path.exists():
            return cache_path
            
        try:
            return self._download_grid(min_lat, min_lon, max_lat, max_lon, cache_path)
        except Exception as ex:
            print(f"Error downloading DEM (Circuit Breaker or API Fail): {ex}")
            # Offline Fallback
            local_dem = self._find_local_coverage(s, n, w, e)
            if local_dem:
                print(f"Offline Mode: Using local DEM: {local_dem}")
                return local_dem
                
            # Clean up partial file
            if cache_path.exists():
                cache_path.unlink()
            return None

    @CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    def _download_grid(self, s, n, w, e, cache_path):
        print(f"Downloading DEM for bounds: {s, n, w, e}")
        params = {
            'demtype': 'SRTMGL3',
            'south': s,
            'north': n,
            'west': w,
            'east': e,
            'outputFormat': 'GTiff'
        }
        
        headers = {}
        if self.api_key:
            params['API_Key'] = self.api_key
        
        response = requests.get(self.base_url, params=params, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(cache_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return cache_path

    def get_elevation_at_point(self, lat, lon):
        """Returns the elevation (Z) at a specific point."""
        from backend.core.utils import cache_key
        
        # Use round to 4 decimals (approx 11m) to improve cache reuse for point queries
        key = cache_key(["elev_pt", f"{lat:.4f}", f"{lon:.4f}"])
        cached = self.cache.get(key)
        if cached is not None:
            return float(cached["z"])

        import rasterio
        # Define a small bounding box
        tif_path = self.get_elevation_grid(lat, lon, lat, lon)
        if not tif_path:
            return None
            
        with rasterio.open(tif_path) as src:
            vals = list(src.sample([(lon, lat)]))
            if vals and len(vals) > 0:
                elev = float(vals[0][0])
                self.cache.set(key, {"z": elev}, ttl=86400) # Elevation is stable, 24h cache
                return elev
        return None

    def get_elevation_profile(self, coordinates):
        """
        Returns elevation for a list of (lat, lon) coordinates.
        Optimized to download a single covering DEM if points are close.
        """
        import rasterio
        if not coordinates:
            return []
            
        lats = [c[0] for c in coordinates]
        lons = [c[1] for c in coordinates]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        tif_path = self.get_elevation_grid(min_lat, min_lon, max_lat, max_lon)
        
        points = [(lon, lat) for lat, lon in coordinates]
        elevations = []
        
        with rasterio.open(tif_path) as src:
            sampled = src.sample(points)
            for val in sampled:
                elevations.append(float(val[0]))
                
        return elevations

    def get_contours(self, min_lat, min_lon, max_lat, max_lon, interval=10.0):
        """
        Generates contour lines (iso-elevation) for the given bounding box.
        Returns a list of dicts: {'elevation': float, 'geometry': LineString(lat, lon)}
        """
        import rasterio
        import numpy as np
        import matplotlib.pyplot as plt

        tif_path = self.get_elevation_grid(min_lat, min_lon, max_lat, max_lon)
        
        with rasterio.open(tif_path) as src:
            # Read data for the requested window
            # Convert lat/lon window to pixel window
            window = rasterio.windows.from_bounds(min_lon, min_lat, max_lon, max_lat, transform=src.transform)
            
            # Read elevation data as numpy array
            data = src.read(1, window=window)
            
            # Handle nodata
            data = np.nan_to_num(data, nan=src.nodata or -9999)
            
            # Determine levels
            z_min = np.nanmin(data)
            z_max = np.nanmax(data)
            
            # Align levels to interval (e.g., 0, 10, 20...)
            start = math.floor(z_min / interval) * interval
            end = math.ceil(z_max / interval) * interval
            levels = np.arange(start, end + interval, interval)
            
            if len(levels) < 2:
                 return []

            results = []
            transform = src.window_transform(window)

            # Use origin='upper' so that y-coordinate 0 matches row 0 (North).
            contours_obj = plt.contour(data, levels=levels, origin='upper')
            
            # Use allsegs to get simplified access to vertices
            # allsegs is a list of segments for each level
            # allsegs[i] -> list of polygons/lines
            for i, segs in enumerate(contours_obj.allsegs):
                if i >= len(levels): break
                level_elev = float(levels[i])
                
                for verts in segs:
                    # verts is numpy array of (x, y) -> (col, row) pixels
                    coords_latlon = []
                    for x_px, y_px in verts:
                        # Apply transform: transform * (col, row) -> (lon, lat)
                        lon, lat = transform * (x_px, y_px)
                        coords_latlon.append((lat, lon))
                    
                    if len(coords_latlon) >= 2:
                        results.append({
                            'elevation': level_elev,
                            'geometry': coords_latlon # List of (lat, lon)
                        })
            
            plt.close()
            return results
