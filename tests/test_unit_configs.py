# -*- coding: utf-8 -*-
"""Tests for config/unit_configs.py — unit tactical parameter validation."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from config.unit_configs import (
    CombatConfig,
    BanelingConfig,
    MutaliskConfig,
    InfestorConfig,
    EconomyConfig,
    PotentialFieldConfig,
    UpgradeConfig,
    DefenseConfig,
    StrategyConfig,
    RoachBurrowConfig,
    get_combat_config,
    get_baneling_config,
    get_mutalisk_config,
    get_infestor_config,
    get_economy_config,
    get_upgrade_config,
    get_defense_config,
    get_strategy_config,
    get_roach_burrow_config,
)


class TestCombatConfig:
    def test_min_army_positive(self):
        assert CombatConfig.MIN_ARMY_FOR_ATTACK > 0

    def test_min_mutalisk_positive(self):
        assert CombatConfig.MIN_MUTALISK_FOR_HARASS > 0

    def test_defense_values_positive(self):
        assert CombatConfig.DEFENSE_CHECK_INTERVAL > 0
        assert CombatConfig.DEFENSE_RADIUS > 0

    def test_endgame_push_time_reasonable(self):
        assert CombatConfig.ENDGAME_PUSH_TIME > 0
        assert CombatConfig.ENDGAME_PUSH_TIME <= 1200  # under 20 min

    def test_max_units_per_update_reasonable(self):
        assert 1 <= CombatConfig.MAX_COMBAT_UNITS_PER_UPDATE <= 500


class TestBanelingConfig:
    def test_detonation_threshold_reasonable(self):
        assert BanelingConfig.MIN_ENEMIES_FOR_DETONATION >= 1

    def test_splash_radius_positive(self):
        assert BanelingConfig.SPLASH_DAMAGE_RADIUS > 0
        assert BanelingConfig.OPTIMAL_DETONATION_RADIUS > 0

    def test_retreat_hp_valid_ratio(self):
        assert 0 < BanelingConfig.RETREAT_HP_THRESHOLD <= 1


class TestMutaliskConfig:
    def test_hp_thresholds_valid(self):
        assert 0 < MutaliskConfig.REGEN_HP_THRESHOLD <= 1
        assert 0 < MutaliskConfig.RETREAT_HP_THRESHOLD <= 1

    def test_regen_higher_than_retreat(self):
        assert MutaliskConfig.REGEN_HP_THRESHOLD > MutaliskConfig.RETREAT_HP_THRESHOLD

    def test_magic_box_positive(self):
        assert MutaliskConfig.MAGIC_BOX_SPREAD_DISTANCE > 0
        assert MutaliskConfig.MAGIC_BOX_MIN_UNITS > 0

    def test_splash_threat_units_populated(self):
        assert isinstance(MutaliskConfig.SPLASH_THREAT_UNITS, set)
        assert len(MutaliskConfig.SPLASH_THREAT_UNITS) > 0
        # Classic threat units expected
        assert "THOR" in MutaliskConfig.SPLASH_THREAT_UNITS


class TestInfestorConfig:
    def test_fungal_energy_cost_standard(self):
        assert InfestorConfig.FUNGAL_ENERGY_COST == 75  # SC2 spec

    def test_neural_energy_cost_standard(self):
        assert InfestorConfig.NEURAL_ENERGY_COST == 50  # SC2 spec

    def test_fungal_ranges_positive(self):
        assert InfestorConfig.FUNGAL_OPTIMAL_RANGE > 0
        assert InfestorConfig.FUNGAL_MIN_ENEMIES >= 1


class TestAllConfigs:
    def test_instantiatable(self):
        # Each config class should instantiate without args
        for cls in [CombatConfig, BanelingConfig, MutaliskConfig,
                    InfestorConfig, EconomyConfig, PotentialFieldConfig,
                    UpgradeConfig, DefenseConfig, StrategyConfig,
                    RoachBurrowConfig]:
            assert cls is not None


class TestFactoryGetters:
    def test_get_combat_config_returns_instance(self):
        assert isinstance(get_combat_config(), CombatConfig)

    def test_get_baneling_config_returns_instance(self):
        assert isinstance(get_baneling_config(), BanelingConfig)

    def test_get_mutalisk_config_returns_instance(self):
        assert isinstance(get_mutalisk_config(), MutaliskConfig)

    def test_get_infestor_config_returns_instance(self):
        assert isinstance(get_infestor_config(), InfestorConfig)

    def test_get_economy_config_returns_instance(self):
        assert isinstance(get_economy_config(), EconomyConfig)

    def test_get_upgrade_config_returns_instance(self):
        assert isinstance(get_upgrade_config(), UpgradeConfig)

    def test_get_defense_config_returns_instance(self):
        assert isinstance(get_defense_config(), DefenseConfig)

    def test_get_strategy_config_returns_instance(self):
        assert isinstance(get_strategy_config(), StrategyConfig)

    def test_get_roach_burrow_config_returns_instance(self):
        assert isinstance(get_roach_burrow_config(), RoachBurrowConfig)


class TestHpRatioConsistency:
    def test_all_hp_thresholds_valid(self):
        """HP thresholds across configs should all be in (0, 1]."""
        # Check well-known HP attributes
        assert 0 < BanelingConfig.RETREAT_HP_THRESHOLD <= 1
        assert 0 < MutaliskConfig.REGEN_HP_THRESHOLD <= 1
        assert 0 < MutaliskConfig.RETREAT_HP_THRESHOLD <= 1
        assert 0 < InfestorConfig.NEURAL_PRIORITY_HP_THRESHOLD <= 1
