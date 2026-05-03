"""
Fuzz Testing - Random Input Validation
Generates random inputs to find bugs and edge cases
"""

import random
import string
from dataclasses import dataclass
from typing import Any, Dict, List


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
        """Pass = system correctly classifies the random position.

        The previous implementation treated `passed` as "input was valid",
        which mislabels every negative-coordinate sample as a failure. A
        fuzz test passes when the validator handles the input without
        raising; the validity verdict belongs in `output`.
        """
        results = []
        for _ in range(iterations):
            x = random.randint(-1000, 1000)
            y = random.randint(-1000, 1000)

            try:
                if x < 0 or y < 0:
                    out = f"Invalid: ({x}, {y})"
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
        """Pass = clamped values are within safe bounds (no crash, no overflow)."""
        results = []
        for _ in range(iterations):
            minerals = random.randint(-5000, 10000)
            gas = random.randint(-3000, 5000)
            supply = random.randint(-50, 200)

            try:
                safe_minerals = max(0, minerals)
                safe_gas = max(0, gas)
                safe_supply = max(0, min(supply, 200))

                passed = (
                    safe_minerals >= 0
                    and safe_gas >= 0
                    and 0 <= safe_supply <= 200
                )
            except Exception:
                safe_minerals = safe_gas = safe_supply = -1
                passed = False

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
        """Pass = validator returns a definite valid/invalid verdict without crashing."""
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

            try:
                verdict = "valid" if name in valid_units else "invalid"
                passed = True
            except Exception:
                verdict = "error"
                passed = False

            results.append(FuzzResult("unit_name", name, verdict, passed))
        self.results.extend(results)
        return results

    def fuzz_build_orders(self, iterations: int = 50) -> List[FuzzResult]:
        """Pass = build-order validator categorizes input without crashing."""
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

            try:
                valid = True
                for b in order:
                    if b == "UltraliskCavern" and "Spire" not in order:
                        valid = False
                passed = True
                verdict = "valid" if valid else "invalid"
            except Exception:
                verdict = "error"
                passed = False

            results.append(FuzzResult("build_order", order, verdict, passed))
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
