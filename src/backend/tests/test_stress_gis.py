import pytest
import time
from backend.application.gis import GisService

def generate_large_kml(num_features: int = 1000) -> str:
    """Gera um arquivo KML grande para teste de estresse."""
    features = []
    for i in range(num_features):
        features.append(f"""
        <Placemark>
          <name>Feature {i}</name>
          <Point>
            <coordinates>{-45.0 + i*0.0001},{-23.0 + i*0.0001},0</coordinates>
          </Point>
        </Placemark>""")
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    {"".join(features)}
  </Document>
</kml>"""

def test_gis_processing_stress():
    """Teste de estresse: converte KML com 5000 placemarks."""
    service = GisService()
    kml_data = generate_large_kml(5000)
    
    start_time = time.time()
    result = service.process_kml(kml_data)
    duration = time.time() - start_time
    
    assert "features" in result
    assert len(result["features"]) == 5000
    assert "error" not in result
    
    print(f"\n[STRESS TEST] Processados 5000 placemarks em {duration:.4f}s")
    # Meta: < 2 segundos para 5k placemarks (processamento simples)
    assert duration < 5.0 

def test_gis_processing_invalid_kml():
    """Garante que falhas no KML são capturadas graciosamente."""
    service = GisService()
    result = service.process_kml("<invalid>xml</invalid>")
    assert "error" in result
    assert len(result["features"]) == 0
