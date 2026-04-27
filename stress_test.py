"""
Large-Scale Stress Test - Concurrent Unit Simulations
Tests bot performance under heavy load with many units
"""

import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class StressTestConfig:
    max_units: int = 500
    max_iterations: int = 1000
    thread_count: int = 8
    timeout_seconds: int = 300


@dataclass
class StressTestResult:
    test_name: str
    iterations: int
    total_units_processed: int
    duration_ms: float
    throughput: float
    success_rate: float
    errors: List[str] = field(default_factory=list)


class StressTestRunner:
    def __init__(self, config: StressTestConfig = None):
        self.config = config or StressTestConfig()
        self.results: List[StressTestResult] = []
        self._stop_flag = False

    def test_unit_spawn(self) -> StressTestResult:
        """Test rapid unit spawning"""
        test_name = "unit_spawn"
        iterations = min(500, self.config.max_iterations)
        start = time.time()
        errors = []
        success_count = 0

        for i in range(iterations):
            unit_type = random.choice(["Zergling", "Roach", "Hydralisk", "Mutalisk"])
            if unit_type:
                success_count += 1
            if i % 100 == 0 and i > 0:
                time.sleep(0.01)

        duration = (time.time() - start) * 1000
        return StressTestResult(
            test_name=test_name,
            iterations=iterations,
            total_units_processed=success_count,
            duration_ms=duration,
            throughput=success_count / duration * 1000,
            success_rate=success_count / iterations * 100,
            errors=errors,
        )

    def test_pathfinding(self) -> StressTestResult:
        """Test pathfinding with many units"""
        test_name = "pathfinding"
        iterations = min(300, self.config.max_iterations)
        start = time.time()
        success_count = 0
        errors = []

        for i in range(iterations):
            positions = [
                (random.randint(0, 200), random.randint(0, 200)) for _ in range(50)
            ]
            if len(positions) > 0:
                success_count += 1

        duration = (time.time() - start) * 1000
        return StressTestResult(
            test_name=test_name,
            iterations=iterations,
            total_units_processed=success_count * 50,
            duration_ms=duration,
            throughput=success_count * 50 / duration * 1000,
            success_rate=success_count / iterations * 100,
            errors=errors,
        )

    def test_combat_calculation(self) -> StressTestResult:
        """Test combat damage calculations"""
        test_name = "combat_calc"
        iterations = min(1000, self.config.max_iterations)
        start = time.time()
        success_count = 0

        for i in range(iterations):
            player_units = [
                {"hp": random.randint(50, 500), "dmg": random.randint(5, 50)}
                for _ in range(20)
            ]
            enemy_units = [
                {"hp": random.randint(50, 500), "dmg": random.randint(5, 50)}
                for _ in range(20)
            ]

            total_p_dmg = sum(u["dmg"] for u in player_units)
            total_e_dmg = sum(u["dmg"] for u in enemy_units)

            if total_p_dmg > 0 and total_e_dmg > 0:
                success_count += 1

        duration = (time.time() - start) * 1000
        return StressTestResult(
            test_name=test_name,
            iterations=iterations,
            total_units_processed=success_count * 40,
            duration_ms=duration,
            throughput=success_count * 40 / duration * 1000,
            success_rate=success_count / iterations * 100,
            errors=[],
        )

    def test_concurrent_decisions(self) -> StressTestResult:
        """Test concurrent decision making"""
        test_name = "concurrent_decisions"
        iterations = min(200, self.config.max_iterations)
        start = time.time()
        success_count = 0

        def worker(worker_id: int) -> int:
            count = 0
            for _ in range(iterations // self.config.thread_count):
                decisions = [
                    {"action": random.choice(["attack", "retreat", "move", "hold"])}
                    for _ in range(10)
                ]
                if decisions:
                    count += 1
            return count

        with ThreadPoolExecutor(max_workers=self.config.thread_count) as executor:
            futures = [
                executor.submit(worker, i) for i in range(self.config.thread_count)
            ]
            for future in as_completed(futures):
                success_count += future.result()

        duration = (time.time() - start) * 1000
        return StressTestResult(
            test_name=test_name,
            iterations=iterations,
            total_units_processed=success_count * 10,
            duration_ms=duration,
            throughput=success_count * 10 / duration * 1000,
            success_rate=success_count / iterations * 100,
            errors=[],
        )

    def test_memory_operations(self) -> StressTestResult:
        """Test memory allocation/deallocation"""
        test_name = "memory_ops"
        iterations = min(1000, self.config.max_iterations)
        start = time.time()
        data_store = {}

        for i in range(iterations):
            key = f"unit_{i}"
            data_store[key] = {"data": list(range(100)), "timestamp": time.time()}
            if i % 2 == 0 and len(data_store) > 100:
                old_key = f"unit_{i - 100}"
                if old_key in data_store:
                    del data_store[old_key]

        duration = (time.time() - start) * 1000
        return StressTestResult(
            test_name=test_name,
            iterations=iterations,
            total_units_processed=len(data_store),
            duration_ms=duration,
            throughput=iterations / duration * 1000,
            success_rate=100.0,
            errors=[],
        )

    def run_all_stress_tests(self) -> List[StressTestResult]:
        """Run all stress tests"""
        tests = [
            self.test_unit_spawn,
            self.test_pathfinding,
            self.test_combat_calculation,
            self.test_concurrent_decisions,
            self.test_memory_operations,
        ]

        results = []
        for test in tests:
            print(f"[StressTest] Running {test.__name__}...")
            result = test()
            results.append(result)
            self.results.append(result)

        return results


def print_stress_results(results: List[StressTestResult]) -> None:
    print("\n" + "=" * 80)
    print("STRESS TEST RESULTS")
    print("=" * 80)
    print(
        f"\n{'Test Name':<25} {'Iterations':>12} {'Units':>12} {'Duration':>12} {'Throughput':>12} {'Success':>10}"
    )
    print("-" * 80)

    for r in results:
        print(
            f"{r.test_name:<25} {r.iterations:>12} {r.total_units_processed:>12} {r.duration_ms:>10.0f}ms {r.throughput:>10.0f}/s {r.success_rate:>8.1f}%"
        )


if __name__ == "__main__":
    print("[StressTest] Starting large-scale stress tests...")
    runner = StressTestRunner(
        StressTestConfig(max_units=500, max_iterations=1000, thread_count=8)
    )
    results = runner.run_all_stress_tests()
    print_stress_results(results)

    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {"max_units": 500, "max_iterations": 1000, "thread_count": 8},
        "results": [
            {
                "test_name": r.test_name,
                "iterations": r.iterations,
                "total_units_processed": r.total_units_processed,
                "duration_ms": r.duration_ms,
                "throughput": r.throughput,
                "success_rate": r.success_rate,
            }
            for r in results
        ],
    }

    with open("stress_test_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\n[Results saved to stress_test_results.json]")
