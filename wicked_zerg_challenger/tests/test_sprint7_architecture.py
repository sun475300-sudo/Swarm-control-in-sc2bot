# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from building_manager import BuildingManager, UnitTypeId
from core.manager_registry import get_all_manager_configs
from economy_manager import EconomyManager
from strategy_manager import StrategyManager
from utils.distance_cache import DistanceCache


class FakePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.calls = 0

    def distance_to(self, other):
        self.calls += 1
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class FakeBlackboard:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class FakeTechCoordinator:
    def __init__(self):
        self.requests = []

    def is_planned(self, structure_type):
        return False

    def request_structure(self, structure_type, location, priority, requester):
        self.requests.append((structure_type, location, priority, requester))
        return True


class FakeUnit:
    def __init__(self, position, can_attack=True):
        self.position = position
        self.can_attack = can_attack

    def distance_to(self, other):
        target = getattr(other, "position", other)
        return self.position.distance_to(target)


class TestSprint7Architecture(unittest.TestCase):
    def test_distance_cache_reuses_value_within_frame_and_clears_next_frame(self):
        cache = DistanceCache()
        a = FakePoint(0, 0)
        b = FakePoint(3, 4)

        self.assertEqual(cache.get(a, b, 10), 5.0)
        self.assertEqual(cache.get(a, b, 10), 5.0)
        self.assertEqual(a.calls, 1)
        self.assertEqual(cache.size, 1)

        self.assertEqual(cache.get(a, b, 11), 5.0)
        self.assertEqual(a.calls, 2)
        self.assertEqual(cache.size, 1)

    def test_building_manager_registered_in_manager_registry(self):
        configs = get_all_manager_configs()
        config = next(
            cfg for cfg in configs if cfg.attribute_name == "building_manager"
        )

        self.assertEqual(config.module_path, "building_manager")
        self.assertEqual(config.class_name, "BuildingManager")
        self.assertIn("blackboard", config.dependencies)

    def test_building_manager_routes_defensive_request_to_tech_coordinator(self):
        bot = SimpleNamespace(
            time=80.0,
            iteration=120,
            blackboard=FakeBlackboard(),
            tech_coordinator=FakeTechCoordinator(),
            townhalls=[FakeUnit(FakePoint(10, 10)), FakeUnit(FakePoint(60, 60))],
            enemy_units=[FakeUnit(FakePoint(12, 12))],
            start_location=FakePoint(5, 5),
        )

        manager = BuildingManager(bot)
        accepted = manager.request_defensive_building(
            spine=True, spore=True, requester="UnitTest"
        )

        self.assertTrue(accepted)
        self.assertEqual(len(bot.tech_coordinator.requests), 2)
        self.assertEqual(bot.tech_coordinator.requests[0][1].x, 10)
        self.assertTrue(bot.blackboard.get("urgent_spore_all_bases"))

    def test_building_manager_consumes_blackboard_urgent_flags_on_step(self):
        blackboard = FakeBlackboard()
        blackboard.set("urgent_spine_count", 2)
        blackboard.set("urgent_spore_all_bases", True)
        bot = SimpleNamespace(
            time=120.0,
            iteration=22,
            blackboard=blackboard,
            tech_coordinator=FakeTechCoordinator(),
            townhalls=[FakeUnit(FakePoint(20, 20))],
            enemy_units=[],
            start_location=FakePoint(20, 20),
        )
        manager = BuildingManager(bot)

        asyncio.run(manager.on_step(22))

        self.assertEqual(len(bot.tech_coordinator.requests), 3)

    def test_strategy_manager_delegates_defensive_building_requests(self):
        building_manager = MagicMock()
        bot = SimpleNamespace(building_manager=building_manager)
        blackboard = FakeBlackboard()
        strategy = StrategyManager.__new__(StrategyManager)
        strategy.bot = bot
        strategy.blackboard = blackboard
        strategy.emergency_spine_requested = False
        strategy.emergency_spore_requested = False

        StrategyManager._request_defensive_building(
            strategy, spine=True, spore=True
        )

        self.assertTrue(strategy.emergency_spine_requested)
        self.assertTrue(strategy.emergency_spore_requested)
        self.assertTrue(blackboard.get("urgent_spore_all_bases"))
        building_manager.request_defensive_building.assert_called_once_with(
            spine=True,
            spore=True,
            requester="StrategyManager",
        )

    def test_economy_manager_distance_helper_uses_cache(self):
        bot = MagicMock()
        bot.iteration = 33
        manager = EconomyManager(bot)
        a = FakePoint(0, 0)
        b = FakePoint(6, 8)

        self.assertEqual(manager._distance_between(a, b), 10.0)
        self.assertEqual(manager._distance_between(a, b), 10.0)
        self.assertEqual(a.calls, 1)


if __name__ == "__main__":
    unittest.main()
