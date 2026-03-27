# -*- coding: utf-8 -*-
"""
Blackboard (GameStateBlackboard) 테스트

authority mode, production queue, cache, building reservation,
state queries 전체 커버리지
"""
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from blackboard import (
    GameStateBlackboard, Blackboard,
    AuthorityMode, GamePhase, ThreatLevel,
    UnitCounts, ThreatInfo, ResourceState,
)


class TestBlackboardInit(unittest.TestCase):
    def test_initial_state(self):
        bb = GameStateBlackboard()
        self.assertEqual(bb.game_time, 0.0)
        self.assertEqual(bb.game_phase, GamePhase.OPENING)
        self.assertEqual(bb.authority_mode, AuthorityMode.BALANCED)
        self.assertFalse(bb.is_under_attack)
        self.assertEqual(bb.minerals, 0)

    def test_alias(self):
        self.assertIs(Blackboard, GameStateBlackboard)


class TestGameInfo(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_update_game_info_opening(self):
        self.bb.update_game_info(60.0, 100)
        self.assertEqual(self.bb.game_time, 60.0)
        self.assertEqual(self.bb.iteration, 100)
        self.assertEqual(self.bb.game_phase, GamePhase.OPENING)

    def test_update_game_info_early(self):
        self.bb.update_game_info(200.0, 500)
        self.assertEqual(self.bb.game_phase, GamePhase.EARLY_GAME)

    def test_update_game_info_mid(self):
        self.bb.update_game_info(400.0)
        self.assertEqual(self.bb.game_phase, GamePhase.MID_GAME)

    def test_update_game_info_late(self):
        self.bb.update_game_info(800.0)
        self.assertEqual(self.bb.game_phase, GamePhase.LATE_GAME)


class TestResources(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_update_resources(self):
        self.bb.update_resources(500, 200, 50, 100)
        self.assertEqual(self.bb.resources.minerals, 500)
        self.assertEqual(self.bb.resources.vespene, 200)
        self.assertEqual(self.bb.resources.supply_used, 50)
        self.assertEqual(self.bb.resources.supply_cap, 100)
        self.assertEqual(self.bb.resources.supply_left, 50)
        # flat accessors
        self.assertEqual(self.bb.minerals, 500)
        self.assertEqual(self.bb.vespene, 200)

    def test_supply_blocked(self):
        self.bb.update_resources(100, 50, 100, 100)
        self.assertTrue(self.bb.resources.is_supply_blocked)

    def test_supply_not_blocked_at_200(self):
        self.bb.update_resources(100, 50, 200, 200)
        self.assertFalse(self.bb.resources.is_supply_blocked)


class TestUnitCounts(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_update_and_get(self):
        self.bb.update_unit_count("ZERGLING", 10, 2)
        counts = self.bb.get_unit_count("ZERGLING")
        self.assertEqual(counts.current, 10)
        self.assertEqual(counts.pending, 2)
        self.assertEqual(counts.total, 12)

    def test_get_unknown_unit(self):
        counts = self.bb.get_unit_count("ULTRALISK")
        self.assertEqual(counts.current, 0)
        self.assertEqual(counts.total, 0)


class TestThreat(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_update_threat(self):
        self.bb.update_threat(ThreatLevel.HIGH, 60.0, 5, is_rushing=True, is_air_threat=True)
        self.assertEqual(self.bb.threat.level, ThreatLevel.HIGH)
        self.assertEqual(self.bb.threat.enemy_army_supply, 60.0)
        self.assertTrue(self.bb.threat.is_rushing)
        self.assertTrue(self.bb.threat.is_air_threat)

    def test_threat_detected_time(self):
        self.bb.game_time = 120.0
        self.bb.update_threat(ThreatLevel.MEDIUM)
        self.assertEqual(self.bb.threat.detected_at, 120.0)

    def test_low_threat_no_detection_time(self):
        self.bb.game_time = 60.0
        self.bb.update_threat(ThreatLevel.LOW)
        self.assertEqual(self.bb.threat.detected_at, 0.0)


class TestAuthorityMode(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_set_authority_mode(self):
        self.bb.set_authority_mode(AuthorityMode.EMERGENCY, "test")
        self.assertEqual(self.bb.authority_mode, AuthorityMode.EMERGENCY)

    def test_emergency_priority(self):
        self.bb.set_authority_mode(AuthorityMode.EMERGENCY)
        self.assertEqual(self.bb.get_authority_priority("DefenseCoordinator"), 0)
        self.assertEqual(self.bb.get_authority_priority("EconomyManager"), 3)
        self.assertEqual(self.bb.get_authority_priority("UnitFactory"), 3)

    def test_combat_priority(self):
        self.bb.set_authority_mode(AuthorityMode.COMBAT)
        self.assertEqual(self.bb.get_authority_priority("UnitFactory"), 0)
        self.assertEqual(self.bb.get_authority_priority("DefenseCoordinator"), 1)
        self.assertEqual(self.bb.get_authority_priority("EconomyManager"), 3)

    def test_strategy_priority(self):
        self.bb.set_authority_mode(AuthorityMode.STRATEGY)
        self.assertEqual(self.bb.get_authority_priority("AggressiveStrategies"), 0)
        self.assertEqual(self.bb.get_authority_priority("UnitFactory"), 1)

    def test_economy_priority(self):
        self.bb.set_authority_mode(AuthorityMode.ECONOMY)
        self.assertEqual(self.bb.get_authority_priority("EconomyManager"), 0)
        self.assertEqual(self.bb.get_authority_priority("DefenseCoordinator"), 1)

    def test_balanced_priority(self):
        self.assertEqual(self.bb.get_authority_priority("DefenseCoordinator"), 0)
        self.assertEqual(self.bb.get_authority_priority("UnitFactory"), 1)
        self.assertEqual(self.bb.get_authority_priority("AggressiveStrategies"), 1)
        self.assertEqual(self.bb.get_authority_priority("EconomyManager"), 2)

    def test_unknown_requester_defaults(self):
        self.assertEqual(self.bb.get_authority_priority("RandomSystem"), 2)

    def test_auto_adjust_emergency(self):
        self.bb.threat.is_rushing = True
        self.bb.auto_adjust_authority()
        self.assertEqual(self.bb.authority_mode, AuthorityMode.EMERGENCY)

    def test_auto_adjust_combat(self):
        self.bb.update_threat(ThreatLevel.HIGH)
        self.bb.auto_adjust_authority()
        self.assertEqual(self.bb.authority_mode, AuthorityMode.COMBAT)

    def test_auto_adjust_strategy(self):
        self.bb.current_strategy = "roach_rush"
        self.bb.build_order_complete = False
        self.bb.auto_adjust_authority()
        self.assertEqual(self.bb.authority_mode, AuthorityMode.STRATEGY)

    def test_auto_adjust_economy(self):
        self.bb.game_phase = GamePhase.OPENING
        self.bb.update_threat(ThreatLevel.NONE)
        self.bb.current_strategy = "none"
        self.bb.auto_adjust_authority()
        self.assertEqual(self.bb.authority_mode, AuthorityMode.ECONOMY)

    def test_auto_adjust_balanced(self):
        self.bb.game_phase = GamePhase.MID_GAME
        self.bb.update_threat(ThreatLevel.NONE)
        self.bb.current_strategy = "none"
        self.bb.auto_adjust_authority()
        self.assertEqual(self.bb.authority_mode, AuthorityMode.BALANCED)


class TestProductionQueue(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_request_and_get(self):
        self.bb.request_production("ROACH", 5, "UnitFactory", priority=1)
        result = self.bb.get_next_production()
        self.assertEqual(result, ("ROACH", 5, "UnitFactory"))

    def test_priority_order(self):
        self.bb.request_production("DRONE", 1, "EconomyManager", priority=3)
        self.bb.request_production("ZERGLING", 4, "DefenseCoordinator", priority=0)
        self.bb.request_production("ROACH", 2, "UnitFactory", priority=1)
        # Should get priority 0 first
        r1 = self.bb.get_next_production()
        r2 = self.bb.get_next_production()
        r3 = self.bb.get_next_production()
        self.assertEqual(r1[0], "ZERGLING")
        self.assertEqual(r2[0], "ROACH")
        self.assertEqual(r3[0], "DRONE")

    def test_empty_queue_returns_none(self):
        self.assertIsNone(self.bb.get_next_production())

    def test_duplicate_request_updates(self):
        self.bb.request_production("ROACH", 3, "UnitFactory", priority=1)
        self.bb.request_production("ROACH", 8, "UnitFactory", priority=1)
        result = self.bb.get_next_production()
        self.assertEqual(result[1], 8)  # updated count

    def test_clear_all(self):
        self.bb.request_production("ROACH", 5, "UnitFactory", priority=1)
        self.bb.request_production("DRONE", 1, "EconomyManager", priority=3)
        self.bb.clear_production_requests()
        self.assertIsNone(self.bb.get_next_production())

    def test_clear_by_requester(self):
        self.bb.request_production("ROACH", 5, "UnitFactory", priority=1)
        self.bb.request_production("DRONE", 1, "EconomyManager", priority=3)
        self.bb.clear_production_requests("EconomyManager")
        result = self.bb.get_next_production()
        self.assertEqual(result[0], "ROACH")
        self.assertIsNone(self.bb.get_next_production())


class TestBuildingReservation(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_reserve_building(self):
        self.bb.game_time = 100.0
        result = self.bb.reserve_building("SPAWNINGPOOL", "ProductionResilience")
        self.assertTrue(result)
        self.assertTrue(self.bb.is_building_reserved("SPAWNINGPOOL"))

    def test_double_reservation_fails(self):
        self.bb.game_time = 100.0
        self.bb.reserve_building("SPAWNINGPOOL", "ProductionResilience")
        result = self.bb.reserve_building("SPAWNINGPOOL", "EconomyManager")
        self.assertFalse(result)

    def test_reservation_expires(self):
        self.bb.game_time = 100.0
        self.bb.reserve_building("SPAWNINGPOOL", "A", duration=5.0)
        self.bb.game_time = 106.0
        self.assertFalse(self.bb.is_building_reserved("SPAWNINGPOOL", duration=5.0))
        # New reservation should succeed
        result = self.bb.reserve_building("SPAWNINGPOOL", "B", duration=5.0)
        self.assertTrue(result)

    def test_unreserved_building(self):
        self.assertFalse(self.bb.is_building_reserved("ROACHWARREN"))


class TestCache(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_set_and_get(self):
        self.bb.game_time = 10.0
        self.bb.cache_set("enemy_count", 5)
        self.assertEqual(self.bb.cache_get("enemy_count"), 5)

    def test_cache_expiry(self):
        self.bb.game_time = 10.0
        self.bb.cache_set("enemy_count", 5, ttl=2.0)
        self.bb.game_time = 13.0
        self.assertIsNone(self.bb.cache_get("enemy_count"))

    def test_cache_default(self):
        result = self.bb.cache_get("nonexistent", default=42)
        self.assertEqual(result, 42)

    def test_cache_clear(self):
        self.bb.cache_set("a", 1)
        self.bb.cache_set("b", 2)
        self.bb.cache_clear()
        self.assertIsNone(self.bb.cache_get("a"))
        self.assertIsNone(self.bb.cache_get("b"))

    def test_per_key_ttl(self):
        self.bb.game_time = 0.0
        self.bb.cache_set("short", "val1", ttl=1.0)
        self.bb.cache_set("long", "val2", ttl=10.0)
        self.bb.game_time = 2.0
        self.assertIsNone(self.bb.cache_get("short"))
        self.assertEqual(self.bb.cache_get("long"), "val2")


class TestStateQueries(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_should_defend_under_attack(self):
        self.bb.is_under_attack = True
        self.assertTrue(self.bb.should_defend())

    def test_should_defend_medium_threat(self):
        self.bb.update_threat(ThreatLevel.MEDIUM)
        self.assertTrue(self.bb.should_defend())

    def test_should_defend_rushing(self):
        self.bb.update_threat(ThreatLevel.LOW, is_rushing=True)
        self.assertTrue(self.bb.should_defend())

    def test_should_not_defend(self):
        self.bb.update_threat(ThreatLevel.NONE)
        self.assertFalse(self.bb.should_defend())

    def test_can_attack(self):
        self.bb.update_threat(ThreatLevel.NONE)
        self.bb.game_phase = GamePhase.MID_GAME
        self.assertTrue(self.bb.can_attack())

    def test_cannot_attack_during_opening(self):
        self.bb.update_threat(ThreatLevel.NONE)
        self.bb.game_phase = GamePhase.OPENING
        self.assertFalse(self.bb.can_attack())

    def test_cannot_attack_under_threat(self):
        self.bb.update_threat(ThreatLevel.HIGH)
        self.bb.game_phase = GamePhase.MID_GAME
        self.assertFalse(self.bb.can_attack())

    def test_should_expand(self):
        self.bb.update_threat(ThreatLevel.NONE)
        self.bb.update_resources(500, 100, 50, 100)
        self.assertTrue(self.bb.should_expand())

    def test_should_not_expand_low_minerals(self):
        self.bb.update_threat(ThreatLevel.NONE)
        self.bb.update_resources(100, 50, 50, 100)
        self.assertFalse(self.bb.should_expand())

    def test_should_not_expand_under_threat(self):
        self.bb.update_threat(ThreatLevel.LOW)
        self.bb.update_resources(500, 100, 50, 100)
        self.assertFalse(self.bb.should_expand())


class TestBackwardCompatibility(unittest.TestCase):
    def setUp(self):
        self.bb = GameStateBlackboard()

    def test_set_and_get(self):
        self.bb.set("custom_key", "custom_value")
        self.assertEqual(self.bb.get("custom_key"), "custom_value")

    def test_get_default(self):
        self.assertEqual(self.bb.get("missing", "fallback"), "fallback")

    def test_set_strategy_mode_syncs(self):
        self.bb.set("strategy_mode", "AGGRESSIVE")
        self.assertEqual(self.bb.strategy_mode, "AGGRESSIVE")

    def test_set_enemy_race_syncs(self):
        self.bb.set("enemy_race", "Protoss")
        self.assertEqual(self.bb.enemy_race, "Protoss")


if __name__ == "__main__":
    unittest.main()
