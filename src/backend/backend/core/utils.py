"""Compatibility shim: re-exports backend.shared.utils."""
from backend.shared.utils import (  # noqa: F401
    cache_dir, cache_key, norm_optional_str, sanitize_jsonable,
    get_color_from_elevation, to_linestrings, project_lines_to_xy,
    estimate_width_m, get_layer_config, get_layer_name, clean_geometry,
)
