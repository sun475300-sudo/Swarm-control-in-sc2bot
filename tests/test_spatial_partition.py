# -*- coding: utf-8 -*-
"""
spatial_partition 단위 테스트

standalone 모듈. SpatialGrid, DynamicSpatialPartition, build_unit_grid 검증.

주의: 기존 tests/test_spatial_query_optimizer.py는 sc2 미설치 시
     전체 스킵되므로 이 파일은 그와 독립적으로 동작한다.
"""

import importlib.util
import math
import sys
from pathlib import Path

import pytest

BOT_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"


@pytest.fixture(scope="module")
def sp_mod():
    path = BOT_ROOT / "utils" / "spatial_partition.py"
    spec = importlib.util.spec_from_file_location("wzc_spatial_partition", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["wzc_spatial_partition"] = module
    spec.loader.exec_module(module)
    return module


class TestSpatialGridBasic:
    def test_empty(self, sp_mod):
        g = sp_mod.SpatialGrid()
        assert len(g) == 0
        assert bool(g) is False

    def test_insert_increments_size(self, sp_mod):
        g = sp_mod.SpatialGrid()
        g.insert((5, 5), "a")
        g.insert((10, 10), "b")
        assert len(g) == 2
        assert bool(g) is True

    def test_clear(self, sp_mod):
        g = sp_mod.SpatialGrid()
        g.insert((5, 5), "a")
        g.clear()
        assert len(g) == 0

    def test_remove_found(self, sp_mod):
        g = sp_mod.SpatialGrid()
        g.insert((5, 5), "a")
        assert g.remove("a") is True
        assert len(g) == 0

    def test_remove_not_found(self, sp_mod):
        g = sp_mod.SpatialGrid()
        assert g.remove("not_present") is False

    def test_update_moves_point(self, sp_mod):
        g = sp_mod.SpatialGrid()
        g.insert((5, 5), "a")
        g.update((50, 50), "a")
        assert len(g) == 1
        # Query old location — should not find
        old = g.query_radius((5, 5), radius=2.0)
        assert not old
        # Query new location — should find
        new = g.query_radius((50, 50), radius=2.0)
        assert len(new) == 1

    def test_zero_cell_size_clamped(self, sp_mod):
        # Should not raise ZeroDivisionError
        g = sp_mod.SpatialGrid(cell_size=0.0)
        assert g.cell_size > 0.0
        g.insert((1, 1), "a")
        assert len(g) == 1


class TestSpatialGridQueries:
    def test_query_radius_basic(self, sp_mod):
        g = sp_mod.SpatialGrid(cell_size=5.0, map_size=(100, 100))
        g.insert((0, 0), "a")
        g.insert((3, 0), "b")
        g.insert((20, 0), "c")
        results = g.query_radius((0, 0), radius=5.0)
        found = {r[1] for r in results}
        assert found == {"a", "b"}

    def test_query_radius_exclude(self, sp_mod):
        g = sp_mod.SpatialGrid()
        g.insert((0, 0), "a")
        g.insert((1, 0), "b")
        results = g.query_radius((0, 0), radius=5.0, exclude_data="a")
        found = {r[1] for r in results}
        assert found == {"b"}

    def test_nearest_neighbor(self, sp_mod):
        g = sp_mod.SpatialGrid()
        g.insert((0, 0), "a")
        g.insert((5, 0), "b")
        g.insert((100, 100), "far")
        p, data, dist = g.nearest_neighbor((1, 0))
        assert data == "a"

    def test_nearest_neighbor_exclude(self, sp_mod):
        g = sp_mod.SpatialGrid()
        g.insert((0, 0), "a")
        g.insert((5, 0), "b")
        p, data, dist = g.nearest_neighbor((1, 0), exclude_data="a")
        assert data == "b"

    def test_nearest_neighbor_empty(self, sp_mod):
        g = sp_mod.SpatialGrid()
        assert g.nearest_neighbor((0, 0)) is None

    def test_k_nearest_neighbors(self, sp_mod):
        g = sp_mod.SpatialGrid()
        for x in range(10):
            g.insert((x, 0), f"p{x}")
        results = g.k_nearest_neighbors((0, 0), k=3)
        assert len(results) == 3
        distances = [r[2] for r in results]
        assert distances == sorted(distances)
        found = {r[1] for r in results}
        assert found == {"p0", "p1", "p2"}

    def test_k_larger_than_size_returns_all(self, sp_mod):
        g = sp_mod.SpatialGrid()
        g.insert((0, 0), "a")
        g.insert((1, 1), "b")
        results = g.k_nearest_neighbors((0, 0), k=10)
        assert len(results) == 2

    def test_cell_contents(self, sp_mod):
        g = sp_mod.SpatialGrid(cell_size=5.0)
        g.insert((2, 2), "a")
        cell = g._get_cell(2, 2)
        contents = g.get_cell_contents(cell)
        assert any(d == "a" for _, d in contents)

    def test_neighbors_in_cell(self, sp_mod):
        g = sp_mod.SpatialGrid(cell_size=5.0)
        g.insert((2, 2), "a")
        g.insert((3, 3), "b")
        g.insert((100, 100), "far")
        neighbors = g.get_neighbors_in_cell((2, 2))
        found = {d for _, d in neighbors}
        # "a" and "b" share cell (2//5=0); "far" is in a different cell
        assert "a" in found and "b" in found
        assert "far" not in found


class TestDynamicSpatialPartition:
    def test_sparse_uses_brute_force(self, sp_mod):
        dsp = sp_mod.DynamicSpatialPartition(density_threshold=10)
        pts = [((0, 0), "a"), ((1, 0), "b")]
        dsp.build(pts)
        assert dsp.grid is None
        results = dsp.query_radius((0, 0), radius=5.0)
        found = {r[1] for r in results}
        assert found == {"a", "b"}

    def test_dense_uses_grid(self, sp_mod):
        dsp = sp_mod.DynamicSpatialPartition(density_threshold=5)
        pts = [((x, 0), f"p{x}") for x in range(20)]
        dsp.build(pts)
        assert dsp.grid is not None
        results = dsp.query_radius((0, 0), radius=5.0)
        found = {r[1] for r in results}
        # Should find p0..p5 (distances 0..5)
        assert {"p0", "p1", "p2", "p3", "p4", "p5"} <= found

    def test_nearest_sparse(self, sp_mod):
        dsp = sp_mod.DynamicSpatialPartition(density_threshold=100)
        pts = [((0, 0), "a"), ((100, 100), "far")]
        dsp.build(pts)
        assert dsp.grid is None
        p, data, dist = dsp.nearest_neighbor((1, 1))
        assert data == "a"

    def test_nearest_sparse_exclude(self, sp_mod):
        dsp = sp_mod.DynamicSpatialPartition(density_threshold=100)
        pts = [((0, 0), "a"), ((10, 0), "b")]
        dsp.build(pts)
        p, data, dist = dsp.nearest_neighbor((1, 0), exclude_data="a")
        assert data == "b"

    def test_nearest_dense(self, sp_mod):
        dsp = sp_mod.DynamicSpatialPartition(density_threshold=2)
        pts = [((x, 0), f"p{x}") for x in range(5)]
        dsp.build(pts)
        p, data, dist = dsp.nearest_neighbor((0.1, 0))
        assert data == "p0"


class TestBuildUnitGrid:
    def test_build_from_units(self, sp_mod):
        class Pos:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class Unit:
            def __init__(self, x, y, tag):
                self.position = Pos(x, y)
                self.tag = tag

        units = [Unit(0, 0, 1), Unit(3, 4, 2), Unit(50, 50, 3)]
        g = sp_mod.build_unit_grid(units, cell_size=5.0)
        assert len(g) == 3
        results = g.query_radius((0, 0), radius=6.0)
        found = {r[1].tag for r in results}
        assert found == {1, 2}

    def test_build_empty_units(self, sp_mod):
        g = sp_mod.build_unit_grid([], cell_size=5.0)
        assert len(g) == 0


class TestDistance:
    def test_euclidean(self, sp_mod):
        assert sp_mod.SpatialGrid._distance((0, 0), (3, 4)) == pytest.approx(5.0)
