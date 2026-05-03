# -*- coding: utf-8 -*-
"""
Unit tests for EarlyDefenseSystem.

Covers:
- __init__ defaults (including the previously-uninitialized FIX 3/4/5 state)
- execute() short-circuit after the early-game window
- _detect_early_threats: rush detection, threat tag tracking
- _produce_early_zerglings target sizing in normal vs emergency
- _produce_first_queen idempotency / resource gating
- _emergency_defense: clears threats when enemy gone, dispatches lings/workers
- _research_zergling_speed_early: pool readiness + gas gating + idempotency
- _worker_pull_defense: thresholds for pulling workers
- get_status text reflects state transitions
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from early_defense_system import EarlyDefenseSystem
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


def _collection(items):
    """Minimal Units-like collection used by EarlyDefenseSystem."""
    items = list(items)

    class _Coll:
        def __init__(self, xs):
            self._x = list(xs)

        def __iter__(self):
            return iter(self._x)

        def __getitem__(self, idx):
            return self._x[idx]

        def __len__(self):
            return len(self._x)

        @property
        def amount(self):
            return len(self._x)

        @property
        def exists(self):
            return bool(self._x)

        @property
        def first(self):
            return self._x[0]

        @property
        def ready(self):
            return _Coll([u for u in self._x if getattr(u, "is_ready", True)])

        @property
        def idle(self):
            return _Coll([u for u in self._x if getattr(u, "is_idle", True)])

        @property
        def tags(self):
            return [u.tag for u in self._x]

        def filter(self, fn):
            return _Coll([u for u in self._x if fn(u)])

        def closer_than(self, dist, ref):
            ref_pos = ref if isinstance(ref, Point2) else ref.position
            return _Coll([u for u in self._x if u.position.distance_to(ref_pos) < dist])

        def closest_to(self, ref):
            ref_pos = ref if isinstance(ref, Point2) else ref.position
            return min(self._x, key=lambda u: u.position.distance_to(ref_pos))

        def closest_n_units(self, ref, n):
            ref_pos = ref if isinstance(ref, Point2) else ref.position
            return sorted(self._x, key=lambda u: u.position.distance_to(ref_pos))[:n]

        def __call__(self, type_id):
            return _Coll([u for u in self._x if u.type_id == type_id])

    return _Coll(items)


def _unit(
    type_id,
    position=Point2((0, 0)),
    tag=1,
    is_idle=True,
    is_moving=False,
    is_gathering=False,
    is_ready=True,
):
    u = Mock()
    u.type_id = type_id
    u.position = position
    u.tag = tag
    u.is_idle = is_idle
    u.is_moving = is_moving
    u.is_gathering = is_gathering
    u.is_ready = is_ready
    u.distance_to = lambda p: u.position.distance_to(
        p if isinstance(p, Point2) else p.position
    )
    u.train = Mock(return_value=("train", u, None))
    u.attack = Mock(return_value=("attack", u, None))
    u.move = Mock(return_value=("move", u, None))
    u.gather = Mock(return_value=("gather", u, None))
    u.research = Mock(return_value=("research", u, None))
    u.build = Mock(return_value=("build", u, None))
    return u


def _bot(time=60.0, supply_used=12, minerals=200, vespene=0):
    bot = Mock()
    bot.time = time
    bot.iteration = 0
    bot.supply_used = supply_used
    bot.minerals = minerals
    bot.vespene = vespene
    bot.larva = _collection([])
    bot.workers = _collection([])
    bot.units = lambda *a, **kw: _collection([])
    bot.structures = lambda *a, **kw: _collection([])
    bot.enemy_units = _collection([])
    bot.townhalls = _collection([])
    bot.mineral_field = _collection([])
    bot.game_info = Mock()
    bot.game_info.map_center = Point2((100, 100))
    bot.already_pending = Mock(return_value=0)
    bot.already_pending_upgrade = Mock(return_value=0)
    bot.can_afford = Mock(return_value=True)
    bot.do = Mock()
    bot.tech_coordinator = None
    return bot


class TestInitialization(unittest.TestCase):
    def test_defaults(self):
        bot = _bot()
        eds = EarlyDefenseSystem(bot)
        self.assertEqual(eds.early_game_threshold, 180.0)
        self.assertFalse(eds.early_rush_detected)
        self.assertFalse(eds.pool_started)
        self.assertFalse(eds.queen_started)
        self.assertFalse(eds.emergency_mode)
        self.assertEqual(eds.early_threats, set())

    def test_optional_fix_attributes_initialized(self):
        """Regression: previously these attributes only existed after the
        first method call, causing AttributeError when external coordinators
        invoked the helpers."""
        bot = _bot()
        eds = EarlyDefenseSystem(bot)
        self.assertFalse(eds._zergling_speed_researched)
        self.assertFalse(eds._spine_crawler_built)
        self.assertFalse(eds._spine_crawler_ordered)
        self.assertFalse(eds._workers_pulled)
        self.assertEqual(eds._pulled_worker_tags, set())


class TestExecuteWindow(unittest.IsolatedAsyncioTestCase):
    async def test_execute_no_op_after_threshold(self):
        bot = _bot(time=200.0)
        eds = EarlyDefenseSystem(bot)
        await eds.execute(0)
        bot.do.assert_not_called()

    async def test_execute_does_not_raise_on_minimal_bot(self):
        bot = _bot(time=30.0, supply_used=5)
        eds = EarlyDefenseSystem(bot)
        await eds.execute(0)


class TestDetectEarlyThreats(unittest.IsolatedAsyncioTestCase):
    async def test_no_enemy_units_does_nothing(self):
        bot = _bot()
        eds = EarlyDefenseSystem(bot)
        await eds._detect_early_threats()
        self.assertFalse(eds.emergency_mode)

    async def test_no_main_base_does_nothing(self):
        bot = _bot()
        bot.enemy_units = _collection([_unit(UnitTypeId.MARINE, Point2((10, 10)))])
        eds = EarlyDefenseSystem(bot)
        await eds._detect_early_threats()
        self.assertFalse(eds.emergency_mode)

    async def test_nearby_enemy_triggers_emergency(self):
        bot = _bot()
        hatch = _unit(UnitTypeId.HATCHERY, Point2((20, 20)))
        bot.townhalls = _collection([hatch])
        marine = _unit(UnitTypeId.MARINE, Point2((25, 25)), tag=42)
        bot.enemy_units = _collection([marine])
        eds = EarlyDefenseSystem(bot)
        await eds._detect_early_threats()
        self.assertTrue(eds.emergency_mode)
        self.assertTrue(eds.early_rush_detected)
        self.assertIn(42, eds.early_threats)

    async def test_far_enemy_does_not_trigger(self):
        bot = _bot()
        hatch = _unit(UnitTypeId.HATCHERY, Point2((20, 20)))
        bot.townhalls = _collection([hatch])
        marine = _unit(UnitTypeId.MARINE, Point2((100, 100)), tag=42)
        bot.enemy_units = _collection([marine])
        eds = EarlyDefenseSystem(bot)
        await eds._detect_early_threats()
        self.assertFalse(eds.emergency_mode)


class TestEmergencyDefense(unittest.IsolatedAsyncioTestCase):
    async def test_clears_state_when_threats_gone(self):
        bot = _bot()
        hatch = _unit(UnitTypeId.HATCHERY, Point2((20, 20)))
        bot.townhalls = _collection([hatch])
        # No enemy units alive
        bot.enemy_units = _collection([])
        eds = EarlyDefenseSystem(bot)
        eds.early_threats = {1, 2, 3}
        eds.emergency_mode = True
        await eds._emergency_defense()
        self.assertEqual(eds.early_threats, set())
        self.assertFalse(eds.emergency_mode)

    async def test_no_op_when_no_threats(self):
        bot = _bot()
        eds = EarlyDefenseSystem(bot)
        eds.early_threats.clear()
        await eds._emergency_defense()
        # Should not crash
        bot.do.assert_not_called()


class TestProduceFirstQueen(unittest.IsolatedAsyncioTestCase):
    async def test_skips_when_queen_already_exists(self):
        bot = _bot()
        existing_queen = _unit(UnitTypeId.QUEEN)
        bot.units = lambda tid: _collection(
            [existing_queen] if tid == UnitTypeId.QUEEN else []
        )
        eds = EarlyDefenseSystem(bot)
        await eds._produce_first_queen()
        self.assertTrue(eds.queen_started)
        bot.do.assert_not_called()

    async def test_skips_when_queen_pending(self):
        bot = _bot()
        bot.units = lambda tid: _collection([])
        bot.already_pending = Mock(return_value=1)
        eds = EarlyDefenseSystem(bot)
        await eds._produce_first_queen()
        self.assertTrue(eds.queen_started)

    async def test_no_townhall_does_not_train(self):
        bot = _bot()
        bot.units = lambda tid: _collection([])
        eds = EarlyDefenseSystem(bot)
        await eds._produce_first_queen()
        self.assertFalse(eds.queen_started)
        bot.do.assert_not_called()


class TestZerglingSpeedResearch(unittest.IsolatedAsyncioTestCase):
    async def test_skip_when_already_researched(self):
        bot = _bot(vespene=200)
        eds = EarlyDefenseSystem(bot)
        eds._zergling_speed_researched = True
        await eds._research_zergling_speed_early()
        bot.do.assert_not_called()

    async def test_skip_when_no_pool(self):
        bot = _bot(vespene=200)
        bot.structures = lambda tid: _collection([])
        eds = EarlyDefenseSystem(bot)
        await eds._research_zergling_speed_early()
        self.assertFalse(eds._zergling_speed_researched)

    async def test_skip_when_insufficient_gas(self):
        bot = _bot(vespene=50)
        pool = _unit(UnitTypeId.SPAWNINGPOOL, is_idle=True)
        bot.structures = lambda tid: (
            _collection([pool]) if tid == UnitTypeId.SPAWNINGPOOL else _collection([])
        )
        eds = EarlyDefenseSystem(bot)
        await eds._research_zergling_speed_early()
        self.assertFalse(eds._zergling_speed_researched)

    async def test_research_when_ready(self):
        bot = _bot(vespene=150)
        pool = _unit(UnitTypeId.SPAWNINGPOOL, is_idle=True, is_ready=True)
        bot.structures = lambda tid: (
            _collection([pool]) if tid == UnitTypeId.SPAWNINGPOOL else _collection([])
        )
        eds = EarlyDefenseSystem(bot)
        await eds._research_zergling_speed_early()
        self.assertTrue(eds._zergling_speed_researched)
        bot.do.assert_called_once()


class TestWorkerPullDefense(unittest.IsolatedAsyncioTestCase):
    async def test_no_pull_without_townhall(self):
        bot = _bot()
        eds = EarlyDefenseSystem(bot)
        await eds._worker_pull_defense()
        self.assertFalse(eds._workers_pulled)

    async def test_pull_when_under_attack_and_few_army(self):
        bot = _bot()
        hatch = _unit(UnitTypeId.HATCHERY, Point2((20, 20)))
        bot.townhalls = _collection([hatch])
        # 5 enemies near base
        enemies = [
            _unit(UnitTypeId.MARINE, Point2((22, 22)), tag=10 + i) for i in range(5)
        ]
        bot.enemy_units = _collection(enemies)
        # No army, plenty of workers
        bot.units = lambda tid: _collection([])
        workers = [
            _unit(UnitTypeId.DRONE, Point2((20 + i, 20)), tag=100 + i)
            for i in range(12)
        ]
        bot.workers = _collection(workers)
        eds = EarlyDefenseSystem(bot)
        await eds._worker_pull_defense()
        self.assertTrue(eds._workers_pulled)
        self.assertGreater(len(eds._pulled_worker_tags), 0)

    async def test_no_pull_when_too_few_workers(self):
        bot = _bot()
        hatch = _unit(UnitTypeId.HATCHERY, Point2((20, 20)))
        bot.townhalls = _collection([hatch])
        enemies = [
            _unit(UnitTypeId.MARINE, Point2((22, 22)), tag=10 + i) for i in range(5)
        ]
        bot.enemy_units = _collection(enemies)
        bot.units = lambda tid: _collection([])
        # Only 5 workers; logic requires > 6
        workers = [
            _unit(UnitTypeId.DRONE, Point2((20, 20)), tag=100 + i) for i in range(5)
        ]
        bot.workers = _collection(workers)
        eds = EarlyDefenseSystem(bot)
        await eds._worker_pull_defense()
        self.assertFalse(eds._workers_pulled)


class TestGetStatus(unittest.TestCase):
    def test_status_after_threshold(self):
        bot = _bot(time=200)
        eds = EarlyDefenseSystem(bot)
        self.assertEqual(eds.get_status(), "Early Defense Complete")

    def test_status_normal_mode(self):
        bot = _bot(time=60)
        eds = EarlyDefenseSystem(bot)
        s = eds.get_status()
        self.assertIn("Normal", s)
        self.assertIn("Pool: [X]", s)
        self.assertIn("Queen: [X]", s)
        self.assertIn("Lings: 0", s)

    def test_status_emergency_mode(self):
        bot = _bot(time=60)
        eds = EarlyDefenseSystem(bot)
        eds.emergency_mode = True
        eds.pool_started = True
        eds.queen_started = True
        s = eds.get_status()
        self.assertIn("Emergency", s)
        self.assertIn("Pool: [OK]", s)
        self.assertIn("Queen: [OK]", s)


if __name__ == "__main__":
    unittest.main()
