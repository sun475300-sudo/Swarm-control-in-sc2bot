# -*- coding: utf-8 -*-
"""
utils/spatial_partition.py SpatialGrid 단위 테스트.
"""

import math
import os
import sys
import unittest

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.spatial_partition import SpatialGrid


class TestSpatialGridBasic(unittest.TestCase):
    def test_initial_state(self):
        grid = SpatialGrid()
        self.assertEqual(grid.size, 0)
        self.assertIsNone(grid.nearest_neighbor((0, 0)))
        self.assertEqual(grid.query_radius((0, 0), 100), [])

    def test_insert_and_size(self):
        grid = SpatialGrid()
        grid.insert((5, 5), "u1")
        grid.insert((10, 10), "u2")
        self.assertEqual(grid.size, 2)

    def test_remove_existing(self):
        grid = SpatialGrid()
        grid.insert((5, 5), "u1")
        self.assertTrue(grid.remove("u1"))
        self.assertEqual(grid.size, 0)

    def test_remove_nonexistent(self):
        grid = SpatialGrid()
        self.assertFalse(grid.remove("nonexistent"))

    def test_clear(self):
        grid = SpatialGrid()
        grid.insert((5, 5), "u1")
        grid.insert((10, 10), "u2")
        grid.clear()
        self.assertEqual(grid.size, 0)
        self.assertEqual(grid.query_radius((5, 5), 100), [])


class TestSpatialGridQueries(unittest.TestCase):
    def setUp(self):
        self.grid = SpatialGrid(cell_size=5.0, map_size=(100, 100))
        # 클러스터 1: (10,10) 주변
        self.grid.insert((10, 10), "u1")
        self.grid.insert((11, 11), "u2")
        self.grid.insert((12, 12), "u3")
        # 클러스터 2: (50,50)
        self.grid.insert((50, 50), "u4")
        # 외딴 점
        self.grid.insert((90, 90), "u5")

    def test_nearest_neighbor_in_dense_area(self):
        result = self.grid.nearest_neighbor((10.5, 10.5))
        self.assertIsNotNone(result)
        self.assertEqual(result[1], "u1")

    def test_nearest_neighbor_excludes_self(self):
        result = self.grid.nearest_neighbor((10, 10), exclude_data="u1")
        # u1 제외 → u2 또는 u3 중 더 가까운 것
        self.assertIn(result[1], ("u2", "u3"))

    def test_range_query_small_radius(self):
        results = self.grid.query_radius((10, 10), 5.0)
        names = {r[1] for r in results}
        self.assertEqual(names, {"u1", "u2", "u3"})

    def test_range_query_excludes(self):
        results = self.grid.query_radius((10, 10), 5.0, exclude_data="u1")
        names = {r[1] for r in results}
        self.assertNotIn("u1", names)

    def test_range_query_isolation(self):
        results = self.grid.query_radius((50, 50), 1.0)
        names = {r[1] for r in results}
        self.assertEqual(names, {"u4"})


class TestSpatialGridUpdate(unittest.TestCase):
    def test_update_moves_position(self):
        grid = SpatialGrid(cell_size=5.0)
        grid.insert((5, 5), "u1")
        grid.update((50, 50), "u1")
        # 원래 위치엔 없어야 함
        results = grid.query_radius((5, 5), 2.0)
        self.assertEqual(results, [])
        # 새 위치엔 있어야 함
        results = grid.query_radius((50, 50), 2.0)
        self.assertEqual(len(results), 1)
        self.assertEqual(grid.size, 1)


class TestSpatialGridEdge(unittest.TestCase):
    def test_zero_cell_size_handled(self):
        # cell_size=0 이어도 최소값으로 클램프되어 div0 없음
        grid = SpatialGrid(cell_size=0)
        grid.insert((5, 5), "u1")
        self.assertEqual(grid.size, 1)

    def test_out_of_bounds_position_clamped(self):
        # 맵 밖 좌표라도 cell 은 grid bound 안으로 clamp
        grid = SpatialGrid(cell_size=5.0, map_size=(50, 50))
        # 좌표 (100, 100) 은 맵 밖이지만 _get_cell 이 clamp 함
        grid.insert((100, 100), "u_outside")
        self.assertEqual(grid.size, 1)


if __name__ == "__main__":
    unittest.main()
