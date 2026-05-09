#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intel_manager import IntelManager
from scouting_system import ScoutingSystem, UnitTypeId
from strategy_manager import EnemyRace, GamePhase, StrategyManager


class FakePoint:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def towards(self, other, distance):
        total = self.distance_to(other)
        if total == 0:
            return FakePoint(self.x, self.y)
        ratio = distance / total
        return FakePoint(self.x + (other.x - self.x) * ratio, self.y + (other.y - self.y) * ratio)

    def offset(self, delta):
        return FakePoint(self.x + delta[0], self.y + delta[1])

    def __repr__(self):
        return f"FakePoint({self.x:.1f}, {self.y:.1f})"


class FakeBlackboard:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeType:
    def __init__(self, name):
        self.name = name


class FakeUnit:
    def __init__(self, name, tag=1, position=None, idle=True):
        self.type_id = FakeType(name)
        self.tag = tag
        self.position = position or FakePoint(0, 0)
        self.is_idle = idle
        self.move = Mock(return_value=f"move-{tag}")

    def __call__(self, ability):
        return f"ability-{ability}-{self.tag}"


class FakeUnits(list):
    @property
    def amount(self):
        return len(self)

    @property
    def first(self):
        return self[0] if self else None

    @property
    def random(self):
        return self[0] if self else None

    def filter(self, predicate):
        return FakeUnits([unit for unit in self if predicate(unit)])

    def closest_to(self, target):
        return min(self, key=lambda unit: unit.position.distance_to(target)) if self else None

    def find_by_tag(self, tag):
        for unit in self:
            if unit.tag == tag:
                return unit
        return None


class TruthyEmptyUnits:
    amount = 0

    def __bool__(self):
        return True

    def __len__(self):
        return 0

    def filter(self, *_args, **_kwargs):
        return self

    def closest_to(self, *_args, **_kwargs):
        raise AssertionError("closest_to should not run on an empty group")

    @property
    def first(self):
        raise AssertionError("first should not run on an empty group")

    @property
    def random(self):
        raise AssertionError("random should not run on an empty group")


def make_structure(name, position):
    structure = MagicMock()
    structure.type_id = FakeType(name)
    structure.position = position
    structure.build_progress = 1.0
    return structure


