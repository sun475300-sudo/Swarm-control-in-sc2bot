"""Lock the combat task-priority numbers tightened in 34ac508.

Commit 34ac508 ("Enhanced combat aggression") tightened four task
priorities inside `CombatManager._execute_multitasking`:

    aggressive/all_in mode:
      * main_attack:   90 → 95   (more aggression)
      * base_defense:  45 → 40   (less defensive in aggressive mode)
    all_in mode (additional):
      * base_defense:  20 → 15   (deeper defensive sacrifice)
      * worker_harass:        80 (new — explicit worker-harass priority)

These live as bare numerics inside a 200+ line async method, so
unit-testing the behaviour directly would require a heavy bot stub.
Instead, this file pins the *direction* of the change at the source
level so a future cleanup can't silently undo the aggression.

If a future refactor pulls these into named constants, update the
test to read the constants instead — see PLAN-NIGHTLY P2.3
(build-order config externalisation) for the broader trend.
"""
from __future__ import annotations

import inspect
import re

import pytest


def _import_combat_manager_source() -> str:
    try:
        # Use the same path-shim as test_economy_invariants because
        # combat_manager pulls in `utils.logger` etc.
        import os
        import sys

        bot_core = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
        )
        if os.path.isdir(bot_core) and bot_core not in sys.path:
            sys.path.insert(0, bot_core)

        import combat_manager  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.skip(f"combat_manager not importable: {exc}")
    return inspect.getsource(combat_manager.CombatManager)


PRIORITY_LINE_RE = re.compile(
    r"""self\.task_priorities\[
        ['\"](?P<key>[a-z_]+)['\"]
        \]\s*=\s*(?P<value>\d+)""",
    re.VERBOSE,
)


def _collect_priorities() -> list[tuple[str, int]]:
    src = _import_combat_manager_source()
    return [
        (m.group("key"), int(m.group("value")))
        for m in PRIORITY_LINE_RE.finditer(src)
    ]


def test_aggressive_main_attack_priority_at_least_95():
    """In aggressive/all_in mode, main_attack must stay ≥ 95."""
    priorities = _collect_priorities()
    main_attack_values = [v for k, v in priorities if k == "main_attack"]
    assert main_attack_values, "no main_attack priority assignments found"
    assert max(main_attack_values) >= 95, (
        f"main_attack peak priority dropped to {max(main_attack_values)} "
        f"— commit 34ac508 raised it to 95 for aggressive mode"
    )


def test_all_in_base_defense_priority_at_most_15():
    """In all_in mode, base_defense must drop to ≤ 15 (deepest sacrifice)."""
    priorities = _collect_priorities()
    base_def_values = [v for k, v in priorities if k == "base_defense"]
    assert base_def_values, "no base_defense priority assignments found"
    assert min(base_def_values) <= 15, (
        f"base_defense floor raised to {min(base_def_values)} — "
        f"commit 34ac508 lowered the all_in floor to 15 to commit "
        f"more units to attacking"
    )


def test_worker_harass_priority_present():
    """A worker_harass priority assignment must exist (added in 34ac508)."""
    priorities = _collect_priorities()
    harass_values = [v for k, v in priorities if k == "worker_harass"]
    assert harass_values, (
        "worker_harass priority assignment removed — commit 34ac508 "
        "added an explicit worker_harass=80 priority for all_in mode"
    )
    assert max(harass_values) >= 70, (
        f"worker_harass peak priority {max(harass_values)} too low — "
        f"all_in mode needs at least 70 to actually trigger worker raids"
    )
