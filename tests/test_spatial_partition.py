# -*- coding: utf-8 -*-
"""Tests for utils/spatial_partition.py - SpatialGrid and DynamicSpatialPartition."""

import sys
import math
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.spatial_partition import SpatialGrid, DynamicSpatialPartition


class TestSpatialGridBasics:
    def test_init(self):
        grid = SpatialGrid(cell_size=5.0, map_size=(100.0, 100.0))
        assert grid.cell_size == 5.0
        assert len(grid) == 0
        assert not bool(grid)

    def test_zero_cell_size_safe(self):
        # Should not divide-by-zero
        grid = SpatialGrid(cell_size=0.0, map_size=(100.0, 100.0))
        grid.insert((0.0, 0.0), "x")  # should not raise
        assert len(grid) == 1


class TestInsertRemove:
    def setup_method(self):
        self.grid = SpatialGrid(cell_size=5.0, map_size=(100.0, 100.0))

    def test_insert_increases_size(self):
        self.grid.insert((10.0, 10.0), "unit_1")
        assert len(self.grid) == 1
        assert bool(self.grid)

    def test_remove_decreases_size(self):
        self.grid.insert((10.0, 10.0), "u1")
        assert self.grid.remove("u1")
        assert len(self.grid) == 0

    def test_remove_missing_returns_false(self):
        assert not self.grid.remove("never_inserted")

    def test_clear_resets(self):
        self.grid.insert((0.0, 0.0), "a")
        self.grid.insert((5.0, 5.0), "b")
        self.grid.clear()
        assert len(self.grid) == 0


class TestUpdate:
    def test_update_moves_data(self):
        grid = SpatialGrid(cell_size=5.0, map_size=(100.0, 100.0))
        grid.insert((10.0, 10.0), "unit_x")
        grid.update((90.0, 90.0), "unit_x")
        # Size should still be 1
        assert len(grid) == 1


class TestQueryRadius:
    def setup_method(self):
        self.grid = SpatialGrid(cell_size=5.0, map_size=(100.0, 100.0))
        self.grid.insert((0.0, 0.0), "A")
        self.grid.insert((3.0, 0.0), "B")
        self.grid.insert((50.0, 50.0), "C")

    def test_query_includes_nearby(self):
        results = self.grid.query_radius((0.0, 0.0), 5.0)
        # query_radius returns list of (pos, data, dist)
        data_set = {d for _, d, _ in results}
        assert "A" in data_set
        assert "B" in data_set
        assert "C" not in data_set

    def test_query_large_radius_includes_all(self):
        results = self.grid.query_radius((0.0, 0.0), 200.0)
        assert len(results) == 3

    def test_query_zero_radius(self):
        results = self.grid.query_radius((0.0, 0.0), 0.0)
        data_set = {d for _, d, _ in results}
        assert "A" in data_set
        assert "C" not in data_set


class TestNearestNeighbor:
    def setup_method(self):
        self.grid = SpatialGrid(cell_size=5.0, map_size=(100.0, 100.0))
        self.grid.insert((0.0, 0.0), "origin")
        self.grid.insert((50.0, 50.0), "far")
        self.grid.insert((2.0, 0.0), "near")

    def test_nearest_neighbor(self):
        result = self.grid.nearest_neighbor((0.0, 0.0))
        assert result is not None
        _, data, _ = result
        assert data == "origin"

    def test_nearest_with_empty_grid(self):
        empty = SpatialGrid(cell_size=5.0, map_size=(100.0, 100.0))
        assert empty.nearest_neighbor((0.0, 0.0)) is None


class TestKNearestNeighbors:
    def test_k_nearest_returns_k_results(self):
        grid = SpatialGrid(cell_size=5.0, map_size=(100.0, 100.0))
        for i in range(5):
            grid.insert((float(i), 0.0), f"u{i}")

        results = grid.k_nearest_neighbors((0.0, 0.0), k=3)
        assert len(results) == 3


class TestCellOps:
    def test_get_cell_for_origin(self):
        grid = SpatialGrid(cell_size=5.0, map_size=(100.0, 100.0))
        cell = grid._get_cell(0.0, 0.0)
        assert cell == (0, 0)

    def test_get_cell_bounds_respected(self):
        grid = SpatialGrid(cell_size=5.0, map_size=(100.0, 100.0))
        # Beyond map bounds should clamp
        cell = grid._get_cell(999.0, 999.0)
        assert cell[0] < grid.grid_width
        assert cell[1] < grid.grid_height

    def test_distance_helper(self):
        assert abs(SpatialGrid._distance((0, 0), (3, 4)) - 5.0) < 1e-9


class TestDynamicPartition:
    def test_init(self):
        dp = DynamicSpatialPartition()
        assert dp is not None

    def test_build_from_empty(self):
        dp = DynamicSpatialPartition()
        dp.build([])  # should not raise

    def test_build_and_query(self):
        dp = DynamicSpatialPartition(cell_size=5.0)
        points = [((0.0, 0.0), "a"), ((10.0, 10.0), "b"), ((2.0, 2.0), "c")]
        dp.build(points)
        results = dp.query_radius((0.0, 0.0), 5.0)
        # DynamicSpatialPartition.query_radius may return 2- or 3-tuples
        data_set = {r[1] for r in results}
        assert "a" in data_set
        assert "c" in data_set
