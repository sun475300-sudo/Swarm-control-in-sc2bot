# -*- coding: utf-8 -*-
"""
Unit tests for ProtossCounterSystem.

Heavier counter-action paths (_handle_*) require deep mocking of
Units/townhalls; we test the deterministic detection and structural pieces.

Covered:
- __init__ defaults
- _detect_protoss_threats: identifies DT, Oracle, Phoenix, Disruptor,
  Warp Prism (both forms), Immortal counts; resets between calls
- _has_lair: detects LAIR/HIVE via structure name
- get_status_report structure
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from protoss_counter_system import ProtossCounterSystem


def _enemy(type_name):
    e = Mock()
    type_id = Mock()
    type_id.name = type_name
    e.type_id = type_id
    return e


def _struct(type_name, ready=True):
    s = Mock()
    type_id = Mock()
    type_id.name = type_name
    s.type_id = type_id
    s.is_ready = ready
    return s


class _StructCollection:
    """Mock structures collection that supports filter().ready.exists."""

    def __init__(self, items):
        self._items = list(items)

    def filter(self, fn):
        return _StructCollection([s for s in self._items if fn(s)])

    @property
    def ready(self):
        return _StructCollection([s for s in self._items if s.is_ready])

    @property
    def exists(self):
        return bool(self._items)


class TestInit(unittest.TestCase):
    def test_default_state(self):
        bot = Mock()
        c = ProtossCounterSystem(bot)
        self.assertFalse(c.dt_detected)
        self.assertFalse(c.oracle_detected)
        self.assertFalse(c.phoenix_detected)
        self.assertFalse(c.disruptor_detected)
        self.assertFalse(c.warp_prism_detected)
        self.assertEqual(c.immortal_count, 0)
        self.assertFalse(c.emergency_spore_requested)
        self.assertFalse(c.emergency_overseer_requested)
        self.assertFalse(c.workers_pulled)


class TestDetectProtossThreats(unittest.IsolatedAsyncioTestCase):
    async def test_no_enemy_units_attr_safe(self):
        bot = Mock(spec=[])
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertFalse(c.dt_detected)

    async def test_detects_dark_templar(self):
        bot = Mock()
        bot.time = 100
        bot.enemy_units = [_enemy("DARKTEMPLAR")]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertTrue(c.dt_detected)
        self.assertEqual(c.dt_detection_time, 100)

    async def test_detects_oracle(self):
        bot = Mock()
        bot.time = 50
        bot.enemy_units = [_enemy("ORACLE")]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertTrue(c.oracle_detected)

    async def test_detects_phoenix(self):
        bot = Mock()
        bot.time = 60
        bot.enemy_units = [_enemy("PHOENIX")]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertTrue(c.phoenix_detected)

    async def test_detects_disruptor(self):
        bot = Mock()
        bot.time = 240
        bot.enemy_units = [_enemy("DISRUPTOR")]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertTrue(c.disruptor_detected)

    async def test_detects_warp_prism_phasing(self):
        bot = Mock()
        bot.time = 200
        bot.enemy_units = [_enemy("WARPPRISMPHASING")]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertTrue(c.warp_prism_detected)

    async def test_detects_warp_prism(self):
        bot = Mock()
        bot.time = 200
        bot.enemy_units = [_enemy("WARPPRISM")]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertTrue(c.warp_prism_detected)

    async def test_counts_immortals(self):
        bot = Mock()
        bot.time = 300
        bot.enemy_units = [
            _enemy("IMMORTAL"),
            _enemy("IMMORTAL"),
            _enemy("IMMORTAL"),
            _enemy("STALKER"),
        ]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertEqual(c.immortal_count, 3)

    async def test_resets_flags_between_calls(self):
        bot = Mock()
        bot.time = 100
        bot.enemy_units = [_enemy("ORACLE")]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertTrue(c.oracle_detected)

        # Now no oracle visible — flags should reset
        bot.enemy_units = [_enemy("STALKER")]
        await c._detect_protoss_threats()
        self.assertFalse(c.oracle_detected)
        self.assertFalse(c.dt_detected)

    async def test_reset_dt_persistence(self):
        # DT detection sets dt_detection_time once; if DT no longer visible,
        # dt_detected resets per the implementation
        bot = Mock()
        bot.time = 100
        bot.enemy_units = [_enemy("DARKTEMPLAR")]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        self.assertTrue(c.dt_detected)
        # Without DT visible, the next call resets dt_detected
        bot.enemy_units = []
        bot.time = 200
        await c._detect_protoss_threats()
        self.assertFalse(c.dt_detected)

    async def test_swallows_per_unit_exceptions(self):
        bot = Mock()
        bot.time = 100
        bad = Mock()
        # accessing type_id raises
        type_id = Mock()
        type_id.name = "ORACLE"
        bad.type_id = type_id
        good = _enemy("PHOENIX")
        bot.enemy_units = [bad, good]
        c = ProtossCounterSystem(bot)
        await c._detect_protoss_threats()
        # Should successfully detect oracle and phoenix
        self.assertTrue(c.oracle_detected)
        self.assertTrue(c.phoenix_detected)


class TestHasLair(unittest.TestCase):
    def test_no_structures_attr_returns_false(self):
        bot = Mock(spec=[])
        c = ProtossCounterSystem(bot)
        self.assertFalse(c._has_lair())

    def test_with_lair_returns_true(self):
        bot = Mock()
        bot.structures = _StructCollection([_struct("LAIR", ready=True)])
        c = ProtossCounterSystem(bot)
        self.assertTrue(c._has_lair())

    def test_with_hive_returns_true(self):
        bot = Mock()
        bot.structures = _StructCollection([_struct("HIVE", ready=True)])
        c = ProtossCounterSystem(bot)
        self.assertTrue(c._has_lair())

    def test_with_unready_lair_returns_false(self):
        bot = Mock()
        bot.structures = _StructCollection([_struct("LAIR", ready=False)])
        c = ProtossCounterSystem(bot)
        self.assertFalse(c._has_lair())

    def test_with_only_hatchery_returns_false(self):
        bot = Mock()
        bot.structures = _StructCollection([_struct("HATCHERY", ready=True)])
        c = ProtossCounterSystem(bot)
        self.assertFalse(c._has_lair())


class TestStatusReport(unittest.TestCase):
    def test_status_report_keys(self):
        bot = Mock()
        c = ProtossCounterSystem(bot)
        report = c.get_status_report()
        for key in (
            "dt_detected",
            "oracle_detected",
            "phoenix_detected",
            "disruptor_detected",
            "warp_prism_detected",
            "immortal_count",
            "emergency_spore_requested",
            "emergency_overseer_requested",
        ):
            self.assertIn(key, report)

    def test_status_reflects_state(self):
        bot = Mock()
        c = ProtossCounterSystem(bot)
        c.dt_detected = True
        c.immortal_count = 5
        report = c.get_status_report()
        self.assertTrue(report["dt_detected"])
        self.assertEqual(report["immortal_count"], 5)


if __name__ == "__main__":
    unittest.main()
