
import sys
import os
import math
import requests
from io import BytesIO

# Try to import rasterio found in PYTHONPATH
try:
    import rasterio
except ImportError:
    # Add local site-packages if needed (though previous steps installed it)
    pass

def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def test_aws_tile():
    # Pico da Bandeira
    lat = -20.433
    lon = -41.796
    zoom = 12
    
    x, y = latlon_to_tile(lat, lon, zoom)
    print(f"Tile Z={zoom} X={x} Y={y}")
    
    url = f"https://s3.amazonaws.com/elevation-tiles-prod/geotiff/{zoom}/{x}/{y}.tif"
    print(f"Fetching {url}...")
    
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        print(f"Success! Size: {len(r.content)} bytes")
        
        # Try to read with rasterio
        with rasterio.open(BytesIO(r.content)) as src:
            print(f"Raster profile: {src.profile}")
            
            # Transform lat/lon (4326) to Web Mercator (3857)
            from pyproj import Transformer
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
            x_proj, y_proj = transformer.transform(lon, lat)
            
            print(f"Projected coordinates: {x_proj}, {y_proj}")
            
            vals = list(src.sample([(x_proj, y_proj)]))
            print(f"Elevation at {lat}, {lon}: {vals[0][0]} meters")
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_aws_tile()
