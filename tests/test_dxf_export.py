
import sys
import unittest
import ezdxf
from pathlib import Path
from shapely.geometry import Point, LineString

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src" / "backend"))

from backend.gis_core.dxf_export import DxfExporter

class TestDxfExport(unittest.TestCase):
    def test_dxf_generation(self):
        exporter = DxfExporter()
        
        # Create mock features
        f1 = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [10.0, 20.0]},
            "properties": {"highway": "primary"}
        }
        f2 = {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [10, 10]]},
            "properties": {"highway": "residential"}
        }
        
        exporter.add_features([f1, f2])
        
        # Generate stream
        dxf_str = exporter.get_stream()
        
        # Basic validation
        self.assertTrue("HEADER" in dxf_str)
        self.assertTrue("ENTITIES" in dxf_str)
        
        # Verify layers exist in output
        # Ezdxf writes layer names in various places, but let's check config loading
        self.assertTrue("SISRUA_Vias_Arteriais_Secundarias" in exporter.doc.layers) # primary
        self.assertTrue("SISRUA_Vias_Locais_Residenciais" in exporter.doc.layers) # residential
        
        print("DXF String Header content verified.")

if __name__ == "__main__":
    unittest.main()
