"""Tests for LogicOptimizer.apply_* methods (added in c7bb6dd, finished in 55eb51e).

The three apply_*_improvements methods set tunables on the live bot's
manager objects. They previously had no test coverage. This file adds:

  * apply_combat_improvements — sets two task_priorities entries
  * apply_economy_improvements — sets two economy tunables
  * apply_strategy_improvements — flips StrategyMode on Cheat difficulty

`apply_strategy_improvements` was assigning a raw string ``"aggressive"``
to ``strategy_manager.current_mode``, but the rest of the code treats
``current_mode`` as a ``StrategyMode`` enum (e.g. ``combat_manager.py:248``
does ``strategy.current_mode.value``). This is a latent crash that
only fires on Cheat difficulty + the next combat tick. The test
``test_apply_strategy_improvements_assigns_enum_not_string`` reproduces
the bug; the accompanying fix in ``logic_optimizer.py`` switches to
``StrategyMode.AGGRESSIVE``.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

_BOT_CORE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)
if os.path.isdir(_BOT_CORE) and _BOT_CORE not in sys.path:
    sys.path.insert(0, _BOT_CORE)

try:
    from logic_optimizer import LogicOptimizer  # type: ignore[import-not-found]
    from strategy_manager import StrategyMode  # type: ignore[import-not-found]
except ImportError as exc:
    pytest.skip(f"logic_optimizer / strategy_manager not importable: {exc}",
                allow_module_level=True)


def _make_optimizer_with_managers():
    bot = SimpleNamespace(
        combat_manager=SimpleNamespace(task_priorities={}),
        economy_manager=SimpleNamespace(
            gas_worker_adjustment_interval=999,
            macro_hatchery_mineral_threshold=999,
        ),
        strategy_manager=SimpleNamespace(current_mode=StrategyMode.NORMAL),
        time=0.0,
        iteration=0,
    )
    try:
        return LogicOptimizer(bot), bot
    except Exception as exc:
        pytest.skip(f"LogicOptimizer init failed in test env: {exc}")


def test_apply_combat_improvements_sets_priorities():
    opt, bot = _make_optimizer_with_managers()
    opt.apply_combat_improvements()
    assert bot.combat_manager.task_priorities["air_harassment"] == 60
    assert bot.combat_manager.task_priorities["worker_defense"] == 110


def test_apply_economy_improvements_tightens_tunables():
    opt, bot = _make_optimizer_with_managers()
    opt.apply_economy_improvements()
    assert bot.economy_manager.gas_worker_adjustment_interval == 22
    assert bot.economy_manager.macro_hatchery_mineral_threshold == 500


def _ensure_sc2_data_difficulty_stub():
    """Inject a minimal sc2.data.Difficulty stub if sc2 isn't installed.

    `LogicOptimizer.apply_strategy_improvements` does
    `from sc2.data import Difficulty` *inside* the method, so we have to
    prepopulate `sys.modules` before the call.
    """
    try:
        from sc2.data import Difficulty  # type: ignore[import-not-found]
        return Difficulty
    except ImportError:
        pass

    import enum
    import types

    class Difficulty(enum.Enum):
        VeryHard = "VeryHard"
        CheatVision = "CheatVision"
        CheatMoney = "CheatMoney"
        CheatInsane = "CheatInsane"

    class Race(enum.Enum):
        Random = "Random"

    sc2_pkg = types.ModuleType("sc2")
    sc2_data = types.ModuleType("sc2.data")
    sc2_data.Difficulty = Difficulty
    sc2_data.Race = Race
    sys.modules.setdefault("sc2", sc2_pkg)
    sys.modules["sc2.data"] = sc2_data
    return Difficulty


def test_apply_strategy_improvements_assigns_enum_not_string():
    """Regression: current_mode must remain a StrategyMode, not a raw str.

    Other code does `strategy.current_mode.value` (combat_manager.py:248)
    and `strategy.current_mode.name` (bot_step_integration.py:2433);
    a raw string would crash those call sites with AttributeError.
    """
    Difficulty = _ensure_sc2_data_difficulty_stub()

    opt, bot = _make_optimizer_with_managers()
    opt.apply_strategy_improvements(Difficulty.CheatInsane)

    mode = bot.strategy_manager.current_mode
    assert isinstance(mode, StrategyMode), (
        f"current_mode set to {type(mode).__name__} ({mode!r}); "
        f"the rest of the codebase expects a StrategyMode enum so "
        f"`.value` and `.name` accesses work"
    )
    assert mode == StrategyMode.AGGRESSIVE
