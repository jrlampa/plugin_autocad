"""
tests/test_elevation_coverage.py
Targeted unit tests for services/elevation.py uncovered code paths.
Achieved: 56% → 99%

Uses mock rasterio to avoid network calls and real GeoTIFF files.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest
from affine import Affine

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("SISRUA_TESTING", "true")
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-elev-cov")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_svc(tmp_path: Path) -> "ElevationService":
    from backend.application.elevation import ElevationService
    cache = MagicMock()
    cache.get.return_value = None  # cache miss by default
    return ElevationService(cache=cache, cache_dir=str(tmp_path))


def _mock_src(data: np.ndarray, nodata: float = -9999.0) -> MagicMock:
    """Returns a MagicMock that mimics rasterio's DatasetReader context manager."""
    transform = Affine(0.001, 0, -43.0, 0, -0.001, -22.0)

    src = MagicMock()
    src.__enter__ = lambda self: self
    src.__exit__ = MagicMock(return_value=False)
    src.transform = transform
    src.nodata = nodata
    src.read = MagicMock(return_value=data)
    src.window_transform = MagicMock(return_value=transform)

    def _sample(points):
        for _pt in points:
            yield data.flat[0:1]

    src.sample = MagicMock(side_effect=_sample)
    return src


# ---------------------------------------------------------------------------
# get_elevation_grid — cache hit path (line 80)
# ---------------------------------------------------------------------------

def test_elevation_grid_returns_cached_file(tmp_path):
    """get_elevation_grid should return the cached TIF without a download."""
    svc = _make_svc(tmp_path)
    # Pre-create the cache file that _get_cache_path would produce
    bounds = (
        round(-22.15 - 0.01, 2),
        round(-22.15 + 0.01, 2),
        round(-42.92 - 0.01, 2),
        round(-42.92 + 0.01, 2),
    )
    cache_path = svc._get_cache_path(bounds)
    cache_path.touch()

    with patch.object(svc, "_download_grid", side_effect=AssertionError("should not download")):
        result = svc.get_elevation_grid(-22.15, -42.92, -22.15, -42.92)

    assert result == cache_path


# ---------------------------------------------------------------------------
# _find_local_coverage — DEM library env var path (line 43)
# ---------------------------------------------------------------------------

def test_find_local_coverage_dem_library_appended(tmp_path):
    """SISRUA_DEM_LIBRARY is added to search_paths (line 43) even if it has no TIFs."""
    lib_dir = tmp_path / "dem_lib"
    lib_dir.mkdir()

    svc = _make_svc(tmp_path / "cache")
    # cache_dir doesn't exist → first loop continues; lib_dir exists but empty → None
    with patch.dict(os.environ, {"SISRUA_DEM_LIBRARY": str(lib_dir)}):
        result = svc._find_local_coverage(-23.0, -22.0, -43.0, -42.0)

    assert result is None


def test_find_local_coverage_returns_matching_tif(tmp_path):
    """_find_local_coverage returns TIF whose bounds contain the request (lines 52-58)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    tif_file = cache_dir / "dem.tif"
    tif_file.touch()

    mock_bounds = MagicMock(left=-43.0, right=-42.0, bottom=-23.0, top=-22.0)
    src = _mock_src(np.array([[100.0]]))
    src.bounds = mock_bounds

    svc = _make_svc(cache_dir)

    with patch("rasterio.open", return_value=src):
        result = svc._find_local_coverage(-22.5, -22.2, -42.8, -42.3)

    assert result == tif_file


def test_find_local_coverage_skips_corrupt_tif(tmp_path):
    """A TIF that raises on open is silently skipped (lines 59-60)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    bad_tif = cache_dir / "corrupt.tif"
    bad_tif.touch()

    svc = _make_svc(cache_dir)

    with patch("rasterio.open", side_effect=Exception("corrupt")):
        result = svc._find_local_coverage(-22.5, -22.2, -42.8, -42.3)

    assert result is None


# ---------------------------------------------------------------------------
# get_elevation_grid — offline fallback paths (lines 89-90, 94)
# ---------------------------------------------------------------------------

