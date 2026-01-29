# -*- coding: utf-8 -*-
"""
Unit Tests for config/unit_configs.py

Tests all configuration classes:
- CombatConfig
- BanelingConfig
- MutaliskConfig
- InfestorConfig
- EconomyConfig
- PotentialFieldConfig
- UpgradeConfig
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.unit_configs import (
    CombatConfig,
    BanelingConfig,
    MutaliskConfig,
    InfestorConfig,
    EconomyConfig,
    PotentialFieldConfig,
    UpgradeConfig,
    get_combat_config,
    get_baneling_config,
    get_mutalisk_config,
    get_infestor_config,
    get_economy_config,
    get_potential_field_config,
    get_upgrade_config
)


class TestCombatConfig(unittest.TestCase):
    """Test CombatConfig class"""

    def test_min_army_values(self):
        """Test minimum army requirements"""
        config = CombatConfig()
        self.assertEqual(config.MIN_ARMY_FOR_ATTACK, 6)
        self.assertEqual(config.MIN_MUTALISK_FOR_HARASS, 3)
        self.assertEqual(config.MIN_ROACH_FOR_TIMING, 8)

    def test_defense_settings(self):
        """Test defense configuration"""
        config = CombatConfig()
        self.assertEqual(config.DEFENSE_CHECK_INTERVAL, 3)
        self.assertEqual(config.DEFENSE_THREAT_THRESHOLD, 1)
        self.assertEqual(config.DEFENSE_RADIUS, 8)

    def test_endgame_settings(self):
        """Test endgame configuration"""
        config = CombatConfig()
        self.assertEqual(config.ENDGAME_PUSH_TIME, 360)
        self.assertEqual(config.ENDGAME_CHECK_INTERVAL, 110)

    def test_combat_unit_limit(self):
        """Test combat unit processing limit"""
        config = CombatConfig()
        self.assertEqual(config.MAX_COMBAT_UNITS_PER_UPDATE, 50)

    def test_get_combat_config_helper(self):
        """Test get_combat_config helper function"""
        config = get_combat_config()
        self.assertIsInstance(config, CombatConfig)


class TestBanelingConfig(unittest.TestCase):
    """Test BanelingConfig class"""

    def test_detonation_settings(self):
        """Test baneling detonation configuration"""
        config = BanelingConfig()
        self.assertEqual(config.MIN_ENEMIES_FOR_DETONATION, 3)
        self.assertEqual(config.OPTIMAL_DETONATION_RADIUS, 2.5)
        self.assertEqual(config.SPLASH_DAMAGE_RADIUS, 2.2)

    def test_landmine_tactics(self):
        """Test landmine tactical settings"""
        config = BanelingConfig()
        self.assertEqual(config.LANDMINE_BURROW_RANGE, 3.5)
        self.assertEqual(config.LANDMINE_CHOKE_PRIORITY, 1)
        self.assertEqual(config.LANDMINE_EXPANSION_PRIORITY, 2)

    def test_retreat_threshold(self):
        """Test retreat HP threshold"""
        config = BanelingConfig()
        self.assertEqual(config.RETREAT_HP_THRESHOLD, 0.3)

    def test_get_baneling_config_helper(self):
        """Test get_baneling_config helper function"""
        config = get_baneling_config()
        self.assertIsInstance(config, BanelingConfig)


class TestMutaliskConfig(unittest.TestCase):
    """Test MutaliskConfig class"""

    def test_hp_management(self):
        """Test HP management thresholds"""
        config = MutaliskConfig()
        self.assertEqual(config.REGEN_HP_THRESHOLD, 0.7)
        self.assertEqual(config.RETREAT_HP_THRESHOLD, 0.3)

    def test_magic_box_settings(self):
        """Test magic box configuration"""
        config = MutaliskConfig()
        self.assertEqual(config.MAGIC_BOX_SPREAD_DISTANCE, 3.0)
        self.assertEqual(config.MAGIC_BOX_MIN_UNITS, 4)

    def test_targeting_settings(self):
        """Test targeting configuration"""
        config = MutaliskConfig()
        self.assertEqual(config.WORKER_HARASSMENT_RANGE, 9.0)
        self.assertIn("THOR", config.SPLASH_THREAT_UNITS)
        self.assertIn("ARCHON", config.SPLASH_THREAT_UNITS)
        self.assertIn("LIBERATOR", config.SPLASH_THREAT_UNITS)

    def test_get_mutalisk_config_helper(self):
        """Test get_mutalisk_config helper function"""
        config = get_mutalisk_config()
        self.assertIsInstance(config, MutaliskConfig)


class TestInfestorConfig(unittest.TestCase):
    """Test InfestorConfig class"""

    def test_fungal_growth_settings(self):
        """Test Fungal Growth configuration"""
        config = InfestorConfig()
        self.assertEqual(config.FUNGAL_MIN_ENEMIES, 3)
        self.assertEqual(config.FUNGAL_OPTIMAL_RANGE, 10.0)
        self.assertEqual(config.FUNGAL_ENERGY_COST, 75)

    def test_burrow_movement_settings(self):
        """Test Burrow Movement configuration"""
        config = InfestorConfig()
        self.assertEqual(config.BURROW_MOVE_SAFETY_RANGE, 15.0)
        self.assertEqual(config.BURROW_INFILTRATION_RANGE, 8.0)

    def test_neural_parasite_settings(self):
        """Test Neural Parasite configuration"""
        config = InfestorConfig()
        self.assertEqual(config.NEURAL_PRIORITY_HP_THRESHOLD, 0.5)
        self.assertEqual(config.NEURAL_ENERGY_COST, 50)

    def test_get_infestor_config_helper(self):
        """Test get_infestor_config helper function"""
        config = get_infestor_config()
        self.assertIsInstance(config, InfestorConfig)


class TestEconomyConfig(unittest.TestCase):
    """Test EconomyConfig class"""

    def test_gold_mineral_settings(self):
        """Test gold mineral configuration"""
        config = EconomyConfig()
        self.assertEqual(config.GOLD_MINERAL_THRESHOLD, 1200)
        self.assertEqual(config.GOLD_BASE_PRIORITY, 5)

    def test_expansion_settings(self):
        """Test expansion configuration"""
        config = EconomyConfig()
        self.assertEqual(config.EXPANSION_MINERAL_THRESHOLD, 400)
        self.assertEqual(config.EXPANSION_COOLDOWN, 120)
        self.assertEqual(config.EXPANSION_SAFETY_RADIUS, 30)

    def test_worker_settings(self):
        """Test worker configuration"""
        config = EconomyConfig()
        self.assertEqual(config.WORKER_CAP, 80)
        self.assertEqual(config.WORKER_PER_BASE, 22)

    def test_resource_balancing(self):
        """Test resource balancing configuration"""
        config = EconomyConfig()
        self.assertEqual(config.GAS_OVERFLOW_THRESHOLD, 3000)
        self.assertEqual(config.MINERAL_DEFICIT_THRESHOLD, 200)

    def test_get_economy_config_helper(self):
        """Test get_economy_config helper function"""
        config = get_economy_config()
        self.assertIsInstance(config, EconomyConfig)


class TestPotentialFieldConfig(unittest.TestCase):
    """Test PotentialFieldConfig class"""

    def test_basic_weights(self):
        """Test basic field weights"""
        config = PotentialFieldConfig()
        self.assertEqual(config.ALLY_WEIGHT, 1.0)
        self.assertEqual(config.ENEMY_WEIGHT, 1.4)
        self.assertEqual(config.STRUCTURE_WEIGHT, 6.0)
        self.assertEqual(config.TERRAIN_WEIGHT, 8.0)

    def test_splash_weight(self):
        """Test splash damage weight"""
        config = PotentialFieldConfig()
        self.assertEqual(config.SPLASH_WEIGHT, 3.0)

    def test_radius_settings(self):
        """Test field radius settings"""
        config = PotentialFieldConfig()
        self.assertEqual(config.ALLY_RADIUS, 4.0)
        self.assertEqual(config.ENEMY_RADIUS, 6.0)
        self.assertEqual(config.STRUCTURE_RADIUS, 8.0)
        self.assertEqual(config.TERRAIN_RADIUS, 5.0)

    def test_get_potential_field_config_helper(self):
        """Test get_potential_field_config helper function"""
        config = get_potential_field_config()
        self.assertIsInstance(config, PotentialFieldConfig)


class TestUpgradeConfig(unittest.TestCase):
    """Test UpgradeConfig class"""

    def test_critical_upgrades(self):
        """Test critical upgrade set"""
        config = UpgradeConfig()
        self.assertIn("ZERGLINGMOVEMENTSPEED", config.CRITICAL_UPGRADES)
        self.assertIn("OVERLORDSPEED", config.CRITICAL_UPGRADES)

    def test_unit_specific_upgrades(self):
        """Test unit-specific upgrade mappings"""
        config = UpgradeConfig()
        self.assertIn("MUTALISK", config.UNIT_SPECIFIC_UPGRADES)
        self.assertIn("ROACH", config.UNIT_SPECIFIC_UPGRADES)
        self.assertIn("HYDRALISK", config.UNIT_SPECIFIC_UPGRADES)

    def test_upgrade_priorities(self):
        """Test upgrade priority values"""
        config = UpgradeConfig()
        self.assertEqual(config.ATTACK_UPGRADE_PRIORITY, 1)
        self.assertEqual(config.ARMOR_UPGRADE_PRIORITY, 2)
        self.assertEqual(config.TECH_UPGRADE_PRIORITY, 3)

    def test_get_upgrade_config_helper(self):
        """Test get_upgrade_config helper function"""
        config = get_upgrade_config()
        self.assertIsInstance(config, UpgradeConfig)


class TestConfigConsistency(unittest.TestCase):
    """Test consistency across configurations"""

    def test_all_configs_instantiate(self):
        """Test all config classes can be instantiated"""
        configs = [
            CombatConfig(),
            BanelingConfig(),
            MutaliskConfig(),
            InfestorConfig(),
            EconomyConfig(),
            PotentialFieldConfig(),
            UpgradeConfig()
        ]
        for config in configs:
            self.assertIsNotNone(config)

    def test_all_helpers_return_correct_types(self):
        """Test all helper functions return correct types"""
        helpers_and_types = [
            (get_combat_config, CombatConfig),
            (get_baneling_config, BanelingConfig),
            (get_mutalisk_config, MutaliskConfig),
            (get_infestor_config, InfestorConfig),
            (get_economy_config, EconomyConfig),
            (get_potential_field_config, PotentialFieldConfig),
            (get_upgrade_config, UpgradeConfig)
        ]
        for helper, expected_type in helpers_and_types:
            result = helper()
            self.assertIsInstance(result, expected_type)

    def test_hp_thresholds_valid(self):
        """Test HP thresholds are between 0 and 1"""
        baneling = BanelingConfig()
        mutalisk = MutaliskConfig()
        infestor = InfestorConfig()

        self.assertGreaterEqual(baneling.RETREAT_HP_THRESHOLD, 0.0)
        self.assertLessEqual(baneling.RETREAT_HP_THRESHOLD, 1.0)

        self.assertGreaterEqual(mutalisk.REGEN_HP_THRESHOLD, 0.0)
        self.assertLessEqual(mutalisk.REGEN_HP_THRESHOLD, 1.0)
        self.assertGreaterEqual(mutalisk.RETREAT_HP_THRESHOLD, 0.0)
        self.assertLessEqual(mutalisk.RETREAT_HP_THRESHOLD, 1.0)

        self.assertGreaterEqual(infestor.NEURAL_PRIORITY_HP_THRESHOLD, 0.0)
        self.assertLessEqual(infestor.NEURAL_PRIORITY_HP_THRESHOLD, 1.0)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
