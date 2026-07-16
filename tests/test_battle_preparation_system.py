# -*- coding: utf-8 -*-
"""
Unit tests -- BattlePreparationSystem._find_enemy_clusters

Locks in cluster-centroid behavior after routing the calculation through
utils.position_utils.get_center_position() instead of an inline duplicate.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from battle_preparation_system import BattlePreparationSystem
except ImportError:
    pytest.skip(
        "battle_preparation_system not importable (SC2 env required)",
        allow_module_level=True,
    )


class FakePoint2:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)


class FakeUnit:
    def __init__(self, tag, x, y):
        self.tag = tag
        self.position = FakePoint2(x, y)

    def distance_to(self, other):
        ox, oy = other.position.x, other.position.y
        return ((self.position.x - ox) ** 2 + (self.position.y - oy) ** 2) ** 0.5


@pytest.fixture
def system():
    return BattlePreparationSystem(bot=None)


def test_no_enemies_returns_empty(system):
    assert system._find_enemy_clusters([]) == []


def test_single_cluster_centroid(system):
    units = [FakeUnit(1, 0, 0), FakeUnit(2, 2, 0), FakeUnit(3, 1, 2)]
    clusters = system._find_enemy_clusters(units)

    assert len(clusters) == 1
    center, members = clusters[0]
    assert center.x == pytest.approx(1.0)
    assert center.y == pytest.approx(2.0 / 3.0)
    assert {u.tag for u in members} == {1, 2, 3}


def test_two_separate_clusters(system):
    near_a = [FakeUnit(1, 0, 0), FakeUnit(2, 1, 0)]
    near_b = [FakeUnit(3, 100, 100), FakeUnit(4, 101, 100)]
    clusters = system._find_enemy_clusters(near_a + near_b)

    assert len(clusters) == 2
    tags = [{u.tag for u in members} for _, members in clusters]
    assert {1, 2} in tags
    assert {3, 4} in tags
