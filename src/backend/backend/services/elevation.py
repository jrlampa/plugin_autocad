import os
import requests
import rasterio
import numpy as np
from pathlib import Path
import hashlib
import matplotlib.pyplot as plt
from shapely.geometry import LineString, mapping
import math


CACHE_DIR = Path(os.environ.get('LOCALAPPDATA', '')) / 'sisRUA' / 'cache' / 'elevation'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class ElevationService:
    def __init__(self):
        # OpenTopography API base URL for SRTMGL3 (90m resolution) or SRTMGL1 (30m)
        # Using SRTMGL3 (90m) for speed and smaller file sizes initially.
        self.base_url = "https://portal.opentopography.org/API/globaldem"
        
    def _get_cache_path(self, bounds):
        """Generates a cache filename based on bounds."""
        bounds_str = f"{bounds[0]}_{bounds[1]}_{bounds[2]}_{bounds[3]}"
        hash_digest = hashlib.md5(bounds_str.encode()).hexdigest()
        return CACHE_DIR / f"srtm_{hash_digest}.tif"

    def get_elevation_grid(self, min_lat, min_lon, max_lat, max_lon):
        """
        Downloads or retrieves cached elevation grid (GeoTIFF) for the specified bounding box.
        Returns the path to the GeoTIFF file.
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
            
        print(f"Downloading DEM for bounds: {bounds}")
        params = {
            'demtype': 'SRTMGL3',
            'south': s,
            'north': n,
            'west': w,
            'east': e,
            'outputFormat': 'GTiff'
        }
        
        try:
            response = requests.get(self.base_url, params=params, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return cache_path
        except Exception as ex:
            print(f"Error downloading DEM: {ex}")
            # Clean up partial file
            if cache_path.exists():
                cache_path.unlink()
            raise

    def get_elevation_at_point(self, lat, lon):
        """Returns the elevation (Z) at a specific point."""
        # Define a small bounding box
        tif_path = self.get_elevation_grid(lat, lon, lat, lon)
        
        with rasterio.open(tif_path) as src:
            vals = list(src.sample([(lon, lat)]))
            if vals and len(vals) > 0:
                return float(vals[0][0])
        return None

    def get_elevation_profile(self, coordinates):
        """
        Returns elevation for a list of (lat, lon) coordinates.
        Optimized to download a single covering DEM if points are close.
        """
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

            # Generate contours using matplotlib
            # We need to flip the data because matplotlib origin is bottom-left, rasterio image is top-left usually
            # Actually rasterio reads as array (row, col). 
            # Row 0 is North. Row N is South. 
            
            contours_obj = plt.contour(data, levels=levels)
            
            results = []
            
            # Transform from pixel coordinates to lat/lon
            transform = src.window_transform(window)
            
            for i, collection in enumerate(contours_obj.collections):
                level_elev = levels[i]
                for path in collection.get_paths():
                    # path.vertices contains (col, row) in array coordinates?
                    # Matplotlib contour (x, y) corresponds to (col, row) index usually?
                    # Let's verify: plt.contour(Z) treats Z as Z[y, x]. 
                    # So x corresponds to column index, y to row index.
                    # HOWEVER, generic array plotting in mpl puts [0,0] at bottom-left or top-left depending on origin.
                    # Default origin=None -> usually 'upper' for images? No, contour defaults to origin=None which usually means [0,0] is bottom-left.
                    # BUT rasterio reads image with row 0 at top.
                    
                    # To be safe, we should use origin='upper' in contour if we treat it as image rows.
                    # Let's re-run contour with origin='upper' to match matrix index convention (row 0 = top).
                    pass

            # Rerunning logic cleanly
            plt.close() # Clean state
            
            # Use origin='upper' so that y-coordinate 0 matches row 0 (North).
            contours_obj = plt.contour(data, levels=levels, origin='upper')
            
            for i, collection in enumerate(contours_obj.collections):
                level_elev = float(levels[i])
                for path in collection.get_paths():
                    verts = path.vertices # (x, y) -> (col, row)
                    
                    coords_latlon = []
                    for x_px, y_px in verts:
                        # Rasterio pixel to geographic: xy(row, col)
                        # Note: transform * (col, row) -> (x, y) [lon, lat]
                        # Verts are (x, y) in plot space. 
                        # With origin='upper', y=0 is top row. y increases downwards.
                        # So y_px corresponds to row index. x_px corresponds to col index.
                        
                        # Apply transform: transform * (col, row)
                        lon, lat = transform * (x_px, y_px)
                        coords_latlon.append((lat, lon))
                    
                    if len(coords_latlon) >= 2:
                        results.append({
                            'elevation': level_elev,
                            'geometry': coords_latlon # List of (lat, lon)
                        })
            
            plt.close()
            return results
