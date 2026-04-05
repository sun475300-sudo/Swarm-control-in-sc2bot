# Phase 651: Chaos Engineering for SC2 Bot Resilience Testing
# Fault injection and resilience testing framework for SC2 bots

from __future__ import annotations

import copy
import json
import math
import os
import random
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import numpy as np
    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False

# ============================================================
# NumPy Fallback Utilities
# ============================================================


def _np_mean(values: list) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _np_std(values: list) -> float:
    if not values:
        return 0.0
    m = _np_mean(values)
    var = sum((v - m) ** 2 for v in values) / max(len(values), 1)
    return math.sqrt(var)


def _np_percentile(values: list, pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = pct / 100.0 * (len(s) - 1)
    lo = int(math.floor(idx))
    hi = min(lo + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


# ============================================================
# Enums for Chaos types and severities
# ============================================================

class ChaosSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChaosCategory(Enum):
    NETWORK = "network"
    LATENCY = "latency"
    RESOURCE = "resource"
    OBSERVATION = "observation"
    ACTION = "action"
    MEMORY = "memory"


# ============================================================
# SteadyStateHypothesis: Define expected behavior
# ============================================================

@dataclass
class SteadyStateHypothesis:
    """Define what 'normal' looks like so we can measure degradation."""
    name: str
    description: str = ""

    # Thresholds
    max_action_latency_ms: float = 100.0
    min_actions_per_second: float = 5.0
    max_observation_miss_rate: float = 0.05
    max_decision_error_rate: float = 0.10
    min_resource_efficiency: float = 0.70
    max_supply_block_ratio: float = 0.15

    # Custom checks
    custom_checks: List[Callable[..., bool]] = field(default_factory=list)

    def evaluate(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Evaluate metrics against the hypothesis. Returns pass/fail per check."""
        results: Dict[str, Any] = {"passed": True, "checks": {}}

        checks = {
            "action_latency": (
                metrics.get("avg_action_latency_ms", 0) <= self.max_action_latency_ms
            ),
            "actions_per_second": (
                metrics.get("actions_per_second", 0) >= self.min_actions_per_second
            ),
            "observation_miss_rate": (
                metrics.get("observation_miss_rate", 0) <= self.max_observation_miss_rate
            ),
            "decision_error_rate": (
                metrics.get("decision_error_rate", 0) <= self.max_decision_error_rate
            ),
            "resource_efficiency": (
                metrics.get("resource_efficiency", 1.0) >= self.min_resource_efficiency
            ),
            "supply_block_ratio": (
                metrics.get("supply_block_ratio", 0) <= self.max_supply_block_ratio
            ),
        }

        results["checks"] = checks
        results["passed"] = all(checks.values())
        results["failed_checks"] = [k for k, v in checks.items() if not v]
        return results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "max_action_latency_ms": self.max_action_latency_ms,
            "min_actions_per_second": self.min_actions_per_second,
            "max_observation_miss_rate": self.max_observation_miss_rate,
            "max_decision_error_rate": self.max_decision_error_rate,
            "min_resource_efficiency": self.min_resource_efficiency,
            "max_supply_block_ratio": self.max_supply_block_ratio,
        }


# ============================================================
# ChaosExperiment: Base class for chaos experiments
# ============================================================

@dataclass
class ChaosExperiment:
    """A single chaos experiment with fault injection parameters."""
    experiment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "unnamed"
    category: ChaosCategory = ChaosCategory.NETWORK
    severity: ChaosSeverity = ChaosSeverity.MEDIUM
    description: str = ""

    # Timing
    duration_seconds: float = 30.0
    cooldown_seconds: float = 10.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    # Blast radius
    target_modules: List[str] = field(default_factory=list)
    affected_fraction: float = 1.0  # 0.0 to 1.0

    # State
    is_running: bool = False
    completed: bool = False

    # Results
    baseline_metrics: Dict[str, float] = field(default_factory=dict)
    chaos_metrics: Dict[str, float] = field(default_factory=dict)
    impact_scores: Dict[str, float] = field(default_factory=dict)

    def start(self) -> None:
        self.is_running = True
        self.start_time = time.time()

    def stop(self) -> None:
        self.is_running = False
        self.completed = True
        self.end_time = time.time()

    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    def compute_impact(self) -> Dict[str, float]:
        """Compute impact scores by comparing baseline to chaos metrics."""
        impact: Dict[str, float] = {}
        for key in self.baseline_metrics:
            baseline_val = self.baseline_metrics[key]
            chaos_val = self.chaos_metrics.get(key, baseline_val)
            if abs(baseline_val) > 1e-9:
                impact[key] = round((chaos_val - baseline_val) / abs(baseline_val) * 100, 2)
            else:
                impact[key] = 0.0
        self.impact_scores = impact
        return impact

    def summary(self) -> str:
        status = "RUNNING" if self.is_running else ("DONE" if self.completed else "PENDING")
        return (
            f"[{self.experiment_id}] {self.name} ({self.category.value}/{self.severity.value}) "
            f"status={status} elapsed={self.elapsed():.1f}s"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "duration_seconds": self.duration_seconds,
            "is_running": self.is_running,
            "completed": self.completed,
            "elapsed": self.elapsed(),
            "baseline_metrics": self.baseline_metrics,
            "chaos_metrics": self.chaos_metrics,
            "impact_scores": self.impact_scores,
            "target_modules": self.target_modules,
            "affected_fraction": self.affected_fraction,
        }


# ============================================================
# NetworkChaos: Simulate network issues
# ============================================================

class NetworkChaos:
    """Simulate network faults: packet loss, reordering, corruption."""

    def __init__(self, packet_loss_rate: float = 0.1, corruption_rate: float = 0.02):
        self.packet_loss_rate = packet_loss_rate
        self.corruption_rate = corruption_rate
        self._rng = random.Random()
        self.dropped_packets: int = 0
        self.corrupted_packets: int = 0
        self.total_packets: int = 0

    def configure(self, loss_rate: float, corruption_rate: float) -> None:
        self.packet_loss_rate = max(0.0, min(1.0, loss_rate))
        self.corruption_rate = max(0.0, min(1.0, corruption_rate))

    def process_observation(self, observation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Simulate network effects on an observation.
        Returns None if packet is dropped, corrupted dict otherwise.
        """
        self.total_packets += 1

        # Packet loss
        if self._rng.random() < self.packet_loss_rate:
            self.dropped_packets += 1
            return None

        result = copy.deepcopy(observation)

        # Corruption: randomly zero out some values
        if self._rng.random() < self.corruption_rate:
            self.corrupted_packets += 1
            result = self._corrupt_observation(result)

        return result

    def _corrupt_observation(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Randomly corrupt parts of an observation."""
        if "resources" in obs:
            for pid in obs["resources"]:
                if self._rng.random() < 0.5:
                    obs["resources"][pid]["minerals"] = 0
        if "units" in obs:
            keys = list(obs["units"].keys())
            if keys:
                drop_key = self._rng.choice(keys)
                del obs["units"][drop_key]
        return obs

    def process_action(self, action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simulate network effects on an outgoing action."""
        self.total_packets += 1
        if self._rng.random() < self.packet_loss_rate:
            self.dropped_packets += 1
            return None
        return action

    def stats(self) -> Dict[str, Any]:
        return {
            "total_packets": self.total_packets,
            "dropped_packets": self.dropped_packets,
            "corrupted_packets": self.corrupted_packets,
            "effective_loss_rate": round(
                self.dropped_packets / max(self.total_packets, 1), 4
            ),
            "effective_corruption_rate": round(
                self.corrupted_packets / max(self.total_packets, 1), 4
            ),
        }

    def reset(self) -> None:
        self.dropped_packets = 0
        self.corrupted_packets = 0
        self.total_packets = 0


# ============================================================
# LatencyChaos: Simulate latency spikes
# ============================================================

class LatencyChaos:
    """Simulate latency spikes and jitter for SC2 actions and observations."""

    def __init__(
        self,
        base_latency_ms: float = 10.0,
        spike_probability: float = 0.05,
        spike_magnitude_ms: float = 500.0,
        jitter_std_ms: float = 5.0,
    ):
        self.base_latency_ms = base_latency_ms
        self.spike_probability = spike_probability
        self.spike_magnitude_ms = spike_magnitude_ms
        self.jitter_std_ms = jitter_std_ms
        self._rng = random.Random()
        self._latency_log: deque = deque(maxlen=5000)

    def configure(
        self,
        base_ms: Optional[float] = None,
        spike_prob: Optional[float] = None,
        spike_mag_ms: Optional[float] = None,
        jitter_ms: Optional[float] = None,
    ) -> None:
        if base_ms is not None:
            self.base_latency_ms = base_ms
        if spike_prob is not None:
            self.spike_probability = max(0.0, min(1.0, spike_prob))
        if spike_mag_ms is not None:
            self.spike_magnitude_ms = spike_mag_ms
        if jitter_ms is not None:
            self.jitter_std_ms = jitter_ms

    def sample_latency(self) -> float:
        """Sample a latency value in milliseconds."""
        latency = self.base_latency_ms + self._rng.gauss(0, self.jitter_std_ms)

        # Spike
        if self._rng.random() < self.spike_probability:
            spike = self.spike_magnitude_ms * (0.5 + self._rng.random() * 0.5)
            latency += spike

        latency = max(0.0, latency)
        self._latency_log.append(latency)
        return latency

    def delay_action(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """Return the action with its simulated delay in ms."""
        delay = self.sample_latency()
        delayed_action = copy.deepcopy(action)
        delayed_action["_chaos_delay_ms"] = delay
        return delayed_action, delay

    def delay_observation(self, observation: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """Return the observation with its simulated delay in ms."""
        delay = self.sample_latency()
        delayed_obs = copy.deepcopy(observation)
        delayed_obs["_chaos_delay_ms"] = delay
        return delayed_obs, delay

    def stats(self) -> Dict[str, Any]:
        log = list(self._latency_log)
        if not log:
            return {"samples": 0}
        return {
            "samples": len(log),
            "mean_ms": round(_np_mean(log), 2),
            "std_ms": round(_np_std(log), 2),
            "p50_ms": round(_np_percentile(log, 50), 2),
            "p95_ms": round(_np_percentile(log, 95), 2),
            "p99_ms": round(_np_percentile(log, 99), 2),
            "max_ms": round(max(log), 2),
            "spike_count": sum(1 for x in log if x > self.base_latency_ms * 3),
        }

    def reset(self) -> None:
        self._latency_log.clear()


# ============================================================
# ResourceChaos: Simulate CPU/memory pressure
# ============================================================

class ResourceChaos:
    """Simulate CPU throttle, memory pressure, and decision budget constraints."""

    def __init__(
        self,
        cpu_throttle_factor: float = 1.0,
        memory_pressure_mb: float = 0.0,
        max_decision_budget_ms: float = 50.0,
    ):
        self.cpu_throttle_factor = cpu_throttle_factor  # >1.0 means slower
        self.memory_pressure_mb = memory_pressure_mb
        self.max_decision_budget_ms = max_decision_budget_ms
        self._rng = random.Random()
        self._decision_times: deque = deque(maxlen=5000)
        self._budget_exceeded_count: int = 0
        self._total_decisions: int = 0

    def configure(
        self,
        cpu_factor: Optional[float] = None,
        memory_mb: Optional[float] = None,
        budget_ms: Optional[float] = None,
    ) -> None:
        if cpu_factor is not None:
            self.cpu_throttle_factor = max(0.1, cpu_factor)
        if memory_mb is not None:
            self.memory_pressure_mb = max(0.0, memory_mb)
        if budget_ms is not None:
            self.max_decision_budget_ms = max(1.0, budget_ms)

    def simulate_decision_time(self, base_time_ms: float) -> Tuple[float, bool]:
        """
        Simulate a decision under resource pressure.
        Returns (actual_time_ms, exceeded_budget).
        """
        self._total_decisions += 1

        # CPU throttle inflates decision time
        actual = base_time_ms * self.cpu_throttle_factor

        # Memory pressure adds random overhead
        if self.memory_pressure_mb > 0:
            gc_pause = self._rng.expovariate(1.0 / max(self.memory_pressure_mb * 0.1, 0.1))
            actual += gc_pause

        # Jitter
        actual += self._rng.gauss(0, base_time_ms * 0.1)
        actual = max(0.1, actual)

        exceeded = actual > self.max_decision_budget_ms
        if exceeded:
            self._budget_exceeded_count += 1

        self._decision_times.append(actual)
        return actual, exceeded

    def simulate_observation_processing(
        self, observation: Dict[str, Any], base_time_ms: float = 5.0
    ) -> Tuple[Dict[str, Any], float, bool]:
        """Simulate processing an observation under resource constraints."""
        proc_time, exceeded = self.simulate_decision_time(base_time_ms)

        result = observation
        # Under extreme pressure, drop some observation data
        if exceeded and self.cpu_throttle_factor > 2.0:
            result = copy.deepcopy(observation)
            units = result.get("units", {})
            if len(units) > 10:
                keys = list(units.keys())
                # Keep only a subset of units
                keep = max(5, len(keys) // 2)
                for k in keys[keep:]:
                    del units[k]

        return result, proc_time, exceeded

    def stats(self) -> Dict[str, Any]:
        times = list(self._decision_times)
        return {
            "total_decisions": self._total_decisions,
            "budget_exceeded": self._budget_exceeded_count,
            "exceed_rate": round(
                self._budget_exceeded_count / max(self._total_decisions, 1), 4
            ),
            "cpu_throttle_factor": self.cpu_throttle_factor,
            "memory_pressure_mb": self.memory_pressure_mb,
            "mean_decision_ms": round(_np_mean(times), 2) if times else 0.0,
            "p95_decision_ms": round(_np_percentile(times, 95), 2) if times else 0.0,
        }

    def reset(self) -> None:
        self._decision_times.clear()
        self._budget_exceeded_count = 0
        self._total_decisions = 0


# ============================================================
# BlastRadius: Control scope of chaos injection
# ============================================================

@dataclass
class BlastRadius:
    """Controls which modules and what fraction of traffic is affected by chaos."""
    allowed_modules: List[str] = field(default_factory=list)
    excluded_modules: List[str] = field(default_factory=list)
    affected_fraction: float = 1.0
    max_concurrent_experiments: int = 3

    def is_module_allowed(self, module_name: str) -> bool:
        if self.excluded_modules and module_name in self.excluded_modules:
            return False
        if self.allowed_modules:
            return module_name in self.allowed_modules
        return True

    def should_affect(self, rng: random.Random) -> bool:
        return rng.random() < self.affected_fraction

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed_modules": self.allowed_modules,
            "excluded_modules": self.excluded_modules,
            "affected_fraction": self.affected_fraction,
            "max_concurrent_experiments": self.max_concurrent_experiments,
        }


# ============================================================
# ExperimentResult: Detailed result of a chaos experiment
# ============================================================

@dataclass
class ExperimentResult:
    """Detailed result of a completed chaos experiment."""
    experiment: ChaosExperiment
    hypothesis: SteadyStateHypothesis
    hypothesis_result: Dict[str, Any] = field(default_factory=dict)
    resilience_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)

    def compute_resilience_score(self) -> float:
        """Score from 0 (fragile) to 1 (fully resilient)."""
        if not self.hypothesis_result:
            return 0.0
        checks = self.hypothesis_result.get("checks", {})
        if not checks:
            return 0.0
        passed = sum(1 for v in checks.values() if v)
        self.resilience_score = round(passed / len(checks), 4)
        return self.resilience_score

    def generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on failures."""
        self.recommendations = []
        failed = self.hypothesis_result.get("failed_checks", [])

        rec_map = {
            "action_latency": "Optimize action pipeline; consider pre-computing common actions.",
            "actions_per_second": "Reduce per-tick computation; prioritize critical actions under load.",
            "observation_miss_rate": "Add observation caching/interpolation for missed frames.",
            "decision_error_rate": "Implement fallback decision logic for degraded states.",
            "resource_efficiency": "Add resource spending safeguards under high latency.",
            "supply_block_ratio": "Pre-build supply structures with larger safety margin.",
        }

        for check_name in failed:
            if check_name in rec_map:
                self.recommendations.append(rec_map[check_name])

        if not self.recommendations:
            self.recommendations.append("Bot passed all checks -- resilience is adequate.")

        return self.recommendations

    def summary(self) -> str:
        status = "PASSED" if self.hypothesis_result.get("passed", False) else "FAILED"
        return (
            f"Experiment: {self.experiment.name} | Hypothesis: {self.hypothesis.name} | "
            f"Status: {status} | Resilience: {self.resilience_score:.2%}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment": self.experiment.to_dict(),
            "hypothesis": self.hypothesis.to_dict(),
            "hypothesis_result": self.hypothesis_result,
            "resilience_score": self.resilience_score,
            "recommendations": self.recommendations,
        }


# ============================================================
# ChaosMonkey: Main orchestrator
# ============================================================

class ChaosMonkey:
    """
    Main chaos engineering controller for SC2 bot resilience testing.

    Orchestrates fault injection experiments, evaluates steady-state
    hypotheses, and generates resilience reports.
    """

    def __init__(
        self,
        blast_radius: Optional[BlastRadius] = None,
        default_hypothesis: Optional[SteadyStateHypothesis] = None,
    ):
        self.monkey_id = uuid.uuid4().hex[:12]
        self.blast_radius = blast_radius or BlastRadius()
        self.default_hypothesis = default_hypothesis or SteadyStateHypothesis(
            name="SC2BotDefault",
            description="Default steady-state hypothesis for SC2 bot",
        )

        self.network_chaos = NetworkChaos()
        self.latency_chaos = LatencyChaos()
        self.resource_chaos = ResourceChaos()

        self._experiments: List[ChaosExperiment] = []
        self._results: List[ExperimentResult] = []
        self._active_experiments: List[ChaosExperiment] = []
        self._rng = random.Random()
        self._creation_time = time.time()

    # ---- Experiment creation ----

    def create_experiment(
        self,
        name: str,
        category: ChaosCategory,
        severity: ChaosSeverity = ChaosSeverity.MEDIUM,
        duration: float = 30.0,
        target_modules: Optional[List[str]] = None,
        affected_fraction: float = 1.0,
        description: str = "",
    ) -> ChaosExperiment:
        exp = ChaosExperiment(
            name=name,
            category=category,
            severity=severity,
            duration_seconds=duration,
            target_modules=target_modules or [],
            affected_fraction=affected_fraction,
            description=description,
        )
        self._experiments.append(exp)
        return exp

    def create_network_experiment(
        self, loss_rate: float = 0.1, corruption_rate: float = 0.02, duration: float = 30.0
    ) -> ChaosExperiment:
        exp = self.create_experiment(
            name=f"NetworkChaos_loss{loss_rate:.0%}",
            category=ChaosCategory.NETWORK,
            severity=ChaosSeverity.HIGH if loss_rate > 0.2 else ChaosSeverity.MEDIUM,
            duration=duration,
            description=f"Packet loss={loss_rate:.0%}, corruption={corruption_rate:.0%}",
        )
        self.network_chaos.configure(loss_rate, corruption_rate)
        return exp

    def create_latency_experiment(
        self,
        spike_prob: float = 0.1,
        spike_mag_ms: float = 500.0,
        duration: float = 30.0,
    ) -> ChaosExperiment:
        exp = self.create_experiment(
            name=f"LatencyChaos_spike{spike_prob:.0%}",
            category=ChaosCategory.LATENCY,
            severity=ChaosSeverity.HIGH if spike_mag_ms > 300 else ChaosSeverity.MEDIUM,
            duration=duration,
            description=f"Spike probability={spike_prob:.0%}, magnitude={spike_mag_ms:.0f}ms",
        )
        self.latency_chaos.configure(spike_prob=spike_prob, spike_mag_ms=spike_mag_ms)
        return exp

    def create_resource_experiment(
        self,
        cpu_factor: float = 2.0,
        memory_mb: float = 100.0,
        duration: float = 30.0,
    ) -> ChaosExperiment:
        exp = self.create_experiment(
            name=f"ResourceChaos_cpu{cpu_factor:.1f}x",
            category=ChaosCategory.RESOURCE,
            severity=ChaosSeverity.CRITICAL if cpu_factor > 3.0 else ChaosSeverity.MEDIUM,
            duration=duration,
            description=f"CPU throttle={cpu_factor:.1f}x, memory pressure={memory_mb:.0f}MB",
        )
        self.resource_chaos.configure(cpu_factor=cpu_factor, memory_mb=memory_mb)
        return exp

    # ---- Experiment execution ----

    def run_experiment(
        self,
        experiment: ChaosExperiment,
        bot_tick_fn: Callable[[Dict[str, Any]], Dict[str, float]],
        observations: List[Dict[str, Any]],
        hypothesis: Optional[SteadyStateHypothesis] = None,
    ) -> ExperimentResult:
        """
        Run a chaos experiment against a bot tick function.

        Args:
            experiment: The chaos experiment to run.
            bot_tick_fn: A function that takes an observation dict and returns metrics dict.
            observations: List of SC2 observation dicts to replay.
            hypothesis: Steady-state hypothesis to evaluate against.
        """
        hyp = hypothesis or self.default_hypothesis

        # Phase 1: Collect baseline metrics (no chaos)
        baseline_metrics_list: List[Dict[str, float]] = []
        for obs in observations[:len(observations) // 2]:
            metrics = bot_tick_fn(obs)
            baseline_metrics_list.append(metrics)

        baseline_avg = self._average_metrics(baseline_metrics_list)
        experiment.baseline_metrics = baseline_avg

        # Phase 2: Inject chaos and collect metrics
        experiment.start()
        chaos_metrics_list: List[Dict[str, float]] = []

        for obs in observations[len(observations) // 2:]:
            # Apply chaos based on category
            processed_obs = obs
            extra_latency = 0.0

            if experiment.category == ChaosCategory.NETWORK:
                result = self.network_chaos.process_observation(obs)
                if result is None:
                    chaos_metrics_list.append({"observation_miss_rate": 1.0})
                    continue
                processed_obs = result

            if experiment.category == ChaosCategory.LATENCY:
                processed_obs, delay = self.latency_chaos.delay_observation(obs)
                extra_latency = delay

            if experiment.category == ChaosCategory.RESOURCE:
                processed_obs, proc_time, exceeded = (
                    self.resource_chaos.simulate_observation_processing(obs)
                )
                extra_latency = proc_time

            # Run bot tick
            metrics = bot_tick_fn(processed_obs)
            if extra_latency > 0:
                metrics["avg_action_latency_ms"] = metrics.get(
                    "avg_action_latency_ms", 10.0
                ) + extra_latency
            chaos_metrics_list.append(metrics)

        experiment.stop()
        chaos_avg = self._average_metrics(chaos_metrics_list)
        experiment.chaos_metrics = chaos_avg
        experiment.compute_impact()

        # Phase 3: Evaluate hypothesis
        hyp_result = hyp.evaluate(chaos_avg)

        result = ExperimentResult(
            experiment=experiment,
            hypothesis=hyp,
            hypothesis_result=hyp_result,
        )
        result.compute_resilience_score()
        result.generate_recommendations()
        self._results.append(result)

        return result

    def _average_metrics(self, metrics_list: List[Dict[str, float]]) -> Dict[str, float]:
        if not metrics_list:
            return {}
        all_keys = set()
        for m in metrics_list:
            all_keys.update(m.keys())
        avg: Dict[str, float] = {}
        for key in all_keys:
            vals = [m[key] for m in metrics_list if key in m]
            avg[key] = round(_np_mean(vals), 4)
        return avg

    # ---- Predefined chaos suites ----

    def run_standard_suite(
        self,
        bot_tick_fn: Callable[[Dict[str, Any]], Dict[str, float]],
        observations: List[Dict[str, Any]],
    ) -> List[ExperimentResult]:
        """Run a standard suite of chaos experiments."""
        results: List[ExperimentResult] = []

        # Network chaos: 10% loss
        exp1 = self.create_network_experiment(loss_rate=0.10, corruption_rate=0.02)
        r1 = self.run_experiment(exp1, bot_tick_fn, observations)
        results.append(r1)

        # Network chaos: 30% loss (severe)
        self.network_chaos.reset()
        exp2 = self.create_network_experiment(loss_rate=0.30, corruption_rate=0.05)
        r2 = self.run_experiment(exp2, bot_tick_fn, observations)
        results.append(r2)

        # Latency spikes
        self.latency_chaos.reset()
        exp3 = self.create_latency_experiment(spike_prob=0.15, spike_mag_ms=400.0)
        r3 = self.run_experiment(exp3, bot_tick_fn, observations)
        results.append(r3)

        # CPU throttle
        self.resource_chaos.reset()
        exp4 = self.create_resource_experiment(cpu_factor=2.5, memory_mb=200.0)
        r4 = self.run_experiment(exp4, bot_tick_fn, observations)
        results.append(r4)

        return results

    # ---- Reporting ----

    def resilience_report(self) -> Dict[str, Any]:
        """Generate a full resilience report across all experiments."""
        if not self._results:
            return {"error": "No experiments have been run yet"}

        scores = [r.resilience_score for r in self._results]
        all_recs = []
        for r in self._results:
            all_recs.extend(r.recommendations)
        unique_recs = list(dict.fromkeys(all_recs))

        passed = sum(1 for r in self._results if r.hypothesis_result.get("passed", False))
        failed = len(self._results) - passed

        return {
            "monkey_id": self.monkey_id,
            "total_experiments": len(self._results),
            "passed": passed,
            "failed": failed,
            "avg_resilience_score": round(_np_mean(scores), 4),
            "min_resilience_score": round(min(scores), 4),
            "max_resilience_score": round(max(scores), 4),
            "recommendations": unique_recs,
            "experiments": [r.summary() for r in self._results],
            "network_stats": self.network_chaos.stats(),
            "latency_stats": self.latency_chaos.stats(),
            "resource_stats": self.resource_chaos.stats(),
        }

    def save_report(self, filepath: str) -> str:
        """Save resilience report to JSON file."""
        report = self.resilience_report()
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        return filepath

    def get_experiment_history(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._results]

    def full_stats(self) -> Dict[str, Any]:
        return {
            "monkey_id": self.monkey_id,
            "uptime": round(time.time() - self._creation_time, 1),
            "total_experiments_defined": len(self._experiments),
            "total_experiments_completed": len(self._results),
            "network": self.network_chaos.stats(),
            "latency": self.latency_chaos.stats(),
            "resource": self.resource_chaos.stats(),
            "blast_radius": self.blast_radius.to_dict(),
        }


# ============================================================
# Utility: Simulated bot tick function for testing
# ============================================================

def _simulated_bot_tick(observation: Dict[str, Any]) -> Dict[str, float]:
    """A mock SC2 bot tick function that returns performance metrics."""
    rng = random.Random()
    game_loop = observation.get("game_loop", 0)
    num_units = len(observation.get("units", {}))

    base_latency = 8.0 + num_units * 0.3 + rng.gauss(0, 2)
    base_latency = max(1.0, base_latency)

    actions_per_sec = max(1.0, 15.0 - num_units * 0.2 + rng.gauss(0, 1))
    obs_miss = max(0.0, 0.01 + rng.gauss(0, 0.005))
    decision_err = max(0.0, 0.03 + rng.gauss(0, 0.01))
    res_eff = min(1.0, max(0.0, 0.85 + rng.gauss(0, 0.05)))
    supply_block = max(0.0, 0.05 + rng.gauss(0, 0.02))

    return {
        "avg_action_latency_ms": round(base_latency, 2),
        "actions_per_second": round(actions_per_sec, 2),
        "observation_miss_rate": round(obs_miss, 4),
        "decision_error_rate": round(decision_err, 4),
        "resource_efficiency": round(res_eff, 4),
        "supply_block_ratio": round(supply_block, 4),
    }


def _generate_test_observations(count: int = 100) -> List[Dict[str, Any]]:
    """Generate synthetic SC2 observations for testing."""
    rng = random.Random(651)
    observations: List[Dict[str, Any]] = []
    for i in range(count):
        loop = i * 100
        num_units = max(5, 10 + loop // 200 + int(rng.gauss(0, 2)))
        units: Dict[str, Dict[str, Any]] = {}
        for uid in range(num_units):
            units[str(uid)] = {
                "type": rng.choice(["Marine", "Zergling", "Stalker", "Roach"]),
                "owner": 1 if uid < num_units // 2 else 2,
                "position": [rng.uniform(10, 190), rng.uniform(10, 190)],
                "health": rng.uniform(20, 150),
                "max_health": 150,
                "is_alive": True,
            }
        observations.append({
            "game_loop": loop,
            "resources": {
                "1": {"minerals": 400 + loop * 1.5, "vespene": 200 + loop * 0.8,
                       "supply_used": num_units // 2, "supply_cap": num_units // 2 + 10},
                "2": {"minerals": 380 + loop * 1.4, "vespene": 180 + loop * 0.7,
                       "supply_used": num_units // 2, "supply_cap": num_units // 2 + 8},
            },
            "units": units,
            "map_name": "Equilibrium",
        })
    return observations


# ============================================================
# Demo
# ============================================================

def demo() -> None:
    """Demonstrate the Phase 651 Chaos Engineering system."""
    print("=" * 70)
    print("Phase 651: Chaos Engineering for SC2 Bot Resilience Testing")
    print("=" * 70)

    observations = _generate_test_observations(100)

    # --- [1] Create ChaosMonkey with hypothesis ---
    print("\n[1] Creating ChaosMonkey with steady-state hypothesis...")
    hypothesis = SteadyStateHypothesis(
        name="SC2BotResilience",
        description="Bot must maintain performance under chaos",
        max_action_latency_ms=80.0,
        min_actions_per_second=5.0,
        max_observation_miss_rate=0.10,
        max_decision_error_rate=0.15,
        min_resource_efficiency=0.65,
        max_supply_block_ratio=0.20,
    )
    monkey = ChaosMonkey(
        blast_radius=BlastRadius(
            affected_fraction=0.8,
            max_concurrent_experiments=2,
        ),
        default_hypothesis=hypothesis,
    )
    print(f"    Monkey ID: {monkey.monkey_id}")
    print(f"    Hypothesis: {hypothesis.name}")

    # --- [2] Network chaos: 10% packet loss ---
    print("\n[2] Running network chaos (10% packet loss)...")
    exp1 = monkey.create_network_experiment(loss_rate=0.10, corruption_rate=0.02)
    r1 = monkey.run_experiment(exp1, _simulated_bot_tick, observations)
    print(f"    {r1.summary()}")
    print(f"    Impact: {exp1.impact_scores}")

    # --- [3] Network chaos: 30% packet loss (severe) ---
    print("\n[3] Running network chaos (30% packet loss - severe)...")
    monkey.network_chaos.reset()
    exp2 = monkey.create_network_experiment(loss_rate=0.30, corruption_rate=0.05)
    r2 = monkey.run_experiment(exp2, _simulated_bot_tick, observations)
    print(f"    {r2.summary()}")
    for rec in r2.recommendations[:2]:
        print(f"    Recommendation: {rec}")

    # --- [4] Latency spikes ---
    print("\n[4] Running latency chaos (15% spike probability, 400ms spikes)...")
    monkey.latency_chaos.reset()
    exp3 = monkey.create_latency_experiment(spike_prob=0.15, spike_mag_ms=400.0)
    r3 = monkey.run_experiment(exp3, _simulated_bot_tick, observations)
    print(f"    {r3.summary()}")
    lat_stats = monkey.latency_chaos.stats()
    print(f"    Latency p95: {lat_stats.get('p95_ms', 0):.1f}ms, "
          f"p99: {lat_stats.get('p99_ms', 0):.1f}ms")

    # --- [5] CPU throttle ---
    print("\n[5] Running resource chaos (2.5x CPU throttle, 200MB memory pressure)...")
    monkey.resource_chaos.reset()
    exp4 = monkey.create_resource_experiment(cpu_factor=2.5, memory_mb=200.0)
    r4 = monkey.run_experiment(exp4, _simulated_bot_tick, observations)
    print(f"    {r4.summary()}")
    res_stats = monkey.resource_chaos.stats()
    print(f"    Budget exceeded rate: {res_stats.get('exceed_rate', 0):.2%}")
    print(f"    Mean decision time: {res_stats.get('mean_decision_ms', 0):.1f}ms")

    # --- [6] Blast radius check ---
    print("\n[6] Blast radius configuration:")
    br = monkey.blast_radius
    print(f"    Affected fraction: {br.affected_fraction:.0%}")
    print(f"    Max concurrent: {br.max_concurrent_experiments}")
    print(f"    Module 'combat' allowed: {br.is_module_allowed('combat')}")

    # --- [7] Hypothesis evaluation on baseline ---
    print("\n[7] Evaluating hypothesis on normal (no chaos) metrics...")
    normal_metrics = {
        "avg_action_latency_ms": 12.0,
        "actions_per_second": 14.0,
        "observation_miss_rate": 0.01,
        "decision_error_rate": 0.03,
        "resource_efficiency": 0.88,
        "supply_block_ratio": 0.05,
    }
    eval_result = hypothesis.evaluate(normal_metrics)
    print(f"    Passed: {eval_result['passed']}")
    print(f"    Checks: {eval_result['checks']}")

    # --- [8] Individual NetworkChaos test ---
    print("\n[8] Direct NetworkChaos packet processing test (20 packets)...")
    net = NetworkChaos(packet_loss_rate=0.25, corruption_rate=0.10)
    dropped = 0
    for i in range(20):
        result = net.process_observation({"game_loop": i * 100, "units": {"1": {}, "2": {}}})
        if result is None:
            dropped += 1
    print(f"    Dropped: {dropped}/20")
    print(f"    Stats: {net.stats()}")

    # --- [9] Individual LatencyChaos test ---
    print("\n[9] Direct LatencyChaos sampling (50 samples)...")
    lat = LatencyChaos(base_latency_ms=15.0, spike_probability=0.20, spike_magnitude_ms=300.0)
    for _ in range(50):
        lat.sample_latency()
    print(f"    Stats: {lat.stats()}")

    # --- [10] Full resilience report ---
    print("\n[10] Full resilience report:")
    report = monkey.resilience_report()
    print(f"    Total experiments: {report['total_experiments']}")
    print(f"    Passed: {report['passed']}, Failed: {report['failed']}")
    print(f"    Avg resilience score: {report['avg_resilience_score']:.2%}")
    print(f"    Min resilience score: {report['min_resilience_score']:.2%}")
    print(f"    Max resilience score: {report['max_resilience_score']:.2%}")
    print("    Recommendations:")
    for rec in report.get("recommendations", [])[:4]:
        print(f"      - {rec}")
    print("    Experiment summaries:")
    for exp_summary in report.get("experiments", []):
        print(f"      {exp_summary}")

    print("\n" + "=" * 70)
    print("Phase 651 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 651: Chaos Engineering registered
