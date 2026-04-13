"""
Test Comparison Analysis - Compare test results across configurations
Analyzes unit combinations, scenarios, and provides detailed comparison reports
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics


@dataclass
class UnitComboResult:
    unit_combo: str
    tests_run: int
    passed: int
    failed: int
    win_rate: float
    avg_duration: float
    std_deviation: float
    synergy_score: float


@dataclass
class ScenarioComparison:
    scenario: str
    before: Dict[str, Any]
    after: Dict[str, Any]
    improvement: float
    details: List[Dict[str, Any]] = field(default_factory=list)


class TestComparisonAnalyzer:
    def __init__(self, data_dir: str = "test_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.history_file = self.data_dir / "comparison_history.json"
        self.results = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        if self.history_file.exists():
            with open(self.history_file, "r") as f:
                return json.load(f)
        return []

    def _save_history(self) -> None:
        with open(self.history_file, "w") as f:
            json.dump(self.results[-1000:], f, indent=2)

    def analyze_unit_combinations(self, results: List[Dict]) -> List[UnitComboResult]:
        combo_data = defaultdict(lambda: {"passed": 0, "failed": 0, "durations": []})

        for r in results:
            combo = r.get("unit_combo", "Unknown")
            if r.get("passed"):
                combo_data[combo]["passed"] += 1
            else:
                combo_data[combo]["failed"] += 1
            combo_data[combo]["durations"].append(r.get("duration_ms", 0))

        results = []
        for combo, data in combo_data.items():
            total = data["passed"] + data["failed"]
            win_rate = (data["passed"] / total * 100) if total > 0 else 0
            durations = data["durations"]
            avg_dur = statistics.mean(durations) if durations else 0
            std_dev = statistics.stdev(durations) if len(durations) > 1 else 0

            synergy = self._calculate_synergy_score(combo, win_rate, avg_dur)

            results.append(
                UnitComboResult(
                    unit_combo=combo,
                    tests_run=total,
                    passed=data["passed"],
                    failed=data["failed"],
                    win_rate=win_rate,
                    avg_duration=avg_dur,
                    std_deviation=std_dev,
                    synergy_score=synergy,
                )
            )

        return sorted(results, key=lambda x: x.synergy_score, reverse=True)

    def _calculate_synergy_score(
        self, combo: str, win_rate: float, avg_duration: float
    ) -> float:
        base_score = win_rate
        speed_bonus = max(0, (5000 - avg_duration) / 100)
        complexity_bonus = len(combo.split("+")) * 2
        return base_score + speed_bonus + complexity_bonus

    def compare_before_after(
        self, before_results: List[Dict], after_results: List[Dict]
    ) -> Dict[str, Any]:
        before_stats = self._calculate_stats(before_results)
        after_stats = self._calculate_stats(after_results)

        improvement = {
            "win_rate_change": after_stats["win_rate"] - before_stats["win_rate"],
            "avg_duration_change": after_stats["avg_duration"]
            - before_stats["avg_duration"],
            "tests_improved": sum(1 for a in after_results if a.get("passed")),
            "tests_degraded": sum(
                1
                for a in after_results
                if not a.get("passed") and self._was_passed_before(a, before_results)
            ),
        }

        return {
            "before": before_stats,
            "after": after_stats,
            "improvement": improvement,
        }

    def _calculate_stats(self, results: List[Dict]) -> Dict[str, float]:
        if not results:
            return {"win_rate": 0, "avg_duration": 0, "total_tests": 0}

        passed = sum(1 for r in results if r.get("passed"))
        durations = [r.get("duration_ms", 0) for r in results]

        return {
            "win_rate": (passed / len(results) * 100) if results else 0,
            "avg_duration": statistics.mean(durations) if durations else 0,
            "total_tests": len(results),
        }

    def _was_passed_before(self, result: Dict, before_results: List[Dict]) -> bool:
        for br in before_results:
            if br.get("test_name") == result.get("test_name"):
                return br.get("passed", False)
        return False

    def generate_comparison_report(
        self, before_results: List[Dict], after_results: List[Dict]
    ) -> str:
        comparison = self.compare_before_after(before_results, after_results)

        report = f"""
