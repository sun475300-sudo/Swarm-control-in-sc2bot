# -*- coding: utf-8 -*-
"""
Unit tests for idle_unit_manager module.

Covers:
- IdleUnitManager.combat_unit_types whitelist
- _is_unit_managed_by_other_system delegation across sub-systems
- _update_rally_point with and without map info
- _find_main_force centroid calculation
- get_idle_count / get_status_report output structure
- HarassmentManager._find_harassment_target priority and fallbacks
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from idle_unit_manager import HarassmentManager, IdleUnitManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


def _make_units(unit_specs):
    """Build a mock Units-like object that supports .filter, iteration,
    .amount, and indexed iteration enough for the tested methods."""
    units = list(unit_specs)

    class _Collection:
        def __init__(self, items):
            self._items = list(items)

        def filter(self, fn):
            return _Collection([u for u in self._items if fn(u)])

        @property
        def amount(self):
            return len(self._items)

        @property
        def exists(self):
            return len(self._items) > 0

        def __iter__(self):
            return iter(self._items)

        def __call__(self, type_id):  # noqa: D401  - mimic Units(unit_typeid)
            return _Collection([u for u in self._items if u.type_id == type_id])

        @property
        def idle(self):
            return _Collection([u for u in self._items if getattr(u, "is_idle", False)])

        def take(self, n):
            return self._items[:n]

        def closer_than(self, dist, ref):
            return _Collection(
                [u for u in self._items if u.position.distance_to(ref.position) < dist]
            )

        def find_by_tag(self, tag):
            for u in self._items:
                if u.tag == tag:
                    return u
            return None

        def closest_to(self, ref):
            ref_pos = ref.position if hasattr(ref, "position") else ref
            return min(self._items, key=lambda u: u.position.distance_to(ref_pos))

        def furthest_to(self, ref):
            ref_pos = ref.position if hasattr(ref, "position") else ref
            return max(self._items, key=lambda u: u.position.distance_to(ref_pos))

        @property
        def first(self):
            return self._items[0]

    return _Collection(units)


def _make_unit(
    type_id, position, tag=1, is_idle=False, is_attacking=False, hp=100, hp_max=100
):
    u = Mock()
    u.type_id = type_id
    u.position = position
    u.tag = tag
    u.is_idle = is_idle
    u.is_attacking = is_attacking
    u.health = hp
    u.health_max = hp_max
    u.distance_to = lambda p: u.position.distance_to(
        p if isinstance(p, Point2) else p.position
    )
    u.move = Mock(return_value=("move", u, None))
    u.attack = Mock(return_value=("attack", u, None))
    return u


class TestCombatUnitTypes(unittest.TestCase):
    def test_combat_types_include_core_zerg_army(self):
        bot = Mock()
        mgr = IdleUnitManager(bot)
        for tid in (
            UnitTypeId.ZERGLING,
            UnitTypeId.ROACH,
            UnitTypeId.HYDRALISK,
            UnitTypeId.MUTALISK,
            UnitTypeId.ULTRALISK,
        ):
            self.assertIn(tid, mgr.combat_unit_types)

    def test_combat_types_exclude_non_army(self):
        bot = Mock()
        mgr = IdleUnitManager(bot)
        for tid in (UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.QUEEN):
            self.assertNotIn(tid, mgr.combat_unit_types)


class TestIsUnitManagedByOtherSystem(unittest.TestCase):
    def setUp(self):
        self.bot = Mock(spec=[])  # no managers attached
        self.mgr = IdleUnitManager(self.bot)

    def test_no_other_systems_returns_false(self):
        self.assertFalse(self.mgr._is_unit_managed_by_other_system(123))

    def test_unit_authority_other_owner_returns_true(self):
        authority = Mock()
        auth_record = Mock()
        auth_record.owner = "HarassmentCoord"
        authority.authorities = {7: auth_record}
        self.bot.unit_authority = authority
        self.assertTrue(self.mgr._is_unit_managed_by_other_system(7))

    def test_unit_authority_idle_owner_returns_false(self):
        authority = Mock()
        auth_record = Mock()
        auth_record.owner = "IdleUnitManager"
        authority.authorities = {7: auth_record}
        self.bot.unit_authority = authority
        self.assertFalse(self.mgr._is_unit_managed_by_other_system(7))

    def test_harassment_zergling_runby_returns_true(self):
        harass = Mock(
            spec=[
                "zergling_runby_tags",
                "mutalisk_harass_tags",
                "roach_poke_tags",
                "drop_unit_tags",
                "locked_units",
            ]
        )
        harass.zergling_runby_tags = {42}
        harass.mutalisk_harass_tags = set()
        harass.roach_poke_tags = set()
        harass.drop_unit_tags = set()
        harass.locked_units = set()
        self.bot.harassment_coord = harass
        self.assertTrue(self.mgr._is_unit_managed_by_other_system(42))

    def test_advanced_scout_returns_true(self):
        scout = Mock()
        scout.active_scouts = {99}
        self.bot.advanced_scout_v2 = scout
        self.assertTrue(self.mgr._is_unit_managed_by_other_system(99))

    def test_rogue_drop_overlord_returns_true(self):
        rogue = Mock()
        rogue._drop_overlords = {55}
        self.bot.rogue_tactics = rogue
        self.assertTrue(self.mgr._is_unit_managed_by_other_system(55))


class TestUpdateRallyPoint(unittest.TestCase):
    def test_no_townhalls_keeps_rally_point_none(self):
        bot = Mock()
        bot.townhalls = _make_units([])
        mgr = IdleUnitManager(bot)
        mgr._update_rally_point()
        self.assertIsNone(mgr.rally_point)

    def test_rally_point_offset_toward_map_center(self):
        bot = Mock()
        th = _make_unit(UnitTypeId.HATCHERY, Point2((20, 20)))
        bot.townhalls = _make_units([th])
        bot.game_info = Mock()
        bot.game_info.map_center = Point2((100, 100))
        mgr = IdleUnitManager(bot)
        mgr._update_rally_point()
        # Result must be on the line between base and map_center, at distance 10 from base
        self.assertIsNotNone(mgr.rally_point)
        d = mgr.rally_point.distance_to(Point2((20, 20)))
        self.assertAlmostEqual(d, 10.0, delta=0.01)

    def test_no_game_info_uses_main_base(self):
        bot = Mock(spec=["townhalls"])
        th = _make_unit(UnitTypeId.HATCHERY, Point2((20, 20)))
        bot.townhalls = _make_units([th])
        mgr = IdleUnitManager(bot)
        mgr._update_rally_point()
        self.assertEqual(mgr.rally_point, Point2((20, 20)))


class TestFindMainForce(unittest.TestCase):
    def test_no_units_returns_none(self):
        bot = Mock()
        bot.units = _make_units([])
        mgr = IdleUnitManager(bot)
        self.assertIsNone(mgr._find_main_force())

    def test_returns_centroid(self):
        bot = Mock()
        u1 = _make_unit(UnitTypeId.ZERGLING, Point2((0, 0)), tag=1)
        u2 = _make_unit(UnitTypeId.ZERGLING, Point2((10, 10)), tag=2)
        u3 = _make_unit(UnitTypeId.ROACH, Point2((20, 20)), tag=3)
        bot.units = _make_units([u1, u2, u3])
        mgr = IdleUnitManager(bot)
        center = mgr._find_main_force()
        self.assertAlmostEqual(center.x, 10.0, delta=0.01)
        self.assertAlmostEqual(center.y, 10.0, delta=0.01)


class TestStatusReport(unittest.TestCase):
    def test_get_idle_count_filters_to_idle_combat_units(self):
        bot = Mock()
        idle_zerg = _make_unit(UnitTypeId.ZERGLING, Point2((0, 0)), tag=1, is_idle=True)
        busy_zerg = _make_unit(
            UnitTypeId.ZERGLING, Point2((1, 1)), tag=2, is_idle=False
        )
        idle_drone = _make_unit(UnitTypeId.DRONE, Point2((2, 2)), tag=3, is_idle=True)
        bot.units = _make_units([idle_zerg, busy_zerg, idle_drone])
        mgr = IdleUnitManager(bot)
        self.assertEqual(mgr.get_idle_count(), 1)

    def test_status_report_structure(self):
        bot = Mock()
        u1 = _make_unit(
            UnitTypeId.ZERGLING, Point2((0, 0)), tag=1, is_idle=True, hp=20, hp_max=100
        )
        u2 = _make_unit(
            UnitTypeId.ROACH, Point2((10, 10)), tag=2, is_idle=False, hp=100, hp_max=100
        )
        bot.units = _make_units([u1, u2])
        mgr = IdleUnitManager(bot)
        report = mgr.get_status_report()
        self.assertEqual(report["total_combat_units"], 2)
        self.assertEqual(report["idle_units"], 1)
        self.assertEqual(report["wounded_units"], 1)
        self.assertIn("rally_point", report)


class TestHarassmentManagerTarget(unittest.IsolatedAsyncioTestCase):
    async def test_target_prefers_far_enemy_expansion(self):
        bot = Mock()
        my_main = _make_unit(UnitTypeId.HATCHERY, Point2((10, 10)))
        bot.townhalls = _make_units([my_main])
        # Two enemy hatcheries: one near, one far
        near = _make_unit(UnitTypeId.HATCHERY, Point2((30, 30)))
        far = _make_unit(UnitTypeId.HATCHERY, Point2((100, 100)))
        bot.enemy_structures = _make_units([near, far])
        bot.enemy_start_locations = [Point2((110, 110))]

        mgr = HarassmentManager(bot)
        target = await mgr._find_harassment_target()
        self.assertEqual(target, Point2((100, 100)))

    async def test_target_falls_back_to_enemy_start(self):
        bot = Mock()
        my_main = _make_unit(UnitTypeId.HATCHERY, Point2((10, 10)))
        bot.townhalls = _make_units([my_main])
        bot.enemy_structures = _make_units([])  # no enemy bases known
        bot.enemy_start_locations = [Point2((100, 100))]

        mgr = HarassmentManager(bot)
        target = await mgr._find_harassment_target()
        self.assertEqual(target, Point2((100, 100)))

    async def test_target_returns_none_when_no_information(self):
        bot = Mock()
        bot.townhalls = _make_units([])
        bot.enemy_structures = _make_units([])
        bot.enemy_start_locations = []

        mgr = HarassmentManager(bot)
        target = await mgr._find_harassment_target()
        self.assertIsNone(target)


class TestHarassmentManagerStepResilience(unittest.IsolatedAsyncioTestCase):
    async def test_on_step_swallows_errors(self):
        bot = Mock()
        # Make any access raise
        bot.units = Mock(side_effect=RuntimeError("boom"))
        mgr = HarassmentManager(bot)
        await mgr.on_step(0)


if __name__ == "__main__":
    unittest.main()
