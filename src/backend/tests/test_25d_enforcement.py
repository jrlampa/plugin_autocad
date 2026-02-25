
import pytest
from backend.domain.dto import CadFeature

def test_cad_feature_25d_consistency():
    """
    Verifica se o modelo CadFeature aceita coordenadas 2D e possui o campo elevation.
    """
    feature = CadFeature(
        feature_type="Polyline",
        layer="Roads",
        coords_xy=[[0.0, 0.0], [10.0, 10.0]],
        elevation=15.0
    )
    
    assert len(feature.coords_xy[0]) == 2
    assert feature.elevation == 15.0

def test_cad_feature_point_25d():
    """
    Verifica se o ponto de inserção segue o padrão 2.5D.
    """
    feature = CadFeature(
        feature_type="Point",
        layer="Utility",
        insertion_point_xy=[50.0, 50.0],
        elevation=2.5,
        block_name="POLE"
    )
    
    assert len(feature.insertion_point_xy) == 2
    assert feature.elevation == 2.5
