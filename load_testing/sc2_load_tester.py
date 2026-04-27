# Phase 660: Load Testing for SC2 Infrastructure Scalability
# Simulates concurrent users and bot instances to measure throughput, latency, and error rates

from __future__ import annotations

import json
import math
import os
import random
import statistics
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ============================================================
# Statistics Helpers
# ============================================================


def _percentile(data: List[float], pct: float) -> float:
    """Calculate percentile without numpy."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def _mean(data: List[float]) -> float:
    if not data:
        return 0.0
    return sum(data) / len(data)


def _stddev(data: List[float]) -> float:
    if len(data) < 2:
        return 0.0
    m = _mean(data)
    var = sum((x - m) ** 2 for x in data) / (len(data) - 1)
    return math.sqrt(var)


# ============================================================
# Enums and Constants
# ============================================================


class LoadProfileType(Enum):
    """Types of load profiles for testing."""

    CONSTANT = "constant"
    RAMP_UP = "ramp_up"
    SPIKE = "spike"
    SOAK = "soak"


class RequestType(Enum):
    """SC2-specific request types to simulate."""

    BOT_API_CALL = "bot_api_call"
    TRAINING_PIPELINE = "training_pipeline"
    DASHBOARD_QUERY = "dashboard_query"
    REPLAY_ANALYSIS = "replay_analysis"
    MODEL_INFERENCE = "model_inference"
    STRATEGY_LOOKUP = "strategy_lookup"


# ============================================================
# ResponseMetrics
# ============================================================


@dataclass
class ResponseMetrics:
    """Metrics collected from a single request."""

    request_id: str
    request_type: str
    start_time: float
    end_time: float
    latency_ms: float
    status_code: int
    success: bool
    payload_bytes: int = 0
    error_message: str = ""
    virtual_user_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request_type": self.request_type,
            "latency_ms": round(self.latency_ms, 3),
            "status_code": self.status_code,
            "success": self.success,
            "payload_bytes": self.payload_bytes,
            "error_message": self.error_message,
        }


# ============================================================
# LoadProfile
# ============================================================


@dataclass
class LoadProfile:
    """Defines how load is applied over time."""

    profile_type: LoadProfileType
    duration_seconds: float
    target_users: int
    ramp_up_seconds: float = 0.0
    spike_multiplier: float = 3.0
    spike_duration_seconds: float = 5.0
    spike_interval_seconds: float = 30.0
    requests_per_second_per_user: float = 1.0

    def get_active_users_at(self, elapsed: float) -> int:
        """Return the number of active virtual users at a given elapsed time."""
        if elapsed < 0 or elapsed > self.duration_seconds:
            return 0

        if self.profile_type == LoadProfileType.CONSTANT:
            return self.target_users

        elif self.profile_type == LoadProfileType.RAMP_UP:
            if self.ramp_up_seconds <= 0:
                return self.target_users
            progress = min(elapsed / self.ramp_up_seconds, 1.0)
            return max(1, int(self.target_users * progress))

        elif self.profile_type == LoadProfileType.SPIKE:
            base = self.target_users
            if self.spike_interval_seconds > 0:
                cycle_pos = elapsed % self.spike_interval_seconds
                if cycle_pos < self.spike_duration_seconds:
                    return min(int(base * self.spike_multiplier), base * 10)
            return base

        elif self.profile_type == LoadProfileType.SOAK:
            # Soak: constant load for long duration
            return self.target_users

        return self.target_users

    def describe(self) -> str:
        desc = f"Profile: {self.profile_type.value}, Duration: {self.duration_seconds}s"
        desc += f", Target Users: {self.target_users}"
        if self.profile_type == LoadProfileType.RAMP_UP:
            desc += f", Ramp-up: {self.ramp_up_seconds}s"
        elif self.profile_type == LoadProfileType.SPIKE:
            desc += (
                f", Spike: {self.spike_multiplier}x for {self.spike_duration_seconds}s"
            )
        return desc


# ============================================================
# VirtualUser
# ============================================================


class VirtualUser:
    """Simulates a single concurrent user making requests."""

    def __init__(
        self,
        user_id: str,
        request_types: Optional[List[RequestType]] = None,
        think_time_range: Tuple[float, float] = (0.05, 0.2),
    ):
        self.user_id = user_id
        self.request_types = request_types or list(RequestType)
        self.think_time_range = think_time_range
        self.metrics: List[ResponseMetrics] = []
        self.active = False
        self._request_count = 0

    def simulate_request(
        self,
        request_type: Optional[RequestType] = None,
        target_handler: Optional[Callable] = None,
    ) -> ResponseMetrics:
        """Simulate a single request and collect metrics."""
        req_type = request_type or random.choice(self.request_types)
        request_id = f"{self.user_id}-req-{self._request_count}"
        self._request_count += 1

        start_time = time.time()

        if target_handler is not None:
            try:
                result = target_handler(req_type.value, self.user_id)
                latency_ms = (time.time() - start_time) * 1000
                metric = ResponseMetrics(
                    request_id=request_id,
                    request_type=req_type.value,
                    start_time=start_time,
                    end_time=time.time(),
                    latency_ms=latency_ms,
                    status_code=result.get("status_code", 200),
                    success=result.get("success", True),
                    payload_bytes=result.get("payload_bytes", 0),
                    virtual_user_id=self.user_id,
                )
            except Exception as exc:
                latency_ms = (time.time() - start_time) * 1000
                metric = ResponseMetrics(
                    request_id=request_id,
                    request_type=req_type.value,
                    start_time=start_time,
                    end_time=time.time(),
                    latency_ms=latency_ms,
                    status_code=500,
                    success=False,
                    error_message=str(exc),
                    virtual_user_id=self.user_id,
                )
        else:
            # Simulated response with realistic latencies per request type
            latency_map: Dict[str, Tuple[float, float]] = {
                RequestType.BOT_API_CALL.value: (5.0, 50.0),
                RequestType.TRAINING_PIPELINE.value: (100.0, 2000.0),
                RequestType.DASHBOARD_QUERY.value: (10.0, 200.0),
                RequestType.REPLAY_ANALYSIS.value: (50.0, 500.0),
                RequestType.MODEL_INFERENCE.value: (20.0, 300.0),
                RequestType.STRATEGY_LOOKUP.value: (2.0, 30.0),
            }
            low, high = latency_map.get(req_type.value, (5.0, 100.0))
            simulated_latency = random.uniform(low, high)
            # Inject occasional errors (~3%)
            is_error = random.random() < 0.03
            status_code = 500 if is_error else 200

            time.sleep(simulated_latency / 10000.0)  # Scaled-down sleep
            end_time = time.time()
            metric = ResponseMetrics(
                request_id=request_id,
                request_type=req_type.value,
                start_time=start_time,
                end_time=end_time,
                latency_ms=simulated_latency,
                status_code=status_code,
                success=not is_error,
                payload_bytes=random.randint(128, 8192),
                error_message="Simulated server error" if is_error else "",
                virtual_user_id=self.user_id,
            )

        self.metrics.append(metric)
        return metric

    def run_session(
        self,
        duration_seconds: float,
        requests_per_second: float = 1.0,
        target_handler: Optional[Callable] = None,
    ) -> List[ResponseMetrics]:
        """Run a session of requests for a given duration."""
        self.active = True
        session_start = time.time()
        interval = 1.0 / max(requests_per_second, 0.01)

        while time.time() - session_start < duration_seconds and self.active:
            self.simulate_request(target_handler=target_handler)
            think_time = random.uniform(*self.think_time_range)
            time.sleep(min(interval, think_time) * 0.1)  # Scaled for demo

        self.active = False
        return self.metrics

    def get_summary(self) -> Dict[str, Any]:
        latencies = [m.latency_ms for m in self.metrics]
        successes = sum(1 for m in self.metrics if m.success)
        return {
            "user_id": self.user_id,
            "total_requests": len(self.metrics),
            "successes": successes,
            "failures": len(self.metrics) - successes,
            "avg_latency_ms": round(_mean(latencies), 2),
            "p50_latency_ms": round(_percentile(latencies, 50), 2),
            "p95_latency_ms": round(_percentile(latencies, 95), 2),
            "p99_latency_ms": round(_percentile(latencies, 99), 2),
        }


# ============================================================
# LoadBalancer
# ============================================================


class LoadBalancer:
    """Simulates request distribution across backend instances."""

    def __init__(self, num_instances: int = 3, algorithm: str = "round_robin"):
        self.num_instances = max(num_instances, 1)
        self.algorithm = algorithm
        self._rr_index = 0
        self.instance_loads: Dict[int, int] = {i: 0 for i in range(self.num_instances)}
        self.instance_latencies: Dict[int, List[float]] = {
            i: [] for i in range(self.num_instances)
        }
        self._lock = threading.Lock()

    def select_instance(self) -> int:
        """Select a backend instance based on the balancing algorithm."""
        with self._lock:
            if self.algorithm == "round_robin":
                idx = self._rr_index % self.num_instances
                self._rr_index += 1
                return idx
            elif self.algorithm == "least_connections":
                return min(self.instance_loads, key=lambda k: self.instance_loads[k])
            elif self.algorithm == "random":
                return random.randint(0, self.num_instances - 1)
            elif self.algorithm == "weighted":
                # Prefer instances with lower average latency
                weights = []
                for i in range(self.num_instances):
                    avg = (
                        _mean(self.instance_latencies[i])
                        if self.instance_latencies[i]
                        else 1.0
                    )
                    weights.append(1.0 / max(avg, 0.1))
                total = sum(weights)
                probs = [w / total for w in weights]
                r = random.random()
                cumulative = 0.0
                for i, p in enumerate(probs):
                    cumulative += p
                    if r <= cumulative:
                        return i
                return self.num_instances - 1
            else:
                return random.randint(0, self.num_instances - 1)

    def record_request(self, instance_id: int, latency_ms: float) -> None:
        with self._lock:
            self.instance_loads[instance_id] = (
                self.instance_loads.get(instance_id, 0) + 1
            )
            if instance_id not in self.instance_latencies:
                self.instance_latencies[instance_id] = []
            self.instance_latencies[instance_id].append(latency_ms)

    def release_connection(self, instance_id: int) -> None:
        with self._lock:
            if instance_id in self.instance_loads:
                self.instance_loads[instance_id] = max(
                    0, self.instance_loads[instance_id] - 1
                )

    def get_distribution_report(self) -> Dict[str, Any]:
        report: Dict[str, Any] = {"algorithm": self.algorithm, "instances": {}}
        for i in range(self.num_instances):
            lats = self.instance_latencies.get(i, [])
            report["instances"][f"instance_{i}"] = {
                "total_requests": len(lats),
                "active_connections": self.instance_loads.get(i, 0),
                "avg_latency_ms": round(_mean(lats), 2) if lats else 0.0,
                "p95_latency_ms": round(_percentile(lats, 95), 2) if lats else 0.0,
            }
        return report


# ============================================================
# LatencyHistogram
# ============================================================


class LatencyHistogram:
    """Builds a histogram of latency distribution."""

    def __init__(self, bucket_count: int = 20):
        self.bucket_count = bucket_count
        self._data: List[float] = []

    def add(self, value: float) -> None:
        self._data.append(value)

    def add_many(self, values: List[float]) -> None:
        self._data.extend(values)

    def render(self, width: int = 50) -> str:
        if not self._data:
            return "  (no data)"
        mn = min(self._data)
        mx = max(self._data)
        if mn == mx:
            return f"  All values = {mn:.2f}ms"

        bucket_width = (mx - mn) / self.bucket_count
        buckets = [0] * self.bucket_count
        for v in self._data:
            idx = min(int((v - mn) / bucket_width), self.bucket_count - 1)
            buckets[idx] += 1

        max_count = max(buckets) if buckets else 1
        lines = []
        for i, count in enumerate(buckets):
            lo = mn + i * bucket_width
            hi = lo + bucket_width
            bar_len = int((count / max_count) * width) if max_count > 0 else 0
            bar = "#" * bar_len
            lines.append(f"  {lo:8.1f}-{hi:8.1f}ms | {bar} ({count})")
        return "\n".join(lines)


# ============================================================
# TestScenario
# ============================================================


@dataclass
class TestScenario:
    """Defines a complete load test scenario."""

    name: str
    profile: LoadProfile
    request_types: List[RequestType] = field(default_factory=lambda: list(RequestType))
    load_balancer_instances: int = 3
    load_balancer_algorithm: str = "round_robin"
    tags: Dict[str, str] = field(default_factory=dict)

    def describe(self) -> str:
        return (
            f"Scenario: {self.name}\n"
            f"  {self.profile.describe()}\n"
            f"  Request Types: {[r.value for r in self.request_types]}\n"
            f"  LB: {self.load_balancer_algorithm} x{self.load_balancer_instances}"
        )


# ============================================================
# TestReport
# ============================================================


class TestReport:
    """Aggregates and reports on load test results."""

    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.all_metrics: List[ResponseMetrics] = []
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def add_metrics(self, metrics: List[ResponseMetrics]) -> None:
        self.all_metrics.extend(metrics)

    def compute_summary(self) -> Dict[str, Any]:
        if not self.all_metrics:
            return {"error": "No metrics collected"}

        latencies = [m.latency_ms for m in self.all_metrics]
        successes = sum(1 for m in self.all_metrics if m.success)
        failures = len(self.all_metrics) - successes
        elapsed = (
            self.end_time - self.start_time if self.end_time > self.start_time else 1.0
        )

        # Per request type breakdown
        by_type: Dict[str, List[float]] = {}
        for m in self.all_metrics:
            by_type.setdefault(m.request_type, []).append(m.latency_ms)

        type_summaries = {}
        for rtype, lats in by_type.items():
            type_summaries[rtype] = {
                "count": len(lats),
                "avg_ms": round(_mean(lats), 2),
                "p50_ms": round(_percentile(lats, 50), 2),
                "p95_ms": round(_percentile(lats, 95), 2),
                "p99_ms": round(_percentile(lats, 99), 2),
                "min_ms": round(min(lats), 2),
                "max_ms": round(max(lats), 2),
            }

        return {
            "scenario": self.scenario_name,
            "total_requests": len(self.all_metrics),
            "successes": successes,
            "failures": failures,
            "error_rate": round(failures / max(len(self.all_metrics), 1) * 100, 2),
            "throughput_rps": round(len(self.all_metrics) / elapsed, 2),
            "duration_seconds": round(elapsed, 2),
            "latency": {
                "avg_ms": round(_mean(latencies), 2),
                "p50_ms": round(_percentile(latencies, 50), 2),
                "p95_ms": round(_percentile(latencies, 95), 2),
                "p99_ms": round(_percentile(latencies, 99), 2),
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2),
                "stddev_ms": round(_stddev(latencies), 2),
            },
            "by_request_type": type_summaries,
        }

    def print_report(self) -> None:
        summary = self.compute_summary()
        print(f"\n{'=' * 70}")
        print(f"  LOAD TEST REPORT: {summary.get('scenario', 'N/A')}")
        print(f"{'=' * 70}")
        print(f"  Total Requests:  {summary['total_requests']}")
        print(f"  Successes:       {summary['successes']}")
        print(f"  Failures:        {summary['failures']}")
        print(f"  Error Rate:      {summary['error_rate']}%")
        print(f"  Throughput:      {summary['throughput_rps']} req/s")
        print(f"  Duration:        {summary['duration_seconds']}s")
        print(f"\n  Latency Summary:")
        lat = summary["latency"]
        print(f"    Average:  {lat['avg_ms']} ms")
        print(f"    p50:      {lat['p50_ms']} ms")
        print(f"    p95:      {lat['p95_ms']} ms")
        print(f"    p99:      {lat['p99_ms']} ms")
        print(f"    Min:      {lat['min_ms']} ms")
        print(f"    Max:      {lat['max_ms']} ms")
        print(f"    Stddev:   {lat['stddev_ms']} ms")

        print(f"\n  Per Request Type:")
        for rtype, stats in summary.get("by_request_type", {}).items():
            print(f"    {rtype}:")
            print(
                f"      Count: {stats['count']}, Avg: {stats['avg_ms']}ms, "
                f"p95: {stats['p95_ms']}ms, p99: {stats['p99_ms']}ms"
            )

        # Histogram
        latencies = [m.latency_ms for m in self.all_metrics]
        hist = LatencyHistogram(bucket_count=15)
        hist.add_many(latencies)
        print(f"\n  Latency Distribution:")
        print(hist.render(width=40))
        print(f"{'=' * 70}")

    def export_json(self, filepath: str) -> None:
        summary = self.compute_summary()
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


# ============================================================
# SC2LoadTester
# ============================================================


class SC2LoadTester:
    """Main load testing orchestrator for SC2 bot infrastructure."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.scenarios: List[TestScenario] = []
        self.reports: List[TestReport] = []
        self._default_think_time = (0.01, 0.05)

    def add_scenario(self, scenario: TestScenario) -> None:
        self.scenarios.append(scenario)

    def create_constant_load_scenario(
        self,
        name: str,
        users: int = 10,
        duration: float = 10.0,
        rps_per_user: float = 2.0,
    ) -> TestScenario:
        profile = LoadProfile(
            profile_type=LoadProfileType.CONSTANT,
            duration_seconds=duration,
            target_users=users,
            requests_per_second_per_user=rps_per_user,
        )
        scenario = TestScenario(name=name, profile=profile)
        self.add_scenario(scenario)
        return scenario

    def create_ramp_up_scenario(
        self,
        name: str,
        max_users: int = 50,
        ramp_up_seconds: float = 10.0,
        duration: float = 30.0,
    ) -> TestScenario:
        profile = LoadProfile(
            profile_type=LoadProfileType.RAMP_UP,
            duration_seconds=duration,
            target_users=max_users,
            ramp_up_seconds=ramp_up_seconds,
        )
        scenario = TestScenario(name=name, profile=profile)
        self.add_scenario(scenario)
        return scenario

    def create_spike_scenario(
        self,
        name: str,
        base_users: int = 10,
        spike_multiplier: float = 5.0,
        spike_duration: float = 3.0,
        duration: float = 30.0,
    ) -> TestScenario:
        profile = LoadProfile(
            profile_type=LoadProfileType.SPIKE,
            duration_seconds=duration,
            target_users=base_users,
            spike_multiplier=spike_multiplier,
            spike_duration_seconds=spike_duration,
            spike_interval_seconds=10.0,
        )
        scenario = TestScenario(name=name, profile=profile)
        self.add_scenario(scenario)
        return scenario

    def create_soak_scenario(
        self,
        name: str,
        users: int = 5,
        duration: float = 60.0,
    ) -> TestScenario:
        profile = LoadProfile(
            profile_type=LoadProfileType.SOAK,
            duration_seconds=duration,
            target_users=users,
        )
        scenario = TestScenario(name=name, profile=profile)
        self.add_scenario(scenario)
        return scenario

    def _run_scenario(
        self,
        scenario: TestScenario,
        target_handler: Optional[Callable] = None,
    ) -> TestReport:
        """Execute a single load test scenario."""
        report = TestReport(scenario_name=scenario.name)
        lb = LoadBalancer(
            num_instances=scenario.load_balancer_instances,
            algorithm=scenario.load_balancer_algorithm,
        )

        # Create virtual users
        users: List[VirtualUser] = []
        for i in range(scenario.profile.target_users):
            vu = VirtualUser(
                user_id=f"vu-{i:04d}",
                request_types=scenario.request_types,
                think_time_range=self._default_think_time,
            )
            users.append(vu)

        report.start_time = time.time()
        all_metrics: List[ResponseMetrics] = []
        step_interval = 0.5  # Check active user count every 0.5s
        elapsed = 0.0
        duration = scenario.profile.duration_seconds

        while elapsed < duration:
            active_count = scenario.profile.get_active_users_at(elapsed)
            active_users = users[:active_count]

            for vu in active_users:
                instance_id = lb.select_instance()
                metric = vu.simulate_request(target_handler=target_handler)
                lb.record_request(instance_id, metric.latency_ms)
                lb.release_connection(instance_id)
                all_metrics.append(metric)

            time.sleep(step_interval * 0.05)  # Scaled for demo speed
            elapsed = time.time() - report.start_time

        report.end_time = time.time()
        report.add_metrics(all_metrics)

        # Attach LB report
        lb_report = lb.get_distribution_report()
        print(f"\n  Load Balancer ({lb_report['algorithm']}) distribution:")
        for inst, stats in lb_report["instances"].items():
            print(
                f"    {inst}: {stats['total_requests']} reqs, "
                f"avg={stats['avg_latency_ms']}ms"
            )

        return report

    def run_all(
        self,
        target_handler: Optional[Callable] = None,
    ) -> List[TestReport]:
        """Run all registered scenarios sequentially."""
        self.reports = []
        for scenario in self.scenarios:
            print(f"\n{'~' * 70}")
            print(f"  Running scenario: {scenario.name}")
            print(f"  {scenario.profile.describe()}")
            print(f"{'~' * 70}")
            report = self._run_scenario(scenario, target_handler=target_handler)
            report.print_report()
            self.reports.append(report)
        return self.reports

    def run_training_pipeline_stress(
        self,
        concurrent_pipelines: int = 5,
        batches_per_pipeline: int = 10,
    ) -> Dict[str, Any]:
        """SC2-specific: stress test training pipeline throughput."""
        print(f"\n  Training Pipeline Stress Test")
        print(
            f"    Pipelines: {concurrent_pipelines}, Batches each: {batches_per_pipeline}"
        )

        all_latencies: List[float] = []
        errors = 0

        for p in range(concurrent_pipelines):
            for b in range(batches_per_pipeline):
                # Simulate batch processing: data load + forward pass + backprop
                data_load_ms = random.uniform(5.0, 20.0)
                forward_ms = random.uniform(10.0, 50.0)
                backprop_ms = random.uniform(15.0, 60.0)
                total_ms = data_load_ms + forward_ms + backprop_ms
                if random.random() < 0.02:
                    errors += 1
                else:
                    all_latencies.append(total_ms)

        total_batches = concurrent_pipelines * batches_per_pipeline
        result = {
            "concurrent_pipelines": concurrent_pipelines,
            "total_batches": total_batches,
            "successful_batches": total_batches - errors,
            "errors": errors,
            "avg_batch_ms": round(_mean(all_latencies), 2),
            "p95_batch_ms": round(_percentile(all_latencies, 95), 2),
            "p99_batch_ms": round(_percentile(all_latencies, 99), 2),
            "estimated_throughput_batches_per_sec": (
                round(1000.0 / max(_mean(all_latencies), 0.01), 2)
                if all_latencies
                else 0.0
            ),
        }
        print(
            f"    Avg batch: {result['avg_batch_ms']}ms, "
            f"p95: {result['p95_batch_ms']}ms, "
            f"Errors: {result['errors']}"
        )
        return result

    def run_dashboard_concurrency_test(
        self,
        concurrent_users: int = 20,
        queries_per_user: int = 10,
    ) -> Dict[str, Any]:
        """SC2-specific: test dashboard under concurrent user load."""
        print(f"\n  Dashboard Concurrency Test")
        print(f"    Users: {concurrent_users}, Queries each: {queries_per_user}")

        query_types = [
            ("game_stats", (5.0, 30.0)),
            ("replay_list", (10.0, 80.0)),
            ("strategy_heatmap", (20.0, 150.0)),
            ("matchup_winrates", (8.0, 50.0)),
            ("training_progress", (5.0, 40.0)),
        ]

        all_latencies: List[float] = []
        by_query: Dict[str, List[float]] = {}
        errors = 0

        for _ in range(concurrent_users):
            for _ in range(queries_per_user):
                qname, (lo, hi) = random.choice(query_types)
                # Add load-dependent latency increase
                load_factor = 1.0 + (concurrent_users / 100.0) * 0.5
                latency = random.uniform(lo, hi) * load_factor
                if random.random() < 0.01 * (concurrent_users / 10.0):
                    errors += 1
                else:
                    all_latencies.append(latency)
                    by_query.setdefault(qname, []).append(latency)

        result: Dict[str, Any] = {
            "concurrent_users": concurrent_users,
            "total_queries": concurrent_users * queries_per_user,
            "successful": len(all_latencies),
            "errors": errors,
            "avg_latency_ms": round(_mean(all_latencies), 2),
            "p50_ms": round(_percentile(all_latencies, 50), 2),
            "p95_ms": round(_percentile(all_latencies, 95), 2),
            "p99_ms": round(_percentile(all_latencies, 99), 2),
            "by_query_type": {},
        }
        for qname, lats in by_query.items():
            result["by_query_type"][qname] = {
                "count": len(lats),
                "avg_ms": round(_mean(lats), 2),
                "p95_ms": round(_percentile(lats, 95), 2),
            }

        print(
            f"    Avg: {result['avg_latency_ms']}ms, p95: {result['p95_ms']}ms, "
            f"Errors: {errors}"
        )
        return result

    def generate_full_report(self, output_dir: str = "load_test_results") -> None:
        """Export all reports to JSON."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        for report in self.reports:
            filename = f"{report.scenario_name.replace(' ', '_').lower()}_report.json"
            report.export_json(str(out_path / filename))
        print(f"\n  Reports exported to: {out_path.resolve()}")


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate SC2 Load Testing capabilities."""
    print("=" * 70)
    print("  Phase 660: Load Testing for SC2 Infrastructure Scalability")
    print("=" * 70)

    tester = SC2LoadTester()

    # 1. Constant load
    print("\n[1] Constant Load Test (5 users, 2s)")
    tester.create_constant_load_scenario(
        name="Constant Load",
        users=5,
        duration=1.0,
        rps_per_user=2.0,
    )

    # 2. Ramp-up load
    print("\n[2] Ramp-Up Load Test (1 -> 10 users over 1.5s)")
    tester.create_ramp_up_scenario(
        name="Ramp Up",
        max_users=10,
        ramp_up_seconds=1.0,
        duration=1.5,
    )

    # 3. Spike load
    print("\n[3] Spike Load Test (5 users, 3x spikes)")
    tester.create_spike_scenario(
        name="Spike Traffic",
        base_users=5,
        spike_multiplier=3.0,
        spike_duration=0.5,
        duration=1.5,
    )

    # Run all scenarios
    tester.run_all()

    # 4. Training pipeline stress test
    print("\n[4] Training Pipeline Stress Test")
    pipeline_result = tester.run_training_pipeline_stress(
        concurrent_pipelines=3,
        batches_per_pipeline=20,
    )
    print(
        f"    Throughput: ~{pipeline_result['estimated_throughput_batches_per_sec']} batches/sec"
    )

    # 5. Dashboard concurrency test
    print("\n[5] Dashboard Concurrency Test")
    dash_result = tester.run_dashboard_concurrency_test(
        concurrent_users=15,
        queries_per_user=8,
    )
    for qtype, stats in dash_result.get("by_query_type", {}).items():
        print(f"      {qtype}: {stats['count']} queries, avg={stats['avg_ms']}ms")

    # 6. Load profile visualization
    print("\n[6] Load Profile User Curves")
    profiles = [
        LoadProfile(LoadProfileType.CONSTANT, 10.0, 20),
        LoadProfile(LoadProfileType.RAMP_UP, 10.0, 20, ramp_up_seconds=8.0),
        LoadProfile(
            LoadProfileType.SPIKE,
            10.0,
            10,
            spike_multiplier=4.0,
            spike_duration_seconds=2.0,
            spike_interval_seconds=5.0,
        ),
    ]
    for prof in profiles:
        points = [
            prof.get_active_users_at(t)
            for t in range(0, int(prof.duration_seconds) + 1)
        ]
        print(f"    {prof.profile_type.value:>10}: {points}")

    # 7. Latency histogram
    print("\n[7] Latency Histogram (sampled)")
    hist = LatencyHistogram(bucket_count=10)
    sample_latencies = [random.gauss(50.0, 20.0) for _ in range(200)]
    hist.add_many(sample_latencies)
    print(hist.render(width=35))

    # 8. Virtual user summary
    print("\n[8] Individual Virtual User Summary")
    vu = VirtualUser(user_id="demo-vu-001")
    for _ in range(50):
        vu.simulate_request()
    summary = vu.get_summary()
    for key, val in summary.items():
        print(f"    {key}: {val}")

    print("\n" + "=" * 70)
    print("Phase 660 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 660: Load Testing registered
