"""
Import-safety regression tests for ``wicked_zerg_challenger``.

These tests guard against the class of bugs that broke the bot's import
graph in the past:

- module-level ``sys.exit(...)`` (e.g. ``check_proxy``,
  ``tools/visualize_learning`` before the matplotlib guard fix)
- attribute access on stub classes that fail when the real ``sc2`` runtime
  is unavailable (e.g. ``UnitTypeId.OVERLORD`` evaluated as a default
  argument on a class definition, or ``Difficulty.*`` referenced at class
  body level without a fallback)

A regression here would mean CI / unit tests can no longer load large
parts of the bot — much harder to detect downstream than a normal
``ImportError`` on a single module.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BOT_ROOT = REPO_ROOT / "wicked_zerg_challenger"


@pytest.fixture(scope="module", autouse=True)
def _add_bot_root_to_syspath():
    if str(BOT_ROOT) not in sys.path:
        sys.path.insert(0, str(BOT_ROOT))
    yield


# Modules that we expect to import cleanly even when the SC2 runtime is
# missing. Anything import-time-fragile (e.g. matplotlib-only utilities)
# stays out of this list.
CRITICAL_MODULES = [
    "blackboard",
    "check_proxy",
    "combat_manager",
    "creep_manager",
    "difficulty_progression",
    "economy_manager",
    "intel_manager",
    "macro_cycle",
    "opponent_modeling",
    "production_controller",
    "runtime_self_healing",
    "spell_unit_manager",
    "utils.error_handler",
]


@pytest.mark.parametrize("module_name", CRITICAL_MODULES)
def test_module_import_does_not_explode(module_name):
    """The module must import without raising ``SystemExit`` or ``AttributeError``.

    ``ModuleNotFoundError`` is tolerated because most bot modules have a
    legitimate dependency on ``sc2`` / ``torch`` / ``loguru`` that is not
    installed in the unit-test environment.
    """
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError:
        pytest.skip(f"{module_name} requires an unavailable runtime dep")
    except (SystemExit, AttributeError) as exc:  # pragma: no cover - regression
        pytest.fail(
            f"{module_name} raised {type(exc).__name__} at import: {exc!r}. "
            "This indicates a module-level side-effect or stub-class bug."
        )


def test_check_proxy_is_callable_not_executable():
    """``check_proxy`` must not call ``sys.exit`` at import time on Linux/CI."""
    module = importlib.import_module("check_proxy")
    # The hardcoded Windows path will not exist; main() should return non-zero.
    rc = module.main()
    assert rc != 0
    assert callable(module.main)


def test_difficulty_progression_has_ladder_without_sc2():
    """``DifficultyProgression.DIFFICULTY_LADDER`` is computed at class-body
    time. Before the fallback Difficulty enum was added, this raised
    ``ModuleNotFoundError`` and prevented the bot from loading."""
    module = importlib.import_module("difficulty_progression")
    ladder = module.DifficultyProgression.DIFFICULTY_LADDER
    assert len(ladder) == 10
    assert ladder[0].name == "VeryEasy"
    assert ladder[-1].name == "CheatInsane"
