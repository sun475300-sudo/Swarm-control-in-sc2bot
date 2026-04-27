"""Lock the canonical `task_priorities` key set.

The canonical dict is initialised in
`wicked_zerg_challenger/combat/initialization.py`:

    base_defense, worker_defense, counter_attack,
    air_harass, scout, main_attack, creep_spread

Iter 9 (commit dc6e8ac) fixed a bug where `LogicOptimizer` was writing
to `task_priorities["air_harassment"]` — a typo that landed in a dead
dict slot since the multitasking loop reads `air_harass`. This test
catches the same class of typo by scanning every assignment to
`task_priorities[<str-literal>]` across the bot core and asserting
each key is in a known-allowed set.

Allowed keys = canonical defaults + known dynamic keys added at
runtime by the multitasking method (e.g. `worker_harass` set in
all_in mode at `combat_manager.py:263`, and the `combat/multitasking.py`
keys `early_harass`, `expansion_denial`, `creep_denial`).

Adding a new task type? Add the key here and to whichever pickup loop
will read it.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BOT_CORE = REPO_ROOT / "wicked_zerg_challenger"

# Canonical priorities set in combat/initialization.py — read by
# combat_manager._execute_multitasking and combat/multitasking.py.
# Keep this list in sync if you add a new task pickup.
ALLOWED_KEYS = frozenset({
    # canonical defaults from combat/initialization.py
    "base_defense", "worker_defense", "counter_attack",
    "air_harass", "scout", "main_attack", "creep_spread",
    # dynamic keys added at runtime by the multitasking method
    "worker_harass",       # combat_manager.py:263 (all_in mode)
    "early_harass",        # combat/multitasking.py
    "expansion_denial",    # combat/multitasking.py
    "creep_denial",        # combat/multitasking.py
})

ASSIGNMENT_RE = re.compile(
    r"""task_priorities\[\s*['\"](?P<key>[a-z_]+)['\"]\s*\]"""
)


def _scan_keys() -> dict[str, list[tuple[Path, int]]]:
    """Return {key: [(file, lineno), ...]} for every task_priorities[<str>]."""
    found: dict[str, list[tuple[Path, int]]] = {}
    for py_file in BOT_CORE.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in ASSIGNMENT_RE.finditer(line):
                key = m.group("key")
                found.setdefault(key, []).append((py_file, lineno))
    return found


def test_no_unknown_task_priorities_keys():
    """Every task_priorities[<str>] key must be in the canonical set.

    A typo (e.g. "air_harassment" vs "air_harass") would silently
    land in a dead dict slot and the multitasking loop would never
    read it back — exactly the iter 9 bug.
    """
    found = _scan_keys()
    unknown = {k: locs for k, locs in found.items() if k not in ALLOWED_KEYS}
    if not unknown:
        return

    msg = ["task_priorities access uses unrecognised key(s):"]
    for key, locs in sorted(unknown.items()):
        msg.append(f"  '{key}':")
        for path, lineno in locs:
            msg.append(f"    {path.relative_to(REPO_ROOT)}:{lineno}")
    msg.append("")
    msg.append(
        f"Allowed keys: {sorted(ALLOWED_KEYS)}. If this is a new task "
        f"type, add the key to ALLOWED_KEYS *and* wire up a pickup loop "
        f"in combat_manager._execute_multitasking or combat/multitasking.py."
    )
    raise AssertionError("\n".join(msg))
