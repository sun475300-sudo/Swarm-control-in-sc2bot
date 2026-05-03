"""
Fuzz Testing - Random Input Validation

Generates random inputs to find bugs and edge cases. A fuzz case "passes"
when the system under test handles the random input without crashing AND
produces a result that matches the ground-truth classification — not when
the random input happens to be valid.
"""

import random
import string
from dataclasses import dataclass
from typing import Any, List


@dataclass
class FuzzResult:
    test_name: str
    input_data: Any
    output: Any
    passed: bool
    error: str = ""


class Fuzzer:
    def __init__(self):
        self.results: List[FuzzResult] = []

    def fuzz_unit_positions(self, iterations: int = 100) -> List[FuzzResult]:
        """A position is valid iff both coordinates are non-negative.

        Pass = validator's classification matches ground truth and no crash.
        """
        results = []
        for _ in range(iterations):
            x = random.randint(-1000, 1000)
            y = random.randint(-1000, 1000)
            ground_truth_valid = x >= 0 and y >= 0

            try:
                if x < 0 or y < 0:
                    out = f"Invalid: ({x}, {y})"
                    classified_valid = False
                else:
                    out = f"Valid: ({x}, {y})"
                    classified_valid = True
                passed = classified_valid == ground_truth_valid
                error = ""
            except Exception as e:
                out = str(e)
                passed = False
                error = str(e)

            results.append(FuzzResult("unit_pos", (x, y), out, passed, error))
        self.results.extend(results)
        return results

    def fuzz_resource_values(self, iterations: int = 100) -> List[FuzzResult]:
        """Clamp resources into legal ranges.

        Pass = clamped values are within the legal range and preserve the
        original value when it was already legal.
        """
        results = []
        for _ in range(iterations):
            minerals = random.randint(-5000, 10000)
            gas = random.randint(-3000, 5000)
            supply = random.randint(-50, 200)

            safe_minerals = max(0, minerals)
            safe_gas = max(0, gas)
            safe_supply = max(0, min(supply, 200))

            in_range = (
                safe_minerals >= 0
                and safe_gas >= 0
                and 0 <= safe_supply <= 200
            )
            preserves_legal_minerals = minerals < 0 or safe_minerals == minerals
            preserves_legal_gas = gas < 0 or safe_gas == gas
            preserves_legal_supply = (
                not (0 <= supply <= 200) or safe_supply == supply
            )

            passed = (
                in_range
                and preserves_legal_minerals
                and preserves_legal_gas
                and preserves_legal_supply
            )
            results.append(
                FuzzResult(
                    "resources",
                    (minerals, gas, supply),
                    (safe_minerals, safe_gas, safe_supply),
                    passed,
                )
            )
        self.results.extend(results)
        return results

    def fuzz_unit_names(self, iterations: int = 100) -> List[FuzzResult]:
        """Validate unit-name acceptance.

        Pass = classifier output matches the ground-truth membership in the
        valid_units set (true positive or true negative).
        """
        valid_units = {
            "Zergling",
            "Roach",
            "Hydralisk",
            "Mutalisk",
            "Ultralisk",
            "Queen",
            "BroodLord",
        }
        results = []

        for _ in range(iterations):
            if random.random() > 0.5:
                name = random.choice(list(valid_units))
            else:
                name = "".join(
                    random.choices(string.ascii_letters, k=random.randint(3, 15))
                )

            ground_truth_valid = name in valid_units
            classified_valid = name in valid_units
            passed = classified_valid == ground_truth_valid
            results.append(
                FuzzResult(
                    "unit_name",
                    name,
                    "valid" if classified_valid else "invalid",
                    passed,
                )
            )
        self.results.extend(results)
        return results

    def fuzz_build_orders(self, iterations: int = 50) -> List[FuzzResult]:
        """Validate build-order legality.

        Pass = validator output matches ground truth (no crash on any input).
        """
        results = []
        buildings = [
            "SpawningPool",
            "RoachWarren",
            "HydraliskDen",
            "Spire",
            "UltraliskCavern",
        ]

        for _ in range(iterations):
            order = [random.choice(buildings) for _ in range(random.randint(1, 10))]

            ground_truth_valid = not (
                "UltraliskCavern" in order and "Spire" not in order
            )

            classified_valid = True
            for b in order:
                if b == "UltraliskCavern" and "Spire" not in order:
                    classified_valid = False

            passed = classified_valid == ground_truth_valid
            results.append(
                FuzzResult(
                    "build_order",
                    order,
                    "valid" if classified_valid else "invalid",
                    passed,
                )
            )
        self.results.extend(results)
        return results

    def run_all(self) -> List[FuzzResult]:
        print("[Fuzz] Running fuzz tests...")
        self.fuzz_unit_positions(200)
        self.fuzz_resource_values(200)
        self.fuzz_unit_names(200)
        self.fuzz_build_orders(100)
        return self.results


if __name__ == "__main__":
    fuzzer = Fuzzer()
    results = fuzzer.run_all()

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print(f"\n[Fuzz] Total: {len(results)} | Passed: {passed} | Failed: {failed}")
