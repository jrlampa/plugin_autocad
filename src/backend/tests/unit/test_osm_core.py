import json

import pytest
from fastapi import HTTPException

from backend.domain import osm as osm_mod


class DictCache:
    def __init__(self):
        self._d = {}

    def get(self, key: str):
        return self._d.get(key)

    def set(self, key: str, value, ttl=None):
        self._d[key] = value


class DummyElevation:
    def get_elevation_profile(self, latlon_query):
        return [100.0 for _ in latlon_query]

    def get_contours(self, *args, **kwargs):
        return []


class TestOsmCore:
    def test_prepare_osm_compute_invalid_coordinates(self):
        with pytest.raises(HTTPException) as ex:
            osm_mod.prepare_osm_compute(1000, 0, 10, cache_service=DictCache(), elevation_service=DummyElevation())
        assert ex.value.status_code == 400

    def test_prepare_osm_compute_radius_must_be_positive(self):
        with pytest.raises(HTTPException) as ex:
            osm_mod.prepare_osm_compute(-23.55, -46.63, 0, cache_service=DictCache(), elevation_service=DummyElevation())
        assert ex.value.status_code == 400

    def test_prepare_osm_compute_radius_too_large(self):
        with pytest.raises(HTTPException) as ex:
            osm_mod.prepare_osm_compute(-23.55, -46.63, osm_mod.MAX_RADIUS_M + 1, cache_service=DictCache(), elevation_service=DummyElevation())
        assert ex.value.status_code == 400

    def test_prepare_osm_compute_cache_hit(self, mocker):
        cache = DictCache()
        key = osm_mod.cache_key(["prepare_osm", f"{-23.55:.6f}", f"{-46.63:.6f}", str(int(100))])
        cache.set(key, {"crs_out": "EPSG:31983", "features": [], "cache_hit": False})

        out = osm_mod.prepare_osm_compute(-23.55, -46.63, 100, cache_service=cache, elevation_service=DummyElevation())
        assert out["cache_hit"] is True

    def test_prepare_osm_compute_happy_path_minimal(self, mocker):
        cache = DictCache()
        elev = DummyElevation()

        # Stub Overpass fetch + parsing
        mocker.patch.object(osm_mod.OsmClient, "fetch_overpass_data", return_value={"elements": []})

        class DummyLine:
            def __init__(self, coords):
                self.coords = coords

        class DummyGeom:
            geom_type = "LineString"

            def __init__(self, coords):
                self.coords = coords

        class EdgeRow:
            def __init__(self):
                self.geometry = DummyGeom([(1.0, 2.0), (3.0, 4.0)])
                self.highway = ["residential"]
                self.name = "Rua Teste"

            def _asdict(self):
                return {"highway": "residential", "name": "Rua Teste"}

        class NodeGeom:
            geom_type = "Point"

            def __init__(self, x, y):
                self.x = x
                self.y = y

        class NodeRow:
            def __init__(self):
                self.geometry = NodeGeom(10.0, 20.0)

            def _asdict(self):
                return {"amenity": "bench", "name": "Banco"}

        mocker.patch.object(osm_mod.OsmParser, "parse_to_features", return_value=([NodeRow()], [EdgeRow()]))

        # Make to_linestrings deterministic (avoid shapely dependency)
        mocker.patch.object(osm_mod, "to_linestrings", return_value=[DummyLine([(1.0, 2.0), (3.0, 4.0)])])

        # Topology + precision hardening are expensive: stub to no-op but keep signature injection
        healer = mocker.Mock()
        healer.heal_network.side_effect = lambda feats: feats
        healer.get_integrity_signature.return_value = "sig"
        mocker.patch.object(osm_mod, "TopologyHealer", return_value=healer)

        mocker.patch.object(osm_mod, "get_bounding_offset", return_value=(0.0, 0.0))
        mocker.patch.object(osm_mod, "apply_local_offset", side_effect=lambda coords, ox, oy: coords)
        mocker.patch.object(osm_mod, "snap_to_edge", side_effect=lambda coords: coords)

        # clean_geometry to no-op
        mocker.patch("backend.shared.utils.clean_geometry", side_effect=lambda feats: feats)

        # Transformers: only used for elevation injection/contours; provide minimal
        tf = mocker.Mock()
        tf.itransform.side_effect = lambda pts: iter(pts)
        mocker.patch("pyproj.Transformer.from_crs", return_value=tf)

        check_calls = {"n": 0}

        def check_cancel():
            check_calls["n"] += 1

        out = osm_mod.prepare_osm_compute(
            -23.55,
            -46.63,
            100,
            cache_service=cache,
            elevation_service=elev,
            check_cancel=check_cancel,
        )

        assert out["crs_out"].startswith("EPSG:")
        assert out.get("cache_hit") is not True
        assert isinstance(out["features"], list)
        assert len(out["features"]) >= 1
        assert check_calls["n"] >= 1

        # Ensure signature injected
        for f in out["features"]:
            props = f.get("original_geojson_properties") or {}
            assert props.get("sys_sisrua_integrity") == "sig"
            assert props.get("sys_sisrua_origin") == [0.0, 0.0]

    def test_prepare_osm_compute_skips_non_point_nodes(self, mocker):
        cache = DictCache()
        elev = DummyElevation()

        mocker.patch.object(osm_mod.OsmClient, "fetch_overpass_data", return_value={"elements": []})

        class DummyLine:
            def __init__(self, coords):
                self.coords = coords

        class DummyGeom:
            geom_type = "LineString"

            def __init__(self, coords):
                self.coords = coords

        class EdgeRow:
            def __init__(self):
                self.geometry = DummyGeom([(1.0, 2.0), (3.0, 4.0)])
                self.highway = "residential"
                self.name = "Rua Teste"

            def _asdict(self):
                return {"highway": "residential", "name": "Rua Teste"}

        class NonPointGeom:
            geom_type = "LineString"

        class NodeRowBad:
            def __init__(self):
                self.geometry = NonPointGeom()

            def _asdict(self):
                return {"amenity": "bench", "name": "Banco"}

        mocker.patch.object(osm_mod.OsmParser, "parse_to_features", return_value=([NodeRowBad()], [EdgeRow()]))
        mocker.patch.object(osm_mod, "to_linestrings", return_value=[DummyLine([(1.0, 2.0), (3.0, 4.0)])])

        healer = mocker.Mock()
        healer.heal_network.side_effect = lambda feats: feats
        healer.get_integrity_signature.return_value = "sig"
        mocker.patch.object(osm_mod, "TopologyHealer", return_value=healer)

        mocker.patch.object(osm_mod, "get_bounding_offset", return_value=(0.0, 0.0))
        mocker.patch.object(osm_mod, "apply_local_offset", side_effect=lambda coords, ox, oy: coords)
        mocker.patch.object(osm_mod, "snap_to_edge", side_effect=lambda coords: coords)
        mocker.patch("backend.shared.utils.clean_geometry", side_effect=lambda feats: feats)

        tf = mocker.Mock()
        tf.itransform.side_effect = lambda pts: iter(pts)
        mocker.patch("pyproj.Transformer.from_crs", return_value=tf)

        out = osm_mod.prepare_osm_compute(-23.55, -46.63, 100, cache_service=cache, elevation_service=elev)

        assert isinstance(out["features"], list)

    def test_prepare_osm_compute_node_loop_cancellation_hook(self, mocker):
        cache = DictCache()
        elev = DummyElevation()

        mocker.patch.object(osm_mod.OsmClient, "fetch_overpass_data", return_value={"elements": []})

        class NodeGeom:
            geom_type = "Point"

            def __init__(self, x, y):
                self.x = x
                self.y = y

        class NodeRow:
            def __init__(self):
                self.geometry = NodeGeom(10.0, 20.0)

            def _asdict(self):
                return {"name": "N1"}

        mocker.patch.object(osm_mod.OsmParser, "parse_to_features", return_value=([NodeRow()], []))

        healer = mocker.Mock()
        healer.heal_network.side_effect = lambda feats: feats
        healer.get_integrity_signature.return_value = "sig"
        mocker.patch.object(osm_mod, "TopologyHealer", return_value=healer)

        mocker.patch.object(osm_mod, "get_bounding_offset", return_value=(0.0, 0.0))
        mocker.patch.object(osm_mod, "apply_local_offset", side_effect=lambda coords, ox, oy: coords)
        mocker.patch.object(osm_mod, "snap_to_edge", side_effect=lambda coords: coords)
        mocker.patch("backend.shared.utils.clean_geometry", side_effect=lambda feats: feats)

        tf = mocker.Mock()
        tf.itransform.side_effect = lambda pts: iter(pts)
        mocker.patch("pyproj.Transformer.from_crs", return_value=tf)

        check_calls = {"n": 0}

        def check_cancel():
            check_calls["n"] += 1

        out = osm_mod.prepare_osm_compute(
            -23.55,
            -46.63,
            100,
            cache_service=cache,
            elevation_service=elev,
            check_cancel=check_cancel,
        )

        assert isinstance(out["features"], list)
        assert check_calls["n"] >= 1
