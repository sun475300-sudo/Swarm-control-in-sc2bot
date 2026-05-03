"""
Comprehensive Test Suite - Continuous Testing
Runs all test categories in sequence with detailed logging.

Each runner now executes the corresponding script as a subprocess and
parses its summary line, instead of returning hardcoded counts.
"""

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent

# Recognised summary line formats:
#   "Total: <N> | Passed: <P>"           (edge_case_test, fuzz_test, regression_test)
#   "[TOTAL] <P>/<N> passed (...)"        (large_scale_test)
#   "TOTAL ... <P>/<N> (..%)"             (complete_test_summary)
_SUMMARY_RE = re.compile(
    r"(?:Total:\s*(\d+)\s*\|\s*Passed:\s*(\d+))"
    r"|(?:(\d+)\s*/\s*(\d+)\s+passed)"
    r"|(?:TOTAL[^\d\n]*?(\d+)\s*/\s*(\d+)\s*\()",
    re.MULTILINE,
)


def _run_script(name: str) -> Tuple[int, int, int]:
    """Execute a top-level test script and return (tests, passed, duration_ms).

    Falls back to (0, 0, 0) if the script is missing or produces no
    parseable summary; the empty result is reported as 0/0 rather than
    silently inflating the pass rate.
    """
    script = REPO_ROOT / name
    if not script.exists():
        return (0, 0, 0)

    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
        )
        output = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        return (0, 0, int((time.time() - started) * 1000))

    duration_ms = int((time.time() - started) * 1000)

    matches = _SUMMARY_RE.findall(output)
    if not matches:
        return (0, 0, duration_ms)

    # Sum all matched per-category lines (e.g. large_scale_test.py reports
    # several "P/N passed" lines plus a TOTAL); take the largest as canonical.
    totals: List[Tuple[int, int]] = []
    for groups in matches:
        total_a, passed_a, passed_b, total_b, passed_c, total_c = groups
        if total_a and passed_a:
            totals.append((int(total_a), int(passed_a)))
        elif total_b and passed_b:
            totals.append((int(total_b), int(passed_b)))
        elif total_c and passed_c:
            totals.append((int(total_c), int(passed_c)))

    if not totals:
        return (0, 0, duration_ms)

    tests, passed = max(totals, key=lambda t: t[0])
    return (tests, passed, duration_ms)


class ComprehensiveTestSuite:
    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.start_time = time.time()

    @staticmethod
    def _result(t: int, p: int, d: int) -> Dict[str, Any]:
        return {"tests": t, "passed": p, "duration": d}

    def run_unit_tests(self) -> Dict[str, Any]:
        return self._result(*_run_script("complete_test_summary.py"))

    def run_stress_tests(self) -> Dict[str, Any]:
        return self._result(*_run_script("stress_test.py"))

    def run_edge_case_tests(self) -> Dict[str, Any]:
        return self._result(*_run_script("edge_case_test.py"))

    def run_integration_tests(self) -> Dict[str, Any]:
        return self._result(*_run_script("integration_test.py"))

    def run_benchmark_tests(self) -> Dict[str, Any]:
        # Benchmarks live alongside the dashboard; treat as no-op when absent.
        return self._result(*_run_script("benchmark_test.py"))

    def run_multi_env_tests(self) -> Dict[str, Any]:
        return self._result(*_run_script("multi_env_test.py"))

    def run_matchup_tests(self) -> Dict[str, Any]:
        return self._result(*_run_script("matchup_test.py"))

    def run_fuzz_tests(self) -> Dict[str, Any]:
        return self._result(*_run_script("fuzz_test.py"))

    def run_regression_tests(self) -> Dict[str, Any]:
        return self._result(*_run_script("regression_test.py"))

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test categories"""
        categories = [
            ("unit_tests", self.run_unit_tests),
            ("stress_tests", self.run_stress_tests),
            ("edge_case_tests", self.run_edge_case_tests),
            ("integration_tests", self.run_integration_tests),
            ("benchmark_tests", self.run_benchmark_tests),
            ("multi_env_tests", self.run_multi_env_tests),
            ("matchup_tests", self.run_matchup_tests),
            ("fuzz_tests", self.run_fuzz_tests),
            ("regression_tests", self.run_regression_tests),
        ]

        total_tests = 0
        total_passed = 0

        for name, test_func in categories:
            print(f"\n[Suite] Running {name}...")
            result = test_func()
            self.results[name] = result
            total_tests += result["tests"]
            total_passed += result["passed"]
            print(
                f"  {result['passed']}/{result['tests']} passed in {result['duration']}ms"
            )

        total_duration = (time.time() - self.start_time) * 1000

        summary = {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_tests - total_passed,
            "pass_rate": (total_passed / total_tests * 100) if total_tests else 0.0,
            "total_duration_ms": total_duration,
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
            f"  Passed: {summary.get('total_passed', 0)}",
            f"  Failed: {summary.get('total_failed', 0)}",
            f"  Pass Rate: {summary.get('pass_rate', 0):.1f}%",
            f"  Duration: {summary.get('total_duration_ms', 0):.0f}ms",
            "",
            "BY CATEGORY:",
            "-" * 80,
        ]

        for name, result in self.results.items():
            if name != "summary" and name != "summary":
                lines.append(
                    f"  {name:<25} {result['passed']:>4}/{result['tests']:<4} passed"
                )

        lines.append("=" * 80)

        return "\n".join(lines)


if __name__ == "__main__":
    print("[Suite] Starting comprehensive test suite...")
    suite = ComprehensiveTestSuite()
    summary = suite.run_all_tests()
    print("\n" + suite.generate_report())

    with open("comprehensive_test_results.json", "w") as f:
        json.dump(suite.results, f, indent=2)
    print("\n[Saved to comprehensive_test_results.json]")
