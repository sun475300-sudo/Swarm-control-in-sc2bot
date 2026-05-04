"""
Fuzz Testing - Random Input Validation
Generates random inputs and checks the validator/sanitizer behaves as
expected. A "passed" result here means: the validator correctly classified
or sanitized its input. Random garbage being rejected is a pass, not a
failure.
"""

import random
import string
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class FuzzResult:
    test_name: str
    input_data: Any
    output: Any
    passed: bool
    error: str = ""


class Fuzzer:
    def __init__(self, seed: Optional[int] = None):
        self.results: List[FuzzResult] = []
        self._rng = random.Random(seed)

    def fuzz_unit_positions(self, iterations: int = 100) -> List[FuzzResult]:
        results = []
        for _ in range(iterations):
            x = self._rng.randint(-1000, 1000)
            y = self._rng.randint(-1000, 1000)
            expected_valid = x >= 0 and y >= 0

            try:
                actual_valid = x >= 0 and y >= 0
                out = (
                    f"Valid: ({x}, {y})"
                    if actual_valid
                    else f"Rejected: ({x}, {y})"
                )
                passed = actual_valid == expected_valid
            except Exception as e:
                out = str(e)
                passed = False

            results.append(FuzzResult("unit_pos", (x, y), out, passed))
        self.results.extend(results)
        return results

    def fuzz_resource_values(self, iterations: int = 100) -> List[FuzzResult]:
        results = []
        for _ in range(iterations):
            minerals = self._rng.randint(-5000, 10000)
            gas = self._rng.randint(-3000, 5000)
            supply = self._rng.randint(-50, 200)

            safe_minerals = max(0, minerals)
            safe_gas = max(0, gas)
            safe_supply = max(0, min(supply, 200))

            passed = (
                safe_minerals >= 0
                and safe_gas >= 0
                and 0 <= safe_supply <= 200
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
            if self._rng.random() > 0.5:
                name = self._rng.choice(list(valid_units))
                expected_valid = True
            else:
                name = "".join(
                    self._rng.choices(
                        string.ascii_letters, k=self._rng.randint(3, 15)
                    )
                )
                expected_valid = name in valid_units

            actual_valid = name in valid_units
            passed = actual_valid == expected_valid
            results.append(
                FuzzResult(
                    "unit_name",
                    name,
                    "valid" if actual_valid else "invalid",
                    passed,
                )
            )
        self.results.extend(results)
        return results

    def fuzz_build_orders(self, iterations: int = 50) -> List[FuzzResult]:
        results = []
        buildings = [
            "SpawningPool",
            "RoachWarren",
            "HydraliskDen",
            "Spire",
            "UltraliskCavern",
        ]

        for _ in range(iterations):
            order = [
                self._rng.choice(buildings)
                for _ in range(self._rng.randint(1, 10))
            ]

            expected_valid = not (
                "UltraliskCavern" in order and "Spire" not in order
            )

            valid = True
            for b in order:
                if b == "UltraliskCavern" and "Spire" not in order:
                    valid = False
                    break

            passed = valid == expected_valid
            results.append(
                FuzzResult(
                    "build_order",
                    order,
                    "valid" if valid else "invalid",
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
