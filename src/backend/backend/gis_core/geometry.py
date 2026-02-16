
from typing import List, Tuple, Any
import math

def apply_local_offset(coords: List[List[float]], offset_x: float, offset_y: float) -> List[List[float]]:
    """
    Shifts coordinates to a 0,0 local origin to preserve double precision.
    """
    return [[x - offset_x, y - offset_y] for x, y in coords]

def snap_to_edge(coords: List[List[float]], precision: int = 6) -> List[List[float]]:
    """
    Applies deterministic rounding and snapping to ensure topologically closed polygons 
    survive the GIS-to-CAD projection.
    """
    # Deterministic rounding
    rounded = [[round(x, precision), round(y, precision)] for x, y in coords]
    
    # Vertex snapping (ensure start/end identity for closed loops)
    if len(rounded) > 2:
        dist = math.sqrt((rounded[0][0] - rounded[-1][0])**2 + (rounded[0][1] - rounded[-1][1])**2)
        if dist < (10 ** -precision) * 2:
            rounded[-1] = [rounded[0][0], rounded[0][1]]
            
    return rounded

def get_bounding_offset(features: List[Any], return_bounds: bool = False) -> Tuple[float, ...]:
    """
    Calculates the first coordinate of the first feature as a global offset.
    If return_bounds=True, returns (min_x, min_y, max_x, max_y).
    """
    if return_bounds:
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        any_found = False
        
        for f in features:
            coords = []
            if hasattr(f, "coords_xy") and f.coords_xy:
                coords = f.coords_xy
            elif hasattr(f, "insertion_point_xy") and f.insertion_point_xy:
                coords = [f.insertion_point_xy]
            
            for pt in coords:
                any_found = True
                min_x = min(min_x, pt[0])
                min_y = min(min_y, pt[1])
                max_x = max(max_x, pt[0])
                max_y = max(max_y, pt[1])
        
        if not any_found:
            return 0.0, 0.0, 0.0, 0.0
        return min_x, min_y, max_x, max_y

    for f in features:
        if hasattr(f, "coords_xy") and f.coords_xy:
            return f.coords_xy[0][0], f.coords_xy[0][1]
        if hasattr(f, "insertion_point_xy") and f.insertion_point_xy:
            return f.insertion_point_xy[0], f.insertion_point_xy[1]
    return 0.0, 0.0
