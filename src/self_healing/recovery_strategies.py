"""Recovery strategy registry: retry / fallback / restart variants."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

Action = Callable[[], Any]


def retry(
    action: Action,
    attempts: int = 3,
    base_delay: float = 0.0,
    backoff: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Run ``action`` up to ``attempts`` times with exponential backoff."""
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last_exc: Optional[BaseException] = None
    delay = base_delay
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except Exception as exc:  # noqa: BLE001 - surface only after retries
            last_exc = exc
            if attempt == attempts:
                break
            if delay > 0:
                sleep(delay)
            delay = delay * backoff if delay > 0 else (base_delay or 0.0)
    raise last_exc  # type: ignore[misc]


def fallback(action: Action, fallback_action: Action) -> Any:
    """Run ``action``; on failure run ``fallback_action`` instead."""
    try:
        return action()
    except Exception:  # noqa: BLE001 - explicit fallback path
        return fallback_action()


class RecoveryStrategies:
    """Maps exception categories to registered recovery strategies."""

    name = "recovery_strategies"

    def __init__(self) -> None:
        self._strategies: Dict[str, Callable[[BaseException, Action], Any]] = {}

    def register(
        self,
        category: str,
        strategy: Callable[[BaseException, Action], Any],
    ) -> None:
        if not callable(strategy):
            raise TypeError("strategy must be callable")
        self._strategies[category] = strategy

    def has(self, category: str) -> bool:
        return category in self._strategies

    def recover(self, category: str, error: BaseException, action: Action) -> Any:
        if category not in self._strategies:
            raise KeyError(f"no strategy registered for category {category!r}")
        return self._strategies[category](error, action)

    def categories(self) -> tuple:
        return tuple(self._strategies.keys())
