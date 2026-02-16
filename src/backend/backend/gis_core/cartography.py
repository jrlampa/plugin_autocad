import math
from typing import List, Tuple
from ..models import CadFeature

class CartographyEngine:
    @staticmethod
    def generate_north_arrow(x: float, y: float, size: float = 10.0) -> List[CadFeature]:
        """Generates a stylized North Arrow as a set of Polylines and Text."""
        features = []
        # Triangle pointing up
        p1 = [x, y + size]
        p2 = [x - size/3, y]
        p3 = [x + size/3, y]
        
        features.append(CadFeature(
            feature_type="Polyline",
            layer="SISRUA_CART_NORTH",
            coords_xy=[p1, p2, p3, p1],
            name="NORTH_ARROW_BODY"
        ))
        
        features.append(CadFeature(
            feature_type="Text",
            layer="SISRUA_CART_NORTH",
            insertion_point_xy=[x, y + size + size/5],
            text_content="N",
            scale=size/3,
            name="NORTH_LABEL"
        ))
        return features

    @staticmethod
    def generate_scale_bar(x: float, y: float, length_m: float = 50.0) -> List[CadFeature]:
        """Generates a metric scale bar."""
        features = []
        h = length_m / 10
        
        # Main bar
        features.append(CadFeature(
            feature_type="Polyline",
            layer="SISRUA_CART_SCALE",
            coords_xy=[[x, y], [x + length_m, y], [x + length_m, y + h], [x, y + h], [x, y]],
            name="SCALE_BAR_OUTLINE"
        ))
        
        # Subdivisions
        divisions = [0, length_m/2, length_m]
        for d in divisions:
            features.append(CadFeature(
                feature_type="Polyline",
                layer="SISRUA_CART_SCALE",
                coords_xy=[[x + d, y], [x + d, y + h]],
                name=f"SCALE_TICK_{d}"
            ))
            features.append(CadFeature(
                feature_type="Text",
                layer="SISRUA_CART_SCALE",
                insertion_point_xy=[x + d, y - h],
                text_content=f"{int(d)}m",
                scale=h * 0.8,
                name=f"SCALE_TEXT_{d}"
            ))
            
        return features

    @staticmethod
    def generate_coordinate_grid(bounds: Tuple[float, float, float, float], step: float = 100.0) -> List[CadFeature]:
        """Generates a coordinate frame with labels."""
        min_x, min_y, max_x, max_y = bounds
        features = []
        
        # Outer Frame
        features.append(CadFeature(
            feature_type="Polyline",
            layer="SISRUA_CART_GRID",
            coords_xy=[[min_x, min_y], [max_x, min_y], [max_x, max_y], [min_x, max_y], [min_x, min_y]],
            name="GRID_FRAME"
        ))
        
        # X Ticks (Easting)
        start_x = math.ceil(min_x / step) * step
        curr_x = start_x
        while curr_x < max_x:
            features.append(CadFeature(
                feature_type="Text",
                layer="SISRUA_CART_GRID",
                insertion_point_xy=[curr_x, min_y - 5],
                text_content=f"E:{int(curr_x)}",
                scale=5.0,
                rotation=0,
                name=f"GRID_LABEL_E_{curr_x}"
            ))
            curr_x += step
            
        # Y Ticks (Northing)
        start_y = math.ceil(min_y / step) * step
        curr_y = start_y
        while curr_y < max_y:
            features.append(CadFeature(
                feature_type="Text",
                layer="SISRUA_CART_GRID",
                insertion_point_xy=[min_x - 5, curr_y],
                text_content=f"N:{int(curr_y)}",
                scale=5.0,
                rotation=1.5708, # 90 degrees in radians
                name=f"GRID_LABEL_N_{curr_y}"
            ))
            curr_y += step
            
        return features
