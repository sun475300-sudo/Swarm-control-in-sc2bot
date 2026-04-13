"""
Performance Benchmark Suite - Detailed Performance Metrics
Benchmarks various system components and operations
"""

import json
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    min_duration: float
    max_duration: float
    avg_duration: float
    p50_duration: float
    p95_duration: float
    p99_duration: float
    ops_per_second: float
    total_time: float


class PerformanceBenchmark:
    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def benchmark_unit_sorting(self) -> BenchmarkResult:
        """Benchmark unit sorting algorithms"""
        iterations = 10000
        units = [
            {"id": i, "hp": random.randint(30, 500), "damage": random.randint(5, 50)}
            for i in range(100)
        ]

        durations = []
        for _ in range(iterations):
            start = time.perf_counter()
            sorted_units = sorted(
                units, key=lambda x: (x["hp"], x["damage"]), reverse=True
            )
            durations.append((time.perf_counter() - start) * 1000)

        return self._create_result("unit_sorting", iterations, durations)

    def benchmark_path_cache(self) -> BenchmarkResult:
        """Benchmark pathfinding cache"""
        iterations = 5000
        cache = {}

        durations = []
        for _ in range(iterations):
            key = f"{random.randint(0, 100)}-{random.randint(0, 100)}"
            start = time.perf_counter()

            if key in cache:
                result = cache[key]
            else:
                path = [(i, i) for i in range(10)]
                cache[key] = path
                result = path

            durations.append((time.perf_counter() - start) * 1000)

        return self._create_result("path_cache", iterations, durations)

    def benchmark_state_updates(self) -> BenchmarkResult:
        """Benchmark state update operations"""
        iterations = 20000
        state = {"units": [], "structures": [], "resources": {}}

        durations = []
        for i in range(iterations):
            start = time.perf_counter()

            state["units"].append({"id": i, "hp": 100})
            if len(state["units"]) > 1000:
                state["units"].pop(0)
            state["structures"] = [
                s for s in state["structures"] if random.random() > 0.001
            ]
            state["resources"]["minerals"] = random.randint(0, 10000)

            durations.append((time.perf_counter() - start) * 1000)

        return self._create_result("state_updates", iterations, durations)

    def benchmark_decision_making(self) -> BenchmarkResult:
        """Benchmark AI decision making"""
        iterations = 10000

        durations = []
        for _ in range(iterations):
            start = time.perf_counter()

            priorities = [
                {"action": "expand", "score": random.random()},
                {"action": "train_worker", "score": random.random()},
                {"action": "train_army", "score": random.random()},
                {"action": "research_tech", "score": random.random()},
                {"action": "attack", "score": random.random()},
            ]
            priorities.sort(key=lambda x: x["score"], reverse=True)
            decision = priorities[0] if priorities else None

            durations.append((time.perf_counter() - start) * 1000)

        return self._create_result("decision_making", iterations, durations)

    def benchmark_spatial_search(self) -> BenchmarkResult:
        """Benchmark spatial search operations"""
        iterations = 5000
        points = [(random.randint(0, 200), random.randint(0, 200)) for _ in range(500)]

        durations = []
        for _ in range(iterations):
            target = (random.randint(0, 200), random.randint(0, 200))
            start = time.perf_counter()

            nearby = [
                p
                for p in points
                if abs(p[0] - target[0]) < 20 and abs(p[1] - target[1]) < 20
            ]

            durations.append((time.perf_counter() - start) * 1000)

        return self._create_result("spatial_search", iterations, durations)

    def benchmark_json_serialization(self) -> BenchmarkResult:
        """Benchmark JSON serialization"""
        iterations = 5000
        data = {
            "game_state": {
                "units": [
                    {
                        "id": i,
                        "type": random.choice(["Zergling", "Roach", "Hydralisk"]),
                        "hp": random.randint(30, 500),
                        "pos": (random.randint(0, 200), random.randint(0, 200)),
                    }
                    for i in range(50)
                ],
                "structures": [
                    {
                        "id": i,
                        "type": random.choice(
                            ["Hatchery", "SpawningPool", "RoachWarren"]
                        ),
                    }
                    for i in range(10)
                ],
                "resources": {
                    "minerals": random.randint(0, 10000),
                    "gas": random.randint(0, 5000),
                },
            }
        }

        durations = []
        for _ in range(iterations):
            start = time.perf_counter()
            serialized = json.dumps(data)
            deserialized = json.loads(serialized)
            durations.append((time.perf_counter() - start) * 1000)

        return self._create_result("json_serialization", iterations, durations)

    def _create_result(
        self, name: str, iterations: int, durations: List[float]
    ) -> BenchmarkResult:
        durations.sort()
        total_time = sum(durations)

        return BenchmarkResult(
            name=name,
            iterations=iterations,
            min_duration=min(durations),
            max_duration=max(durations),
            avg_duration=total_time / iterations,
            p50_duration=durations[len(durations) // 2],
            p95_duration=durations[int(len(durations) * 0.95)],
            p99_duration=durations[int(len(durations) * 0.99)],
            ops_per_second=iterations / total_time * 1000,
            total_time=total_time,
        )

    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all benchmarks"""
        benchmarks = [
            self.benchmark_unit_sorting,
            self.benchmark_path_cache,
            self.benchmark_state_updates,
            self.benchmark_decision_making,
            self.benchmark_spatial_search,
            self.benchmark_json_serialization,
        ]

        results = []
        for bench in benchmarks:
            print(f"[Benchmark] Running {bench.__name__}...")
            result = bench()
            results.append(result)
            self.results.append(result)

        return results


def print_benchmark_results(results: List[BenchmarkResult]) -> None:
    print("\n" + "=" * 100)
    print("PERFORMANCE BENCHMARK RESULTS")
    print("=" * 100)
    print(
        f"\n{'Operation':<25} {'Iterations':>12} {'Avg (ms)':>12} {'P50':>10} {'P95':>10} {'P99':>10} {'Ops/sec':>15}"
    )
    print("-" * 100)

    for r in results:
        print(
            f"{r.name:<25} {r.iterations:>12} {r.avg_duration:>10.3f} {r.p50_duration:>10.3f} {r.p95_duration:>10.3f} {r.p99_duration:>10.3f} {r.ops_per_second:>15,.0f}"
        )


if __name__ == "__main__":
    print("[Benchmark] Starting performance benchmarks...")
    bench = PerformanceBenchmark()
    results = bench.run_all_benchmarks()
    print_benchmark_results(results)

    output = {
        "timestamp": datetime.now().isoformat(),
        "results": [
            {
                "name": r.name,
                "iterations": r.iterations,
                "min_duration_ms": r.min_duration,
                "max_duration_ms": r.max_duration,
                "avg_duration_ms": r.avg_duration,
                "p50_ms": r.p50_duration,
                "p95_ms": r.p95_duration,
                "p99_ms": r.p99_duration,
                "ops_per_second": r.ops_per_second,
            }
            for r in results
        ],
    }

    with open("benchmark_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\n[Results saved to benchmark_results.json]")
