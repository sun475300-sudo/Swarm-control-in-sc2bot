# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/upgrade_manager.py
(EvolutionUpgradeManager, 1352 LOC — previously without dedicated test file).

Covers pure-logic static helpers and deterministic queries. Async research
orchestration paths are out of scope for this test (needs extensive SC2
client mocking).
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)


def _import():
    try:
        from upgrade_manager import EvolutionUpgradeManager
        return EvolutionUpgradeManager
    except ImportError:
        return None


EvolutionUpgradeManager = _import()

pytestmark = pytest.mark.skipif(
    EvolutionUpgradeManager is None, reason="upgrade_manager not importable"
)


@pytest.fixture
def bot():
    b = MagicMock()
    b.time = 0.0
    b.minerals = 100
    b.vespene = 100
    b.units = []
    b.structures = []
    b.enemy_units = []
    b.state = MagicMock()
    b.state.upgrades = set()
    b.already_pending_upgrade = MagicMock(return_value=0)
    return b


@pytest.fixture
def um(bot):
    return EvolutionUpgradeManager(bot)


class TestStaticTypeLists:
    def test_melee_list(self):
        from sc2.ids.unit_typeid import UnitTypeId
        melee = EvolutionUpgradeManager._melee_unit_types()
        assert UnitTypeId.ZERGLING in melee
        assert UnitTypeId.BANELING in melee
        assert UnitTypeId.ULTRALISK in melee
        # Ranged should NOT be in melee list
        assert UnitTypeId.HYDRALISK not in melee
        assert UnitTypeId.ROACH not in melee

    def test_ranged_list_uses_lurkermp(self):
        """Regression: LURKERMP (id 502), NOT LURKER (id 911)."""
        from sc2.ids.unit_typeid import UnitTypeId
        ranged = EvolutionUpgradeManager._ranged_unit_types()
        assert UnitTypeId.LURKERMP in ranged
        assert UnitTypeId.LURKER not in ranged

    def test_air_list(self):
        from sc2.ids.unit_typeid import UnitTypeId
        air = EvolutionUpgradeManager._air_unit_types()
        assert UnitTypeId.MUTALISK in air
        assert UnitTypeId.CORRUPTOR in air
        assert UnitTypeId.BROODLORD in air
        assert UnitTypeId.VIPER in air
        # Ground units NOT in air list
        assert UnitTypeId.ZERGLING not in air


class TestNormalizeEnemyRace:
    def test_none(self):
        assert EvolutionUpgradeManager._normalize_enemy_race(None) == ""

    def test_plain_string(self):
        assert (
            EvolutionUpgradeManager._normalize_enemy_race("Terran") == "terran"
        )

    def test_strip_race_prefix(self):
        assert (
            EvolutionUpgradeManager._normalize_enemy_race("Race.Zerg") == "zerg"
        )

    def test_enum_like_name_attr(self):
        class FakeEnum:
            name = "Protoss"
        assert (
            EvolutionUpgradeManager._normalize_enemy_race(FakeEnum()) == "protoss"
        )


class TestHasUnit:
    def test_no_enemies(self):
        assert EvolutionUpgradeManager._has_unit([], ["ZERGLING"]) is False

    def test_found(self):
        from sc2.ids.unit_typeid import UnitTypeId
        enemy = MagicMock()
        enemy.type_id = UnitTypeId.MARINE
        assert (
            EvolutionUpgradeManager._has_unit([enemy], ["MARINE"]) is True
        )

    def test_not_found(self):
        from sc2.ids.unit_typeid import UnitTypeId
        enemy = MagicMock()
        enemy.type_id = UnitTypeId.MARINE
        assert (
            EvolutionUpgradeManager._has_unit([enemy], ["ZEALOT"]) is False
        )

    def test_nonexistent_name_safely_skipped(self):
        enemy = MagicMock()
        enemy.type_id = MagicMock()
        assert (
            EvolutionUpgradeManager._has_unit([enemy], ["NOT_A_UNIT_NAME"])
            is False
        )


class TestHasLair:
    def _fake_structures(self, ready_types):
        def q(unit_type):
            s = MagicMock()
            s.ready = [object()] if unit_type in ready_types else []
            s.__bool__ = lambda self: True
            return s
        return q

    def test_no_structures_attr(self, bot, um):
        del bot.structures
        assert um._has_lair() is False

    def test_has_lair(self, bot, um):
        from sc2.ids.unit_typeid import UnitTypeId
        bot.structures = self._fake_structures({UnitTypeId.LAIR})
        assert um._has_lair() is True

    def test_hive_also_counts_as_lair(self, bot, um):
        """Hive is a Lair upgrade — tech-gated abilities should still pass."""
        from sc2.ids.unit_typeid import UnitTypeId
        bot.structures = self._fake_structures({UnitTypeId.HIVE})
        assert um._has_lair() is True

    def test_no_lair_no_hive(self, bot, um):
        bot.structures = self._fake_structures(set())
        assert um._has_lair() is False


class TestHasHive:
    def _fake_structures(self, ready_types):
        def q(unit_type):
            s = MagicMock()
            s.ready = [object()] if unit_type in ready_types else []
            return s
        return q

    def test_lair_does_not_count_as_hive(self, bot, um):
        from sc2.ids.unit_typeid import UnitTypeId
        bot.structures = self._fake_structures({UnitTypeId.LAIR})
        assert um._has_hive() is False

    def test_hive_ready(self, bot, um):
        from sc2.ids.unit_typeid import UnitTypeId
        bot.structures = self._fake_structures({UnitTypeId.HIVE})
        assert um._has_hive() is True


class TestGetUnitComposition:
    def test_no_units_attr_returns_zeros(self, bot, um):
        del bot.units
        comp = um._get_unit_composition()
        for k in ["melee", "ranged", "zergling", "baneling", "hydralisk",
                  "roach", "mutalisk", "corruptor"]:
            assert comp[k] == 0

    def test_counts_include_aggregates(self, bot, um):
        from sc2.ids.unit_typeid import UnitTypeId
        def q(unit_type):
            table = {
                UnitTypeId.ZERGLING: 30,
                UnitTypeId.BANELING: 5,
                UnitTypeId.HYDRALISK: 12,
                UnitTypeId.ROACH: 8,
                UnitTypeId.MUTALISK: 4,
                UnitTypeId.CORRUPTOR: 2,
            }
            res = MagicMock()
            res.amount = table.get(unit_type, 0)
            return res
        bot.units = q
        comp = um._get_unit_composition()
        assert comp["zergling"] == 30
        assert comp["baneling"] == 5
        assert comp["hydralisk"] == 12
        assert comp["roach"] == 8
        # Aggregates
        assert comp["melee"] == 35  # ling + baneling
        assert comp["ranged"] == 20  # hydra + roach


class TestGetUpgradeStats:
    def test_stats_shape(self, um):
        stats = um.get_upgrade_stats()
        assert set(stats.keys()) >= {
            "reserved_upgrades",
            "intel_boosts",
            "zergling_speed",
            "overlord_speed",
        }

    def test_initial_values(self, um):
        stats = um.get_upgrade_stats()
        assert stats["reserved_upgrades"] == 0
        assert stats["zergling_speed"] is False
        assert stats["overlord_speed"] is False
