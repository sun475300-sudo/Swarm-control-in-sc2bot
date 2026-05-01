# -*- coding: utf-8 -*-
"""
Unit tests for WickedZergBotProImpl._track_build_order.

Specifically guards the off-by-one in `_expansions_built`: the starting
main hatchery is NOT an expansion. Only subsequent HATCHERY structures
should increment the counter.
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wicked_zerg_bot_pro_impl import WickedZergBotProImpl


def _struct(tag, name, ready=True, x=10.0, y=10.0):
    s = Mock()
    s.tag = tag
    type_id = Mock()
    type_id.name = name
    s.type_id = type_id
    s.is_ready = ready
    pos = Mock()
    pos.x = x
    pos.y = y
    s.position = pos
    return s


class _BotStub:
    """Minimal stand-in for the WickedZergBotProImpl instance.

    We can't easily instantiate the real BotAI subclass without a full SC2
    environment, so we call the unbound method against a duck-typed stub.
    """

    def __init__(self, structures, time=0.0):
        self.structures = structures
        self.time = time
        self._tracked_structure_tags = set()
        self._build_order_log = []
        self._expansions_built = 0
        self.logger = Mock()


class TestTrackBuildOrderExpansionCount(unittest.TestCase):
    def test_starting_main_hatchery_does_not_count_as_expansion(self):
        bot = _BotStub([_struct(1, "HATCHERY")])
        WickedZergBotProImpl._track_build_order(bot)
        self.assertTrue(bot._main_hatchery_tracked)
        self.assertEqual(bot._expansions_built, 0)
        self.assertEqual(len(bot._build_order_log), 1)
        self.assertEqual(bot._build_order_log[0]["structure"], "HATCHERY")

    def test_second_hatchery_counts_as_expansion(self):
        bot = _BotStub([_struct(1, "HATCHERY"), _struct(2, "HATCHERY", x=50, y=50)])
        WickedZergBotProImpl._track_build_order(bot)
        self.assertEqual(bot._expansions_built, 1)

    def test_three_hatcheries_two_expansions(self):
        bot = _BotStub(
            [
                _struct(1, "HATCHERY"),
                _struct(2, "HATCHERY", x=50, y=50),
                _struct(3, "HATCHERY", x=100, y=100),
            ]
        )
        WickedZergBotProImpl._track_build_order(bot)
        self.assertEqual(bot._expansions_built, 2)

    def test_unready_hatchery_does_not_count(self):
        bot = _BotStub([_struct(1, "HATCHERY", ready=False)])
        WickedZergBotProImpl._track_build_order(bot)
        # Nothing tracked: main flag stays unset, expansions stay zero.
        self.assertFalse(getattr(bot, "_main_hatchery_tracked", False))
        self.assertEqual(bot._expansions_built, 0)
        self.assertEqual(bot._build_order_log, [])

    def test_already_tracked_skipped(self):
        bot = _BotStub([_struct(1, "HATCHERY")])
        bot._tracked_structure_tags.add(1)
        WickedZergBotProImpl._track_build_order(bot)
        self.assertEqual(bot._expansions_built, 0)
        self.assertEqual(bot._build_order_log, [])

    def test_non_key_structure_ignored(self):
        bot = _BotStub([_struct(1, "QUEEN")])  # QUEEN isn't a key structure
        WickedZergBotProImpl._track_build_order(bot)
        self.assertEqual(bot._build_order_log, [])
        self.assertEqual(bot._expansions_built, 0)

    def test_other_key_structure_logged(self):
        bot = _BotStub([_struct(1, "SPAWNINGPOOL")])
        WickedZergBotProImpl._track_build_order(bot)
        self.assertEqual(len(bot._build_order_log), 1)
        self.assertEqual(bot._build_order_log[0]["structure"], "SPAWNINGPOOL")
        # Spawning pool is NOT a hatchery — must not affect expansion counter.
        self.assertEqual(bot._expansions_built, 0)

    def test_two_calls_only_count_each_structure_once(self):
        s1 = _struct(1, "HATCHERY")
        bot = _BotStub([s1])
        WickedZergBotProImpl._track_build_order(bot)
        WickedZergBotProImpl._track_build_order(bot)
        self.assertEqual(len(bot._build_order_log), 1)
        self.assertEqual(bot._expansions_built, 0)

    def test_game_time_format_is_mm_ss(self):
        bot = _BotStub([_struct(1, "SPAWNINGPOOL")], time=125.7)
        WickedZergBotProImpl._track_build_order(bot)
        entry = bot._build_order_log[0]
        self.assertEqual(entry["game_time_seconds"], 125.7)
        self.assertEqual(entry["game_time_formatted"], "2:05")


def _unit(tag, name, x=0.0, y=0.0):
    u = Mock()
    u.tag = tag
    type_id = Mock()
    type_id.name = name
    u.type_id = type_id
    pos = Mock()
    pos.x = x
    pos.y = y
    u.position = pos
    return u


class _UnitBotStub:
    """Stub for `_track_known_units` tests."""

    def __init__(self, units):
        self.units = units
        self._workers_created = 0


class TestTrackKnownUnitsWorkerCounter(unittest.TestCase):
    def test_starting_drones_do_not_count_as_created(self):
        # Zerg starts with 12 drones — none are "created" yet.
        bot = _UnitBotStub([_unit(i, "DRONE") for i in range(12)])
        WickedZergBotProImpl._track_known_units(bot)
        self.assertEqual(bot._workers_created, 0)
        self.assertEqual(len(bot._known_unit_tags), 12)

    def test_drone_built_after_seed_counts_as_created(self):
        bot = _UnitBotStub([_unit(i, "DRONE") for i in range(12)])
        WickedZergBotProImpl._track_known_units(bot)  # seed
        # Now 13 drones (one new)
        bot.units = [_unit(i, "DRONE") for i in range(13)]
        WickedZergBotProImpl._track_known_units(bot)
        self.assertEqual(bot._workers_created, 1)

    def test_two_new_drones_counted(self):
        bot = _UnitBotStub([_unit(i, "DRONE") for i in range(12)])
        WickedZergBotProImpl._track_known_units(bot)  # seed
        bot.units = [_unit(i, "DRONE") for i in range(14)]
        WickedZergBotProImpl._track_known_units(bot)
        self.assertEqual(bot._workers_created, 2)

    def test_destroyed_drone_pruned_from_known_tags(self):
        bot = _UnitBotStub([_unit(i, "DRONE") for i in range(12)])
        WickedZergBotProImpl._track_known_units(bot)
        # Lose drone tag 5
        bot.units = [_unit(i, "DRONE") for i in range(12) if i != 5]
        WickedZergBotProImpl._track_known_units(bot)
        self.assertNotIn(5, bot._known_unit_tags)
        self.assertEqual(len(bot._known_unit_tags), 11)

    def test_same_drone_seen_twice_only_seeds_once(self):
        d1 = _unit(1, "DRONE")
        bot = _UnitBotStub([d1])
        WickedZergBotProImpl._track_known_units(bot)
        WickedZergBotProImpl._track_known_units(bot)
        self.assertEqual(bot._workers_created, 0)

    def test_non_drone_units_do_not_increment_workers(self):
        bot = _UnitBotStub([_unit(1, "DRONE")])
        WickedZergBotProImpl._track_known_units(bot)  # seed
        bot.units = [_unit(1, "DRONE"), _unit(2, "ZERGLING"), _unit(3, "ZERGLING")]
        WickedZergBotProImpl._track_known_units(bot)
        # Two new zerglings, but no drones built
        self.assertEqual(bot._workers_created, 0)
        self.assertIn(2, bot._known_unit_tags)
        self.assertIn(3, bot._known_unit_tags)


if __name__ == "__main__":
    unittest.main()
