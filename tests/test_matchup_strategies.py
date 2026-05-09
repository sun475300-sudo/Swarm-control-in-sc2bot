# -*- coding: utf-8 -*-
"""Matchup strategy scenario tests for STRATEGY_PLAN Phase 5."""

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "wicked_zerg_challenger"))

from build_order_system import BuildOrderSystem, BuildOrderTransition, BuildOrderType
from combat.base_defense import BaseDefenseSystem
from combat.micro_combat import (
    ZvPMicroAdjustments,
    ZvTMicroAdjustments,
    ZvZMicroAdjustments,
)
from strategy_manager import EnemyRace, GamePhase, StrategyManager


class Blackboard:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class Point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other):
        pos = getattr(other, "position", other)
        return ((self.x - pos.x) ** 2 + (self.y - pos.y) ** 2) ** 0.5

    def towards(self, other, distance):
        pos = getattr(other, "position", other)
        total = self.distance_to(pos) or 1.0
        return Point(
            self.x + (pos.x - self.x) / total * distance,
            self.y + (pos.y - self.y) / total * distance,
        )

    def offset(self, delta):
        return Point(self.x + delta[0], self.y + delta[1])


class FakeUnit:
    def __init__(self, tag, name, position, health=100, shield=0):
        self.tag = tag
        self.type_id = SimpleNamespace(name=name)
        self.name = name
        self.position = position
        self.health = health
        self.health_max = max(health, 1)
        self.health_percentage = health / self.health_max
        self.shield = shield
        self.weapon_cooldown = 0
        self.ground_range = 1
        self.is_biological = True
        self.is_ground = name not in {"ORACLE", "VOIDRAY", "CARRIER", "MUTALISK"}
        self.can_attack = True

    def distance_to(self, other):
        return self.position.distance_to(other)

    def attack(self, target):
        return ("attack", self.tag, target)

    def move(self, target):
        return ("move", self.tag, target)

    def __call__(self, ability, target=None):
        return ("ability", self.tag, ability, target)


class FakeStructure(FakeUnit):
    pass


class UnitList(list):
    @property
    def amount(self):
        return len(self)

    @property
    def exists(self):
        return bool(self)

    @property
    def first(self):
        return self[0] if self else None


class FakeWorkers:
    amount = 30


class FakeBot:
    def __init__(self, enemy_race="Race.Terran", blackboard=None):
        self.time = 120.0
        self.iteration = 22
        self.enemy_race = enemy_race
        self.blackboard = blackboard or Blackboard()
        self.supply_used = 12
        self.supply_cap = 14
        self.minerals = 50
        self.vespene = 0
        self.start_location = Point(10, 10)
        self.enemy_start_locations = [Point(100, 100)]
        self.game_info = SimpleNamespace(map_center=Point(50, 50))
        self.townhalls = UnitList([FakeStructure(900, "HATCHERY", Point(10, 10))])
        self.enemy_units = []
        self.enemy_structures = []
        self.units = UnitList()
        self.structures = UnitList()
        self.workers = FakeWorkers()
        self.state = SimpleNamespace(
            upgrades=[],
            effects=[],
        )
        self.actions = []

    def do(self, action):
        self.actions.append(action)

    def already_pending_upgrade(self, _upgrade):
        return False


