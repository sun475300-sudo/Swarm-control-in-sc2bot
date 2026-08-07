"""Composable health checks for the self-healing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

LEVELS = ("ok", "degraded", "critical")
_LEVEL_ORDER = {level: i for i, level in enumerate(LEVELS)}


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str
    detail: str = ""


class HealthChecker:
    """Aggregates predicate-based health checks into a single status."""

    name = "health_checker"

    def __init__(self) -> None:
        self._checks: Dict[str, Dict] = {}

    def add_check(
        self,
        name: str,
        predicate: Callable[[], bool],
        severity: str = "critical",
        detail: str = "",
    ) -> None:
        if severity not in LEVELS:
            raise ValueError(f"severity must be one of {LEVELS}")
        if not callable(predicate):
            raise TypeError("predicate must be callable")
        self._checks[name] = {
            "predicate": predicate,
            "severity": severity,
            "detail": detail,
        }

    def remove_check(self, name: str) -> bool:
        return self._checks.pop(name, None) is not None

    def run(self) -> List[CheckResult]:
        results: List[CheckResult] = []
        for name, spec in self._checks.items():
            try:
                passed = bool(spec["predicate"]())
            except Exception as exc:  # noqa: BLE001 - aggregate predicate errors
                passed = False
                detail = f"predicate raised {type(exc).__name__}: {exc}"
            else:
                detail = spec["detail"]
            results.append(
                CheckResult(
                    name=name,
                    passed=passed,
                    severity=spec["severity"],
                    detail=detail,
                )
            )
        return results

    def status(self) -> Dict:
        results = self.run()
        worst = "ok"
        for result in results:
            if not result.passed:
                if _LEVEL_ORDER[result.severity] > _LEVEL_ORDER[worst]:
                    worst = result.severity
        return {
            "level": worst,
            "healthy": worst == "ok",
            "checks": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "detail": r.detail,
                }
                for r in results
            ],
        }
