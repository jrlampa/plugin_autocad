
import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src" / "backend"))

from backend.gis_core.topology import TopologyHealer

class MockFeature:
    def __init__(self, coords):
        self.coords_xy = coords

class TestRobustHashing(unittest.TestCase):
    def test_deterministic_rounding(self):
        healer = TopologyHealer()
        
        # Feature 1: "Clean" geometry
        f1 = MockFeature([(10.123, 20.123), (30.123, 40.123)])
        
        # Feature 2: Micro-deviations (AutoCAD floating point noise)
        # 0.0001 difference (beyond 3 decimal places)
        f2 = MockFeature([(10.1234, 20.1234), (30.1234, 40.1234)])
        
        hash1 = healer.get_robust_integrity_signature([f1])
        hash2 = healer.get_robust_integrity_signature([f2])
        
        print(f"Hash 1: {hash1}")
        print(f"Hash 2: {hash2}")
        
        self.assertEqual(hash1, hash2, "Robust hashing should ignore micro-deviations < 1mm")

    def test_spatial_sorting(self):
        healer = TopologyHealer()
        
        fA = MockFeature([(10, 10), (20, 20)])
        fB = MockFeature([(30, 30), (40, 40)])
        
        # Order 1: A then B
        hash1 = healer.get_robust_integrity_signature([fA, fB])
        
        # Order 2: B then A (simulating EXPLODE/Select Order change)
        hash2 = healer.get_robust_integrity_signature([fB, fA])
        
        print(f"Hash Order 1: {hash1}")
        print(f"Hash Order 2: {hash2}")
        
        self.assertEqual(hash1, hash2, "Robust hashing must be independent of feature order")

if __name__ == "__main__":
    unittest.main()
