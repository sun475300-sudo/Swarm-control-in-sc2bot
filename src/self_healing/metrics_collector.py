"""Lightweight in-process metrics collector for the self-healing pipeline."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List


class MetricsCollector:
    """Tracks counters, gauges, and bounded time-series histograms."""

    name = "metrics_collector"

    def __init__(self, history_size: int = 256) -> None:
        if history_size <= 0:
            raise ValueError("history_size must be positive")
        self._history_size = history_size
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=history_size)
        )

    def increment(self, name: str, by: float = 1.0) -> float:
        self._counters[name] += by
        return self._counters[name]

    def set(self, name: str, value: float) -> None:
        self._gauges[name] = float(value)

    def record(self, name: str, value: float) -> None:
        self._histograms[name].append(float(value))

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str, default: float = 0.0) -> float:
        return self._gauges.get(name, default)

    def get_history(self, name: str) -> List[float]:
        return list(self._histograms.get(name, ()))

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()

    def snapshot(self) -> Dict[str, Dict]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: list(v) for k, v in self._histograms.items()},
        }
