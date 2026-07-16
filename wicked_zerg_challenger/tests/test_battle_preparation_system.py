"""Tests for BattlePreparationSystem._find_enemy_clusters.

Covers the migration from an inline centroid calculation to
utils.position_utils.get_center_position (see REMAINING_ISSUES.md Issue #5).
"""

import os
import sys

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

try:
    from sc2.position import Point2
except ImportError:
    pytest.skip("sc2 library not available", allow_module_level=True)

from battle_preparation_system import BattlePreparationSystem


class FakeUnit:
    def __init__(self, tag, x, y):
        self.tag = tag
        self.position = Point2((x, y))

    def distance_to(self, other):
        return self.position.distance_to(other.position)


def _make_system():
    return BattlePreparationSystem.__new__(BattlePreparationSystem)


class TestFindEnemyClusters:
    def test_empty_input_returns_no_clusters(self):
        system = _make_system()

        clusters = system._find_enemy_clusters([])

        assert clusters == []

    def test_single_cluster_centroid(self):
        system = _make_system()
        units = [FakeUnit(1, 0, 0), FakeUnit(2, 2, 0), FakeUnit(3, 1, 1)]

        clusters = system._find_enemy_clusters(units)

        assert len(clusters) == 1
        center, members = clusters[0]
        assert len(members) == 3
        assert center.x == pytest.approx(1.0)
        assert center.y == pytest.approx(1 / 3)

    def test_multi_cluster_splitting(self):
        system = _make_system()
        near_origin = [FakeUnit(1, 0, 0), FakeUnit(2, 1, 0)]
        far_away = [FakeUnit(3, 100, 100), FakeUnit(4, 101, 100)]
        units = near_origin + far_away

        clusters = system._find_enemy_clusters(units)

        assert len(clusters) == 2
        cluster_sizes = sorted(len(members) for _, members in clusters)
        assert cluster_sizes == [2, 2]
