# -*- coding: utf-8 -*-
"""
Unit tests -- BattlePreparationSystem._find_enemy_clusters

Locks in cluster-center computation after migrating the inline centroid
math to utils.position_utils.get_center_position (Issue #5 cleanup).
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from battle_preparation_system import BattlePreparationSystem
    from sc2.position import Point2
except ImportError:
    pytest.skip(
        "battle_preparation_system not importable (SC2 env required)",
        allow_module_level=True,
    )


class FakeUnit:
    def __init__(self, tag, x, y):
        self.tag = tag
        self.position = Point2((x, y))

    def distance_to(self, other):
        return self.position.distance_to(other.position)


@pytest.fixture
def system():
    return BattlePreparationSystem(bot=None)


def test_no_enemies_returns_empty(system):
    assert system._find_enemy_clusters([]) == []


def test_single_cluster_center_is_geometric_mean(system):
    units = [FakeUnit(1, 0, 0), FakeUnit(2, 2, 0), FakeUnit(3, 1, 3)]
    clusters = system._find_enemy_clusters(units)

    assert len(clusters) == 1
    center, members = clusters[0]
    assert center.x == pytest.approx(1.0)
    assert center.y == pytest.approx(1.0)
    assert len(members) == 3


def test_far_apart_units_form_separate_clusters(system):
    near_pair = [FakeUnit(1, 0, 0), FakeUnit(2, 1, 0)]
    far_unit = [FakeUnit(3, 100, 100)]
    clusters = system._find_enemy_clusters(near_pair + far_unit)

    assert len(clusters) == 2
    sizes = sorted(len(members) for _, members in clusters)
    assert sizes == [1, 2]
