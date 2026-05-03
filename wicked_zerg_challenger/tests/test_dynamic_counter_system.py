# -*- coding: utf-8 -*-
"""
Unit tests for DynamicCounterSystem.

Covers:
- __init__ defaults + intel_manager fallback to bot.intel
- counter_rules: schema correctness for known threats
- _scan_enemy_threats: detects rule-matching units, records first-seen
  time, returns only new threats
- _activate_counters: populates active_counters with the right keys
- _register_counter_to_blackboard: writes override + flags into blackboard
- _update_active_counters: marks target_met when counter unit count
  reaches min_count and clears the dynamic_counter_active flag
- get_active_threats: structure
- get_highest_threat: returns highest threat_value rule
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dynamic_counter_system import DynamicCounterSystem
from sc2.ids.unit_typeid import UnitTypeId


def _enemy(type_name):
    e = Mock()
    type_id = Mock()
    type_id.name = type_name
    e.type_id = type_id
    return e


class _UnitsCollection:
    def __init__(self, items):
        self._items = list(items)

    def __call__(self, unit_type):
        # Match by .name on the type_id (UnitTypeId)
        target_name = unit_type.name if hasattr(unit_type, "name") else str(unit_type)
        return _UnitsCollection(
            [
                u
                for u in self._items
                if getattr(u.type_id, "name", "").upper() == target_name.upper()
            ]
        )

    @property
    def amount(self):
        return len(self._items)


class TestInit(unittest.TestCase):
    def test_defaults(self):
        bot = Mock()
        bot.intel = None
        s = DynamicCounterSystem(bot)
        self.assertIsNone(s.intel)
        self.assertEqual(s.detected_threats, set())
        self.assertEqual(s.threat_first_seen, {})
        self.assertEqual(s.active_counters, {})
        self.assertEqual(s.check_interval, 33)

    def test_intel_param_overrides_bot(self):
        bot = Mock()
        bot.intel = "X"
        intel = "Y"
        s = DynamicCounterSystem(bot, intel_manager=intel)
        self.assertEqual(s.intel, "Y")

    def test_intel_falls_back_to_bot_intel(self):
        bot = Mock()
        bot.intel = "Z"
        s = DynamicCounterSystem(bot)
        self.assertEqual(s.intel, "Z")


class TestCounterRules(unittest.TestCase):
    def setUp(self):
        bot = Mock()
        self.s = DynamicCounterSystem(bot)

    def test_battlecruiser_rule(self):
        rule = self.s.counter_rules["BATTLECRUISER"]
        self.assertIn("corruptor", rule["counter_units"])
        self.assertEqual(rule["urgency"], "CRITICAL")
        self.assertEqual(rule["min_count"], 8)

    def test_carrier_rule(self):
        rule = self.s.counter_rules["CARRIER"]
        self.assertEqual(rule["urgency"], "CRITICAL")
        self.assertGreaterEqual(rule["threat_value"], 100)

    def test_all_ratio_lists_match_unit_lists(self):
        for threat, rule in self.s.counter_rules.items():
            self.assertEqual(
                len(rule["counter_units"]),
                len(rule["counter_ratios"]),
                msg=f"Ratio/unit mismatch for {threat}",
            )
            self.assertAlmostEqual(
                sum(rule["counter_ratios"]),
                1.0,
                places=2,
                msg=f"Ratios don't sum to 1.0 for {threat}",
            )


class TestScanEnemyThreats(unittest.IsolatedAsyncioTestCase):
    async def test_no_enemy_units_attr_returns_empty(self):
        bot = Mock(spec=[])
        s = DynamicCounterSystem(bot)
        s.intel = Mock()
        # Even without intel, the scan returns set() when no enemy_units
        result = await s._scan_enemy_threats()
        self.assertEqual(result, set())

    async def test_detects_battlecruiser(self):
        bot = Mock()
        bot.time = 100
        bot.enemy_units = [_enemy("BATTLECRUISER")]
        s = DynamicCounterSystem(bot)
        result = await s._scan_enemy_threats()
        self.assertIn("BATTLECRUISER", result)
        self.assertIn("BATTLECRUISER", s.detected_threats)
        self.assertEqual(s.threat_first_seen["BATTLECRUISER"], 100)

    async def test_already_active_threats_excluded_from_new(self):
        bot = Mock()
        bot.time = 100
        bot.enemy_units = [_enemy("BATTLECRUISER")]
        s = DynamicCounterSystem(bot)
        s.active_counters["BATTLECRUISER"] = {"rule": {}, "activated_time": 50}
        result = await s._scan_enemy_threats()
        # Already active → not in 'new'
        self.assertNotIn("BATTLECRUISER", result)

    async def test_non_threat_unit_ignored(self):
        bot = Mock()
        bot.time = 100
        bot.enemy_units = [_enemy("MARINE")]
        s = DynamicCounterSystem(bot)
        result = await s._scan_enemy_threats()
        self.assertEqual(result, set())


class TestActivateCounters(unittest.IsolatedAsyncioTestCase):
    async def test_populates_active_counters(self):
        bot = Mock()
        bot.time = 200
        bot.blackboard = None
        s = DynamicCounterSystem(bot)
        await s._activate_counters({"VOIDRAY"})
        self.assertIn("VOIDRAY", s.active_counters)
        info = s.active_counters["VOIDRAY"]
        self.assertEqual(info["activated_time"], 200)
        self.assertEqual(info["units_produced"], 0)
        self.assertFalse(info["target_met"])

    async def test_unknown_threat_skipped(self):
        bot = Mock()
        bot.time = 200
        bot.blackboard = None
        s = DynamicCounterSystem(bot)
        await s._activate_counters({"UNKNOWN_THREAT"})
        self.assertNotIn("UNKNOWN_THREAT", s.active_counters)


class TestRegisterCounterToBlackboard(unittest.IsolatedAsyncioTestCase):
    async def test_writes_override_and_flags(self):
        bot = Mock()
        bb = Mock()
        bb.get = Mock(return_value={})
        bb.set = Mock()
        bot.blackboard = bb

        s = DynamicCounterSystem(bot)
        rule = s.counter_rules["VOIDRAY"]
        await s._register_counter_to_blackboard("VOIDRAY", rule)

        calls = {c.args[0] for c in bb.set.call_args_list}
        self.assertIn("unit_composition_override", calls)
        self.assertIn("dynamic_counter_active", calls)
        self.assertIn("active_counter_threat", calls)

    async def test_no_blackboard_is_safe(self):
        bot = Mock(spec=["intel"])
        bot.intel = None
        s = DynamicCounterSystem(bot)
        # No bot.blackboard attr set; should not raise
        await s._register_counter_to_blackboard("VOIDRAY", s.counter_rules["VOIDRAY"])


class TestUpdateActiveCounters(unittest.IsolatedAsyncioTestCase):
    async def test_marks_target_met_when_unit_count_reaches_min(self):
        bot = Mock()
        bot.time = 300
        bb = Mock()
        bb.set = Mock()
        bot.blackboard = bb
        # Build 8 corruptors (BATTLECRUISER min_count is 8)
        bot.units = _UnitsCollection([_enemy("CORRUPTOR") for _ in range(8)])

        s = DynamicCounterSystem(bot)
        s.active_counters["BATTLECRUISER"] = {
            "rule": s.counter_rules["BATTLECRUISER"],
            "activated_time": 200,
            "units_produced": 0,
            "target_met": False,
        }
        await s._update_active_counters(0)
        self.assertTrue(s.active_counters["BATTLECRUISER"]["target_met"])
        # Blackboard should have flipped dynamic_counter_active off
        keys = {c.args[0] for c in bb.set.call_args_list}
        self.assertIn("dynamic_counter_active", keys)

    async def test_does_not_mark_when_below_min(self):
        bot = Mock()
        bot.time = 300
        bot.blackboard = None
        # Only 2 corruptors
        bot.units = _UnitsCollection([_enemy("CORRUPTOR") for _ in range(2)])

        s = DynamicCounterSystem(bot)
        s.active_counters["BATTLECRUISER"] = {
            "rule": s.counter_rules["BATTLECRUISER"],
            "activated_time": 200,
            "units_produced": 0,
            "target_met": False,
        }
        await s._update_active_counters(0)
        self.assertFalse(s.active_counters["BATTLECRUISER"]["target_met"])

    async def test_no_units_attr_safe(self):
        bot = Mock(spec=["blackboard", "time"])
        bot.time = 100
        bot.blackboard = None
        s = DynamicCounterSystem(bot)
        s.active_counters["ULTRALISK"] = {
            "rule": s.counter_rules["ULTRALISK"],
            "activated_time": 50,
            "units_produced": 0,
            "target_met": False,
        }
        # Must not raise
        await s._update_active_counters(0)


class TestQueries(unittest.TestCase):
    def test_get_active_threats_empty(self):
        bot = Mock()
        s = DynamicCounterSystem(bot)
        self.assertEqual(s.get_active_threats(), [])

    def test_get_active_threats_returns_tuples(self):
        bot = Mock()
        s = DynamicCounterSystem(bot)
        s.active_counters["VOIDRAY"] = {"info": "x"}
        self.assertEqual(s.get_active_threats(), [("VOIDRAY", {"info": "x"})])

    def test_get_highest_threat_none(self):
        bot = Mock()
        s = DynamicCounterSystem(bot)
        self.assertEqual(s.get_highest_threat(), ("NONE", 0))

    def test_get_highest_threat_picks_max(self):
        bot = Mock()
        s = DynamicCounterSystem(bot)
        # CARRIER threat_value 100, VOIDRAY 40
        s.detected_threats = {"VOIDRAY", "CARRIER"}
        name, value = s.get_highest_threat()
        self.assertEqual(name, "CARRIER")
        self.assertEqual(value, 100)

    def test_get_highest_threat_skips_unknown(self):
        bot = Mock()
        s = DynamicCounterSystem(bot)
        s.detected_threats = {"NEVER_SEEN"}
        name, value = s.get_highest_threat()
        # Default still NONE, 0
        self.assertEqual((name, value), ("NONE", 0))


if __name__ == "__main__":
    unittest.main()
