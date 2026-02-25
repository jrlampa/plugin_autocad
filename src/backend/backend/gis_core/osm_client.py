"""
backend/gis_core/osm_client.py
Re-exporta OsmClient de `backend.infrastructure.osm_client`.

Permite que testes monkeypatch/patch via `backend.gis_core.osm_client.OsmClient`
sem depender do caminho completo do módulo de infraestrutura.
"""
from backend.infrastructure.osm_client import OsmClient

__all__ = ["OsmClient"]
