# -*- coding: utf-8 -*-
"""Unit tests for EarlyDefenseSystem.

Targets the proxy-rush response path (recently modified — see
``Update early_defense_system.py`` commit) which had no direct test
coverage before this commit.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from early_defense_system import EarlyDefenseSystem


class _FakePos:
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

    def distance_to(self, other) -> float:
        ox = getattr(other, "x", getattr(getattr(other, "position", None), "x", 0.0))
        oy = getattr(other, "y", getattr(getattr(other, "position", None), "y", 0.0))
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

    def towards(self, _other, _dist):
        return _FakePos(self.x, self.y)


class _FakeStructure:
    def __init__(self, name: str, x: float, y: float, tag: int) -> None:
        self.type_id = Mock()
        self.type_id.name = name
        self.position = _FakePos(x, y)
        self.tag = tag

    def distance_to(self, other):
        return self.position.distance_to(other)


def _build_bot(time_s: float = 60.0):
    """Build a minimal mock bot suitable for EarlyDefenseSystem."""
    bot = Mock()
    bot.time = time_s
    bot.iteration = int(time_s * 22.4)
    bot.minerals = 200
    bot.vespene = 0
    bot.supply_used = 14
    bot.supply_left = 6
    bot.supply_cap = 20
    class _FakeMain:
        def __init__(self, position: _FakePos) -> None:
            self.position = position
            self.x = position.x
            self.y = position.y

        def distance_to(self, other):
            return self.position.distance_to(other)

    main = _FakeMain(_FakePos(50.0, 50.0))

    class _FakeTownhalls(list):
        @property
        def first(self):
            return self[0] if self else None

        @property
        def amount(self):
            return len(self)

    bot.townhalls = _FakeTownhalls([main])
    bot.enemy_structures = []
    bot.enemy_units = []
    bot.structures = Mock(return_value=Mock(ready=Mock(exists=False)))
    bot.units = Mock(return_value=[])
    bot.larva = []
    bot.workers = []
    bot.do = Mock()
    bot.blackboard = Mock()
    bot.game_info = Mock()
    bot.game_info.map_center = _FakePos(100.0, 100.0)
    return bot


class TestEarlyDefenseSystemProxyDetection(unittest.TestCase):
    def setUp(self) -> None:
        self.bot = _build_bot(time_s=60.0)
        self.defense = EarlyDefenseSystem(self.bot)

    def test_no_proxy_when_no_enemy_structures(self) -> None:
        asyncio.run(self.defense._detect_proxy_structure_rush())
        self.assertFalse(self.defense.proxy_response_active)
        self.assertFalse(self.defense.emergency_mode)

    def test_proxy_barracks_in_range_triggers_response(self) -> None:
        self.bot.enemy_structures = [
            _FakeStructure("BARRACKS", x=55.0, y=55.0, tag=1001),
        ]
        asyncio.run(self.defense._detect_proxy_structure_rush())
        self.assertTrue(self.defense.proxy_response_active)
        self.assertTrue(self.defense.emergency_mode)
        self.assertTrue(self.defense.early_rush_detected)
        self.assertIn(1001, self.defense.proxy_structure_tags)
        self.bot.blackboard.set.assert_any_call("proxy_structure_rush", True)
        self.bot.blackboard.set.assert_any_call("drone_production_policy", "HALT")

    def test_far_proxy_does_not_trigger(self) -> None:
        # >40 distance threshold per implementation
        self.bot.enemy_structures = [
            _FakeStructure("BARRACKS", x=200.0, y=200.0, tag=1002),
        ]
        asyncio.run(self.defense._detect_proxy_structure_rush())
        self.assertFalse(self.defense.proxy_response_active)

    def test_unknown_structure_type_ignored(self) -> None:
        self.bot.enemy_structures = [
            _FakeStructure("COMMANDCENTER", x=55.0, y=55.0, tag=1003),
        ]
        asyncio.run(self.defense._detect_proxy_structure_rush())
        self.assertFalse(self.defense.proxy_response_active)

    def test_after_150s_disables_detection(self) -> None:
        self.bot.time = 200.0
        self.bot.enemy_structures = [
            _FakeStructure("BARRACKS", x=55.0, y=55.0, tag=1004),
        ]
        asyncio.run(self.defense._detect_proxy_structure_rush())
        self.assertFalse(self.defense.proxy_response_active)

    def test_proxy_clears_after_structures_destroyed(self) -> None:
        # First trigger proxy response
        self.bot.enemy_structures = [
            _FakeStructure("PHOTONCANNON", x=55.0, y=55.0, tag=1005),
        ]
        asyncio.run(self.defense._detect_proxy_structure_rush())
        self.assertTrue(self.defense.proxy_response_active)

        # Then remove the structures and re-run
        self.bot.enemy_structures = []
        asyncio.run(self.defense._detect_proxy_structure_rush())
        self.assertFalse(self.defense.proxy_response_active)
        self.bot.blackboard.set.assert_any_call("proxy_structure_rush", False)


class TestEarlyDefenseSystemReset(unittest.TestCase):
    def test_reset_clears_all_state(self) -> None:
        bot = _build_bot()
        defense = EarlyDefenseSystem(bot)
        # Dirty all the state
        defense.early_rush_detected = True
        defense.pool_started = True
        defense.queen_started = True
        defense.emergency_mode = True
        defense.last_enemy_check = 99.0
        defense.early_threats.add("zealot")
        defense.proxy_structure_tags.add(1)
        defense.proxy_response_active = True
        defense._proxy_spines_requested = 2
        defense._proxy_worker_tags.add(2)
        defense._pulled_worker_tags.add(3)
        defense._workers_pulled = True
        defense._zergling_speed_researched = True
        defense._spine_crawler_built = True
        defense._spine_crawler_ordered = True

        defense.reset()

        self.assertFalse(defense.early_rush_detected)
        self.assertFalse(defense.pool_started)
        self.assertFalse(defense.queen_started)
        self.assertFalse(defense.emergency_mode)
        self.assertEqual(defense.last_enemy_check, 0)
        self.assertEqual(defense.early_threats, set())
        self.assertEqual(defense.proxy_structure_tags, set())
        self.assertFalse(defense.proxy_response_active)
        self.assertEqual(defense._proxy_spines_requested, 0)
        self.assertEqual(defense._proxy_worker_tags, set())
        self.assertEqual(defense._pulled_worker_tags, set())
        self.assertFalse(defense._workers_pulled)
        self.assertFalse(defense._zergling_speed_researched)
        self.assertFalse(defense._spine_crawler_built)
        self.assertFalse(defense._spine_crawler_ordered)


if __name__ == "__main__":
    unittest.main()