class TestSprint2ScoutingSystem(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.time = 120.0
        self.bot.blackboard = FakeBlackboard()
        self.bot.enemy_start_locations = [FakePoint(100, 100)]
        self.bot.start_location = FakePoint(10, 10)
        self.bot.game_info = MagicMock()
        self.bot.game_info.map_center = FakePoint(50, 50)
        self.bot.expansion_locations_list = [
            FakePoint(100, 100),
            FakePoint(88, 88),
            FakePoint(75, 75),
            FakePoint(62, 62),
        ]
        self.bot.watchtowers = [FakePoint(50, 40)]
        self.bot.enemy_units = []
        self.bot.enemy_structures = []
        self.bot.do = Mock()
        self.scouting = ScoutingSystem(self.bot)

    def test_overlord_scout_interval_changes_after_early_game(self):
        self.assertEqual(self.scouting.get_overlord_scout_interval(120.0), 15.0)
        self.assertEqual(self.scouting.get_overlord_scout_interval(360.0), 30.0)

    def test_overlord_pipeline_records_base_scouted_flags(self):
        target = self.scouting.select_overlord_scout_target({})
        self.assertIsNotNone(target)
        self.assertEqual(
            self.bot.blackboard.get("active_overlord_scout_target"),
            "enemy_main_ramp",
        )

        natural = self.scouting._enemy_natural()
        self.scouting.record_scouted_location(natural, "enemy_natural")

        self.assertTrue(self.bot.blackboard.get("enemy_base_scouted"))
        self.assertTrue(self.bot.blackboard.get("enemy_natural_scouted"))

    def test_zergling_patrol_assigns_route_target(self):
        zergling = FakeUnit("ZERGLING", tag=7, position=FakePoint(20, 20))

        result = self.scouting.assign_zergling_patrol(zergling)

        self.assertTrue(result)
        self.assertIn(7, self.scouting.zergling_patrol_tags)
        self.bot.do.assert_called_once()

    def test_cloak_detection_requests_overseer_when_no_detector_exists(self):
        dark_templar = FakeUnit("DARKTEMPLAR", tag=20, position=FakePoint(40, 40))
        overlord = FakeUnit("OVERLORD", tag=3, position=FakePoint(12, 12))
        self.bot.enemy_units = [dark_templar]

        def units_by_type(unit_type):
            name = getattr(unit_type, "name", str(unit_type))
            if name == "OVERLORD":
                return FakeUnits([overlord])
            if name == "OVERSEER":
                return FakeUnits([])
            return FakeUnits([])

        self.bot.units = units_by_type

        result = self.scouting.handle_cloak_detection()

        self.assertFalse(result)
        self.assertTrue(self.bot.blackboard.get("cloak_threat_detected"))
        self.assertTrue(self.bot.blackboard.get("overseer_morph_requested"))
        self.assertTrue(self.bot.blackboard.get("urgent_overseer"))

    def test_replacement_overlord_skips_truthy_empty_group(self):
        self.bot.units = Mock(return_value=TruthyEmptyUnits())

        result = self.scouting.get_replacement_overlord(FakePoint(40, 40))

        self.assertIsNone(result)

    def test_cloak_detection_skips_truthy_empty_detector_and_overlord_groups(self):
        dark_templar = FakeUnit("DARKTEMPLAR", tag=20, position=FakePoint(40, 40))
        self.bot.enemy_units = [dark_templar]

        def units_by_type(unit_type):
            if unit_type in (UnitTypeId.OVERSEER, UnitTypeId.OVERLORD):
                return TruthyEmptyUnits()
            return FakeUnits([])

        self.bot.units = units_by_type

        result = self.scouting.handle_cloak_detection()

        self.assertFalse(result)
        self.assertTrue(self.bot.blackboard.get("overseer_morph_requested"))
        self.bot.do.assert_not_called()


class TestSprint2IntelAndAirResponse(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.time = 120.0
        self.bot.iteration = 22
        self.bot.enemy_race = MagicMock()
        self.bot.enemy_race.name = "Terran"
        self.bot.enemy_units = []
        self.bot.enemy_structures = []
        self.bot.townhalls = []
        self.bot.blackboard = FakeBlackboard()
        self.bot.data_cache = None
        self.bot.enemy_start_locations = [FakePoint(100, 100)]
        self.bot.start_location = FakePoint(10, 10)
        self.bot.all_units = []
        self.intel = IntelManager(self.bot)

    def test_proxy_barracks_pattern_sets_aggression_flags(self):
        self.bot.enemy_structures = [
            make_structure("BARRACKS", FakePoint(25, 25)),
            make_structure("BARRACKS", FakePoint(26, 25)),
        ]

        self.intel.update(0)

        self.assertEqual(self.intel.get_enemy_build_pattern(), "proxy_barracks")
        self.assertIn("spine_crawler", self.intel.get_recommended_response())
        self.assertTrue(self.bot.blackboard.get("enemy_aggression"))
        self.assertTrue(self.bot.blackboard.get("urgent_spine_all_bases"))

    def test_battlecruiser_rush_sets_air_warning_flags(self):
        self.bot.time = 300.0
        self.bot.enemy_structures = [
            make_structure("STARPORT", FakePoint(92, 92)),
            make_structure("FUSIONCORE", FakePoint(94, 94)),
        ]

        self.intel.update(0)

        self.assertEqual(self.intel.get_enemy_build_pattern(), "battlecruiser_rush")
        self.assertTrue(self.bot.blackboard.get("AIR_THREAT_INCOMING"))
        self.assertTrue(self.bot.blackboard.get("urgent_spore_all_bases"))

    def test_strategy_reacts_to_air_threat_before_air_units_visible(self):
        self.bot.blackboard.set("AIR_THREAT_INCOMING", True)
        strategy = StrategyManager(self.bot, self.bot.blackboard)
        strategy.detected_enemy_race = EnemyRace.TERRAN
        strategy.game_phase = GamePhase.MID

        strategy._detect_blackboard_air_threat()

        self.assertTrue(strategy.emergency_spore_requested)
        self.assertTrue(self.bot.blackboard.get("air_threat_response_active"))
        self.assertIn("hydralisk", self.bot.blackboard.get("unit_ratios"))


if __name__ == "__main__":
    unittest.main()
