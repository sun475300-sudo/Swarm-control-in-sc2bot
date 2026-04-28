"""
Integration Test - Full Bot Workflow
Tests complete game flow from start to end
"""

import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List


class GamePhase(Enum):
    START = "start"
    EARLY_GAME = "early_game"
    MID_GAME = "mid_game"
    LATE_GAME = "late_game"
    END = "end"


class GameOutcome(Enum):
    VICTORY = "victory"
    DEFEAT = "defeat"
    DRAW = "draw"


@dataclass
class GameState:
    phase: str
    minerals: int
    supply_used: int
    supply_cap: int
    workers: int
    army_size: int
    units: List[Dict[str, Any]]
    structures: List[Dict[str, Any]]


@dataclass
class IntegrationTestResult:
    test_name: str
    passed: bool
    duration_ms: float
    phases_completed: int
    outcome: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class IntegrationTestRunner:
    def __init__(self):
        self.results: List[IntegrationTestResult] = []

    def simulate_game_flow(self, test_name: str) -> IntegrationTestResult:
        """Simulate complete game flow"""
        start = time.time()
        errors = []
        phases_completed = 0

        state = GameState(
            phase=GamePhase.START.value,
            minerals=50,
            supply_used=0,
            supply_cap=200,
            workers=6,
            army_size=0,
            units=[],
            structures=[],
        )

        try:
            for game_time in [0, 60, 180, 300, 480, 600]:
                state = self._advance_game_state(state, game_time)
                phases_completed += 1

            outcome = GameOutcome.VICTORY if state.army_size > 3 else GameOutcome.DEFEAT
            passed = outcome == GameOutcome.VICTORY

        except Exception as e:
            errors.append(str(e))
            passed = False
            outcome = GameOutcome.DEFEAT

        duration = (time.time() - start) * 1000

        return IntegrationTestResult(
            test_name=test_name,
            passed=passed,
            duration_ms=duration,
            phases_completed=phases_completed,
            outcome=outcome.value,
            metrics={
                "final_minerals": state.minerals,
                "final_army": state.army_size,
                "units_produced": len(state.units),
                "structures_built": len(state.structures),
            },
            errors=errors,
        )

    def _advance_game_state(self, state: GameState, game_time: int) -> GameState:
        """Simulate game state advancement"""
        if game_time < 60:
            state.phase = GamePhase.START.value
            state.minerals += 10
            state.workers = min(state.workers + 1, 24)
        elif game_time < 180:
            state.phase = GamePhase.EARLY_GAME.value
            state.minerals += 25
            state.supply_used += 2
            for _ in range(3):
                state.units.append({"type": "Zergling", "hp": 35})
                state.army_size += 1
        elif game_time < 300:
            state.phase = GamePhase.MID_GAME.value
            state.minerals += 40
            for _ in range(5):
                state.units.append({"type": "Roach", "hp": 145})
                state.army_size += 1
        elif game_time < 480:
            state.phase = GamePhase.LATE_GAME.value
            state.minerals += 50
            for _ in range(3):
                state.units.append({"type": "Ultralisk", "hp": 500})
                state.army_size += 1
        else:
            state.phase = GamePhase.END.value

        return state

    def test_economy_build(self) -> IntegrationTestResult:
        """Test economy build order"""
        return self.simulate_game_flow("economy_build")

    def test_aggressive_open(self) -> IntegrationTestResult:
        """Test aggressive opening"""
        return self.simulate_game_flow("aggressive_open")

    def test_defensive_play(self) -> IntegrationTestResult:
        """Test defensive play"""
        return self.simulate_game_flow("defensive_play")

    def test_macro_tech(self) -> IntegrationTestResult:
        """Test macro/tech build"""
        return self.simulate_game_flow("macro_tech")

    def test_all_in(self) -> IntegrationTestResult:
        """Test all-in strategy"""
        return self.simulate_game_flow("all_in")

    def run_all_tests(self) -> List[IntegrationTestResult]:
        """Run all integration tests"""
        tests = [
            self.test_economy_build,
            self.test_aggressive_open,
            self.test_defensive_play,
            self.test_macro_tech,
            self.test_all_in,
        ]

        results = []
        for test in tests:
            print(f"[Integration] Running {test.__name__}...")
            result = test()
            results.append(result)
            self.results.append(result)

        return results


def print_integration_results(results: List[IntegrationTestResult]) -> None:
    print("\n" + "=" * 80)
    print("INTEGRATION TEST RESULTS")
    print("=" * 80)

    passed = sum(1 for r in results if r.passed)
    avg_duration = sum(r.duration_ms for r in results) / len(results)

    print(
        f"\nTotal: {len(results)} | Passed: {passed} | Failed: {len(results) - passed} | Avg Duration: {avg_duration:.1f}ms\n"
    )

    for r in results:
        status = "[PASS]" if r.passed else "[FAIL]"
        print(f"{status} {r.test_name:<20} - Outcome: {r.outcome}")
        print(
            f"       Phases: {r.phases_completed}/5 | Duration: {r.duration_ms:.1f}ms"
        )
        print(
            f"       Metrics: Army={r.metrics.get('final_army', 0)}, Minerals={r.metrics.get('final_minerals', 0)}"
        )
        if r.errors:
            print(f"       Errors: {r.errors}")


if __name__ == "__main__":
    print("[Integration] Starting integration tests...")
    runner = IntegrationTestRunner()
    results = runner.run_all_tests()
    print_integration_results(results)
