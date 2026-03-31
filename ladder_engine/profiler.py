"""
Phase 371: Performance Profiler
In-game performance profiler tracking APM, decision latency, and efficiency
metrics. Exports data to a Prometheus-compatible metrics endpoint.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import threading
from collections import deque


@dataclass
class MetricSnapshot:
    timestamp: float
    actions_per_minute: float
    decision_latency_ms: float
    macro_efficiency: float      # 0.0–1.0
    micro_efficiency: float      # 0.0–1.0
    worker_count: int
    army_supply: int
    supply_blocked_seconds: float

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "apm": round(self.actions_per_minute, 1),
            "latency_ms": round(self.decision_latency_ms, 2),
            "macro_efficiency": round(self.macro_efficiency, 4),
            "micro_efficiency": round(self.micro_efficiency, 4),
            "worker_count": self.worker_count,
            "army_supply": self.army_supply,
            "supply_blocked_s": round(self.supply_blocked_seconds, 2),
        }


class PerformanceProfiler:
    """
    Collects and aggregates bot performance metrics during ladder games.
    Thread-safe; can export to Prometheus text format.
    """

    HISTORY_WINDOW = 120     # seconds of rolling history
    APM_WINDOW_SEC = 60      # window for APM calculation

    def __init__(self):
        self._lock = threading.Lock()
        self._action_times: deque = deque()        # timestamps of each action
        self._latency_samples: deque = deque()     # (timestamp, latency_ms)
        self._snapshots: List[MetricSnapshot] = []
        self._supply_blocked_start: Optional[float] = None
        self._supply_blocked_total: float = 0.0
        self._decision_start: Optional[float] = None
        self._game_start: float = time.time()
        self._last_snap_time: float = time.time()

    # ------------------------------------------------------------------
    # Action tracking
    # ------------------------------------------------------------------

    def record_action(self):
        """Call once for every game action issued."""
        with self._lock:
            now = time.time()
            self._action_times.append(now)
            # Prune old entries
            cutoff = now - self.APM_WINDOW_SEC
            while self._action_times and self._action_times[0] < cutoff:
                self._action_times.popleft()

    def current_apm(self) -> float:
        with self._lock:
            now = time.time()
            cutoff = now - self.APM_WINDOW_SEC
            recent = [t for t in self._action_times if t >= cutoff]
            elapsed = min(now - self._game_start, self.APM_WINDOW_SEC)
            if elapsed <= 0:
                return 0.0
            return len(recent) / elapsed * 60.0

    # ------------------------------------------------------------------
    # Decision latency tracking
    # ------------------------------------------------------------------

    def start_decision(self):
        """Mark the start of a decision computation cycle."""
        self._decision_start = time.perf_counter()

    def end_decision(self) -> float:
        """Mark the end; return latency in milliseconds."""
        if self._decision_start is None:
            return 0.0
        latency_ms = (time.perf_counter() - self._decision_start) * 1000.0
        with self._lock:
            now = time.time()
            self._latency_samples.append((now, latency_ms))
            cutoff = now - self.HISTORY_WINDOW
            while self._latency_samples and self._latency_samples[0][0] < cutoff:
                self._latency_samples.popleft()
        self._decision_start = None
        return latency_ms

    def avg_latency_ms(self) -> float:
        with self._lock:
            if not self._latency_samples:
                return 0.0
            return sum(s[1] for s in self._latency_samples) / len(self._latency_samples)

    # ------------------------------------------------------------------
    # Supply block tracking
    # ------------------------------------------------------------------

    def supply_blocked_start(self):
        if self._supply_blocked_start is None:
            self._supply_blocked_start = time.time()

    def supply_blocked_end(self):
        if self._supply_blocked_start is not None:
            self._supply_blocked_total += time.time() - self._supply_blocked_start
            self._supply_blocked_start = None

    # ------------------------------------------------------------------
    # Efficiency metrics
    # ------------------------------------------------------------------

    def compute_macro_efficiency(
        self,
        minerals: int,
        vespene: int,
        worker_count: int,
        base_count: int,
        injection_lag_s: float = 0.0,
    ) -> float:
        """
        Score macro play quality on 0–1 scale.
        Penalises high bank, low workers, and injection lag.
        """
        bank_penalty = min((minerals + vespene) / 1000.0, 0.4)
        worker_score = min(worker_count / (base_count * 16 + 1), 1.0)
        inject_penalty = min(injection_lag_s / 30.0, 0.2)
        return max(0.0, worker_score - bank_penalty - inject_penalty)

    def compute_micro_efficiency(
        self,
        units_lost: int,
        units_killed: int,
        retreat_count: int,
        kite_count: int,
    ) -> float:
        """
        Score army micromanagement quality on 0–1 scale.
        """
        if units_lost + units_killed == 0:
            return 0.5
        kill_ratio = units_killed / max(units_lost, 1)
        kite_bonus = min(kite_count * 0.02, 0.2)
        retreat_penalty = min(retreat_count * 0.01, 0.1)
        score = min(kill_ratio / 4.0, 0.7) + kite_bonus - retreat_penalty
        return max(0.0, min(score, 1.0))

    # ------------------------------------------------------------------
    # Snapshot and export
    # ------------------------------------------------------------------

    def take_snapshot(
        self,
        worker_count: int = 0,
        army_supply: int = 0,
        macro_efficiency: float = 0.5,
        micro_efficiency: float = 0.5,
    ) -> MetricSnapshot:
        snap = MetricSnapshot(
            timestamp=time.time(),
            actions_per_minute=self.current_apm(),
            decision_latency_ms=self.avg_latency_ms(),
            macro_efficiency=macro_efficiency,
            micro_efficiency=micro_efficiency,
            worker_count=worker_count,
            army_supply=army_supply,
            supply_blocked_seconds=self._supply_blocked_total,
        )
        self._snapshots.append(snap)
        return snap

    def latest_snapshot(self) -> Optional[MetricSnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def export_prometheus(self) -> str:
        """Export latest metrics in Prometheus text exposition format."""
        snap = self.latest_snapshot()
        if not snap:
            return "# No data\n"
        lines = [
            "# HELP sc2bot_apm Actions per minute",
            "# TYPE sc2bot_apm gauge",
            f"sc2bot_apm {snap.actions_per_minute:.2f}",
            "# HELP sc2bot_decision_latency_ms Decision latency in ms",
            "# TYPE sc2bot_decision_latency_ms gauge",
            f"sc2bot_decision_latency_ms {snap.decision_latency_ms:.2f}",
            "# HELP sc2bot_macro_efficiency Macro efficiency score",
            "# TYPE sc2bot_macro_efficiency gauge",
            f"sc2bot_macro_efficiency {snap.macro_efficiency:.4f}",
            "# HELP sc2bot_micro_efficiency Micro efficiency score",
            "# TYPE sc2bot_micro_efficiency gauge",
            f"sc2bot_micro_efficiency {snap.micro_efficiency:.4f}",
            "# HELP sc2bot_supply_blocked_seconds Total seconds supply blocked",
            "# TYPE sc2bot_supply_blocked_seconds counter",
            f"sc2bot_supply_blocked_seconds {snap.supply_blocked_seconds:.2f}",
        ]
        return "\n".join(lines) + "\n"
