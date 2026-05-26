# -*- coding: utf-8 -*-
"""PhaseScoutCadence 단위 테스트.

순수 함수 layer(phase_for_time, cadence_for_phase) + stateful
PhaseScoutCadence의 dispatch 결정을 검증한다.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scouting.phase_scout_cadence import (
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


class _StubBot:
    """phase_scout_cadence가 필요로 하는 최소 인터페이스 stub."""

    def __init__(self, enemy_main=(50.0, 50.0)):
        self.enemy_start_locations = [enemy_main]

        class _PlayableArea:
            width = 120
            height = 80

        class _GameInfo:
            playable_area = _PlayableArea()

        self.game_info = _GameInfo()


class TestPhaseMapping(unittest.TestCase):
    def test_phase_1_early(self):
        self.assertIs(phase_for_time(0.0), ScoutPhase.OVERLORD_EARLY)
        self.assertIs(phase_for_time(60.0), ScoutPhase.OVERLORD_EARLY)
        self.assertIs(phase_for_time(PHASE_1_END_S - 0.001), ScoutPhase.OVERLORD_EARLY)

    def test_phase_2_zergling(self):
        self.assertIs(phase_for_time(PHASE_1_END_S), ScoutPhase.ZERGLING_SWEEP)
        self.assertIs(phase_for_time(300.0), ScoutPhase.ZERGLING_SWEEP)
        self.assertIs(phase_for_time(PHASE_2_END_S - 0.001), ScoutPhase.ZERGLING_SWEEP)

    def test_phase_3_overseer(self):
        self.assertIs(phase_for_time(PHASE_2_END_S), ScoutPhase.OVERSEER_DETECT)
        self.assertIs(phase_for_time(900.0), ScoutPhase.OVERSEER_DETECT)


class TestCadenceForPhase(unittest.TestCase):
    def test_overlord_cadence(self):
        self.assertEqual(
            cadence_for_phase(ScoutPhase.OVERLORD_EARLY), PHASE_1_CADENCE_S
        )

    def test_zergling_cadence(self):
        self.assertEqual(
            cadence_for_phase(ScoutPhase.ZERGLING_SWEEP), PHASE_2_CADENCE_S
        )

    def test_overseer_cadence(self):
        self.assertEqual(
            cadence_for_phase(ScoutPhase.OVERSEER_DETECT), PHASE_3_CADENCE_S
        )


class TestDispatchTiming(unittest.TestCase):
    def setUp(self):
        self.cadence = PhaseScoutCadence(_StubBot())

    def test_first_dispatch_emits_plan(self):
        plan = self.cadence.next_dispatch(game_time_s=10.0)
        self.assertIsNotNone(plan)
        self.assertIs(plan.phase, ScoutPhase.OVERLORD_EARLY)

    def test_second_dispatch_within_cadence_returns_none(self):
        self.cadence.next_dispatch(game_time_s=10.0)
        self.assertIsNone(self.cadence.next_dispatch(game_time_s=20.0))

    def test_dispatch_emits_again_after_cadence(self):
        self.cadence.next_dispatch(game_time_s=10.0)
        plan = self.cadence.next_dispatch(game_time_s=10.0 + PHASE_1_CADENCE_S + 1)
        self.assertIsNotNone(plan)


class TestZerglingQuadrantRotation(unittest.TestCase):
    """zergling sweep은 4분면을 round-robin 으로 돈다."""

    def test_round_robin(self):
        cadence = PhaseScoutCadence(_StubBot())
        t = PHASE_1_END_S + 1.0
        seen = []
        for _ in range(4):
            plan = cadence.next_dispatch(game_time_s=t)
            self.assertIsNotNone(plan)
            seen.append(plan.quadrant_index)
            t += PHASE_2_CADENCE_S + 1.0
        self.assertEqual(seen, [0, 1, 2, 3])


class TestEnemyMainResolution(unittest.TestCase):
    def test_uses_enemy_start_locations(self):
        cadence = PhaseScoutCadence(_StubBot(enemy_main=(77.0, 33.0)))
        plan = cadence.next_dispatch(game_time_s=5.0)
        self.assertIsNotNone(plan)
        # OVERLORD plan는 enemy_main을 그대로 target으로 사용
        self.assertEqual(tuple(plan.target), (77.0, 33.0))

    def test_returns_none_without_enemy_main(self):
        class _Empty:
            enemy_start_locations = []

        cadence = PhaseScoutCadence(_Empty())
        self.assertIsNone(cadence.next_dispatch(game_time_s=5.0))


if __name__ == "__main__":
    unittest.main()
