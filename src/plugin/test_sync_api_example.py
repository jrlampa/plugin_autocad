import pytest
from pydantic import ValidationError

# Importa o módulo e a função do seu backend
from sync_api_example import (
    ProjectSyncPayload, 
    CadFeatureSyncDto, 
    payload_to_geodataframe, 
    HAS_GEOPANDAS
)

try:
    import geopandas as gpd
    from shapely.geometry import Point, LineString
except ImportError:
    pass

@pytest.mark.skipif(not HAS_GEOPANDAS, reason="GeoPandas e Shapely são necessários para este teste.")
def test_payload_to_geodataframe_success():
    """
    Verifica se a conversão de um payload JSON/Pydantic em GeoDataFrame 
    constrói as geometrias Shapely corretas e extrai atributos.
    """
    # 1. Arrange: Monta um payload simulando o que o C# envia
    feat_polyline = CadFeatureSyncDto(
        feature_id="uuid-1111",
        project_id="proj-99",
        feature_type="Polyline",
        coords_xy=[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]],
        layer="SISRUA_RUAS",
        original_geojson_properties={"surface": "asphalt"}
    )
    
    feat_point = CadFeatureSyncDto(
        feature_id="uuid-2222",
        project_id="proj-99",
        feature_type="Point",
        insertion_point_xy=[5.0, 5.0],
        layer="SISRUA_POSTES",
        block_name="POSTE_CONCRETO"
    )
    
    payload = ProjectSyncPayload(
        project_id="proj-99",
        project_name="Projeto Teste",
        crs_out="EPSG:31983",
        features=[feat_polyline, feat_point]
    )

    # 2. Act: Executa a função
    gdf = payload_to_geodataframe(payload)

    # 3. Assert: Valida a estrutura de dados geoespaciais
    assert isinstance(gdf, gpd.GeoDataFrame), "O retorno deve ser um GeoDataFrame."
    assert len(gdf) == 2, "As duas feições deveriam estar no GeoDataFrame."
    assert gdf.crs == "EPSG:31983", "O CRS do projeto deve ser repassado ao GDF."
    
    # Validação Geométrica (Shapely)
    assert isinstance(gdf.iloc[0].geometry, LineString), "A primeira feição deve ser convertida em LineString."
    assert isinstance(gdf.iloc[1].geometry, Point), "A segunda feição deve ser convertida em Point."
    
    # Validação de Propriedades ("Flattening")
    assert gdf.iloc[0]["layer"] == "SISRUA_RUAS"
    assert gdf.iloc[0]["osm_surface"] == "asphalt", "A propriedade aninhada original_geojson deve ser extraída com prefixo osm_."
    assert gdf.iloc[1]["block_name"] == "POSTE_CONCRETO"