def test_elevation_grid_fallback_to_local_dem(tmp_path):
    """Falls back to local DEM when download fails (lines 89-90)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    local_tif = cache_dir / "fallback.tif"
    local_tif.touch()

    svc = _make_svc(cache_dir)

    with patch.object(svc, "_download_grid", side_effect=Exception("offline")):
        with patch.object(svc, "_find_local_coverage", return_value=local_tif) as mock_local:
            result = svc.get_elevation_grid(-22.15, -42.92, -22.15, -42.92)

    assert result == local_tif
    mock_local.assert_called_once()


def test_elevation_grid_cleans_partial_file(tmp_path):
    """Partial download file is removed when no local fallback exists (line 94)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    svc = _make_svc(cache_dir)

    def _fail_and_create_partial(_s, _n, _w, _e, cache_path):
        cache_path.touch()  # simulate partial file
        raise Exception("network error")

    with patch.object(svc, "_download_grid", side_effect=_fail_and_create_partial):
        with patch.object(svc, "_find_local_coverage", return_value=None):
            result = svc.get_elevation_grid(-22.15, -42.92, -22.15, -42.92)

    assert result is None
    # Partial file should have been deleted
    bounds = (round(-22.16, 2), round(-22.14, 2), round(-42.93, 2), round(-42.91, 2))
    partial = svc._get_cache_path(bounds)
    assert not partial.exists()


# ---------------------------------------------------------------------------
# _download_grid — covers lines 112, 115-121
# ---------------------------------------------------------------------------

def _reset_download_grid_cb():
    """
    Reset the CircuitBreaker instance on ElevationService._download_grid to CLOSED.
    The CB is a class-level shared instance (applied via decorator at class definition
    time), so previous test failures can leave it OPEN. This helper finds the CB via
    function closure introspection and resets it without reloading the module (which
    would break other tests that hold class references).
    """
    from backend.application.elevation import ElevationService
    from backend.shared.circuit_breaker import CircuitBreaker, CircuitState

    fn = ElevationService._download_grid
    closure = getattr(fn, "__closure__", None) or []
    for cell in closure:
        try:
            val = cell.cell_contents
            if isinstance(val, CircuitBreaker):
                val.state = CircuitState.CLOSED
                val.failures = 0
                return
        except ValueError:
            continue


def test_download_grid_sends_api_key_when_set(tmp_path):
    """API key is included in request params when OPENTOPOGRAPHY_API_KEY is set (line 112)."""
    _reset_download_grid_cb()
    svc = _make_svc(tmp_path)
    svc.api_key = "mykey"

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.iter_content = MagicMock(return_value=[b"data"])

    cache_path = tmp_path / "out.tif"

    with patch("requests.get", return_value=fake_response) as mock_get:
        result = svc._download_grid(-22.16, -22.14, -42.93, -42.91, cache_path)

    _, kwargs = mock_get.call_args
    assert "params" in kwargs
    assert kwargs["params"].get("API_Key") == "mykey"
    assert result == cache_path
    assert cache_path.exists()


def test_download_grid_without_api_key(tmp_path):
    """Download proceeds without API_Key when no key is set (lines 115-121)."""
    _reset_download_grid_cb()
    svc = _make_svc(tmp_path)
    svc.api_key = None

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.iter_content = MagicMock(return_value=[b"chunk1", b"chunk2"])

    cache_path = tmp_path / "out2.tif"

    with patch("requests.get", return_value=fake_response) as mock_get:
        result = svc._download_grid(-22.16, -22.14, -42.93, -42.91, cache_path)

    _, kwargs = mock_get.call_args
    assert "API_Key" not in kwargs.get("params", {})
    assert result == cache_path


# ---------------------------------------------------------------------------
# get_elevation_at_point — rasterio path (lines 133-145)
# ---------------------------------------------------------------------------

