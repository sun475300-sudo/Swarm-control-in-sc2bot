# -*- coding: utf-8 -*-
"""
utils/kd_tree.py 단위 테스트.

KDTree 의 build / nearest_neighbor / range_query / k_nearest_neighbors
를 brute-force 결과와 비교 검증한다.
"""

import math
import os
import random
import sys
import unittest

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.kd_tree import KDTree


def _brute_nearest(query, points, exclude=None):
    best = None
    best_d = float("inf")
    for (x, y), data in points:
        if data == exclude:
            continue
        d = math.hypot(x - query[0], y - query[1])
        if d < best_d:
            best = ((x, y), data, d)
            best_d = d
    return best


def _brute_range(center, points, radius):
    results = []
    for (x, y), data in points:
        d = math.hypot(x - center[0], y - center[1])
        if d <= radius:
            results.append(((x, y), data, d))
    return sorted(results, key=lambda r: r[2])


class TestKDTreeBasic(unittest.TestCase):
    def test_empty_tree_returns_none(self):
        tree = KDTree()
        self.assertIsNone(tree.nearest_neighbor((0, 0)))
        self.assertEqual(tree.range_query((0, 0), 100.0), [])
        self.assertEqual(tree.k_nearest_neighbors((0, 0), 5), [])
        self.assertFalse(bool(tree))
        self.assertEqual(len(tree), 0)

    def test_single_point(self):
        tree = KDTree([((5, 5), "unit1")])
        result = tree.nearest_neighbor((0, 0))
        self.assertIsNotNone(result)
        self.assertEqual(result[0], (5, 5))
        self.assertEqual(result[1], "unit1")
        self.assertAlmostEqual(result[2], math.hypot(5, 5))
        self.assertTrue(bool(tree))
        self.assertEqual(len(tree), 1)

    def test_exclude_self(self):
        tree = KDTree([((0, 0), "me"), ((10, 0), "other")])
        result = tree.nearest_neighbor((0, 0), exclude_data="me")
        self.assertEqual(result[1], "other")


class TestKDTreeNearestVsBrute(unittest.TestCase):
    """무작위 점 집합으로 KDTree 와 brute-force 의 정확도 비교."""

    def setUp(self):
        random.seed(42)
        self.points = [
            ((random.uniform(0, 100), random.uniform(0, 100)), f"u{i}")
            for i in range(50)
        ]
        self.tree = KDTree(self.points)

    def test_nearest_matches_brute(self):
        for query in [(0, 0), (50, 50), (100, 100), (25, 75)]:
            tree_result = self.tree.nearest_neighbor(query)
            brute_result = _brute_nearest(query, self.points)
            self.assertAlmostEqual(tree_result[2], brute_result[2], places=6)

    def test_range_query_matches_brute(self):
        for center, radius in [((50, 50), 10), ((25, 25), 30), ((0, 0), 1000)]:
            tree_result = sorted(
                self.tree.range_query(center, radius), key=lambda r: r[2]
            )
            brute_result = _brute_range(center, self.points, radius)
            self.assertEqual(len(tree_result), len(brute_result))
            tree_dists = [r[2] for r in tree_result]
            brute_dists = [r[2] for r in brute_result]
            for td, bd in zip(tree_dists, brute_dists):
                self.assertAlmostEqual(td, bd, places=6)

    def test_knn_returns_k_or_fewer(self):
        result = self.tree.k_nearest_neighbors((50, 50), k=5)
        self.assertLessEqual(len(result), 5)
        # 결과는 거리 오름차순
        dists = [r[2] for r in result]
        self.assertEqual(dists, sorted(dists))

    def test_knn_k_zero_returns_empty(self):
        self.assertEqual(self.tree.k_nearest_neighbors((0, 0), k=0), [])

    def test_knn_k_larger_than_tree(self):
        result = self.tree.k_nearest_neighbors((50, 50), k=1000)
        # 트리 크기 만큼만 반환
        self.assertEqual(len(result), len(self.points))


class TestRangeQueryEdge(unittest.TestCase):
    def test_radius_zero_returns_exact_match(self):
        tree = KDTree([((5, 5), "match"), ((10, 10), "other")])
        result = tree.range_query((5, 5), 0.0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "match")

    def test_radius_negative_returns_empty(self):
        tree = KDTree([((5, 5), "u")])
        result = tree.range_query((5, 5), -1.0)
        # 음수 반경: 한 점도 dist <= -1 일 수 없음
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
