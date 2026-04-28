"""
SC2 Bot performance benchmark suite.
Measures inference latency percentiles, throughput, memory usage,
and APM calculation speed. Generates a JSON report.

Usage:
    pytest benchmarks/bot_benchmark.py --benchmark-json=results.json
    python benchmarks/bot_benchmark.py  # standalone mode
"""

from __future__ import annotations

import json
import os
import random
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# ── Fake policy inference (replace with actual model calls) ──────────────────


def fake_observation(num_units: int = 64) -> dict[str, Any]:
    return {
        "minerals": random.randint(0, 2000),
        "vespene": random.randint(0, 1000),
        "supply_used": random.randint(0, 200),
        "supply_cap": 200,
        "units": [
            {
                "tag": i,
                "type": random.randint(0, 200),
                "x": random.random() * 200,
                "y": random.random() * 200,
                "hp": random.random() * 100,
            }
            for i in range(num_units)
        ],
        "enemy_units": [
            {
                "tag": 10000 + i,
                "type": random.randint(0, 200),
                "x": random.random() * 200,
                "y": random.random() * 200,
                "hp": random.random() * 100,
            }
            for i in range(num_units // 2)
        ],
    }


def fake_inference(obs: dict[str, Any]) -> dict[str, Any]:
    """Simulate a neural network forward pass (~1ms)."""
    time.sleep(0.001)
    return {
        "action_type": random.choice(["attack", "move", "train", "noop"]),
        "unit_tag": random.randint(0, 1000),
        "confidence": random.random(),
    }


def calculate_apm(
    action_log: list[tuple[float, str]], duration_seconds: float
) -> float:
    """Compute APM from a timestamped action log."""
    if duration_seconds <= 0:
        return 0.0
    minutes = duration_seconds / 60.0
    return len(action_log) / minutes


# ── Pytest-benchmark fixtures ─────────────────────────────────────────────────


@pytest.fixture
def sample_obs():
    return fake_observation(num_units=64)


@pytest.fixture
def large_obs():
    return fake_observation(num_units=512)


# ── Inference latency benchmarks ──────────────────────────────────────────────


def test_inference_latency_small(benchmark, sample_obs):
    """Benchmark inference latency with 64 units."""
    result = benchmark(fake_inference, sample_obs)
    assert "action_type" in result


def test_inference_latency_large(benchmark, large_obs):
    """Benchmark inference latency with 512 units (stress test)."""
    result = benchmark(fake_inference, large_obs)
    assert "action_type" in result


def test_observation_construction(benchmark):
    """Benchmark observation dict construction speed."""
    result = benchmark(fake_observation, 128)
    assert "units" in result


# ── APM calculation benchmark ─────────────────────────────────────────────────


def test_apm_calculation(benchmark):
    """Benchmark APM calculation over 1000 actions."""
    action_log = [(i * 0.1, "attack") for i in range(1000)]
    result = benchmark(calculate_apm, action_log, 100.0)
    assert result > 0


# ── Standalone benchmark runner ───────────────────────────────────────────────


def run_latency_benchmark(n: int = 200) -> dict[str, float]:
    """Measure p50/p95/p99 inference latency over n trials."""
    obs = fake_observation(64)
    latencies: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        fake_inference(obs)
        latencies.append((time.perf_counter() - t0) * 1000)  # ms

    latencies.sort()
    return {
        "p50_ms": latencies[int(n * 0.50)],
        "p95_ms": latencies[int(n * 0.95)],
        "p99_ms": latencies[int(n * 0.99)],
        "min_ms": latencies[0],
        "max_ms": latencies[-1],
        "mean_ms": sum(latencies) / n,
    }


def run_throughput_benchmark(duration_s: float = 5.0) -> dict[str, float]:
    """Measure how many inferences per second the system can sustain."""
    obs = fake_observation(64)
    count = 0
    t_start = time.perf_counter()
    while time.perf_counter() - t_start < duration_s:
        fake_inference(obs)
        count += 1
    elapsed = time.perf_counter() - t_start
    return {
        "inferences_per_second": count / elapsed,
        "games_per_hour_estimate": (count / elapsed) * 3600 / 500,
        "total_inferences": count,
        "elapsed_s": elapsed,
    }


def run_memory_benchmark() -> dict[str, float]:
    """Measure peak memory usage during inference."""
    tracemalloc.start()
    obs = fake_observation(512)
    for _ in range(100):
        fake_inference(obs)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "current_kb": current / 1024,
        "peak_kb": peak / 1024,
    }


def main() -> None:
    print("Running SC2 Bot Performance Benchmarks...\n")

    print("1/3 Latency benchmark (200 trials)...")
    latency = run_latency_benchmark(200)

    print("2/3 Throughput benchmark (5s)...")
    throughput = run_throughput_benchmark(5.0)

    print("3/3 Memory benchmark...")
    memory = run_memory_benchmark()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency": latency,
        "throughput": throughput,
        "memory": memory,
    }

    output_path = Path("benchmarks") / "benchmark_results.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))

    print(f"\nResults saved to {output_path}")
    print(f"  p50 latency : {latency['p50_ms']:.2f} ms")
    print(f"  p99 latency : {latency['p99_ms']:.2f} ms")
    print(f"  Throughput  : {throughput['inferences_per_second']:.1f} inf/s")
    print(f"  Peak memory : {memory['peak_kb']:.1f} KB")


if __name__ == "__main__":
    main()
