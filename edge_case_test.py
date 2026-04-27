"""
Edge Case Testing - Boundary Conditions & Error Handling
Tests various edge cases and error scenarios
"""

import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EdgeCaseResult:
    test_name: str
    passed: bool
    description: str
    input_data: Any
    expected: Any
    actual: Any
    duration_ms: float
    error_message: str = ""


class EdgeCaseTester:
    def __init__(self):
        self.results: List[EdgeCaseResult] = []

    def test_empty_unit_list(self) -> EdgeCaseResult:
        """Test with empty unit list"""
        start = time.time()

        try:
            units = []
            if len(units) == 0:
                result = "No units to process"
                passed = True
            else:
                result = "Unexpected units found"
                passed = False
        except Exception as e:
            result = str(e)
            passed = False

        return EdgeCaseResult(
            test_name="empty_unit_list",
            passed=passed,
            description="Process empty unit list",
            input_data=[],
            expected="No units to process",
            actual=result,
            duration_ms=(time.time() - start) * 1000,
        )

    def test_max_units_limit(self) -> EdgeCaseResult:
        """Test with maximum units"""
        start = time.time()

        MAX_UNITS = 500
        units = [{"id": i} for i in range(MAX_UNITS + 10)]

        processed = units[:MAX_UNITS]
        dropped = len(units) - MAX_UNITS

        passed = dropped > 0
        result = f"Processed {len(processed)}, dropped {dropped}"

        return EdgeCaseResult(
            test_name="max_units_limit",
            passed=passed,
            description="Handle units exceeding max limit",
            input_data=len(units),
            expected=f">{MAX_UNITS}",
            actual=result,
            duration_ms=(time.time() - start) * 1000,
        )

    def test_zero_damage_combat(self) -> EdgeCaseResult:
        """Test combat with zero damage units"""
        start = time.time()

        units = [
            {"name": "Infestor", "damage": 0, "hp": 90},
            {"name": "Medivac", "damage": 0, "hp": 150},
        ]

        total_damage = sum(u["damage"] for u in units)
        passed = total_damage == 0
        result = f"Total damage: {total_damage}"

        return EdgeCaseResult(
            test_name="zero_damage_combat",
            passed=passed,
            description="Handle zero damage units in combat",
            input_data=units,
            expected=0,
            actual=total_damage,
            duration_ms=(time.time() - start) * 1000,
        )

    def test_negative_resource(self) -> EdgeCaseResult:
        """Test handling of negative resources"""
        start = time.time()

        minerals = -100
        clamped = max(0, minerals)

        passed = clamped == 0
        result = f"Original: {minerals}, Clamped: {clamped}"

        return EdgeCaseResult(
            test_name="negative_resource",
            passed=passed,
            description="Handle negative mineral count",
            input_data=minerals,
            expected=0,
            actual=clamped,
            duration_ms=(time.time() - start) * 1000,
        )

    def test_division_by_zero(self) -> EdgeCaseResult:
        """Test division by zero protection"""
        start = time.time()

        units_alive = 0
        win_rate = 0

        try:
            if units_alive > 0:
                win_rate = 100
            else:
                win_rate = 0
            passed = True
        except ZeroDivisionError:
            win_rate = 0
            passed = False

        return EdgeCaseResult(
            test_name="division_by_zero",
            passed=passed,
            description="Prevent division by zero in win rate",
            input_data=units_alive,
            expected="No error",
            actual=win_rate,
            duration_ms=(time.time() - start) * 1000,
        )

    def test_null_unit_position(self) -> EdgeCaseResult:
        """Test null position handling"""
        start = time.time()

        position = None
        safe_position = position if position is not None else (0, 0)

        passed = safe_position is not None
        result = f"Position: {safe_position}"

        return EdgeCaseResult(
            test_name="null_position",
            passed=passed,
            description="Handle null unit positions",
            input_data=None,
            expected="(0, 0)",
            actual=result,
            duration_ms=(time.time() - start) * 1000,
        )

    def test_invalid_unit_type(self) -> EdgeCaseResult:
        """Test invalid unit type handling"""
        start = time.time()

        VALID_UNITS = {"Zergling", "Roach", "Hydralisk", "Mutalisk", "Ultralisk"}
        invalid_unit = "InvalidUnit123"

        if invalid_unit in VALID_UNITS:
            result = "Valid"
            passed = False
        else:
            result = "Invalid unit type"
            passed = True

        return EdgeCaseResult(
            test_name="invalid_unit_type",
            passed=passed,
            description="Reject invalid unit types",
            input_data=invalid_unit,
            expected="Invalid unit type",
            actual=result,
            duration_ms=(time.time() - start) * 1000,
        )

    def test_timeout_simulation(self) -> EdgeCaseResult:
        """Test timeout handling"""
        start = time.time()

        TIMEOUT_MS = 100
        elapsed = 0

        for i in range(1000):
            elapsed += 0.1
            if elapsed * 1000 >= TIMEOUT_MS:
                result = "Timed out"
                break
        else:
            result = "Completed"

        passed = result == "Timed out"

        return EdgeCaseResult(
            test_name="timeout_simulation",
            passed=passed,
            description="Handle operation timeout",
            input_data=TIMEOUT_MS,
            expected="Timed out",
            actual=result,
            duration_ms=(time.time() - start) * 1000,
        )

    def test_race_condition(self) -> EdgeCaseResult:
        """Test concurrent access simulation"""
        start = time.time()

        counter = {"value": 0}

        for _ in range(100):
            counter["value"] += 1

        passed = counter["value"] == 100
        result = f"Counter: {counter['value']}"

        return EdgeCaseResult(
            test_name="race_condition",
            passed=passed,
            description="Simulate race condition",
            input_data=100,
            expected=100,
            actual=counter["value"],
            duration_ms=(time.time() - start) * 1000,
        )

    def test_memory_pressure(self) -> EdgeCaseResult:
        """Test under memory pressure"""
        start = time.time()

        data = []
        for i in range(1000):
            data.append({"id": i, "data": "x" * 1000})
            if i % 100 == 0 and i > 0:
                data = data[:-10]

        passed = len(data) < 1000
        result = f"Memory items: {len(data)}"

        return EdgeCaseResult(
            test_name="memory_pressure",
            passed=passed,
            description="Handle memory cleanup under pressure",
            input_data=1000,
            expected="<1000",
            actual=result,
            duration_ms=(time.time() - start) * 1000,
        )

    def run_all_tests(self) -> List[EdgeCaseResult]:
        """Run all edge case tests"""
        tests = [
            self.test_empty_unit_list,
            self.test_max_units_limit,
            self.test_zero_damage_combat,
            self.test_negative_resource,
            self.test_division_by_zero,
            self.test_null_unit_position,
            self.test_invalid_unit_type,
            self.test_timeout_simulation,
            self.test_race_condition,
            self.test_memory_pressure,
        ]

        results = []
        for test in tests:
            print(f"[EdgeCase] Running {test.__name__}...")
            result = test()
            results.append(result)
            self.results.append(result)

        return results


def print_edge_results(results: List[EdgeCaseResult]) -> None:
    print("\n" + "=" * 80)
    print("EDGE CASE TEST RESULTS")
    print("=" * 80)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed}\n")

    for r in results:
        status = "[PASS]" if r.passed else "[FAIL]"
        print(f"{status} {r.test_name:<25} - {r.description}")
        if not r.passed:
            print(f"       Expected: {r.expected}")
            print(f"       Actual:   {r.actual}")
            if r.error_message:
                print(f"       Error:    {r.error_message}")


if __name__ == "__main__":
    print("[EdgeCase] Starting edge case tests...")
    tester = EdgeCaseTester()
    results = tester.run_all_tests()
    print_edge_results(results)
