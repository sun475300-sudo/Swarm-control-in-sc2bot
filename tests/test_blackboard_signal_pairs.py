"""Lock paired blackboard alert signals so writes don't go to dead readers.

`intel_manager.py` raises two parallel alerts on enemy tech detection:

  * `urgent_spore_all_bases` — anti-air (DT/Oracle/Carrier/BC alerts)
  * `urgent_spine_all_bases` — anti-ground (NYDUS alert)

The first is consumed by `economy_manager._check_air_threat_response`
which reads it via `blackboard.get("urgent_spore_all_bases", False)`
and then builds spores at every base. The second was dropped on the
floor — no reader anywhere — so a NYDUS_INCOMING alert silently never
caused any defensive reaction.

This test asserts that *both* signals have at least one consumer
somewhere in the bot core. Future paired-alert additions should
extend the SIGNAL_PAIRS list.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BOT_CORE = REPO_ROOT / "wicked_zerg_challenger"

# Alerts that must round-trip — set somewhere AND read somewhere.
# These are the "actionable" signals whose entire purpose is to gate
# defensive behaviour. Telemetry-only signals (sitrep, threat_level,
# etc.) are NOT in this list.
#
# `urgent_overseer` is *intentionally* not in this list: it is set as
# telemetry on DT/cloak detection, but the actionable response (morph
# an overlord into an overseer) is already wired through
# `protoss_counter_system._handle_dark_templar_threat` which calls
# `_emergency_overseer_morph` directly off the same intel signal.
# Adding a redundant blackboard reader would double-fire the morph.
ACTIONABLE_SIGNALS = (
    "urgent_spore_all_bases",
    "urgent_spine_all_bases",
)


def _scan(pattern: str) -> dict[str, list[tuple[Path, int]]]:
    rx = re.compile(pattern)
    found: dict[str, list[tuple[Path, int]]] = {}
    for py_file in BOT_CORE.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in rx.finditer(line):
                found.setdefault(m.group(1), []).append((py_file, lineno))
    return found


def test_actionable_blackboard_signals_have_readers():
    """Each actionable blackboard alert must have at least one reader."""
    sets = _scan(r'blackboard\.set\(["\'](\w+)["\']')
    gets = _scan(r'blackboard\.get\(["\'](\w+)["\']')

    missing_readers = []
    for sig in ACTIONABLE_SIGNALS:
        if sig not in sets:
            continue  # not even set — separate problem
        if sig not in gets:
            set_locs = sets[sig]
            missing_readers.append((sig, set_locs))

    assert not missing_readers, (
        "Actionable blackboard alert(s) set but never read — the alert "
        "is silently dropped on the floor and the defensive reaction "
        "never fires:\n"
        + "\n".join(
            f"  '{sig}' set at:\n"
            + "\n".join(
                f"    {p.relative_to(REPO_ROOT)}:{l}" for p, l in locs
            )
            for sig, locs in missing_readers
        )
        + "\n\nAdd a reader (typically `blackboard.get(<sig>, False)` "
        "in the relevant manager) or remove the dead set call."
    )