class TestZvTStrategies(unittest.TestCase):
    def test_build_selection_default(self):
        system = BuildOrderSystem(FakeBot("Race.Terran"))

        self.assertEqual(system.current_build_order, BuildOrderType.HATCH_FIRST_16)
        self.assertEqual(system.current_matchup_build_key, "hatch_first_16")

    def test_build_switch_on_proxy(self):
        bot = FakeBot("Race.Terran", Blackboard({"enemy_proxy_detected": True}))
        system = BuildOrderSystem(bot)

        self.assertEqual(system._select_zvt_build(), "aggressive_pool_first")

    def test_counter_bio(self):
        bot = FakeBot("Race.Terran")
        bot.time = 360.0
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.TERRAN
        manager.game_phase = GamePhase.MID
        manager._cached_enemy_composition = {"MARINE": 8, "MARAUDER": 2}

        manager._apply_zvt_composition_timeline()

        ratios = manager.get_unit_ratios()
        self.assertEqual(bot.blackboard.get("zvt_enemy_composition"), "vs_bio")
        self.assertGreaterEqual(ratios["baneling"], 0.24)

    def test_counter_mech(self):
        bot = FakeBot("Race.Terran")
        bot.time = 360.0
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.TERRAN
        manager.game_phase = GamePhase.MID
        manager._cached_enemy_composition = {"SIEGETANK": 2, "HELLION": 3}

        manager._apply_zvt_composition_timeline()

        ratios = manager.get_unit_ratios()
        self.assertEqual(bot.blackboard.get("zvt_enemy_composition"), "vs_mech")
        self.assertGreaterEqual(ratios["ravager"], 0.29)

    def test_medivac_drop_response(self):
        bot = FakeBot("Race.Terran")
        bot.time = 180.0
        bot.units = UnitList([FakeUnit(10, "QUEEN", Point(12, 10))])
        bot.units += [FakeUnit(20 + i, "ZERGLING", Point(13 + i, 10)) for i in range(4)]
        bot.units += [FakeUnit(100 + i, "ROACH", Point(35 + i, 35)) for i in range(8)]
        bot.enemy_units = [FakeUnit(500, "MEDIVAC", Point(16, 16))]
        defense = BaseDefenseSystem(bot)

        asyncio.run(defense.handle_multi_base_drop_defense(110))

        self.assertTrue(bot.blackboard.get("drop_defense_active"))
        self.assertEqual(bot.blackboard.get("drop_defense_target"), "MEDIVAC")
        self.assertTrue(any(action[0] == "attack" for action in bot.actions))

    def test_siege_tank_surround(self):
        bot = FakeBot("Race.Terran")
        lings = [FakeUnit(i, "ZERGLING", Point(8 + i, 8)) for i in range(8)]
        tank = FakeUnit(200, "SIEGETANKSIEGED", Point(12, 12))

        handled = ZvTMicroAdjustments(bot).apply(lings, [tank])

        self.assertGreaterEqual(len(handled), 4)
        self.assertTrue(any(action[0] == "move" for action in bot.actions))


class TestZvPStrategies(unittest.TestCase):
    def test_build_selection_default(self):
        system = BuildOrderSystem(FakeBot("Race.Protoss"))

        self.assertEqual(system.current_build_order, BuildOrderType.ROACH_RUSH)
        self.assertEqual(system.current_matchup_build_key, "roach_rush")

    def test_build_switch_on_cannon_rush(self):
        bot = FakeBot("Race.Protoss", Blackboard({"enemy_cannon_rush_detected": True}))
        system = BuildOrderSystem(bot)

        self.assertEqual(system._select_zvp_build(), "ling_flood_anti_cannon")

    def test_counter_skytoss(self):
        bot = FakeBot("Race.Protoss")
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.PROTOSS
        manager.game_phase = GamePhase.LATE
        manager._cached_enemy_composition = {"CARRIER": 2}

        manager._apply_zvp_counter_rules()

        ratios = manager.get_unit_ratios()
        self.assertEqual(bot.blackboard.get("zvp_counter_rule"), "skytoss_transition")
        self.assertGreaterEqual(ratios["corruptor"], 0.24)

    def test_storm_dodge(self):
        bot = FakeBot("Race.Protoss")
        bot.state.effects = [
            SimpleNamespace(id=SimpleNamespace(name="PSYCHICSTORM"), positions=[Point(10, 10)])
        ]
        ling = FakeUnit(1, "ZERGLING", Point(11, 10))

        handled = ZvPMicroAdjustments(bot).apply([ling], [])

        self.assertIn(1, handled)
        self.assertTrue(any(action[0] == "move" for action in bot.actions))

    def test_dt_emergency(self):
        blackboard = Blackboard({"dark_shrine_scouted": True})
        bot = FakeBot("Race.Protoss", blackboard)
        bot.time = 320.0
        manager = StrategyManager(bot, blackboard)
        manager.detected_enemy_race = EnemyRace.PROTOSS
        manager._cached_enemy_composition = {}

        manager._apply_emergency_response_table()

        self.assertEqual(blackboard.get("emergency_response_key"), "dt_rush")
        self.assertTrue(blackboard.get("urgent_overseer"))
        self.assertTrue(blackboard.get("urgent_spore_all_bases"))


