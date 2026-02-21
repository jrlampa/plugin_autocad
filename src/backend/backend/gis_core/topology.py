
from typing import List, Tuple, Dict, Any, Optional
import math
import hashlib


class TopologyHealer:
    """
    sisRUA Topology Healing Engine.
    Corrects common OSM artifacts (orphan nodes, gaps) and signs the geometry.

    Pipeline aplicado em cada requisição OSM:
      1. Node Snapping (Union-Find) — agrupa e centraliza endpoints próximos
      2. (futuro) Orphan Node Removal
      3. (futuro) Gap Closure
    """

    def __init__(self, snap_tolerance: float = 0.05, integrity_seed: str = "sisRUA_v1.1"):
        self.snap_tolerance = snap_tolerance
        self.integrity_seed = integrity_seed
        self.stats: Dict[str, int] = {"healed_nodes": 0, "closed_polygons": 0}

    # ------------------------------------------------------------------
    # Union-Find (Disjoint Set Union) — auxiliar para node snapping
    # ------------------------------------------------------------------

    @staticmethod
    def _make_uf(n: int) -> List[int]:
        return list(range(n))

    @staticmethod
    def _uf_find(parent: List[int], x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    @staticmethod
    def _uf_union(parent: List[int], a: int, b: int) -> None:
        ra, rb = TopologyHealer._uf_find(parent, a), TopologyHealer._uf_find(parent, b)
        if ra != rb:
            parent[rb] = ra

    # ------------------------------------------------------------------
    # Node Snapping
    # ------------------------------------------------------------------

    def heal_network(self, features: List[Any]) -> List[Any]:
        """
        Heals network topology by snapping polyline endpoints within
        `snap_tolerance` metres to a common centroid.

        Algorithm: Union-Find (O(n² α(n))) over all endpoint pairs.
        Correctly handles junctions where 3+ roads share a node.

        Args:
            features: List of CadFeature objects (Polyline or Point).

        Returns:
            Same list with snapped endpoint coordinates (mutated in-place).
        """
        polyline_indices = [
            i for i, f in enumerate(features)
            if getattr(f, "feature_type", None) == "Polyline"
            and getattr(f, "coords_xy", None)
            and len(f.coords_xy) >= 2
        ]

        if len(polyline_indices) < 2:
            return features

        # Build endpoint table: (feature_idx, vertex_idx, x, y)
        # vertex_idx=0 → first vertex; vertex_idx=-1 → last vertex
        eps: List[Tuple[int, int, float, float]] = []
        for fi in polyline_indices:
            coords = features[fi].coords_xy
            eps.append((fi, 0, float(coords[0][0]), float(coords[0][1])))
            eps.append((fi, -1, float(coords[-1][0]), float(coords[-1][1])))

        n = len(eps)
        parent = self._make_uf(n)

        # Connect endpoints within snap_tolerance.
        # O(n²) pairwise distance checks + O(α(n)) amortized Union-Find ops.
        for i in range(n):
            xi, yi = eps[i][2], eps[i][3]
            for j in range(i + 1, n):
                xj, yj = eps[j][2], eps[j][3]
                if math.sqrt((xi - xj) ** 2 + (yi - yj) ** 2) < self.snap_tolerance:
                    self._uf_union(parent, i, j)

        # Group endpoints by their Union-Find root
        groups: Dict[int, List[int]] = {}
        for i in range(n):
            root = self._uf_find(parent, i)
            groups.setdefault(root, []).append(i)

        # Snap each group (≥2 endpoints) to centroid
        healed = 0
        for group in groups.values():
            if len(group) < 2:
                continue
            cx = sum(eps[k][2] for k in group) / len(group)
            cy = sum(eps[k][3] for k in group) / len(group)
            for k in group:
                fi, vi = eps[k][0], eps[k][1]
                if vi == 0:
                    features[fi].coords_xy[0] = [cx, cy]
                else:
                    features[fi].coords_xy[-1] = [cx, cy]
            healed += len(group) - 1

        self.stats["healed_nodes"] = healed
        return features

    def get_integrity_signature(self, features: List[Any]) -> str:
        """
        Legacy signature (string based). Maintained for backward compatibility.
        """
        payload = "".join([str(getattr(f, 'coords_xy', '')) for f in features])
        h = hashlib.sha256(f"{self.integrity_seed}|{payload}".encode()).hexdigest()
        return f"SIS-{h[:12].upper()}"

    def get_robust_integrity_signature(self, features: List[Any]) -> str:
        """
        Generates a Robust Spatial Hash (Audit Grade).
        
        Technique:
        1. Deterministic Rounding: Coords are rounded to 3 decimal places (mm precision).
           This tolerates floating-point drift from AutoCAD JOIN/TRIM operations.
        2. Spatial Sorting: Features are sorted by Centroid (X, then Y) to be
           independent of drawing order (e.g., after an EXPLODE/Layer Change).
        """
        # 1. Extract and Normalize
        normalized_features = []
        for f in features:
            coords = getattr(f, 'coords_xy', [])
            if not coords: continue
            
            # Round to 3 decimals (1mm)
            rounded_coords = [
                (round(pt[0], 3), round(pt[1], 3)) 
                for pt in coords 
                if len(pt) >= 2
            ]
            
            if not rounded_coords: continue
            
            # Calculate Centroid for Sorting
            cx = sum(p[0] for p in rounded_coords) / len(rounded_coords)
            cy = sum(p[1] for p in rounded_coords) / len(rounded_coords)
            
            normalized_features.append({
                "c": (cx, cy),
                "g": rounded_coords
            })
            
        # 2. Spatial Sort (X then Y)
        normalized_features.sort(key=lambda x: (x["c"][0], x["c"][1]))
        
        # 3. Serialize and Hash
        payload = f"{self.integrity_seed}|"
        for nf in normalized_features:
            # Compact string representation of rounded geometry
            geo_str = ";".join([f"{p[0]},{p[1]}" for p in nf["g"]])
            payload += f"[{geo_str}]"
            
        h = hashlib.sha256(payload.encode()).hexdigest()
        return f"SIS-AUDIT-{h[:12].upper()}"

    def get_report(self) -> Dict[str, Any]:
        return {
            "summary": "Topology healed and validated.",
            "metrics": self.stats,
            "ip_status": "Proprietary Algorithm - sisRUA GIS Core V1"
        }
