"""Compatibility package for legacy imports.

The canonical modules live under backend.application / backend.shared.
"""

from backend.services import executor as executor  # noqa: F401
from backend.services import ai as ai  # noqa: F401
from backend.services import geocode as geocode  # noqa: F401
from backend.services import geojson as geojson  # noqa: F401
from backend.services import health as health  # noqa: F401
from backend.services import jobs as jobs  # noqa: F401
from backend.services import projects as projects  # noqa: F401
from backend.services import webhooks as webhooks  # noqa: F401