================================================================================
                    TEST COMPARISON ANALYSIS REPORT
================================================================================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

BEFORE CONFIGURATION:
  - Total Tests: {comparison["before"]["total_tests"]}
  - Win Rate: {comparison["before"]["win_rate"]:.1f}%
  - Avg Duration: {comparison["before"]["avg_duration"]:.0f}ms

AFTER CONFIGURATION:
  - Total Tests: {comparison["after"]["total_tests"]}
  - Win Rate: {comparison["after"]["win_rate"]:.1f}%
  - Avg Duration: {comparison["after"]["avg_duration"]:.0f}ms

IMPROVEMENT:
  - Win Rate Change: {comparison["improvement"]["win_rate_change"]:+.1f}%
  - Duration Change: {comparison["improvement"]["avg_duration_change"]:+.0f}ms
  - Tests Improved: {comparison["improvement"]["tests_improved"]}
  - Tests Degraded: {comparison["improvement"]["tests_degraded"]}

STATUS: {"[IMPROVED]" if comparison["improvement"]["win_rate_change"] > 0 else "[NEEDS WORK]"}

================================================================================
"""
        return report

    def save_snapshot(self, name: str, results: List[Dict]) -> None:
        snapshot = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "stats": self._calculate_stats(results),
        }
        self.results.append(snapshot)
        self._save_history()

    def get_snapshots(self) -> List[Dict]:
        return self.results

    def compare_snapshots(self, name1: str, name2: str) -> Dict[str, Any]:
        s1 = next((s for s in self.results if s["name"] == name1), None)
        s2 = next((s for s in self.results if s["name"] == name2), None)

        if not s1 or not s2:
            return {"error": "Snapshot not found"}

        return self.compare_before_after(s1["results"], s2["results"])


def run_comparison_demo():
    print("[TestComparisonAnalyzer] Running comparison demo...")

    before_results = [
        {
            "test_name": "rush_1",
            "unit_combo": "Zergling+Baneling",
            "passed": True,
            "win_rate": 75,
            "duration_ms": 1200,
        },
        {
            "test_name": "rush_2",
            "unit_combo": "Zergling+Baneling",
            "passed": True,
            "win_rate": 80,
            "duration_ms": 1100,
        },
        {
            "test_name": "macro_1",
            "unit_combo": "Roach+Hydralisk",
            "passed": False,
            "win_rate": 60,
            "duration_ms": 3500,
        },
        {
            "test_name": "harass_1",
            "unit_combo": "Mutalisk",
            "passed": True,
            "win_rate": 85,
            "duration_ms": 2000,
        },
    ]

    after_results = [
        {
            "test_name": "rush_1",
            "unit_combo": "Zergling+Baneling",
            "passed": True,
            "win_rate": 90,
            "duration_ms": 1000,
        },
        {
            "test_name": "rush_2",
            "unit_combo": "Zergling+Baneling",
            "passed": True,
            "win_rate": 92,
            "duration_ms": 950,
        },
        {
            "test_name": "macro_1",
            "unit_combo": "Roach+Hydralisk",
            "passed": True,
            "win_rate": 78,
            "duration_ms": 3200,
        },
        {
            "test_name": "harass_1",
            "unit_combo": "Mutalisk",
            "passed": True,
            "win_rate": 88,
            "duration_ms": 1800,
        },
    ]

    analyzer = TestComparisonAnalyzer()

    print("\n[Unit Combination Analysis]")
    combos = analyzer.analyze_unit_combinations(after_results)
    for combo in combos:
        print(
            f"  {combo.unit_combo}: {combo.win_rate:.1f}% win rate (synergy: {combo.synergy_score:.1f})"
        )

    print(analyzer.generate_comparison_report(before_results, after_results))


if __name__ == "__main__":
    run_comparison_demo()
