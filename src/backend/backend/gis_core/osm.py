"""Legacy compatibility layer for `backend.gis_core.osm`.

Canonical implementation: backend.domain.osm
"""

from backend.domain.osm import *  # noqa: F401,F403

# Names starting with '_' are not imported by star-import, but legacy tests patch them.
from backend.domain.osm import _fetch_overpass_data  # noqa: F401
from backend.domain.osm import _OsmWayRow, _OsmNodeRow  # noqa: F401
from backend.domain.osm import _parse_overpass_to_features  # noqa: F401
