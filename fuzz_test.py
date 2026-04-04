"""
Fuzz Testing - Random Input Validation
Generates random inputs to find bugs and edge cases
"""

import random
import string
from typing import Any, List, Dict
from dataclasses import dataclass


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
        results = []
        for _ in range(iterations):
            x = random.randint(-1000, 1000)
            y = random.randint(-1000, 1000)

            try:
                if x < 0 or y < 0:
                    out = f"Invalid: ({x}, {y})"
                    passed = False
                else:
                    out = f"Valid: ({x}, {y})"
                    passed = True
            except Exception as e:
                out = str(e)
                passed = False

            results.append(FuzzResult("unit_pos", (x, y), out, passed))
        self.results.extend(results)
        return results

    def fuzz_resource_values(self, iterations: int = 100) -> List[FuzzResult]:
        results = []
        for _ in range(iterations):
            minerals = random.randint(-5000, 10000)
            gas = random.randint(-3000, 5000)
            supply = random.randint(-50, 200)

            safe_minerals = max(0, minerals)
            safe_gas = max(0, gas)
            safe_supply = max(0, min(supply, 200))

            passed = safe_minerals == minerals and safe_gas == gas
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
            if random.random() > 0.5:
                name = random.choice(list(valid_units))
            else:
                name = "".join(
                    random.choices(string.ascii_letters, k=random.randint(3, 15))
                )

            passed = name in valid_units
            results.append(
                FuzzResult("unit_name", name, "valid" if passed else "invalid", passed)
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
            order = [random.choice(buildings) for _ in range(random.randint(1, 10))]

            valid = True
            for b in order:
                if b == "UltraliskCavern" and "Spire" not in order:
                    valid = False

            results.append(
                FuzzResult("build_order", order, "valid" if valid else "invalid", valid)
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
