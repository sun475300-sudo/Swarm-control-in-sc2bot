"""High-level monitoring loop combining metrics, health checks, and alerting."""

from __future__ import annotations

from typing import Dict, Optional

from .alerting import Alerting
from .health_checker import HealthChecker
from .metrics_collector import MetricsCollector


class Monitoring:
    """Orchestrates one tick of the self-healing observation loop."""

    name = "monitoring"

    def __init__(
        self,
        metrics: Optional[MetricsCollector] = None,
        health: Optional[HealthChecker] = None,
        alerting: Optional[Alerting] = None,
    ) -> None:
        self.metrics = metrics or MetricsCollector()
        self.health = health or HealthChecker()
        self.alerting = alerting or Alerting()
        self._tick_count = 0
        self._last_status: Dict = {"level": "ok", "healthy": True, "checks": []}

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def last_status(self) -> Dict:
        return dict(self._last_status)

    def tick(self) -> Dict:
        """Run health checks, emit alerts on failures, advance the tick."""
        self._tick_count += 1
        self.metrics.increment("monitoring.ticks")
        status = self.health.status()
        self._last_status = status
        if not status["healthy"]:
            level = "critical" if status["level"] == "critical" else "warning"
            failed = [c for c in status["checks"] if not c["passed"]]
            self.alerting.alert(
                level,
                f"{len(failed)} health check(s) failing",
                checks=failed,
            )
            self.metrics.increment("monitoring.failed_checks", by=len(failed))
        return status
