"""Early scout evidence must expire instead of latching defensive strategy."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blackboard import GameStateBlackboard
from strategy_manager import StrategyManager, StrategyMode


def make_manager():
    blackboard = GameStateBlackboard()
    blackboard.set("early_scout_last_report_time", 100.0)
    blackboard.set("early_scout_gas_time", 75.0)
    blackboard.set("early_scout_cheese_suspected", True)
    blackboard.set("early_scout_natural_confirmed", False)
    bot = SimpleNamespace(time=120.0, units=[], enemy_units=[], supply_army=40)
    return StrategyManager(bot, blackboard), blackboard


@pytest.mark.parametrize("new_report", [100.0, 600.0])
def test_old_opening_pressure_releases_defensive_latch(new_report):
    manager, blackboard = make_manager()
    manager._apply_early_scout_signals()
    assert manager.current_mode == StrategyMode.DEFENSIVE
    assert manager.early_scout_pressure_active is True

    manager.bot.time = 600.0
    blackboard.set("early_scout_last_report_time", new_report)
    manager._apply_early_scout_signals()
    manager._update_strategy_mode()

    assert manager.early_scout_pressure_active is False
    assert manager.early_scout_cheese_active is False
    assert manager.early_scout_fast_gas is False
    assert manager.current_mode == StrategyMode.AGGRESSIVE


def test_scout_pressure_expires_when_report_stops_during_opening():
    manager, _ = make_manager()
    manager._apply_early_scout_signals()

    manager.bot.time = 180.0
    manager._apply_early_scout_signals()

    assert manager.early_scout_pressure_active is False


def test_future_report_does_not_activate_opening_pressure():
    manager, blackboard = make_manager()
    blackboard.set("early_scout_last_report_time", 150.0)

    manager._apply_early_scout_signals()

    assert manager.early_scout_pressure_active is False
    assert manager.current_mode == StrategyMode.NORMAL


def test_live_emergency_is_preserved_when_opening_pressure_expires():
    manager, _ = make_manager()
    manager._apply_early_scout_signals()
    manager.bot.time = 600.0
    manager.emergency_active = True
    manager.current_mode = StrategyMode.EMERGENCY

    manager._apply_early_scout_signals()
    manager._update_strategy_mode()

    assert manager.early_scout_pressure_active is False
    assert manager.current_mode == StrategyMode.EMERGENCY
