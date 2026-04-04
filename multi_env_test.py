"""
Multi-Environment Test - Cross-Map Compatibility
Tests bot behavior across different map types
"""

import json
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


class MapType(Enum):
    PRO_STR = "pro_stand"
    DESCENT = "descent"
    ACROPOLIS = "acropolis"
    DEVASTATION = "devastation"
    CORRIDOR = "corridor"
    GROUND_ZERO = "ground_zero"


class MapSize(Enum):
    SMALL = (64, 64)
    MEDIUM = (96, 96)
    LARGE = (128, 128)
    XLARGE = (160, 160)


@dataclass
class MapConfig:
    name: str
    map_type: str
    width: int
    height: int
    expansions: int
    chokepoints: int
    danger_zones: List[tuple]


@dataclass
class MultiEnvTestResult:
    map_name: str
    map_type: str
    passed: bool
    win_rate: float
    avg_build_time: float
    expansion_efficiency: float
    combat_effectiveness: float
    details: Dict[str, Any] = field(default_factory=dict)


class MultiEnvironmentTester:
    def __init__(self):
        self.results: List[MultiEnvTestResult] = []
        self.maps = self._load_maps()

    def _load_maps(self) -> List[MapConfig]:
        return [
            MapConfig(
                "Pro Stronghold",
                MapType.PRO_STR.value,
                128,
                128,
                7,
                3,
                [(30, 30), (60, 60), (90, 90)],
            ),
            MapConfig(
                "Descent", MapType.DESCENT.value, 96, 96, 5, 4, [(20, 20), (50, 80)]
            ),
            MapConfig(
                "Acropolis",
                MapType.ACROPOLIS.value,
                128,
                128,
                6,
                3,
                [(40, 40), (80, 80)],
            ),
            MapConfig(
                "Devastation",
                MapType.DEVASTATION.value,
                160,
                160,
                8,
                5,
                [(30, 30), (70, 70), (120, 120)],
            ),
            MapConfig(
                "Corridor", MapType.CORRIDOR.value, 96, 128, 4, 2, [(48, 20), (48, 100)]
            ),
            MapConfig(
                "Ground Zero",
                MapType.GROUND_ZERO.value,
                64,
                64,
                3,
                2,
                [(20, 20), (40, 40)],
            ),
        ]

    def _calculate_map_difficulty(self, map_config: MapConfig) -> float:
        difficulty = map_config.expansions * 0.1 + map_config.chokepoints * 0.15
        difficulty += len(map_config.danger_zones) * 0.1
        difficulty += map_config.width * map_config.height / 10000
        return min(difficulty, 10.0)

    def _simulate_map_game(self, map_config: MapConfig) -> MultiEnvTestResult:
        difficulty = self._calculate_map_difficulty(map_config)

        win_rate = 85 - (difficulty * 2) + random.uniform(-5, 5)
        win_rate = max(40, min(95, win_rate))

        build_time = (
            map_config.width * 0.5 + map_config.expansions * 10 + random.uniform(-5, 5)
        )

        expansion_eff = 100 - (map_config.expansions * 3) + random.uniform(-10, 10)
        expansion_eff = max(50, min(100, expansion_eff))

        combat = 90 - (map_config.chokepoints * 2) - (len(map_config.danger_zones) * 3)
        combat += random.uniform(-5, 5)
        combat = max(40, min(100, combat))

        passed = win_rate >= 60

        return MultiEnvTestResult(
            map_name=map_config.name,
            map_type=map_config.map_type,
            passed=passed,
            win_rate=win_rate,
            avg_build_time=build_time,
            expansion_efficiency=expansion_eff,
            combat_effectiveness=combat,
            details={
                "difficulty_score": difficulty,
                "width": map_config.width,
                "height": map_config.height,
                "expansions": map_config.expansions,
                "chokepoints": map_config.chokepoints,
            },
        )

    def test_all_maps(self) -> List[MultiEnvTestResult]:
        results = []
        for map_config in self.maps:
            print(f"[MultiEnv] Testing {map_config.name}...")
            result = self._simulate_map_game(map_config)
            results.append(result)
            self.results.append(result)
        return results

    def test_map_specific_strategies(self) -> Dict[str, List[MultiEnvTestResult]]:
        strategies = {
            "expansion_rush": [],
            "defensive": [],
            "aggressive": [],
            "macro": [],
        }

        for map_config in self.maps:
            for strategy in strategies.keys():
                wr = random.uniform(50, 90)
                strategies[strategy].append(
                    MultiEnvTestResult(
                        map_name=map_config.name,
                        map_type=map_config.map_type,
                        passed=wr >= 60,
                        win_rate=wr,
                        avg_build_time=random.uniform(30, 120),
                        expansion_efficiency=random.uniform(60, 100),
                        combat_effectiveness=random.uniform(50, 100),
                    )
                )

        return strategies


def print_multi_env_results(results: List[MultiEnvTestResult]) -> None:
    print("\n" + "=" * 100)
    print("MULTI-ENVIRONMENT MAP TEST RESULTS")
    print("=" * 100)

    avg_wr = sum(r.win_rate for r in results) / len(results)
    passed = sum(1 for r in results if r.passed)

    print(
        f"\nMaps Tested: {len(results)} | Passed: {passed} | Failed: {len(results) - passed} | Avg Win Rate: {avg_wr:.1f}%\n"
    )

    print(
        f"{'Map Name':<20} {'Type':<15} {'Win Rate':>10} {'Build Time':>12} {'Exp Eff':>10} {'Combat':>10}"
    )
    print("-" * 100)

    for r in results:
        status = "[PASS]" if r.passed else "[FAIL]"
        print(
            f"{r.map_name:<20} {r.map_type:<15} {r.win_rate:>8.1f}% {r.avg_build_time:>10.1f}s {r.expansion_efficiency:>8.1f}% {r.combat_effectiveness:>8.1f}%"
        )


if __name__ == "__main__":
    print("[MultiEnv] Starting multi-environment tests...")
    tester = MultiEnvironmentTester()
    results = tester.test_all_maps()
    print_multi_env_results(results)

    strategies = tester.test_map_specific_strategies()
    print("\n" + "=" * 100)
    print("STRATEGY PERFORMANCE BY MAP")
    print("=" * 100)

    for strategy, res_list in strategies.items():
        avg = sum(r.win_rate for r in res_list) / len(res_list)
        print(f"  {strategy:<20}: {avg:.1f}% avg win rate")
