"""
Smoke test: every top-level bot module under wicked_zerg_challenger/
must import cleanly. Catches the kind of regression we hit before this
PR landed — a missing transitive dep (loguru, scipy), a default-arg
that explodes on stub fallback (UnitTypeId.OVERLORD), a UTF-8 BOM
making ast.parse choke, etc.

Why this is worth its own file:
  * Lots of bot modules are not exercised by any unit test, so import
    failures can sit there indefinitely until someone actually loads
    the bot in production.
  * The bot's import chain is fragile by design: there's a `utils`
    package at both the repo root and inside wicked_zerg_challenger/,
    and the bot files use absolute imports (`from utils.logger import
    get_logger`) that require the bot dir on sys.path first. Locking
    that ordering in a test means it stays correct.

Strategy: parametrize over a curated list of "matters in the hot path"
modules. For each one, import it via importlib and assert that worked.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

WICKED = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"


def _prepare_sys_path():
    """Ensure the bot dir is first and the root `utils`/`config` packages
    don't shadow the bot's."""
    if str(WICKED) not in sys.path:
        sys.path.insert(0, str(WICKED))
    else:
        # Move it to the front if it's already there at a later slot.
        sys.path.remove(str(WICKED))
        sys.path.insert(0, str(WICKED))
    for modname in [
        m
        for m in list(sys.modules)
        if m == "utils"
        or m.startswith("utils.")
        or m == "config"
        or m.startswith("config.")
    ]:
        sys.modules.pop(modname, None)


# Hot-path modules. If any of these break, the bot is busted.
CORE_MODULES = [
    # Top-level bot
    "wicked_zerg_bot_pro_impl",
    "blackboard",
    "bot_step_integration",
    "combat_phase_controller",
    "combat_manager",
    "build_order_system",
    "early_defense_system",
    # Combat subsystems
    "combat.spatial_query_optimizer",
    "combat.harassment_coordinator",
    "combat.multitasking",
    # Economy
    "economy_manager",
    "economy.queen_transfusion_manager",
    # Scouting / strategy
    "scouting.advanced_scout_system_v2",
    "strategy.adaptive_build_order",
    # Core helpers
    "core.resource_manager",
    "advanced_micro_controller_v3",
]


@pytest.mark.parametrize("modname", CORE_MODULES)
def test_core_module_imports(modname):
    """Each hot-path bot module must import without error."""
    try:
        import sc2  # noqa: F401
    except ImportError:  # pragma: no cover
        pytest.skip("sc2 library not available")

    _prepare_sys_path()
    # If the module is already imported with the wrong context, drop it
    # so we get a fresh resolve under the cleaned sys.modules / sys.path.
    sys.modules.pop(modname, None)
    importlib.import_module(modname)
