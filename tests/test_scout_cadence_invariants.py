"""Lock the scout cadence intervals from PLAN-NIGHTLY P1.1.

The plan calls out three cadences:

  * Initial overlord scout — re-send every 30 s
  * Mid-game zergling map sweep — every 60 s
  * Late-game overseer cloak detection — (separate system)

These intervals live as bare constants inside `early_scout_system.py`
(`_overlord_rescout_interval = 30.0`, plus the literal `60.0` inside
`_mid_game_rescouting`). Without a test, a future edit can silently
change them without notice. This file pins both so any change
forces an explicit test update + review.
"""
from __future__ import annotations

import inspect

import pytest


def _import_early_scout_system():
    try:
        from wicked_zerg_challenger.early_scout_system import EarlyScoutSystem
    except (ImportError, TypeError) as exc:
        pytest.skip(f"EarlyScoutSystem not importable: {exc}")
    return EarlyScoutSystem


class _StubBot:
    """Minimal bot stub so EarlyScoutSystem.__init__ runs without sc2."""

    def __init__(self):
        self.time = 0.0
        self.iteration = 0
        self.minerals = 0
        self.vespene = 0
        self.supply_left = 0
        self.enemy_start_locations = []
        self.start_location = None


def test_overlord_rescout_interval_is_30_seconds():
    """Initial overlord re-scout cadence must stay at 30 s (PLAN-NIGHTLY P1.1)."""
    EarlyScoutSystem = _import_early_scout_system()
    scout = EarlyScoutSystem(_StubBot())
    assert hasattr(scout, "_overlord_rescout_interval"), (
        "EarlyScoutSystem._overlord_rescout_interval was removed — "
        "PLAN-NIGHTLY P1.1 requires a 30 s overlord re-scout cadence"
    )
    assert scout._overlord_rescout_interval == 30.0, (
        f"overlord re-scout interval changed to "
        f"{scout._overlord_rescout_interval} s — must stay at 30 s "
        f"per PLAN-NIGHTLY P1.1, or update the plan + this test together"
    )


def test_mid_game_rescout_interval_is_60_seconds():
    """Mid-game zergling sweep cadence must stay at 60 s (PLAN-NIGHTLY P1.1).

    The interval lives as a literal `60.0` inside
    `EarlyScoutSystem._mid_game_rescouting`. Inspecting the source is
    fragile but better than silently letting the cadence drift; if this
    test breaks because the interval is moved into a named constant,
    update the test to read the constant instead.
    """
    EarlyScoutSystem = _import_early_scout_system()
    src = inspect.getsource(EarlyScoutSystem._mid_game_rescouting)
    assert "60.0" in src or "_mid_game_rescout_interval" in src, (
        "mid-game zergling sweep cadence (60 s) appears to have been "
        "removed or restructured — see PLAN-NIGHTLY P1.1"
    )
