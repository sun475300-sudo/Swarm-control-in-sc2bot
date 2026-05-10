"""Regression tests for OpponentModeling lifecycle unification (PR #150).

These cover three concrete bugs that were silently corrupting the model:

1. The legacy B-API (`on_game_start` / `on_game_end`) wrote to a parallel
   `current_opponent` attribute that the rich `on_step` path never read,
   so the rich tracking was effectively dead code.
2. `on_end()` mapped Victory↔Defeat in reverse, so every loss was recorded
   as a win and vice versa.
3. `get_predicted_strategy()` did `[s.value for s in observed_signals]` —
   but `observed_signals` is `Set[str]`, not `Set[Enum]`, so the call
   raised `AttributeError` whenever there was anything to predict from.

Each test is deliberately tiny and uses MagicMock so the bot harness /
python-sc2 are not required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# wicked_zerg_challenger/ contents are imported as top-level modules
# (the test mirrors how production loads them via sys.path injection).
_WZC = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"
if str(_WZC) not in sys.path:
    sys.path.insert(0, str(_WZC))

from opponent_modeling import OpponentModel, OpponentModeling  # noqa: E402


def _make_modeling(tmp_path: Path) -> OpponentModeling:
    bot = MagicMock()
    bot.time = 0.0
    bot.iteration = 0
    bot.enemy_race = MagicMock()
    bot.enemy_race.name = "Zerg"
    bot.enemy_structures = []
    bot.enemy_units = []
    intel = MagicMock()
    intel.enemy_tech_buildings = set()
    intel.get_enemy_composition = MagicMock(return_value={})
    intel.is_under_attack = MagicMock(return_value=False)
    return OpponentModeling(
        bot, intel_manager=intel, data_file=str(tmp_path / "models.json")
    )


@pytest.fixture
def modeling(tmp_path):
    return _make_modeling(tmp_path)


# ---------------------------------------------------------------------------
# Bug 1 — B-API now writes the canonical `current_opponent_id`
# ---------------------------------------------------------------------------
def test_on_game_start_writes_canonical_opponent_id(modeling):
    modeling.on_game_start("alice", opponent_race=None)
    # rich on_step path reads current_opponent_id; must be set
    assert modeling.current_opponent_id == "alice"
    # Model created
    assert "alice" in modeling.opponent_models
    # Per-game tracking reset
    assert modeling.observed_signals == set()
    assert modeling.predicted_strategy is None


# ---------------------------------------------------------------------------
# Bug 2 — Victory/Defeat ↔ win/loss mapping is no longer inverted
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_on_end_records_victory_as_win(modeling):
    modeling.on_game_start("alice", opponent_race=None)
    modeling.bot.time = 600.0
    await modeling.on_end("Victory")
    model = modeling.opponent_models["alice"]
    # update_from_game flips perspective: our "win" means opponent_lost++
    assert model.games_played == 1
    assert model.games_lost == 1
    assert model.games_won == 0


@pytest.mark.asyncio
async def test_on_end_records_defeat_as_loss(modeling):
    modeling.on_game_start("bob", opponent_race=None)
    modeling.bot.time = 600.0
    await modeling.on_end("Defeat")
    model = modeling.opponent_models["bob"]
    assert model.games_played == 1
    assert model.games_won == 1  # opponent won (because we lost)
    assert model.games_lost == 0


# ---------------------------------------------------------------------------
# Bug 3 — get_predicted_strategy doesn't crash on str-typed signals
# ---------------------------------------------------------------------------
def test_get_predicted_strategy_with_string_signals(modeling):
    modeling.current_opponent_id = "carol"
    modeling.opponent_models["carol"] = OpponentModel("carol")
    # observed_signals is a Set[str]; previously the production path called
    # [s.value for s in ...] and crashed with AttributeError. With the fix
    # it must return a (Optional[str], float) without raising.
    modeling.observed_signals = {"FAST_EXPAND"}
    pred, conf = modeling.get_predicted_strategy()
    # No specific value required — only that it didn't raise
    assert isinstance(conf, float)
    assert pred is None or isinstance(pred, str)


def test_get_predicted_strategy_no_opponent_returns_default(modeling):
    # Sanity: when no opponent has been set we still get the documented default
    pred, conf = modeling.get_predicted_strategy()
    assert pred is None
    assert conf == 0.0


# ---------------------------------------------------------------------------
# Bug 4 — on_game_end is awaitable (B-API now wraps the async on_end)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_on_game_end_awaitable(modeling):
    modeling.on_game_start("dave", opponent_race=None)
    modeling.bot.time = 700.0
    # Must be awaitable; previously it was sync and silently corrupted state.
    await modeling.on_game_end(won=True, lost=False)
    model = modeling.opponent_models["dave"]
    assert model.games_played == 1
    assert model.games_lost == 1  # we won → opponent lost