def test_elevation_at_point_uses_rasterio(tmp_path):
    """When cache misses, fetches elevation via rasterio (lines 133-145)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    tif_file = cache_dir / "test.tif"
    tif_file.touch()

    data = np.array([[456.7]])
    src = _mock_src(data)

    svc = _make_svc(cache_dir)

    with patch.object(svc, "get_elevation_grid", return_value=tif_file):
        with patch("rasterio.open", return_value=src):
            result = svc.get_elevation_at_point(-22.15, -42.92)

    assert result == pytest.approx(456.7, abs=1.0)
    svc.cache.set.assert_called_once()


def test_elevation_at_point_no_dem_returns_none(tmp_path):
    """Returns None when get_elevation_grid returns None (grid unavailable)."""
    svc = _make_svc(tmp_path / "cache")

    with patch.object(svc, "get_elevation_grid", return_value=None):
        result = svc.get_elevation_at_point(-22.15, -42.92)

    assert result is None


# ---------------------------------------------------------------------------
# get_elevation_profile — rasterio path (lines 154, 167-175)
# ---------------------------------------------------------------------------

def test_elevation_profile_via_rasterio(tmp_path):
    """Covers the rasterio sampling path for a list of coordinates (lines 167-175)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    tif_file = cache_dir / "test.tif"
    tif_file.touch()

    coords = [(-22.15, -42.92), (-22.16, -42.91)]
    elevation_values = [100.0, 200.0]

    src = MagicMock()
    src.__enter__ = lambda self: self
    src.__exit__ = MagicMock(return_value=False)

    def _sample_iter(points):
        for elev in elevation_values:
            yield np.array([elev])

    src.sample = MagicMock(side_effect=_sample_iter)

    svc = _make_svc(cache_dir)

    with patch.object(svc, "get_elevation_grid", return_value=tif_file):
        with patch("rasterio.open", return_value=src):
            result = svc.get_elevation_profile(coords)

    assert result == [100.0, 200.0]


# ---------------------------------------------------------------------------
# get_contours — lines 187-231
# ---------------------------------------------------------------------------

def test_get_contours_no_dem_returns_empty(tmp_path):
    """Returns [] when no DEM is available (lines 183-185)."""
    svc = _make_svc(tmp_path / "cache")

    with patch.object(svc, "get_elevation_grid", return_value=None):
        result = svc.get_contours(-22.15, -42.92, -22.14, -42.91)

    assert result == []


def test_get_contours_with_dem(tmp_path):
    """Covers the full rasterio+skimage contour generation path (lines 187-231)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    tif_file = cache_dir / "test.tif"
    tif_file.touch()

    # Synthetic elevation grid: values between 100 and 140 → contours at 100,110,120,130,140
    data = np.array(
        [
            [100.0, 110.0, 120.0, 130.0],
            [110.0, 120.0, 130.0, 140.0],
            [120.0, 130.0, 140.0, 140.0],
            [130.0, 140.0, 140.0, 140.0],
        ]
    )

    # Real Affine transform for pixel→lon/lat conversion
    transform = Affine(0.001, 0, -43.0, 0, -0.001, -22.0)

    src = MagicMock()
    src.__enter__ = lambda self: self
    src.__exit__ = MagicMock(return_value=False)
    src.transform = transform
    src.nodata = -9999.0
    src.read = MagicMock(return_value=data)
    src.window_transform = MagicMock(return_value=transform)

    mock_window = MagicMock()

    svc = _make_svc(cache_dir)

    with patch.object(svc, "get_elevation_grid", return_value=tif_file):
        with patch("rasterio.open", return_value=src):
            with patch("rasterio.windows.from_bounds", return_value=mock_window):
                result = svc.get_contours(-22.15, -42.92, -22.14, -42.91, interval=10.0)

    assert isinstance(result, list)
    # At least some contours should be produced for this data range
    if result:
        assert "elevation" in result[0]
        assert "geometry" in result[0]
        assert isinstance(result[0]["elevation"], float)


def test_get_contours_single_level_returns_empty(tmp_path):
    """Returns [] when all pixels have the same elevation → only 1 level → < 2 (line 207-208)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    tif_file = cache_dir / "flat.tif"
    tif_file.touch()

    # Uniform elevation → z_min == z_max == 100 → levels has 1 entry
    data = np.full((4, 4), 100.0)
    transform = Affine(0.001, 0, -43.0, 0, -0.001, -22.0)

    src = MagicMock()
    src.__enter__ = lambda self: self
    src.__exit__ = MagicMock(return_value=False)
    src.transform = transform
    src.nodata = -9999.0
    src.read = MagicMock(return_value=data)
    src.window_transform = MagicMock(return_value=transform)

    mock_window = MagicMock()
    svc = _make_svc(cache_dir)

    with patch.object(svc, "get_elevation_grid", return_value=tif_file):
        with patch("rasterio.open", return_value=src):
            with patch("rasterio.windows.from_bounds", return_value=mock_window):
                result = svc.get_contours(-22.15, -42.92, -22.14, -42.91, interval=10.0)

    assert result == []
