"""Deterministic regression test for PhaseScoutCadence.

Verifies:
  1. Phase boundaries map correctly (0-3 / 3-8 / 8+ minutes).
  2. Cadence numbers (30s / 60s / 90s) match the spec.
  3. Same (game_time, enemy_main, prior_dispatches) always yields the same
     DispatchPlan — i.e. nothing time-of-day dependent.
  4. Zergling quadrant cycles 0 → 1 → 2 → 3 → 0.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from wicked_zerg_challenger.scouting.phase_scout_cadence import (
    PHASE_1_CADENCE_S,
    PHASE_1_END_S,
    PHASE_2_CADENCE_S,
    PHASE_2_END_S,
    PHASE_3_CADENCE_S,
    PhaseScoutCadence,
    ScoutPhase,
    cadence_for_phase,
    phase_for_time,
)

# ---------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------

class TestPhaseMapping:
    @pytest.mark.parametrize(
        "t,expected",
        [
            (0.0, ScoutPhase.OVERLORD_EARLY),
            (179.9, ScoutPhase.OVERLORD_EARLY),
            (180.0, ScoutPhase.ZERGLING_SWEEP),
            (300.0, ScoutPhase.ZERGLING_SWEEP),
            (479.9, ScoutPhase.ZERGLING_SWEEP),
            (480.0, ScoutPhase.OVERSEER_DETECT),
            (1800.0, ScoutPhase.OVERSEER_DETECT),
        ],
    )
    def test_phase_for_time(self, t, expected):
        assert phase_for_time(t) == expected


class TestCadence:
    def test_cadence_constants(self):
        assert cadence_for_phase(ScoutPhase.OVERLORD_EARLY) == PHASE_1_CADENCE_S == 30.0
        assert cadence_for_phase(ScoutPhase.ZERGLING_SWEEP) == PHASE_2_CADENCE_S == 60.0
        assert cadence_for_phase(ScoutPhase.OVERSEER_DETECT) == PHASE_3_CADENCE_S == 90.0


# ---------------------------------------------------------------------
# Stateful wrapper
# ---------------------------------------------------------------------

@pytest.fixture
def fake_bot():
    return SimpleNamespace(
        enemy_start_locations=[(50.0, 80.0)],
        game_info=SimpleNamespace(
            playable_area=SimpleNamespace(width=100, height=100)
        ),
    )


class TestNextDispatch:
    def test_first_call_in_phase_1_returns_overlord(self, fake_bot):
        cad = PhaseScoutCadence(fake_bot)
        plan = cad.next_dispatch(game_time_s=10.0)
        assert plan is not None
        assert plan.phase is ScoutPhase.OVERLORD_EARLY
        assert plan.target == (50.0, 80.0)

    def test_second_call_within_cadence_returns_none(self, fake_bot):
        cad = PhaseScoutCadence(fake_bot)
        cad.next_dispatch(game_time_s=10.0)
        # 20 s later, still inside the 30 s window
        assert cad.next_dispatch(game_time_s=30.0) is None
        # 30 s later, just at the boundary → fire
        plan = cad.next_dispatch(game_time_s=40.5)
        assert plan is not None
        assert plan.phase is ScoutPhase.OVERLORD_EARLY

    def test_zergling_quadrant_cycles(self, fake_bot):
        cad = PhaseScoutCadence(fake_bot)
        seen = []
        for t in (200.0, 261.0, 322.0, 383.0, 444.0):  # 5 calls inside Phase 2
            plan = cad.next_dispatch(game_time_s=t)
            assert plan is not None and plan.phase is ScoutPhase.ZERGLING_SWEEP
            seen.append(plan.quadrant_index)
        # Should cycle 0,1,2,3,0
        assert seen == [0, 1, 2, 3, 0]

    def test_overseer_phase_picks_overseer(self, fake_bot):
        cad = PhaseScoutCadence(fake_bot)
        plan = cad.next_dispatch(game_time_s=600.0)
        assert plan is not None
        assert plan.phase is ScoutPhase.OVERSEER_DETECT


class TestDeterminism:
    """Same inputs always produce the same DispatchPlan."""

    def test_two_independent_instances_match(self, fake_bot):
        a = PhaseScoutCadence(fake_bot)
        b = PhaseScoutCadence(fake_bot)
        for t in (10.0, 100.0, 200.0, 400.0, 600.0):
            pa = a.next_dispatch(game_time_s=t)
            pb = b.next_dispatch(game_time_s=t)
            assert pa == pb

    def test_no_time_of_day_dependency(self, fake_bot):
        """Calling at the same game_time at different wall times must match."""
        import time

        a = PhaseScoutCadence(fake_bot)
        plan_a = a.next_dispatch(game_time_s=120.0)
        time.sleep(0.05)
        b = PhaseScoutCadence(fake_bot)
        plan_b = b.next_dispatch(game_time_s=120.0)
        assert plan_a == plan_b
