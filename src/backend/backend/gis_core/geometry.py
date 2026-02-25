
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


def generate_street_curbs(
    centerline_coords: List[List[float]],
    width_m: float,
) -> Tuple[List[List[float]], List[List[float]]]:
    """
    Gera as polilinhas de meio-fio (guias) esquerda e direita a partir
    da linha de eixo de uma via (centerline).

    Implementa o conceito de desenho "de meio-fio a meio-fio" (curb-to-curb):
    em vez de representar apenas o eixo da via com largura visual (const_width),
    gera duas polylines paralelas separadas, cada uma a ``width_m / 2`` do eixo,
    representando a borda física da calçada/guia conforme ABNT NBR 14166.

    Princípio 2.5D: as polilinhas geradas são 2D (Z=0). A elevação é atributo.

    Args:
        centerline_coords: Lista de pares [X, Y] em coordenadas UTM.
        width_m:           Largura total da via em metros (de meio-fio a meio-fio).

    Returns:
        Tupla ``(left_coords, right_coords)`` onde cada elemento é uma lista
        de pares [X, Y] representando a guia esquerda e direita, respectivamente.
        Retorna listas vazias se a geometria for inválida.
    """
    if not centerline_coords or len(centerline_coords) < 2 or width_m <= 0:
        return [], []

    try:
        from shapely.geometry import LineString  # type: ignore

        line = LineString([(float(x), float(y)) for x, y in centerline_coords])
        half_w = width_m / 2.0

        # offset_curve: positivo = esquerda, negativo = direita (convenção Shapely)
        left_geom = line.offset_curve(half_w)
        right_geom = line.offset_curve(-half_w)

        left_coords: List[List[float]] = []
        right_coords: List[List[float]] = []

        if left_geom is not None and not left_geom.is_empty:
            left_coords = [
                [float(x), float(y)]
                for x, y in left_geom.coords
                if math.isfinite(x) and math.isfinite(y)
            ]

        if right_geom is not None and not right_geom.is_empty:
            right_coords = [
                [float(x), float(y)]
                for x, y in right_geom.coords
                if math.isfinite(x) and math.isfinite(y)
            ]

        return left_coords, right_coords

    except Exception:
        return [], []

