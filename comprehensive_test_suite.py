"""
Comprehensive Test Suite — Continuous Testing wrapper

Drives the real pytest run under tests/ and groups results by file naming
convention. Replaces the previous version that returned hardcoded numbers
(7/7, 5/5, 700/300 fuzz, etc.) which made the JSON report meaningless.

Usage:
    python comprehensive_test_suite.py
        Runs pytest with --tb=line and writes
        comprehensive_test_results.json + a human-readable report to stdout.

Categories are mapped from test-file basenames (substring match):
    unit_tests       any test_*.py that doesn't fall into another bucket
    integration_tests files under tests/integration/
    matchup_tests    test_matchup_*
    edge_case_tests  test_*_edge*, test_*edge*
    benchmark_tests  test_*perf*, test_*benchmark*, test_phase10_*, test_p606_*
    fuzz_tests       test_*fuzz*
    regression_tests test_*regression*, test_*resilience*
"""

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
RESULT_RE = re.compile(r"^(?P<status>PASSED|FAILED|SKIPPED|ERROR)\s+(?P<nodeid>\S+)")


def _classify(nodeid: str) -> str:
    path = nodeid.split("::", 1)[0]
    base = Path(path).name.lower()
    if "/integration/" in path or path.startswith("tests/integration"):
        return "integration_tests"
    if "matchup" in base:
        return "matchup_tests"
    if "edge" in base:
        return "edge_case_tests"
    if "fuzz" in base:
        return "fuzz_tests"
    if "regression" in base or "resilience" in base:
        return "regression_tests"
    if "perf" in base or "benchmark" in base or "phase10" in base or "p606" in base:
        return "benchmark_tests"
    return "unit_tests"


def _resolve_pytest_cmd() -> List[str]:
    """Prefer a `pytest` script on PATH (its venv has the right plugin set)
    and fall back to `python -m pytest` only if no script is found.
    """
    import shutil

    pytest_bin = shutil.which("pytest")
    if pytest_bin:
        return [pytest_bin]
    return [sys.executable, "-m", "pytest"]


def _run_pytest(extra_args: List[str]) -> Tuple[int, str]:
    """Run pytest and return (exit_code, ANSI-stripped combined output)."""
    cmd = (
        _resolve_pytest_cmd()
        + [
            "tests/",
            "-r",
            "fsxXp",
            "--tb=line",
            "--no-header",
            "-q",
            "--color=no",
        ]
        + extra_args
    )
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    output = proc.stdout + proc.stderr
    return proc.returncode, ANSI_RE.sub("", output)


def _parse_results(output: str) -> Dict[str, Dict[str, int]]:
    """Walk pytest -r output and bucket each PASS/FAIL/SKIP/ERROR by category."""
    buckets: Dict[str, Dict[str, int]] = {}
    for line in output.splitlines():
        m = RESULT_RE.match(line.strip())
        if not m:
            continue
        category = _classify(m.group("nodeid"))
        b = buckets.setdefault(
            category, {"tests": 0, "passed": 0, "failed": 0, "skipped": 0}
        )
        b["tests"] += 1
        status = m.group("status")
        if status == "PASSED":
            b["passed"] += 1
        elif status == "FAILED" or status == "ERROR":
            b["failed"] += 1
        elif status == "SKIPPED":
            b["skipped"] += 1
    return buckets


class ComprehensiveTestSuite:
    """Thin runner that records start time + delegates to pytest."""

    def __init__(self) -> None:
        self.results: Dict[str, Any] = {}
        self.start_time = time.time()

    def run_all_tests(self) -> Dict[str, Any]:
        print("[Suite] Running pytest tests/ ...")
        try:
            _, output = _run_pytest([])
        except FileNotFoundError:
            print("[Suite] ERROR: python or pytest not found on PATH")
            self.results = {
                "summary": {
                    "total_tests": 0,
                    "total_passed": 0,
                    "total_failed": 0,
                    "total_skipped": 0,
                    "pass_rate": 0.0,
                    "total_duration_ms": 0.0,
                    "error": "pytest unavailable",
                }
            }
            return self.results["summary"]

        buckets = _parse_results(output)
        for name, counts in buckets.items():
            self.results[name] = counts

        total_tests = sum(b["tests"] for b in buckets.values())
        total_passed = sum(b["passed"] for b in buckets.values())
        total_failed = sum(b["failed"] for b in buckets.values())
        total_skipped = sum(b["skipped"] for b in buckets.values())

        duration_ms = (time.time() - self.start_time) * 1000
        summary = {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "pass_rate": (total_passed / total_tests * 100) if total_tests else 0.0,
            "total_duration_ms": duration_ms,
        }
        self.results["summary"] = summary
        return summary

    def generate_report(self) -> str:
        summary = self.results.get("summary", {})
        lines = [
            "=" * 80,
            "COMPREHENSIVE TEST SUITE REPORT",
            "=" * 80,
            f"Generated: {datetime.now().isoformat()}",
            "",
            "RESULTS:",
            f"  Total Tests: {summary.get('total_tests', 0)}",
            f"  Passed:      {summary.get('total_passed', 0)}",
            f"  Failed:      {summary.get('total_failed', 0)}",
            f"  Skipped:     {summary.get('total_skipped', 0)}",
            f"  Pass Rate:   {summary.get('pass_rate', 0):.1f}%",
            f"  Duration:    {summary.get('total_duration_ms', 0):.0f}ms",
            "",
            "BY CATEGORY:",
            "-" * 80,
        ]
        for name, result in self.results.items():
            if name == "summary":
                continue
            lines.append(
                f"  {name:<25} "
                f"{result['passed']:>4}/{result['tests']:<4} passed"
                f"  ({result.get('failed', 0)} fail, {result.get('skipped', 0)} skip)"
            )
        lines.append("=" * 80)
        return "\n".join(lines)


if __name__ == "__main__":
    print("[Suite] Starting comprehensive test suite...")
    suite = ComprehensiveTestSuite()
    suite.run_all_tests()
    print("\n" + suite.generate_report())
    out_path = REPO_ROOT / "comprehensive_test_results.json"
    with out_path.open("w") as f:
        json.dump(suite.results, f, indent=2)
    print(f"\n[Saved to {out_path.name}]")
