"""
backend/domain/osm_parser.py
Classe OsmParser — encapsula o parsing de dados Overpass para features CAD.

Wrap orientado a objetos sobre `_parse_overpass_to_features` da `gis_core.osm`,
permitindo injeção e mock nos testes de integração.
"""
from typing import Tuple, List, Any
from backend.gis_core.osm import _parse_overpass_to_features


class OsmParser:
    """
    Parser de dados brutos do Overpass API para features CAD sisRUA.

    Converte o JSON de resposta do Overpass em listas de nós e arestas
    projetados para o CRS de saída (SIRGAS 2000 UTM).
    """

    @staticmethod
    def parse_to_features(
        data: dict,
        epsg_out: int,
    ) -> Tuple[List[Any], List[Any]]:
        """
        Parseia dados Overpass e projeta as geometrias para `epsg_out`.

        Args:
            data:     JSON de resposta do Overpass API (dict com "elements").
            epsg_out: Código EPSG do CRS de saída (ex.: 31983 para UTM 23S).

        Returns:
            Tupla ``(nodes, edges)`` onde:
              - ``nodes``: lista de ``_OsmNodeRow`` (pontos de interesse)
              - ``edges``: lista de ``_OsmWayRow`` (vias/polylines)
        """
        return _parse_overpass_to_features(data, epsg_out)


__all__ = ["OsmParser"]
