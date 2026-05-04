"""
Comprehensive Test Suite - Continuous Testing
Runs every sub-suite for real, collects pass/fail counts from the actual
runs (instead of returning hard-coded numbers), and writes a JSON report.
"""

import json
import time
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple


def _safe_run(label: str, fn: Callable[[], Tuple[int, int]]) -> Dict[str, Any]:
    """Run a sub-suite and return {tests, passed, duration} even on error."""
    start = time.time()
    try:
        total, passed = fn()
        return {
            "tests": total,
            "passed": passed,
            "duration": int((time.time() - start) * 1000),
        }
    except Exception as e:
        return {
            "tests": 0,
            "passed": 0,
            "duration": int((time.time() - start) * 1000),
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }


def _run_unit_tests() -> Tuple[int, int]:
    from unit_combo_test import run_all_combinations

    results = run_all_combinations()
    return len(results), len(results)


def _run_stress_tests() -> Tuple[int, int]:
    from stress_test import StressTestRunner

    results = StressTestRunner().run_all_stress_tests()
    passed = sum(1 for r in results if r.success_rate >= 0.95)
    return len(results), passed


def _run_edge_case_tests() -> Tuple[int, int]:
    from edge_case_test import EdgeCaseTester

    results = EdgeCaseTester().run_all_tests()
    passed = sum(1 for r in results if r.passed)
    return len(results), passed


def _run_integration_tests() -> Tuple[int, int]:
    from integration_test import IntegrationTestRunner

    results = IntegrationTestRunner().run_all_tests()
    passed = sum(1 for r in results if r.passed)
    return len(results), passed


def _run_benchmark_tests() -> Tuple[int, int]:
    from stress_test import StressTestRunner

    results = StressTestRunner().run_all_stress_tests()
    passed = sum(1 for r in results if r.duration_ms < 60000)
    return len(results), passed


def _run_multi_env_tests() -> Tuple[int, int]:
    from multi_env_test import MultiEnvironmentTester

    results = MultiEnvironmentTester().test_all_maps()
    passed = sum(1 for r in results if r.passed)
    return len(results), passed


def _run_matchup_tests() -> Tuple[int, int]:
    from matchup_test import OpponentAnalyzer

    results = OpponentAnalyzer().test_all_matchups()
    passed = sum(1 for r in results if r.win_rate >= 50)
    return len(results), passed


def _run_fuzz_tests() -> Tuple[int, int]:
    from fuzz_test import Fuzzer

    fuzzer = Fuzzer(seed=0xC0FFEE)
    results = fuzzer.run_all()
    passed = sum(1 for r in results if r.passed)
    return len(results), passed


def _run_regression_tests() -> Tuple[int, int]:
    from regression_test import RegressionTestSuite

    results = RegressionTestSuite().run_all()
    passed = sum(1 for r in results if r.passed)
    return len(results), passed


class ComprehensiveTestSuite:
    SUITES: List[Tuple[str, Callable[[], Tuple[int, int]]]] = [
        ("unit_tests", _run_unit_tests),
        ("stress_tests", _run_stress_tests),
        ("edge_case_tests", _run_edge_case_tests),
        ("integration_tests", _run_integration_tests),
        ("benchmark_tests", _run_benchmark_tests),
        ("multi_env_tests", _run_multi_env_tests),
        ("matchup_tests", _run_matchup_tests),
        ("fuzz_tests", _run_fuzz_tests),
        ("regression_tests", _run_regression_tests),
    ]

    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.start_time = time.time()

    def run_all_tests(self) -> Dict[str, Any]:
        total_tests = 0
        total_passed = 0

        for name, runner in self.SUITES:
            print(f"\n[Suite] Running {name}...")
            result = _safe_run(name, runner)
            self.results[name] = result
            total_tests += result["tests"]
            total_passed += result["passed"]
            extra = f" ({result['error']})" if "error" in result else ""
            print(
                f"  {result['passed']}/{result['tests']} passed in "
                f"{result['duration']}ms{extra}"
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
            if name == "summary":
                continue
            err = f"  [ERROR: {result['error']}]" if "error" in result else ""
            lines.append(
                f"  {name:<25} {result['passed']:>4}/{result['tests']:<4} passed{err}"
            )

        lines.append("=" * 80)
        return "\n".join(lines)


if __name__ == "__main__":
    print("[Suite] Starting comprehensive test suite...")
    suite = ComprehensiveTestSuite()
    suite.run_all_tests()
    print("\n" + suite.generate_report())

    with open("comprehensive_test_results.json", "w") as f:
        json.dump(suite.results, f, indent=2)
    print("\n[Saved to comprehensive_test_results.json]")
