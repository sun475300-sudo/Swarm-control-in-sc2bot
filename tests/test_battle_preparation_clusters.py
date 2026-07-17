# -*- coding: utf-8 -*-
"""
Regression test for BattlePreparationSystem._find_enemy_clusters.

Locks in the cluster-center computation after routing it through the shared
utils.position_utils.get_center_position() helper (previously duplicated
inline math -- see REMAINING_ISSUES.md Issue #5).
"""

import os
import sys
from dataclasses import dataclass
from unittest.mock import MagicMock

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


@dataclass
class FakePosition:
    x: float
    y: float


class FakeUnit:
    def __init__(self, tag, x, y):
        self.tag = tag
        self.position = FakePosition(x, y)

    def distance_to(self, other):
        ox, oy = other.position.x, other.position.y
        return ((self.position.x - ox) ** 2 + (self.position.y - oy) ** 2) ** 0.5


def test_find_enemy_clusters_computes_centroid():
    system = BattlePreparationSystem(bot=MagicMock())
    units = [FakeUnit(1, 0.0, 0.0), FakeUnit(2, 2.0, 0.0), FakeUnit(3, 1.0, 2.0)]

    clusters = system._find_enemy_clusters(units)

    assert len(clusters) == 1
    center, members = clusters[0]
    assert center.x == pytest.approx(1.0)
    assert center.y == pytest.approx(2.0 / 3.0)
    assert {u.tag for u in members} == {1, 2, 3}


def test_find_enemy_clusters_separates_distant_groups():
    system = BattlePreparationSystem(bot=MagicMock())
    units = [
        FakeUnit(1, 0.0, 0.0),
        FakeUnit(2, 1.0, 0.0),
        FakeUnit(3, 100.0, 100.0),
        FakeUnit(4, 101.0, 100.0),
    ]

    clusters = system._find_enemy_clusters(units)

    assert len(clusters) == 2
    tags = sorted(sorted(u.tag for u in members) for _, members in clusters)
    assert tags == [[1, 2], [3, 4]]
