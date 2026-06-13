"""Pub-sub alerting hub for the self-healing pipeline."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List

LEVELS = ("info", "warning", "error", "critical")
_LEVEL_ORDER = {level: i for i, level in enumerate(LEVELS)}


@dataclass
class Alert:
    level: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


AlertCallback = Callable[[Alert], None]


class Alerting:
    """Routes alerts to subscribers and keeps a bounded history."""

    name = "alerting"

    def __init__(self, history_size: int = 100) -> None:
        if history_size <= 0:
            raise ValueError("history_size must be positive")
        self._subscribers: List[AlertCallback] = []
        self._history: Deque[Alert] = deque(maxlen=history_size)
        self._min_level = "info"

    def set_min_level(self, level: str) -> None:
        if level not in LEVELS:
            raise ValueError(f"level must be one of {LEVELS}")
        self._min_level = level

    def subscribe(self, callback: AlertCallback) -> None:
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._subscribers.append(callback)

    def unsubscribe(self, callback: AlertCallback) -> bool:
        try:
            self._subscribers.remove(callback)
            return True
        except ValueError:
            return False

    def alert(self, level: str, message: str, **context: Any) -> Alert:
        if level not in LEVELS:
            raise ValueError(f"level must be one of {LEVELS}")
        alert = Alert(level=level, message=message, context=dict(context))
        if _LEVEL_ORDER[level] >= _LEVEL_ORDER[self._min_level]:
            self._history.append(alert)
            for callback in list(self._subscribers):
                try:
                    callback(alert)
                except Exception:  # noqa: BLE001 - never let a callback break us
                    pass
        return alert

    def history(self) -> List[Alert]:
        return list(self._history)
