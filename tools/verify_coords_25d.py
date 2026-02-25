
import os
import sys
import json
import math

# Add src/backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "backend")))

from backend.gis_core.osm import prepare_osm_compute
from backend.core.interfaces import ICache

class MockCache(ICache):
    def get(self, key: str): return None
    def set(self, key: str, value: any, ttl_sec: int = 3600): pass
    def delete(self, key: str): pass
    def clear(self): pass

class MockElevationService:
    def get_elevation_profile(self, latlon_list):
        # Return dummy elevations for testing 2.5D compliance
        return [100.0 + i for i in range(len(latlon_list))]
    
    def get_contours(self, min_lat, min_lon, max_lat, max_lon):
        return [
            {
                "elevation": 110.0,
                "geometry": [[min_lat, min_lon], [max_lat, max_lon]]
            }
        ]

def verify_25d_compliance(latitude, longitude, radius):
    print(f"\n--- Testing Coord: {latitude}, {longitude} | Radius: {radius}m ---")
    
    cache = MockCache()
    elev_svc = MockElevationService()
    
    try:
        result = prepare_osm_compute(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            cache_service=cache,
            elevation_service=elev_svc
        )
        
        features = result.get("features", [])
        print(f"Total features extracted: {len(features)}")
        
        compliance_errors = []
        for i, f in enumerate(features):
            # Check for Polyline 2.5D compliance
            if f.get("feature_type") == "Polyline":
                coords = f.get("coords_xy", [])
                for pt in coords:
                    if len(pt) != 2:
                        compliance_errors.append(f"Feature {i} (Polyline) has non-2D vertex: {pt}")
                
            # Check for Point 2.5D compliance
            elif f.get("feature_type") == "Point":
                pt = f.get("insertion_point_xy", [])
                if len(pt) != 2:
                    compliance_errors.append(f"Feature {i} (Point) has non-2D insertion point: {pt}")
            
            # Check for elevation attribute
            if "elevation" in f and f["elevation"] is not None:
                if not isinstance(f["elevation"], (int, float)):
                    compliance_errors.append(f"Feature {i} has invalid elevation type: {type(f['elevation'])}")

        if compliance_errors:
            print("❌ 2.5D Compliance Failures:")
            for err in compliance_errors[:10]: # Stop at 10
                print(f"  - {err}")
            return False
        else:
            print("✅ 2.5D Compliance Verified: All coordinates are 2D and elevation is stored as attribute.")
            return True

    except Exception as e:
        print(f"💥 Error processing coordinates: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    lat, lon = -22.15018, -42.92185
    radii = [100, 500, 1000]
    
    all_success = True
    for r in radii:
        if not verify_25d_compliance(lat, lon, r):
            all_success = False
            
    if all_success:
        print("\n🏆 GEOGRAPHIC 2.5D VERIFICATION COMPLETE: ALL RADII PASSED.")
        sys.exit(0)
    else:
        print("\n❌ GEOGRAPHIC 2.5D VERIFICATION FAILED.")
        sys.exit(1)
