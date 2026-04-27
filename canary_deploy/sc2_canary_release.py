"""
Phase 657: Canary Deployment for Safe SC2 Bot Updates
=====================================================
Canary release strategy for StarCraft II bot deployments.
Implements progressive traffic splitting, health monitoring,
automatic rollback, and parallel bot-version comparison by win rate.
"""

from __future__ import annotations

import logging
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DeploymentPhase(Enum):
    """Stages of a canary deployment."""

    NOT_STARTED = "not_started"
    CANARY_1_PERCENT = "canary_1%"
    CANARY_5_PERCENT = "canary_5%"
    CANARY_25_PERCENT = "canary_25%"
    CANARY_50_PERCENT = "canary_50%"
    FULL_ROLLOUT = "full_rollout_100%"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"


class HealthStatus(Enum):
    """Health check result."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class RollbackReason(Enum):
    """Reasons for an automatic rollback."""

    WIN_RATE_BELOW_THRESHOLD = "win_rate_below_threshold"
    ERROR_RATE_ABOVE_THRESHOLD = "error_rate_above_threshold"
    LATENCY_ABOVE_THRESHOLD = "latency_above_threshold"
    MANUAL = "manual"
    HEALTH_CHECK_FAILED = "health_check_failed"
    CRASH_DETECTED = "crash_detected"


# ---------------------------------------------------------------------------
# Progressive rollout stages
# ---------------------------------------------------------------------------

ROLLOUT_STAGES: List[Tuple[DeploymentPhase, float]] = [
    (DeploymentPhase.CANARY_1_PERCENT, 0.01),
    (DeploymentPhase.CANARY_5_PERCENT, 0.05),
    (DeploymentPhase.CANARY_25_PERCENT, 0.25),
    (DeploymentPhase.CANARY_50_PERCENT, 0.50),
    (DeploymentPhase.FULL_ROLLOUT, 1.00),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CanaryConfig:
    """
    Configuration for a canary deployment.

    Attributes:
        canary_version: Version string of the new bot being tested.
        stable_version: Version string of the current stable bot.
        min_win_rate: Minimum win rate the canary must maintain.
        max_error_rate: Maximum tolerable error rate for the canary.
        max_latency_ms: Maximum average decision latency in milliseconds.
        min_matches_per_stage: Minimum matches to play before advancing.
        cooldown_seconds: Wait time between rollout stages.
        auto_rollback: Whether to automatically rollback on threshold breach.
        rollout_stages: Ordered list of (phase, weight) for progressive rollout.
    """

    canary_version: str = "v2.0.0-canary"
    stable_version: str = "v1.9.0-stable"
    min_win_rate: float = 0.45
    max_error_rate: float = 0.05
    max_latency_ms: float = 200.0
    min_matches_per_stage: int = 20
    cooldown_seconds: float = 10.0
    auto_rollback: bool = True
    rollout_stages: List[Tuple[DeploymentPhase, float]] = field(
        default_factory=lambda: list(ROLLOUT_STAGES)
    )

    def validate(self) -> List[str]:
        """Validate configuration. Returns list of error messages."""
        errors: List[str] = []
        if not (0.0 <= self.min_win_rate <= 1.0):
            errors.append(f"min_win_rate must be 0-1, got {self.min_win_rate}")
        if not (0.0 <= self.max_error_rate <= 1.0):
            errors.append(f"max_error_rate must be 0-1, got {self.max_error_rate}")
        if self.max_latency_ms <= 0:
            errors.append(f"max_latency_ms must be > 0, got {self.max_latency_ms}")
        if self.min_matches_per_stage < 1:
            errors.append(
                f"min_matches_per_stage must be >= 1, got {self.min_matches_per_stage}"
            )
        if len(self.rollout_stages) == 0:
            errors.append("rollout_stages must have at least one stage")
        return errors


@dataclass
class MatchResult:
    """Outcome of a single SC2 match played by one bot version."""

    match_id: str
    version: str
    opponent: str
    won: bool
    duration_frames: int
    avg_decision_latency_ms: float
    errors_count: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageMetrics:
    """Aggregated metrics for a deployment stage."""

    phase: DeploymentPhase
    canary_matches: int = 0
    canary_wins: int = 0
    canary_errors: int = 0
    canary_total_latency_ms: float = 0.0
    stable_matches: int = 0
    stable_wins: int = 0
    stable_errors: int = 0
    stable_total_latency_ms: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @property
    def canary_win_rate(self) -> float:
        if self.canary_matches == 0:
            return 0.0
        return self.canary_wins / self.canary_matches

    @property
    def canary_error_rate(self) -> float:
        if self.canary_matches == 0:
            return 0.0
        return self.canary_errors / self.canary_matches

    @property
    def canary_avg_latency_ms(self) -> float:
        if self.canary_matches == 0:
            return 0.0
        return self.canary_total_latency_ms / self.canary_matches

    @property
    def stable_win_rate(self) -> float:
        if self.stable_matches == 0:
            return 0.0
        return self.stable_wins / self.stable_matches

    @property
    def stable_avg_latency_ms(self) -> float:
        if self.stable_matches == 0:
            return 0.0
        return self.stable_total_latency_ms / self.stable_matches

    def summary(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "canary_win_rate": round(self.canary_win_rate, 4),
            "canary_error_rate": round(self.canary_error_rate, 4),
            "canary_avg_latency_ms": round(self.canary_avg_latency_ms, 2),
            "canary_matches": self.canary_matches,
            "stable_win_rate": round(self.stable_win_rate, 4),
            "stable_matches": self.stable_matches,
        }


@dataclass
class RollbackEvent:
    """Records a rollback event."""

    deployment_id: str
    reason: RollbackReason
    phase_at_rollback: DeploymentPhase
    canary_metrics: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    message: str = ""


# ---------------------------------------------------------------------------
# TrafficSplitter
# ---------------------------------------------------------------------------


class TrafficSplitter:
    """
    Routes incoming match requests to canary or stable version
    based on the current traffic weight.
    """

    def __init__(self, canary_weight: float = 0.0) -> None:
        self._canary_weight = max(0.0, min(1.0, canary_weight))
        self._total_routed: int = 0
        self._canary_routed: int = 0
        self._stable_routed: int = 0

    @property
    def canary_weight(self) -> float:
        return self._canary_weight

    @canary_weight.setter
    def canary_weight(self, value: float) -> None:
        self._canary_weight = max(0.0, min(1.0, value))
        logger.info(
            "Traffic weight updated: canary=%.2f, stable=%.2f",
            self._canary_weight,
            1.0 - self._canary_weight,
        )

    @property
    def stable_weight(self) -> float:
        return 1.0 - self._canary_weight

    def route(self) -> str:
        """
        Decide whether the next request goes to canary or stable.
        Returns 'canary' or 'stable'.
        """
        self._total_routed += 1
        if random.random() < self._canary_weight:
            self._canary_routed += 1
            return "canary"
        else:
            self._stable_routed += 1
            return "stable"

    def route_deterministic(self, request_id: str) -> str:
        """Deterministic routing based on hash of request_id."""
        hash_val = hash(request_id) % 1000
        threshold = int(self._canary_weight * 1000)
        self._total_routed += 1
        if hash_val < threshold:
            self._canary_routed += 1
            return "canary"
        else:
            self._stable_routed += 1
            return "stable"

    def stats(self) -> Dict[str, Any]:
        return {
            "canary_weight": self._canary_weight,
            "stable_weight": self.stable_weight,
            "total_routed": self._total_routed,
            "canary_routed": self._canary_routed,
            "stable_routed": self._stable_routed,
            "actual_canary_pct": (
                round(self._canary_routed / self._total_routed, 4)
                if self._total_routed > 0
                else 0.0
            ),
        }

    def reset_counters(self) -> None:
        self._total_routed = 0
        self._canary_routed = 0
        self._stable_routed = 0


# ---------------------------------------------------------------------------
# HealthChecker
# ---------------------------------------------------------------------------


class HealthChecker:
    """
    Monitors the health of canary and stable deployments by evaluating
    win rate, error rate, and latency against configured thresholds.
    """

    def __init__(self, config: CanaryConfig) -> None:
        self.config = config
        self._check_history: List[Dict[str, Any]] = []

    def check(self, metrics: StageMetrics) -> Tuple[HealthStatus, List[str]]:
        """
        Evaluate the canary health based on current stage metrics.
        Returns (status, list_of_issues).
        """
        issues: List[str] = []

        # Need minimum data to evaluate
        if metrics.canary_matches < 5:
            result = (HealthStatus.UNKNOWN, ["Insufficient data (< 5 matches)"])
            self._record_check(result[0], result[1], metrics)
            return result

        # Win rate check
        if metrics.canary_win_rate < self.config.min_win_rate:
            issues.append(
                f"Win rate {metrics.canary_win_rate:.2%} below threshold "
                f"{self.config.min_win_rate:.2%}"
            )

        # Error rate check
        if metrics.canary_error_rate > self.config.max_error_rate:
            issues.append(
                f"Error rate {metrics.canary_error_rate:.2%} above threshold "
                f"{self.config.max_error_rate:.2%}"
            )

        # Latency check
        if metrics.canary_avg_latency_ms > self.config.max_latency_ms:
            issues.append(
                f"Avg latency {metrics.canary_avg_latency_ms:.1f}ms above threshold "
                f"{self.config.max_latency_ms:.1f}ms"
            )

        if len(issues) == 0:
            status = HealthStatus.HEALTHY
        elif len(issues) == 1:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        self._record_check(status, issues, metrics)
        return (status, issues)

    def compare_versions(self, metrics: StageMetrics) -> Dict[str, Any]:
        """Compare canary vs stable performance."""
        win_rate_diff = metrics.canary_win_rate - metrics.stable_win_rate
        latency_diff = metrics.canary_avg_latency_ms - metrics.stable_avg_latency_ms
        return {
            "canary_win_rate": round(metrics.canary_win_rate, 4),
            "stable_win_rate": round(metrics.stable_win_rate, 4),
            "win_rate_diff": round(win_rate_diff, 4),
            "canary_avg_latency_ms": round(metrics.canary_avg_latency_ms, 2),
            "stable_avg_latency_ms": round(metrics.stable_avg_latency_ms, 2),
            "latency_diff_ms": round(latency_diff, 2),
            "canary_is_better": win_rate_diff > 0 and latency_diff <= 0,
        }

    def _record_check(
        self,
        status: HealthStatus,
        issues: List[str],
        metrics: StageMetrics,
    ) -> None:
        self._check_history.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "status": status.value,
                "issues": issues,
                "canary_win_rate": metrics.canary_win_rate,
                "canary_matches": metrics.canary_matches,
            }
        )

    @property
    def history(self) -> List[Dict[str, Any]]:
        return list(self._check_history)


# ---------------------------------------------------------------------------
# RollbackManager
# ---------------------------------------------------------------------------


class RollbackManager:
    """
    Handles automatic and manual rollback of canary deployments.
    Tracks rollback history and provides rollback decisions.
    """

    def __init__(self, config: CanaryConfig) -> None:
        self.config = config
        self._rollback_events: List[RollbackEvent] = []
        self._is_rolled_back: bool = False

    @property
    def is_rolled_back(self) -> bool:
        return self._is_rolled_back

    def should_rollback(
        self,
        health_status: HealthStatus,
        issues: List[str],
        metrics: StageMetrics,
    ) -> Tuple[bool, Optional[RollbackReason]]:
        """
        Decide whether a rollback should occur based on health status.
        Returns (should_rollback, reason).
        """
        if not self.config.auto_rollback:
            return (False, None)

        if health_status == HealthStatus.UNHEALTHY:
            # Determine the primary reason
            for issue in issues:
                if "Win rate" in issue:
                    return (True, RollbackReason.WIN_RATE_BELOW_THRESHOLD)
                if "Error rate" in issue:
                    return (True, RollbackReason.ERROR_RATE_ABOVE_THRESHOLD)
                if "latency" in issue.lower():
                    return (True, RollbackReason.LATENCY_ABOVE_THRESHOLD)
            return (True, RollbackReason.HEALTH_CHECK_FAILED)

        return (False, None)

    def execute_rollback(
        self,
        deployment_id: str,
        reason: RollbackReason,
        current_phase: DeploymentPhase,
        metrics: StageMetrics,
        message: str = "",
    ) -> RollbackEvent:
        """Execute a rollback and record the event."""
        event = RollbackEvent(
            deployment_id=deployment_id,
            reason=reason,
            phase_at_rollback=current_phase,
            canary_metrics=metrics.summary(),
            message=message or f"Rollback due to {reason.value}",
        )
        self._rollback_events.append(event)
        self._is_rolled_back = True
        logger.warning(
            "ROLLBACK executed for deployment %s at phase %s: %s",
            deployment_id,
            current_phase.value,
            reason.value,
        )
        return event

    def reset(self) -> None:
        """Reset rollback state for a new deployment."""
        self._is_rolled_back = False

    @property
    def rollback_history(self) -> List[RollbackEvent]:
        return list(self._rollback_events)

    @property
    def total_rollbacks(self) -> int:
        return len(self._rollback_events)


# ---------------------------------------------------------------------------
# SC2 Match Simulator (for demo / testing)
# ---------------------------------------------------------------------------


class SC2MatchSimulator:
    """
    Simulates SC2 matches between bot versions for canary testing.
    Each version has a base win rate; the simulator adds noise.
    """

    def __init__(
        self,
        canary_base_win_rate: float = 0.55,
        stable_base_win_rate: float = 0.52,
        canary_error_prob: float = 0.02,
        stable_error_prob: float = 0.01,
        canary_latency_mean: float = 80.0,
        stable_latency_mean: float = 70.0,
    ) -> None:
        self.canary_base_win_rate = canary_base_win_rate
        self.stable_base_win_rate = stable_base_win_rate
        self.canary_error_prob = canary_error_prob
        self.stable_error_prob = stable_error_prob
        self.canary_latency_mean = canary_latency_mean
        self.stable_latency_mean = stable_latency_mean
        self._opponents = [
            "RandomBot",
            "RushBot",
            "MacroBot",
            "CheeseMaster",
            "TurtleBot",
            "AllInBot",
            "EcoBot",
            "AggroBot",
        ]

    def simulate_match(self, version: str, is_canary: bool) -> MatchResult:
        """Simulate a single match for the given version."""
        if is_canary:
            win_rate = self.canary_base_win_rate
            error_prob = self.canary_error_prob
            latency_mean = self.canary_latency_mean
        else:
            win_rate = self.stable_base_win_rate
            error_prob = self.stable_error_prob
            latency_mean = self.stable_latency_mean

        won = random.random() < win_rate
        errors = 1 if random.random() < error_prob else 0
        latency = max(10.0, random.gauss(latency_mean, latency_mean * 0.2))
        duration = random.randint(3000, 25000)
        opponent = random.choice(self._opponents)

        return MatchResult(
            match_id=uuid.uuid4().hex[:10],
            version=version,
            opponent=opponent,
            won=won,
            duration_frames=duration,
            avg_decision_latency_ms=round(latency, 2),
            errors_count=errors,
        )

    def simulate_batch(
        self,
        version: str,
        is_canary: bool,
        count: int,
    ) -> List[MatchResult]:
        """Simulate multiple matches."""
        return [self.simulate_match(version, is_canary) for _ in range(count)]


# ---------------------------------------------------------------------------
# CanaryDeployer  (main orchestrator)
# ---------------------------------------------------------------------------


class CanaryDeployer:
    """
    Orchestrates a canary deployment lifecycle for SC2 bot updates.

    Workflow:
        1. Start deployment with canary at 1% traffic
        2. Run matches, collect metrics
        3. Health check: if healthy, advance to next stage
        4. If unhealthy, rollback automatically
        5. Repeat until full rollout or rollback
    """

    def __init__(self, config: Optional[CanaryConfig] = None) -> None:
        self.config = config or CanaryConfig()
        self.deployment_id: str = uuid.uuid4().hex[:12]
        self.splitter = TrafficSplitter(canary_weight=0.0)
        self.health_checker = HealthChecker(self.config)
        self.rollback_manager = RollbackManager(self.config)
        self._current_stage_idx: int = -1
        self._current_phase: DeploymentPhase = DeploymentPhase.NOT_STARTED
        self._stage_metrics: List[StageMetrics] = []
        self._all_match_results: List[MatchResult] = []
        self._deployment_log: List[Dict[str, Any]] = []
        self._started_at: Optional[str] = None
        self._completed_at: Optional[str] = None

    @property
    def current_phase(self) -> DeploymentPhase:
        return self._current_phase

    @property
    def is_active(self) -> bool:
        return self._current_phase not in (
            DeploymentPhase.NOT_STARTED,
            DeploymentPhase.FULL_ROLLOUT,
            DeploymentPhase.ROLLED_BACK,
        )

    def start(self) -> Dict[str, Any]:
        """Begin the canary deployment at the first stage."""
        errors = self.config.validate()
        if errors:
            return {"success": False, "errors": errors}

        self._started_at = datetime.utcnow().isoformat()
        self.rollback_manager.reset()
        self._log_event(
            "deployment_started",
            {
                "canary_version": self.config.canary_version,
                "stable_version": self.config.stable_version,
            },
        )

        self._advance_stage()
        return {
            "success": True,
            "deployment_id": self.deployment_id,
            "phase": self._current_phase.value,
            "canary_weight": self.splitter.canary_weight,
        }

    def _advance_stage(self) -> bool:
        """Move to the next rollout stage. Returns True if advanced."""
        self._current_stage_idx += 1
        if self._current_stage_idx >= len(self.config.rollout_stages):
            self._current_phase = DeploymentPhase.FULL_ROLLOUT
            self.splitter.canary_weight = 1.0
            self._completed_at = datetime.utcnow().isoformat()
            self._log_event("full_rollout", {})
            return True

        phase, weight = self.config.rollout_stages[self._current_stage_idx]
        self._current_phase = phase
        self.splitter.canary_weight = weight

        stage_metrics = StageMetrics(
            phase=phase,
            started_at=datetime.utcnow().isoformat(),
        )
        self._stage_metrics.append(stage_metrics)

        self._log_event(
            "stage_advanced",
            {
                "phase": phase.value,
                "canary_weight": weight,
            },
        )
        logger.info("Advanced to %s (canary weight=%.2f)", phase.value, weight)
        return True

    def record_match(self, result: MatchResult) -> None:
        """Record a match result into the current stage metrics."""
        self._all_match_results.append(result)

        if not self._stage_metrics:
            return

        metrics = self._stage_metrics[-1]
        is_canary = result.version == self.config.canary_version

        if is_canary:
            metrics.canary_matches += 1
            if result.won:
                metrics.canary_wins += 1
            metrics.canary_errors += result.errors_count
            metrics.canary_total_latency_ms += result.avg_decision_latency_ms
        else:
            metrics.stable_matches += 1
            if result.won:
                metrics.stable_wins += 1
            metrics.stable_errors += result.errors_count
            metrics.stable_total_latency_ms += result.avg_decision_latency_ms

    def evaluate_and_advance(self) -> Dict[str, Any]:
        """
        Evaluate current stage health and decide to advance, hold, or rollback.
        """
        if not self._stage_metrics:
            return {"action": "no_data", "phase": self._current_phase.value}

        metrics = self._stage_metrics[-1]

        # Check if enough matches played
        total_matches = metrics.canary_matches + metrics.stable_matches
        if metrics.canary_matches < self.config.min_matches_per_stage:
            return {
                "action": "waiting",
                "phase": self._current_phase.value,
                "canary_matches": metrics.canary_matches,
                "needed": self.config.min_matches_per_stage,
            }

        # Health check
        health_status, issues = self.health_checker.check(metrics)

        # Rollback decision
        should_rb, rb_reason = self.rollback_manager.should_rollback(
            health_status,
            issues,
            metrics,
        )
        if should_rb and rb_reason is not None:
            event = self.rollback_manager.execute_rollback(
                deployment_id=self.deployment_id,
                reason=rb_reason,
                current_phase=self._current_phase,
                metrics=metrics,
            )
            self._current_phase = DeploymentPhase.ROLLED_BACK
            self.splitter.canary_weight = 0.0
            self._completed_at = datetime.utcnow().isoformat()
            self._log_event(
                "rolled_back",
                {
                    "reason": rb_reason.value,
                    "metrics": metrics.summary(),
                },
            )
            return {
                "action": "rolled_back",
                "reason": rb_reason.value,
                "issues": issues,
                "metrics": metrics.summary(),
            }

        # Healthy enough to advance
        if health_status in (HealthStatus.HEALTHY, HealthStatus.UNKNOWN):
            metrics.completed_at = datetime.utcnow().isoformat()
            comparison = self.health_checker.compare_versions(metrics)

            # Check if we just completed the last stage
            if self._current_stage_idx >= len(self.config.rollout_stages) - 1:
                self._current_phase = DeploymentPhase.FULL_ROLLOUT
                self.splitter.canary_weight = 1.0
                self._completed_at = datetime.utcnow().isoformat()
                self._log_event("full_rollout", {"comparison": comparison})
                return {
                    "action": "full_rollout",
                    "phase": DeploymentPhase.FULL_ROLLOUT.value,
                    "comparison": comparison,
                    "metrics": metrics.summary(),
                }

            self._advance_stage()
            return {
                "action": "advanced",
                "phase": self._current_phase.value,
                "canary_weight": self.splitter.canary_weight,
                "comparison": comparison,
                "metrics": metrics.summary(),
            }

        # Degraded but not unhealthy - hold at current stage
        return {
            "action": "holding",
            "phase": self._current_phase.value,
            "health": health_status.value,
            "issues": issues,
            "metrics": metrics.summary(),
        }

    def force_rollback(self, message: str = "Manual rollback") -> RollbackEvent:
        """Manually trigger a rollback."""
        metrics = (
            self._stage_metrics[-1]
            if self._stage_metrics
            else StageMetrics(phase=self._current_phase)
        )
        event = self.rollback_manager.execute_rollback(
            deployment_id=self.deployment_id,
            reason=RollbackReason.MANUAL,
            current_phase=self._current_phase,
            metrics=metrics,
            message=message,
        )
        self._current_phase = DeploymentPhase.ROLLED_BACK
        self.splitter.canary_weight = 0.0
        self._completed_at = datetime.utcnow().isoformat()
        self._log_event("manual_rollback", {"message": message})
        return event

    def run_simulated_deployment(
        self,
        simulator: Optional[SC2MatchSimulator] = None,
        matches_per_stage: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run an end-to-end simulated canary deployment.
        Plays matches at each stage, evaluates health, and advances or rolls back.
        """
        sim = simulator or SC2MatchSimulator()
        per_stage = matches_per_stage or self.config.min_matches_per_stage

        start_result = self.start()
        if not start_result.get("success"):
            return start_result

        results_log: List[Dict[str, Any]] = []

        while self.is_active:
            # Simulate matches for this stage
            canary_count = max(1, int(per_stage * self.splitter.canary_weight))
            stable_count = per_stage - canary_count

            canary_matches = sim.simulate_batch(
                self.config.canary_version,
                is_canary=True,
                count=canary_count,
            )
            stable_matches = sim.simulate_batch(
                self.config.stable_version,
                is_canary=False,
                count=stable_count,
            )

            for m in canary_matches + stable_matches:
                self.record_match(m)

            # Evaluate
            eval_result = self.evaluate_and_advance()
            results_log.append(eval_result)

            if eval_result["action"] in ("rolled_back", "full_rollout"):
                break

        return {
            "deployment_id": self.deployment_id,
            "final_phase": self._current_phase.value,
            "stages_completed": len(self._stage_metrics),
            "total_matches": len(self._all_match_results),
            "stage_results": results_log,
            "rollbacks": self.rollback_manager.total_rollbacks,
        }

    def status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        current_metrics = (
            self._stage_metrics[-1].summary() if self._stage_metrics else {}
        )
        return {
            "deployment_id": self.deployment_id,
            "phase": self._current_phase.value,
            "canary_version": self.config.canary_version,
            "stable_version": self.config.stable_version,
            "canary_weight": self.splitter.canary_weight,
            "total_matches": len(self._all_match_results),
            "current_stage_metrics": current_metrics,
            "traffic_stats": self.splitter.stats(),
            "started_at": self._started_at,
            "completed_at": self._completed_at,
            "is_rolled_back": self.rollback_manager.is_rolled_back,
        }

    def full_report(self) -> Dict[str, Any]:
        """Generate a comprehensive deployment report."""
        stage_summaries = [m.summary() for m in self._stage_metrics]
        return {
            "deployment_id": self.deployment_id,
            "config": {
                "canary_version": self.config.canary_version,
                "stable_version": self.config.stable_version,
                "min_win_rate": self.config.min_win_rate,
                "max_error_rate": self.config.max_error_rate,
                "max_latency_ms": self.config.max_latency_ms,
            },
            "final_phase": self._current_phase.value,
            "stages": stage_summaries,
            "total_matches": len(self._all_match_results),
            "rollback_history": [
                {
                    "reason": e.reason.value,
                    "phase": e.phase_at_rollback.value,
                    "timestamp": e.timestamp,
                    "message": e.message,
                }
                for e in self.rollback_manager.rollback_history
            ],
            "health_check_history": self.health_checker.history,
            "event_log": self._deployment_log,
            "started_at": self._started_at,
            "completed_at": self._completed_at,
        }

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        self._deployment_log.append(
            {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
            }
        )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate canary deployment for SC2 bot updates."""
    print("=" * 60)
    print("Phase 657: Canary Deployment for Safe SC2 Bot Updates - Demo")
    print("=" * 60)

    # --- Configuration ---
    print("\n[1] Setting up canary deployment config...")
    config = CanaryConfig(
        canary_version="v2.1.0-zergling-rush-fix",
        stable_version="v2.0.0-stable",
        min_win_rate=0.40,
        max_error_rate=0.10,
        max_latency_ms=250.0,
        min_matches_per_stage=25,
        auto_rollback=True,
    )
    validation_errors = config.validate()
    print(f"  Config valid: {len(validation_errors) == 0}")
    print(f"  Canary: {config.canary_version}")
    print(f"  Stable: {config.stable_version}")
    print(f"  Rollout stages: {[s[0].value for s in config.rollout_stages]}")

    # --- Traffic splitter demo ---
    print("\n[2] Traffic splitter demo...")
    splitter = TrafficSplitter(canary_weight=0.05)
    routing_counts = {"canary": 0, "stable": 0}
    for _ in range(1000):
        dest = splitter.route()
        routing_counts[dest] += 1
    print(
        f"  Weight: canary={splitter.canary_weight:.0%}, stable={splitter.stable_weight:.0%}"
    )
    print(f"  Actual routing (1000 requests): {routing_counts}")

    # --- Successful canary deployment ---
    print("\n[3] Running simulated SUCCESSFUL canary deployment...")
    deployer = CanaryDeployer(config)
    simulator = SC2MatchSimulator(
        canary_base_win_rate=0.58,
        stable_base_win_rate=0.52,
        canary_error_prob=0.01,
        stable_error_prob=0.01,
    )

    result = deployer.run_simulated_deployment(
        simulator=simulator, matches_per_stage=30
    )
    print(f"  Final phase: {result['final_phase']}")
    print(f"  Stages completed: {result['stages_completed']}")
    print(f"  Total matches: {result['total_matches']}")
    print(f"  Rollbacks: {result['rollbacks']}")

    for i, stage_result in enumerate(result["stage_results"]):
        action = stage_result["action"]
        phase = stage_result.get("phase", "n/a")
        print(f"    Stage {i+1}: action={action}, phase={phase}")

    # --- Failed canary deployment (auto rollback) ---
    print("\n[4] Running simulated FAILED canary deployment (should rollback)...")
    config_bad = CanaryConfig(
        canary_version="v2.2.0-broken-micro",
        stable_version="v2.0.0-stable",
        min_win_rate=0.45,
        max_error_rate=0.05,
        max_latency_ms=150.0,
        min_matches_per_stage=25,
        auto_rollback=True,
    )

    deployer_bad = CanaryDeployer(config_bad)
    bad_simulator = SC2MatchSimulator(
        canary_base_win_rate=0.25,
        stable_base_win_rate=0.52,
        canary_error_prob=0.15,
        stable_error_prob=0.01,
        canary_latency_mean=300.0,
        stable_latency_mean=70.0,
    )

    bad_result = deployer_bad.run_simulated_deployment(
        simulator=bad_simulator,
        matches_per_stage=30,
    )
    print(f"  Final phase: {bad_result['final_phase']}")
    print(f"  Rollbacks: {bad_result['rollbacks']}")
    for i, stage_result in enumerate(bad_result["stage_results"]):
        action = stage_result["action"]
        reason = stage_result.get("reason", "n/a")
        print(f"    Stage {i+1}: action={action}, reason={reason}")

    # --- Manual rollback demo ---
    print("\n[5] Manual rollback demo...")
    deployer_manual = CanaryDeployer(
        CanaryConfig(
            canary_version="v3.0.0-experimental",
            stable_version="v2.0.0-stable",
            min_matches_per_stage=100,
        )
    )
    deployer_manual.start()
    print(f"  Phase before rollback: {deployer_manual.current_phase.value}")
    rollback_event = deployer_manual.force_rollback("Operator decided to abort")
    print(f"  Phase after rollback:  {deployer_manual.current_phase.value}")
    print(f"  Rollback reason: {rollback_event.reason.value}")

    # --- Health checker comparison ---
    print("\n[6] Version comparison from successful deployment...")
    report = deployer.full_report()
    print(f"  Deployment ID: {report['deployment_id']}")
    print(f"  Stages recorded: {len(report['stages'])}")
    for stage in report["stages"]:
        print(
            f"    {stage['phase']}: canary_wr={stage['canary_win_rate']:.2%}, "
            f"stable_wr={stage['stable_win_rate']:.2%}"
        )

    print(f"\n  Health check history entries: {len(report['health_check_history'])}")
    print(f"  Event log entries: {len(report['event_log'])}")

    print("\nPhase 657 demo complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()

# Phase 657: Canary Deploy registered
