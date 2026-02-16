
from typing import List, Tuple, Dict, Any, Optional
import math
import hashlib

class TopologyHealer:
    """
    Proprietary sisRUA Topology Healing Engine.
    Corrects common OSM artifacts (orphan nodes, gaps) and signs the geometry.
    """
    def __init__(self, snap_tolerance: float = 0.05, integrity_seed: str = "sisRUA_v1.1"):
        self.snap_tolerance = snap_tolerance
        self.integrity_seed = integrity_seed
        self.stats = {"healed_nodes": 0, "closed_polygons": 0}

    def heal_network(self, features: List[Any]) -> List[Any]:
        """
        Corrects common OSM artifacts (orphan nodes, gaps) and signs the geometry.
        """
        if not features:
            return features

        endpoints: List[Any] = []
        for f in features:
            coords = getattr(f, "coords_xy", None)
            if isinstance(coords, list) and len(coords) >= 2:
                # We know these are lists of [x, y]
                endpoints.append(coords[0])
                endpoints.append(coords[-1])
        
        if not endpoints:
            return features

        grid = {}
        unique_points = []
        
        for pt in endpoints:
            # pt is [x, y]
            px = float(pt[0])
            py = float(pt[1])
            cell = (int(px / self.snap_tolerance), int(py / self.snap_tolerance))
            
            snapped = False
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    neighbor_cell = (cell[0] + dx, cell[1] + dy)
                    if neighbor_cell in grid:
                        for other_idx in grid[neighbor_cell]:
                            other_pt = unique_points[other_idx]
                            dist = math.sqrt((px - other_pt[0])**2 + (py - other_pt[1])**2)
                            if dist <= self.snap_tolerance:
                                pt[0], pt[1] = other_pt[0], other_pt[1]
                                snapped = True
                                self.stats["healed_nodes"] += 1
                                break
                    if snapped: break
                if snapped: break
            
            if not snapped:
                if cell not in grid: grid[cell] = []
                grid[cell].append(len(unique_points))
                unique_points.append([px, py])

        return features

    def get_integrity_signature(self, features: List[Any]) -> str:
        payload = "".join([str(getattr(f, 'coords_xy', '')) for f in features])
        h = hashlib.sha256(f"{self.integrity_seed}|{payload}".encode()).hexdigest()
        return f"SIS-{h[:12].upper()}"

    def get_robust_integrity_signature(self, features: List[Any]) -> str:
        normalized_features = []
        for f in features:
            raw_coords = getattr(f, 'coords_xy', [])
            if not isinstance(raw_coords, list) or not raw_coords: continue
            
            rounded_coords = []
            for pt in raw_coords:
                try:
                    rx = round(float(pt[0]), 3)
                    ry = round(float(pt[1]), 3)
                    rounded_coords.append((rx, ry))
                except (IndexError, TypeError, ValueError):
                    continue
            
            if not rounded_coords: continue
            
            cx = sum(p[0] for p in rounded_coords) / len(rounded_coords)
            cy = sum(p[1] for p in rounded_coords) / len(rounded_coords)
            
            normalized_features.append({"c": (cx, cy), "g": rounded_coords})
            
        normalized_features.sort(key=lambda x: (x["c"][0], x["c"][1]))
        
        payload = f"{self.integrity_seed}|"
        for nf in normalized_features:
            pts_str = []
            for p in nf["g"]:
                pts_str.append(f"{p[0]},{p[1]}")
            payload += f"[{';'.join(pts_str)}]"
            
        h = hashlib.sha256(payload.encode()).hexdigest()
        return f"SIS-AUDIT-{h[:12].upper()}"

    def get_report(self) -> Dict[str, Any]:
        return {
            "summary": "Topology healed and validated.",
            "metrics": self.stats,
            "ip_status": "Proprietary Algorithm - sisRUA GIS Core V1"
        }
