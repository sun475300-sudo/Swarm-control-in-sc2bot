# -*- coding: utf-8 -*-
"""
Unit tests for EarlyScoutSystem.

Covers:
- __init__ defaults
- _get_enemy_natural_location with/without expansion data
- _is_enemy_townhall classification including text-only fallback
- _sync_blackboard_state writes the expected keys
- _analyze_enemy_info detects pool/gas/natural and flags cheese
- get_scout_status reflects state
- is_cheese_detected mirrors flag
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from early_scout_system import EarlyScoutSystem
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


def _collection(items):
    items = list(items)

    class _Coll:
        def __init__(self, xs):
            self._x = list(xs)

        def __iter__(self):
            return iter(self._x)

        @property
        def amount(self):
            return len(self._x)

        @property
        def exists(self):
            return bool(self._x)

        @property
        def first(self):
            return self._x[0]

        def __call__(self, type_id):
            return _Coll([u for u in self._x if u.type_id == type_id])

        def filter(self, fn):
            return _Coll([u for u in self._x if fn(u)])

    return _Coll(items)


def _bot(time=60.0):
    bot = Mock()
    bot.time = time
    bot.start_location = Point2((20, 20))
    bot.enemy_start_locations = [Point2((100, 100))]
    bot.expansion_locations_list = [
        Point2((20, 20)),  # main
        Point2((30, 30)),  # natural
        Point2((50, 50)),  # third
        Point2((90, 90)),  # enemy third
        Point2((100, 100)),  # enemy main
        Point2((90, 100)),  # enemy natural (~10 from main)
    ]
    bot.game_info = Mock()
    bot.game_info.map_center = Point2((60, 60))
    bot.units = lambda *a, **kw: _collection([])
    bot.structures = lambda *a, **kw: _collection([])
    bot.enemy_units = _collection([])
    bot.enemy_structures = _collection([])
    bot.blackboard = None
    bot.do = Mock()
    return bot


class TestInit(unittest.TestCase):
    def test_default_state(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        self.assertEqual(ess.early_game_threshold, 300.0)
        self.assertEqual(ess.scout_ling_tags, [])
        self.assertEqual(ess.max_scout_lings, 3)
        self.assertFalse(ess.ling_scouts_assigned)
        self.assertIsNone(ess.scout_overlord_tag)
        self.assertFalse(ess.overlord_scout_sent)
        self.assertFalse(ess.proxy_detected)
        self.assertFalse(ess.cheese_suspected)
        self.assertFalse(ess.main_base_scouted)
        self.assertFalse(ess.natural_scouted)
        self.assertFalse(ess.third_scouted)


class TestEnemyNaturalLocation(unittest.TestCase):
    def test_returns_closest_non_main_expansion(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        natural = ess._get_enemy_natural_location()
        # The closest expansion to enemy start (100, 100) that's > 1 unit away
        # is (90, 100) at distance 10
        self.assertEqual(natural, Point2((90, 100)))

    def test_no_expansion_list_falls_back_to_map_center_offset(self):
        bot = _bot()
        bot.expansion_locations_list = []
        ess = EarlyScoutSystem(bot)
        natural = ess._get_enemy_natural_location()
        # Should produce a point on the line from map_center towards enemy_start
        self.assertIsNotNone(natural)
        # And it should be between map_center and enemy_start
        self.assertGreater(natural.x, 60)
        self.assertGreater(natural.y, 60)

    def test_no_enemy_start_returns_none(self):
        bot = _bot()
        bot.enemy_start_locations = []
        ess = EarlyScoutSystem(bot)
        self.assertIsNone(ess._get_enemy_natural_location())


class TestIsEnemyTownhall(unittest.TestCase):
    def test_hatchery_is_townhall(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        s = Mock()
        s.type_id = UnitTypeId.HATCHERY
        self.assertTrue(ess._is_enemy_townhall(s))

    def test_orbital_command_via_name(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        s = Mock()
        type_id = Mock()
        type_id.name = "ORBITALCOMMAND"
        s.type_id = type_id
        self.assertTrue(ess._is_enemy_townhall(s))

    def test_non_townhall_returns_false(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        s = Mock()
        s.type_id = UnitTypeId.SPAWNINGPOOL
        self.assertFalse(ess._is_enemy_townhall(s))


class TestSyncBlackboardState(unittest.TestCase):
    def test_no_blackboard_is_safe(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        # Must not raise
        ess._sync_blackboard_state(refresh_report=True)
        self.assertEqual(ess._last_report_time, bot.time)

    def test_with_blackboard_writes_expected_keys(self):
        bot = _bot()
        bb = Mock()
        bb.set = Mock()
        bot.blackboard = bb
        ess = EarlyScoutSystem(bot)
        ess.enemy_pool_timing = 70.0
        ess.enemy_gas_timing = 80.0
        ess.enemy_natural_timing = 100.0
        ess.cheese_suspected = True

        ess._sync_blackboard_state(refresh_report=True)

        keys_set = {call.args[0] for call in bb.set.call_args_list}
        for required in (
            "early_scout_pool_time",
            "early_scout_gas_time",
            "early_scout_natural_confirmed",
            "early_scout_cheese_suspected",
            "early_scout_last_report_time",
            "early_scout_rescout_active",
            "enemy_pool_timing",
            "enemy_gas_timing",
            "enemy_natural_timing",
            "enemy_is_cheese",
        ):
            self.assertIn(required, keys_set)


class TestAnalyzeEnemyInfo(unittest.IsolatedAsyncioTestCase):
    async def test_no_enemy_structures_does_nothing(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        await ess._analyze_enemy_info()
        self.assertIsNone(ess.enemy_pool_timing)

    async def test_detects_spawning_pool_and_flags_cheese(self):
        bot = _bot(time=60.0)
        pool = Mock()
        type_id = Mock()
        type_id.name = "SPAWNINGPOOL"
        pool.type_id = type_id
        pool.distance_to = lambda p: 100.0
        bot.enemy_structures = _collection([pool])
        ess = EarlyScoutSystem(bot)
        await ess._analyze_enemy_info()
        self.assertEqual(ess.enemy_pool_timing, 60.0)
        self.assertTrue(ess.cheese_suspected)

    async def test_late_pool_does_not_flag_cheese(self):
        bot = _bot(time=200.0)
        pool = Mock()
        type_id = Mock()
        type_id.name = "SPAWNINGPOOL"
        pool.type_id = type_id
        pool.distance_to = lambda p: 100.0
        bot.enemy_structures = _collection([pool])
        ess = EarlyScoutSystem(bot)
        await ess._analyze_enemy_info()
        self.assertEqual(ess.enemy_pool_timing, 200.0)
        self.assertFalse(ess.cheese_suspected)

    async def test_detects_gas_building(self):
        bot = _bot(time=80.0)
        ext = Mock()
        type_id = Mock()
        type_id.name = "EXTRACTOR"
        ext.type_id = type_id
        ext.distance_to = lambda p: 100.0
        bot.enemy_structures = _collection([ext])
        ess = EarlyScoutSystem(bot)
        await ess._analyze_enemy_info()
        self.assertEqual(ess.enemy_gas_timing, 80.0)

    async def test_detects_enemy_natural(self):
        bot = _bot(time=100.0)
        # Enemy natural is at (90, 100); place a hatchery there
        hatch = Mock()
        type_id = Mock()
        type_id.name = "HATCHERY"
        hatch.type_id = type_id
        hatch.distance_to = lambda p: p.distance_to(Point2((90, 100)))
        bot.enemy_structures = _collection([hatch])
        ess = EarlyScoutSystem(bot)
        await ess._analyze_enemy_info()
        self.assertEqual(ess.enemy_natural_timing, 100.0)
        self.assertTrue(ess.natural_scouted)

    async def test_records_unique_enemy_unit_tags(self):
        bot = _bot()
        u1 = Mock()
        u1.tag = 1
        u2 = Mock()
        u2.tag = 2
        u3 = Mock()
        u3.tag = 1  # duplicate
        bot.enemy_units = _collection([u1, u2, u3])
        ess = EarlyScoutSystem(bot)
        await ess._analyze_enemy_info()
        self.assertEqual(ess.enemy_early_units, {1, 2})


class TestStatusReport(unittest.TestCase):
    def test_idle_state(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        s = ess.get_scout_status()
        self.assertIn("Lings:idle", s)
        self.assertIn("OL:idle", s)
        self.assertNotIn("Cheese", s)

    def test_active_state(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        ess.ling_scouts_assigned = True
        ess.overlord_scout_sent = True
        ess.main_base_scouted = True
        ess.natural_scouted = True
        ess.cheese_suspected = True
        s = ess.get_scout_status()
        self.assertIn("OL:active", s)
        self.assertIn("Check:main,natural", s)
        self.assertIn("Cheese!", s)

    def test_is_cheese_detected_mirrors_flag(self):
        bot = _bot()
        ess = EarlyScoutSystem(bot)
        self.assertFalse(ess.is_cheese_detected())
        ess.cheese_suspected = True
        self.assertTrue(ess.is_cheese_detected())


if __name__ == "__main__":
    unittest.main()