class TestZvZStrategies(unittest.TestCase):
    def test_build_selection_default(self):
        system = BuildOrderSystem(FakeBot("Race.Zerg"))

        self.assertEqual(system.current_build_order, BuildOrderType.SAFE_14POOL)
        self.assertEqual(system.current_matchup_build_key, "safe_14pool")

    def test_ling_bane_micro(self):
        bot = FakeBot("Race.Zerg")
        ling = FakeUnit(1, "ZERGLING", Point(10, 10))
        bane = FakeUnit(2, "BANELING", Point(8, 8))
        enemy_bane = FakeUnit(20, "BANELING", Point(12, 10))
        enemy_lings = [FakeUnit(30 + i, "ZERGLING", Point(10 + i * 0.2, 10)) for i in range(4)]

        handled = ZvZMicroAdjustments(bot).apply([ling, bane], [enemy_bane] + enemy_lings)

        self.assertIn(1, handled)
        self.assertIn(2, handled)

    def test_roach_transition(self):
        bot = FakeBot("Race.Zerg", Blackboard({"enemy_ling_flood_detected": True}))
        system = BuildOrderSystem(bot)

        self.assertEqual(system._select_zvz_build(), "roach_warren_macro")

    def test_muta_counter(self):
        bot = FakeBot("Race.Zerg")
        bot.time = 360.0
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.ZERG
        manager.game_phase = GamePhase.MID
        manager._cached_enemy_composition = {"MUTALISK": 3}

        manager._apply_zvz_composition_timeline()

        ratios = manager.get_unit_ratios()
        self.assertEqual(bot.blackboard.get("zvz_enemy_composition"), "vs_muta")
        self.assertGreaterEqual(ratios["hydralisk"], 0.49)
        self.assertTrue(bot.blackboard.get("urgent_spore_all_bases"))


class TestBuildTransitions(unittest.TestCase):
    def test_cheese_to_defense(self):
        transition = BuildOrderTransition()
        result = asyncio.run(
            transition.check_transition(90, Blackboard({"cheese_detected": True}))
        )

        self.assertEqual(result, "emergency_defense")
        self.assertTrue(transition.transition_triggered)

    def test_greedy_on_expand(self):
        transition = BuildOrderTransition()
        result = asyncio.run(
            transition.check_transition(
                220,
                Blackboard({"enemy_expand_confirmed": True, "enemy_aggression": False}),
            )
        )

        self.assertEqual(result, "greedy_macro")
        self.assertFalse(transition.transition_triggered)

    def test_timing_attack_trigger(self):
        blackboard = Blackboard({"army_power_ratio": 1.5})
        bot = FakeBot("Race.Zerg", blackboard)
        bot.time = 220.0
        bot.units = UnitList([FakeUnit(i, "ZERGLING", Point(20, 20)) for i in range(12)])
        bot.units += [FakeUnit(100 + i, "BANELING", Point(20, 20)) for i in range(6)]
        bot.state.upgrades = [SimpleNamespace(name="ZERGLINGMOVEMENTSPEED")]
        manager = StrategyManager(bot, blackboard)
        manager.detected_enemy_race = EnemyRace.ZERG
        manager._cached_enemy_composition = {}

        manager._apply_timing_attack_system()

        self.assertTrue(blackboard.get("timing_attack_active"))
        self.assertEqual(blackboard.get("timing_attack_key"), "ling_bane_allin")

    def test_timing_attack_retreat(self):
        blackboard = Blackboard({"roach_speed_done": True, "army_power_ratio": 1.8})
        bot = FakeBot("Race.Protoss", blackboard)
        bot.time = 360.0
        bot.units = UnitList([FakeUnit(i, "ROACH", Point(20, 20)) for i in range(10)])
        manager = StrategyManager(bot, blackboard)
        manager.detected_enemy_race = EnemyRace.PROTOSS
        manager._cached_enemy_composition = {"IMMORTAL": 3}

        manager._apply_timing_attack_system()

        self.assertFalse(blackboard.get("timing_attack_active"))
        self.assertTrue(blackboard.get("timing_attack_retreat"))


if __name__ == "__main__":
    unittest.main()
