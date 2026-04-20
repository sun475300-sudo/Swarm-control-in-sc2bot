# -*- coding: utf-8 -*-
"""Tests for KDTree spatial data structure."""

import sys
import math
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.kd_tree import KDTree


class TestEmptyTree:
    def test_empty_tree_size_zero(self):
        tree = KDTree()
        assert len(tree) == 0

    def test_empty_tree_falsy(self):
        tree = KDTree()
        assert not bool(tree)

    def test_nearest_neighbor_on_empty(self):
        tree = KDTree()
        assert tree.nearest_neighbor((0.0, 0.0)) is None

    def test_range_query_on_empty(self):
        tree = KDTree()
        assert tree.range_query((0.0, 0.0), 10.0) == []


class TestBuild:
    def test_build_with_single_point(self):
        tree = KDTree([((5.0, 5.0), "data1")])
        assert len(tree) == 1

    def test_build_with_multiple_points(self):
        points = [((0.0, 0.0), "a"), ((1.0, 1.0), "b"), ((2.0, 2.0), "c")]
        tree = KDTree(points)
        assert len(tree) == 3

    def test_tree_truthy_when_populated(self):
        tree = KDTree([((0.0, 0.0), "x")])
        assert bool(tree)

    def test_rebuild_replaces_points(self):
        tree = KDTree([((0.0, 0.0), "a"), ((1.0, 1.0), "b")])
        tree.build([((5.0, 5.0), "c")])
        assert len(tree) == 1


class TestNearestNeighbor:
    def setup_method(self):
        self.points = [
            ((0.0, 0.0), "origin"),
            ((10.0, 10.0), "far"),
            ((1.0, 1.0), "close"),
            ((3.0, 0.0), "right"),
        ]
        self.tree = KDTree(self.points)

    def test_query_at_origin_finds_origin(self):
        result = self.tree.nearest_neighbor((0.0, 0.0))
        assert result is not None
        point, data, dist = result
        assert data == "origin"
        assert dist == 0.0

    def test_query_near_close_finds_close(self):
        result = self.tree.nearest_neighbor((0.9, 0.9))
        assert result is not None
        _, data, _ = result
        assert data == "close"

    def test_exclude_data_skips_self(self):
        result = self.tree.nearest_neighbor((0.0, 0.0), exclude_data="origin")
        assert result is not None
        _, data, _ = result
        assert data != "origin"

    def test_nearest_returns_correct_distance(self):
        tree = KDTree([((3.0, 4.0), "pt")])
        result = tree.nearest_neighbor((0.0, 0.0))
        _, _, dist = result
        assert abs(dist - 5.0) < 1e-9  # 3-4-5 triangle


class TestRangeQuery:
    def setup_method(self):
        self.points = [
            ((0.0, 0.0), "A"),
            ((1.0, 0.0), "B"),
            ((0.0, 1.0), "C"),
            ((5.0, 5.0), "D"),
            ((10.0, 10.0), "E"),
        ]
        self.tree = KDTree(self.points)

    def test_range_includes_all_within_radius(self):
        results = self.tree.range_query((0.0, 0.0), 2.0)
        data_set = {r[1] for r in results}
        assert "A" in data_set
        assert "B" in data_set
        assert "C" in data_set
        assert "D" not in data_set
        assert "E" not in data_set

    def test_range_zero_radius_returns_exact_matches_only(self):
        results = self.tree.range_query((0.0, 0.0), 0.0)
        # Only origin should match
        assert len(results) == 1
        assert results[0][1] == "A"

    def test_large_radius_returns_all(self):
        results = self.tree.range_query((0.0, 0.0), 100.0)
        assert len(results) == 5


class TestKNearestNeighbors:
    def test_k_neighbors_basic(self):
        points = [
            ((0.0, 0.0), "a"),
            ((1.0, 0.0), "b"),
            ((2.0, 0.0), "c"),
            ((10.0, 0.0), "d"),
        ]
        tree = KDTree(points)
        results = tree.k_nearest_neighbors((0.0, 0.0), k=2)
        assert len(results) == 2
        # Two closest should be "a" and "b"
        data_set = {r[1] for r in results}
        assert "a" in data_set
        assert "b" in data_set

    def test_k_larger_than_tree(self):
        points = [((0.0, 0.0), "x"), ((1.0, 1.0), "y")]
        tree = KDTree(points)
        results = tree.k_nearest_neighbors((0.0, 0.0), k=10)
        assert len(results) == 2


class TestDistance:
    def test_zero_distance(self):
        assert KDTree._distance((0, 0), (0, 0)) == 0.0

    def test_pythagorean(self):
        assert abs(KDTree._distance((0, 0), (3, 4)) - 5.0) < 1e-9

    def test_symmetric(self):
        d1 = KDTree._distance((1, 2), (5, 7))
        d2 = KDTree._distance((5, 7), (1, 2))
        assert abs(d1 - d2) < 1e-9
