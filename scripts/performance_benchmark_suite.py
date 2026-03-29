# -*- coding: utf-8 -*-
"""
Phase 67: Performance Optimization & Benchmarking Suite
성능 최적화 및 벤치마킹 모음
"""

import time
import json
import statistics
from typing import Dict, List, Callable, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    operations_per_second: float


class PerformanceBenchmark:
    def __init__(self, warmup: int = 3, iterations: int = 100):
        self.warmup = warmup
        self.iterations = iterations
        self.results: Dict[str, BenchmarkResult] = {}

    def benchmark(self, name: str, func: Callable, *args, **kwargs) -> BenchmarkResult:
        for _ in range(self.warmup):
            func(*args, **kwargs)

        times: List[float] = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        result = BenchmarkResult(
            name=name,
            iterations=self.iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0.0,
            operations_per_second=self.iterations / sum(times),
        )
        self.results[name] = result
        return result

    def compare(
        self,
        func_python: Callable,
        func_rust: Callable,
        test_data: Any,
        iterations: int = 1000,
    ) -> Dict[str, Any]:
        py_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func_python(test_data)
            py_times.append(time.perf_counter() - start)

        rust_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func_rust(test_data)
            rust_times.append(time.perf_counter() - start)

        py_avg = statistics.mean(py_times)
        rust_avg = statistics.mean(rust_times)

        return {
            "python_avg_ms": py_avg * 1000,
            "rust_avg_ms": rust_avg * 1000,
            "speedup": py_avg / rust_avg if rust_avg > 0 else 0,
            "iterations": iterations,
        }

    def generate_report(self) -> str:
        lines = [
            "=" * 60,
            "PERFORMANCE BENCHMARK REPORT",
            "=" * 60,
            f"Warmup iterations: {self.warmup}",
            f"Test iterations: {self.iterations}",
            "",
            "RESULTS:",
            "-" * 60,
        ]

        for name, result in sorted(self.results.items(), key=lambda x: x[1].avg_time):
            lines.extend(
                [
                    f"  {result.name}:",
                    f"    Avg:   {result.avg_time * 1000:.4f} ms",
                    f"    Min:   {result.min_time * 1000:.4f} ms",
                    f"    Max:   {result.max_time * 1000:.4f} ms",
                    f"    StdDev: {result.std_dev * 1000:.4f} ms",
                    f"    Ops/s:  {result.operations_per_second:.2f}",
                    "",
                ]
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    def to_json(self) -> Dict:
        return {name: asdict(result) for name, result in self.results.items()}


def nearest_point_python(
    origin: Tuple[float, float], points: List[Tuple[float, float]]
) -> int:
    ox, oy = origin
    best_idx = 0
    best_dist = float("inf")
    for i, (px, py) in enumerate(points):
        dx = ox - px
        dy = oy - py
        d = dx * dx + dy * dy
        if d < best_dist:
            best_dist = d
            best_idx = i
    return best_idx


def batch_nearest_python(
    origins: List[Tuple[float, float]], points: List[Tuple[float, float]]
) -> List[int]:
    return [nearest_point_python(o, points) for o in origins]


def run_full_benchmark():
    bench = PerformanceBenchmark(warmup=3, iterations=100)

    test_sizes = [100, 1000, 10000]

    print("=== Phase 67: Performance Benchmark ===\n")

    for size in test_sizes:
        points = [(float(i % 100), float(i // 100)) for i in range(size)]
        origin = (50.0, 50.0)

        bench.benchmark(
            f"nearest_point_{size}",
            nearest_point_python,
            origin,
            points,
        )

        origins = [
            (float(i % 10) * 10, float(i // 10) * 10)
            for i in range(min(100, size // 10))
        ]
        bench.benchmark(
            f"batch_nearest_{size}",
            batch_nearest_python,
            origins,
            points,
        )

    print(bench.generate_report())

    report_path = Path("benchmark_results.json")
    report_path.write_text(json.dumps(bench.to_json(), indent=2))
    print(f"\nReport saved to: {report_path}")

    try:
        from wicked_zerg_challenger.rust_accel import (
            nearest_point_index as rust_nearest,
        )

        print("\n=== Rust Comparison ===")
        size = 10000
        points = [(float(i % 100), float(i // 100)) for i in range(size)]
        origin = (50.0, 50.0)

        comparison = bench.compare(
            lambda d: nearest_point_python(origin, d),
            lambda d: rust_nearest(origin, d),
            points,
            iterations=1000,
        )
        print(f"Python avg: {comparison['python_avg_ms']:.4f} ms")
        print(f"Rust avg:   {comparison['rust_avg_ms']:.4f} ms")
        print(f"Speedup:    {comparison['speedup']:.2f}x")
    except ImportError:
        print("\n[Rust not available, skipping comparison]")


if __name__ == "__main__":
    run_full_benchmark()
