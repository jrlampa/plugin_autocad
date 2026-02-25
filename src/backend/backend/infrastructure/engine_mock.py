
import random
from typing import List, Any, Dict

class AutoCADMock:
    """
    Simulates AutoCAD's geometry processing with artificial noise 
    to test sisRUA's precision resilience.
    """
    def __init__(self, precision_noise: float = 1e-7):
        self.noise = precision_noise
        self.db = []

    def draw_polyline(self, coords: List[List[float]], layer: str = "0"):
        # Inject "floating point jitter" typical of CAD environments
        noisy_coords = [[x + random.uniform(-self.noise, self.noise), 
                         y + random.uniform(-self.noise, self.noise)] for x, y in coords]
        
        self.db.append({
            "type": "Polyline",
            "layer": layer,
            "coords": noisy_coords,
            "closed": self._is_closed(noisy_coords)
        })

    def _is_closed(self, coords: List[List[float]]) -> bool:
        if len(coords) < 2: return False
        d = ((coords[0][0] - coords[-1][0])**2 + (coords[0][1] - coords[-1][1])**2)**0.5
        return d < 1e-6

    def get_layer_count(self) -> Dict[str, int]:
        counts = {}
        for ent in self.db:
            l = ent["layer"]
            counts[l] = counts.get(l, 0) + 1
        return counts
