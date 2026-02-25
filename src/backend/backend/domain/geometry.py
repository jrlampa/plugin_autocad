
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

def get_bounding_offset(features: List[Any]) -> Tuple[float, float]:
    """
    Calculates the first coordinate of the first feature as a global offset.
    This keeps coordinates near 0,0 during internal processing.
    """
    for f in features:
        if hasattr(f, "coords_xy") and f.coords_xy:
            return f.coords_xy[0][0], f.coords_xy[0][1]
        if hasattr(f, "insertion_point_xy") and f.insertion_point_xy:
            return f.insertion_point_xy[0], f.insertion_point_xy[1]
    return 0.0, 0.0
