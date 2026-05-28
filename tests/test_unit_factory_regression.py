# -*- coding: utf-8 -*-
"""
Regression tests for UnitFactory crash bugs found via static analysis.

A mojibake-corrupted comment had swallowed the
``strategy = getattr(self.bot, "strategy_manager", None)`` assignment in
``_update_gas_ratio_target``, leaving ``strategy`` undefined. Any call to that
method raised ``NameError`` at runtime. These tests lock the behaviour so the
regression cannot return.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from unit_factory import UnitFactory
except ImportError:
    pytest.skip(
        "unit_factory not importable (SC2 env required)", allow_module_level=True
    )

from unittest.mock import MagicMock


def _make_factory(strategy_manager=None, enemy_race=None):
    bot = MagicMock()
    bot.strategy_manager = strategy_manager
    bot.enemy_race = enemy_race
    return UnitFactory(bot)


def test_gas_ratio_target_uses_strategy_detected_race():
    """Reading the detected race from the strategy manager must not crash."""
    strategy = MagicMock()
    strategy.detected_enemy_race = MagicMock(value="Protoss")
    factory = _make_factory(strategy_manager=strategy)

    factory._update_gas_ratio_target()

    assert factory.gas_unit_ratio_target == factory.race_gas_ratios["Protoss"]


def test_gas_ratio_target_falls_back_to_enemy_race():
    """With no strategy manager the bot.enemy_race fallback path runs cleanly."""
    factory = _make_factory(strategy_manager=None, enemy_race="Race.Terran")

    factory._update_gas_ratio_target()

    assert factory.gas_unit_ratio_target == factory.race_gas_ratios["Terran"]


def test_gas_ratio_target_no_race_info_keeps_default():
    """No race information available: the call still must not raise."""
    factory = _make_factory(strategy_manager=None, enemy_race=None)
    default = factory.gas_unit_ratio_target

    factory._update_gas_ratio_target()

    assert factory.gas_unit_ratio_target == default
