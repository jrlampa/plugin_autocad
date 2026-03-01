"""Legacy compatibility layer for `backend.services.geocode`.

Canonical implementation: backend.application.geocode
"""

from backend.application import geocode as _impl


def geocode(query):  # noqa: F401
    return _impl.geocode(query)


def _nominatim_geocode(query):  # noqa: F401
    return _impl._nominatim_geocode(query)


def _sanitize_query(text):  # noqa: F401
    return _impl._sanitize_query(text)


def _try_parse_latlon(text):  # noqa: F401
    return _impl._try_parse_latlon(text)


def _try_parse_utm(text):  # noqa: F401
    return _impl._try_parse_utm(text)
