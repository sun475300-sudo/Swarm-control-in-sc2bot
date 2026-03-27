# -*- coding: utf-8 -*-
"""
UnitFactory 테스트

gas ratio, combat mode, larva saving, emergency mode,
unit table, priority queue 커버리지
"""
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import unittest
import sys
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unit_factory import UnitFactory


class FakeBot:
    """UnitFactory 테스트용 Mock Bot"""
    def __init__(self):
        self.time = 300.0
        self.minerals = 500
        self.vespene = 200
        self.supply_army = 30
        self.supply_left = 10
        self.enemy_race = None
        self.strategy_manager = None
        self.rogue_tactics = None


class TestUnitFactoryInit(unittest.TestCase):
    def test_default_init(self):
        bot = FakeBot()
        uf = UnitFactory(bot)
        self.assertEqual(uf.min_gas_reserve, 50)
        self.assertEqual(uf.larva_pressure_threshold, 6)
        self.assertEqual(uf.gas_unit_ratio_target, 0.50)
        self.assertFalse(uf._combat_mode)

    def test_init_with_config(self):
        bot = FakeBot()
        config = MagicMock()
        config.MIN_GAS_RESERVE = 100
        config.LARVA_PRESSURE_THRESHOLD = 8
        uf = UnitFactory(bot, config=config)
        self.assertEqual(uf.min_gas_reserve, 100)
        self.assertEqual(uf.larva_pressure_threshold, 8)

    def test_init_with_blackboard(self):
        bot = FakeBot()
        bb = MagicMock()
        uf = UnitFactory(bot, blackboard=bb)
        self.assertIs(uf.blackboard, bb)


class TestShouldSaveLarva(unittest.TestCase):
    def test_no_strategy_no_rogue(self):
        bot = FakeBot()
        uf = UnitFactory(bot)
        self.assertFalse(uf._should_save_larva())

    def test_strategy_says_save(self):
        bot = FakeBot()
        bot.strategy_manager = MagicMock()
        bot.strategy_manager.should_save_larva.return_value = True
        uf = UnitFactory(bot)
        self.assertTrue(uf._should_save_larva())

    def test_rogue_larva_saving_active(self):
        bot = FakeBot()
        bot.rogue_tactics = MagicMock()
        bot.rogue_tactics.larva_saving_active = True
        bot.rogue_tactics.preparing_baneling_drop = False
        uf = UnitFactory(bot)
        self.assertTrue(uf._should_save_larva())

    def test_rogue_baneling_drop(self):
        bot = FakeBot()
        bot.rogue_tactics = MagicMock()
        bot.rogue_tactics.larva_saving_active = False
        bot.rogue_tactics.preparing_baneling_drop = True
        uf = UnitFactory(bot)
        self.assertTrue(uf._should_save_larva())

    def test_no_save_needed(self):
        bot = FakeBot()
        bot.strategy_manager = MagicMock()
        bot.strategy_manager.should_save_larva.return_value = False
        bot.rogue_tactics = MagicMock()
        bot.rogue_tactics.larva_saving_active = False
        bot.rogue_tactics.preparing_baneling_drop = False
        uf = UnitFactory(bot)
        self.assertFalse(uf._should_save_larva())


class TestGasRatioTarget(unittest.TestCase):
    def test_terran_ratio(self):
        bot = FakeBot()
        bot.enemy_race = "Terran"
        uf = UnitFactory(bot)
        uf._update_gas_ratio_target()
        self.assertEqual(uf.gas_unit_ratio_target, 0.50)

    def test_protoss_ratio(self):
        bot = FakeBot()
        bot.enemy_race = "Protoss"
        uf = UnitFactory(bot)
        uf._update_gas_ratio_target()
        self.assertEqual(uf.gas_unit_ratio_target, 0.55)

    def test_zerg_ratio(self):
        bot = FakeBot()
        bot.enemy_race = "Zerg"
        uf = UnitFactory(bot)
        uf._update_gas_ratio_target()
        self.assertEqual(uf.gas_unit_ratio_target, 0.45)

    def test_unknown_race_fallback(self):
        bot = FakeBot()
        bot.enemy_race = None
        uf = UnitFactory(bot)
        original = uf.gas_unit_ratio_target
        uf._update_gas_ratio_target()
        self.assertEqual(uf.gas_unit_ratio_target, original)

    def test_strategy_manager_race(self):
        bot = FakeBot()
        bot.strategy_manager = MagicMock()
        bot.strategy_manager.detected_enemy_race = MagicMock()
        bot.strategy_manager.detected_enemy_race.value = "Protoss"
        uf = UnitFactory(bot)
        uf._update_gas_ratio_target()
        self.assertEqual(uf.gas_unit_ratio_target, 0.55)


class TestEmergencyMode(unittest.TestCase):
    def test_no_strategy_manager(self):
        bot = FakeBot()
        uf = UnitFactory(bot)
        self.assertFalse(uf._is_emergency_mode())

    def test_emergency_active(self):
        bot = FakeBot()
        bot.strategy_manager = MagicMock()
        bot.strategy_manager.emergency_active = True
        uf = UnitFactory(bot)
        self.assertTrue(uf._is_emergency_mode())

    def test_not_emergency(self):
        bot = FakeBot()
        bot.strategy_manager = MagicMock()
        bot.strategy_manager.emergency_active = False
        uf = UnitFactory(bot)
        self.assertFalse(uf._is_emergency_mode())


class TestCombatMode(unittest.TestCase):
    def test_initial_not_combat(self):
        bot = FakeBot()
        uf = UnitFactory(bot)
        result = uf._check_combat_mode(0)
        self.assertFalse(result)

    def test_skip_check_within_interval(self):
        bot = FakeBot()
        uf = UnitFactory(bot)
        uf._combat_mode = True
        uf._last_combat_check = 100
        result = uf._check_combat_mode(110)  # within 22 frame interval
        self.assertTrue(result)  # returns cached value

    def test_emergency_triggers_combat(self):
        bot = FakeBot()
        bot.strategy_manager = MagicMock()
        bot.strategy_manager.emergency_active = True
        bot.strategy_manager.defense_active = False
        uf = UnitFactory(bot)
        uf._last_combat_check = -100  # force check
        result = uf._check_combat_mode(100)
        self.assertTrue(result)

    def test_supply_loss_triggers_combat(self):
        bot = FakeBot()
        bot.supply_army = 30
        uf = UnitFactory(bot)
        uf._last_supply_army = 45  # 15 supply loss
        result = uf._check_combat_mode(100)
        self.assertTrue(result)


class TestRaceGasRatios(unittest.TestCase):
    def test_all_races_have_ratios(self):
        bot = FakeBot()
        uf = UnitFactory(bot)
        self.assertIn("Terran", uf.race_gas_ratios)
        self.assertIn("Protoss", uf.race_gas_ratios)
        self.assertIn("Zerg", uf.race_gas_ratios)
        self.assertIn("Unknown", uf.race_gas_ratios)

    def test_ratios_are_reasonable(self):
        bot = FakeBot()
        uf = UnitFactory(bot)
        for race, ratio in uf.race_gas_ratios.items():
            self.assertGreater(ratio, 0.0)
            self.assertLess(ratio, 1.0)


if __name__ == "__main__":
    unittest.main()
