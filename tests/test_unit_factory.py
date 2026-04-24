# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/unit_factory.py (607 LOC, previously untested).

Exercises:
- gas-ratio target adjustment per race
- combat/gas unit counting with mocked unit collections
- _should_save_larva integration with strategy/rogue managers
- _can_train / _requirements_met structure gating
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
        from sc2.ids.unit_typeid import UnitTypeId  # type: ignore
        from unit_factory import UnitFactory
        return UnitFactory, UnitTypeId
    except ImportError:
        return None, None


UnitFactory, UnitTypeId = _import()

pytestmark = pytest.mark.skipif(
    UnitFactory is None or UnitTypeId is None,
    reason="unit_factory or sc2 not importable",
)


def _mock_unit(type_id):
    u = MagicMock()
    u.type_id = type_id
    return u


@pytest.fixture
def bot():
    b = MagicMock()
    b.minerals = 500
    b.vespene = 200
    b.iteration = 0
    b.units = []
    b.enemy_units = []
    b.enemy_race = None
    # By default, no strategy/rogue plugins present. Tests that need them
    # assign real mocks; this prevents MagicMock auto-attrs from making
    # getattr(bot, "strategy_manager", None) return a truthy MagicMock.
    b.strategy_manager = None
    b.rogue_tactics = None
    return b


@pytest.fixture
def factory(bot):
    return UnitFactory(bot)


class TestGasRatioInit:
    def test_default_zerg_ratio(self, factory):
        assert factory.race_gas_ratios["Zerg"] == pytest.approx(0.45)

    def test_terran_ratio(self, factory):
        assert factory.race_gas_ratios["Terran"] == pytest.approx(0.50)

    def test_protoss_ratio(self, factory):
        assert factory.race_gas_ratios["Protoss"] == pytest.approx(0.55)

    def test_unknown_ratio(self, factory):
        assert factory.race_gas_ratios["Unknown"] == pytest.approx(0.50)


class TestCountCombatUnits:
    def test_empty_when_no_units_attr(self, bot, factory):
        del bot.units
        assert factory._count_combat_units() == 0

    def test_counts_only_combat_types(self, bot, factory):
        bot.units = [
            _mock_unit(UnitTypeId.ZERGLING),
            _mock_unit(UnitTypeId.ROACH),
            _mock_unit(UnitTypeId.DRONE),  # not combat
            _mock_unit(UnitTypeId.LURKERMP),
            _mock_unit(UnitTypeId.OVERLORD),  # not combat
        ]
        # zergling + roach + lurker = 3
        assert factory._count_combat_units() == 3

    def test_counts_lurkermp_not_lurker(self, bot, factory):
        """Regression: counting must use LURKERMP (id 502), not LURKER (id 911)."""
        bot.units = [_mock_unit(UnitTypeId.LURKERMP)]
        assert factory._count_combat_units() == 1

        bot.units = [_mock_unit(UnitTypeId.LURKER)]
        # UnitTypeId.LURKER (id 911) is NOT the playable zerg lurker; it
        # must NOT be counted as an owned combat unit.
        assert factory._count_combat_units() == 0


class TestCountGasUnits:
    def test_counts_gas_heavy_units(self, bot, factory):
        bot.units = [
            _mock_unit(UnitTypeId.ROACH),
            _mock_unit(UnitTypeId.RAVAGER),
            _mock_unit(UnitTypeId.HYDRALISK),
            _mock_unit(UnitTypeId.ULTRALISK),
            _mock_unit(UnitTypeId.LURKERMP),
            _mock_unit(UnitTypeId.ZERGLING),  # mineral-only
        ]
        assert factory._count_gas_units() == 5

    def test_zergling_is_not_gas_unit(self, bot, factory):
        bot.units = [_mock_unit(UnitTypeId.ZERGLING) for _ in range(10)]
        assert factory._count_gas_units() == 0


class TestShouldSaveLarva:
    def test_default_false(self, factory):
        assert factory._should_save_larva() is False

    def test_strategy_says_save(self, factory):
        factory.bot.strategy_manager = MagicMock()
        factory.bot.strategy_manager.should_save_larva.return_value = True
        assert factory._should_save_larva() is True

    def test_rogue_larva_saving_active(self, factory):
        factory.bot.strategy_manager = None
        rogue = MagicMock()
        rogue.larva_saving_active = True
        rogue.preparing_baneling_drop = False
        factory.bot.rogue_tactics = rogue
        assert factory._should_save_larva() is True

    def test_rogue_preparing_baneling_drop(self, factory):
        factory.bot.strategy_manager = None
        rogue = MagicMock()
        rogue.larva_saving_active = False
        rogue.preparing_baneling_drop = True
        factory.bot.rogue_tactics = rogue
        assert factory._should_save_larva() is True

    def test_rogue_idle_returns_false(self, factory):
        factory.bot.strategy_manager = None
        rogue = MagicMock()
        rogue.larva_saving_active = False
        rogue.preparing_baneling_drop = False
        factory.bot.rogue_tactics = rogue
        assert factory._should_save_larva() is False


class TestRequirementsMet:
    def _make_structures_query(self, ready_types):
        """Return a fake ``bot.structures(unit_type)`` that has .ready truthy
        only when unit_type is in ``ready_types``."""
        def query(unit_type):
            s = MagicMock()
            is_ready = unit_type in ready_types
            s.ready = [object()] if is_ready else []
            s.__bool__ = lambda self: True
            return s
        return query

    def test_zergling_needs_spawning_pool(self, bot, factory):
        bot.structures = self._make_structures_query({UnitTypeId.SPAWNINGPOOL})
        assert factory._requirements_met(UnitTypeId.ZERGLING) is True

    def test_zergling_blocked_without_pool(self, bot, factory):
        bot.structures = self._make_structures_query(set())
        assert factory._requirements_met(UnitTypeId.ZERGLING) is False

    def test_lurkermp_maps_to_lurkerdenmp(self, bot, factory):
        """Regression: LURKER->LURKERDENMP mapping was broken because
        LURKER (id 911) is never produced. Must use LURKERMP (id 502)."""
        bot.structures = self._make_structures_query({UnitTypeId.LURKERDENMP})
        assert factory._requirements_met(UnitTypeId.LURKERMP) is True

        bot.structures = self._make_structures_query(set())
        assert factory._requirements_met(UnitTypeId.LURKERMP) is False

    def test_unknown_unit_type_defaults_true(self, bot, factory):
        bot.structures = self._make_structures_query(set())
        # Units not in the requirements table should return True (no gate).
        assert factory._requirements_met(UnitTypeId.OVERLORD) is True
