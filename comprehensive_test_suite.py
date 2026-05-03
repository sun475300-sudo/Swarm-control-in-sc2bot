"""
Comprehensive Test Suite - Continuous Testing

Runs all available test categories and aggregates real results from the
existing simulation/fuzz runners (no hard-coded mock numbers).
"""

import json
import time
from datetime import datetime
from typing import Any, Dict


class ComprehensiveTestSuite:
    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.start_time = time.time()

    @staticmethod
    def _measure(func):
        t0 = time.time()
        out = func()
        elapsed_ms = int((time.time() - t0) * 1000)
        if isinstance(out, dict):
            out.setdefault("duration", elapsed_ms)
        return out

    def run_unit_tests(self) -> Dict[str, Any]:
        """Unit combination tests delegated to unit_combo_test.

        TestResult exposes win_rate; pass = win_rate > 50%.
        """
        try:
            from unit_combo_test import run_all_combinations

            results = run_all_combinations()
            tests = len(results)
            passed = sum(1 for r in results if getattr(r, "win_rate", 0) > 50)
            return {"tests": tests, "passed": passed}
        except Exception as e:
            return {"tests": 0, "passed": 0, "error": str(e)}

    def run_stress_tests(self) -> Dict[str, Any]:
        try:
            from large_scale_test import LargeScaleTestRunner

            runner = LargeScaleTestRunner()
            r = runner.test_combat_simulation_extended()
            return {"tests": r.iterations, "passed": r.passed}
        except Exception as e:
            return {"tests": 0, "passed": 0, "error": str(e)}

    def run_edge_case_tests(self) -> Dict[str, Any]:
        try:
            from edge_case_test import EdgeCaseTester

            t = EdgeCaseTester()
            results = t.run_all_tests()
            tests = len(results)
            passed = sum(1 for r in results if getattr(r, "passed", False))
            return {"tests": tests, "passed": passed}
        except Exception as e:
            return {"tests": 0, "passed": 0, "error": str(e)}

    def run_integration_tests(self) -> Dict[str, Any]:
        try:
            from integration_test import IntegrationTestRunner

            t = IntegrationTestRunner()
            results = t.run_all_tests()
            tests = len(results)
            passed = sum(1 for r in results if getattr(r, "passed", False))
            return {"tests": tests, "passed": passed}
        except Exception as e:
            return {"tests": 0, "passed": 0, "error": str(e)}

    def run_benchmark_tests(self) -> Dict[str, Any]:
        try:
            from large_scale_test import LargeScaleTestRunner

            runner = LargeScaleTestRunner()
            r = runner.test_timing_attacks_extended()
            return {"tests": r.iterations, "passed": r.passed}
        except Exception as e:
            return {"tests": 0, "passed": 0, "error": str(e)}

    def run_multi_env_tests(self) -> Dict[str, Any]:
        try:
            from multi_env_test import MultiEnvironmentTester

            t = MultiEnvironmentTester()
            results = t.test_all_maps()
            tests = len(results)
            passed = sum(1 for r in results if getattr(r, "passed", False))
            return {"tests": tests, "passed": passed}
        except Exception as e:
            return {"tests": 0, "passed": 0, "error": str(e)}

    def run_matchup_tests(self) -> Dict[str, Any]:
        """MatchupResult exposes win_rate; pass = win_rate > 50%."""
        try:
            from matchup_test import OpponentAnalyzer

            t = OpponentAnalyzer()
            results = t.test_all_matchups()
            tests = len(results)
            passed = sum(1 for r in results if getattr(r, "win_rate", 0) > 50)
            return {"tests": tests, "passed": passed}
        except Exception as e:
            return {"tests": 0, "passed": 0, "error": str(e)}

    def run_fuzz_tests(self) -> Dict[str, Any]:
        try:
            from fuzz_test import Fuzzer

            fuzzer = Fuzzer()
            results = fuzzer.run_all()
            tests = len(results)
            passed = sum(1 for r in results if r.passed)
            return {"tests": tests, "passed": passed}
        except Exception as e:
            return {"tests": 0, "passed": 0, "error": str(e)}

    def run_regression_tests(self) -> Dict[str, Any]:
        try:
            from regression_test import RegressionTestSuite

            t = RegressionTestSuite()
            results = t.run_all()
            tests = len(results)
            passed = sum(1 for r in results if getattr(r, "passed", False))
            return {"tests": tests, "passed": passed}
        except Exception as e:
            return {"tests": 0, "passed": 0, "error": str(e)}

    def run_all_tests(self) -> Dict[str, Any]:
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
            result = self._measure(test_func)
            self.results[name] = result
            total_tests += result.get("tests", 0)
            total_passed += result.get("passed", 0)
            err = f" ERROR: {result['error']}" if result.get("error") else ""
            print(
                f"  {result.get('passed', 0)}/{result.get('tests', 0)} "
                f"passed in {result.get('duration', 0)}ms{err}"
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
            lines.append(
                f"  {name:<25} {result.get('passed', 0):>4}/"
                f"{result.get('tests', 0):<4} passed"
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
