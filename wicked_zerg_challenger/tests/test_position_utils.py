# -*- coding: utf-8 -*-
"""
Regression tests for utils/position_utils.py.

Covers:
- get_center_position / get_weighted_center correctness (the logic that used
  to be duplicated inline across combat_manager.py, micro_controller.py,
  combat_phase_controller.py, combat/micro_combat.py, combat/infestor_tactics.py,
  combat/combat_execution.py, combat/expansion_defense.py,
  battle_preparation_system.py and idle_unit_manager.py).
- The module must import cleanly even when the `sc2` package isn't installed,
  matching every other module in this codebase's sc2-optional convention.
"""

import importlib.util
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

POSITION_UTILS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "utils", "position_utils.py")
)


def _load_position_utils_from_file():
    """Load position_utils.py by file path, bypassing the `utils` package name.

    This repo has two unrelated top-level `utils` packages (repo-root, used by
    jarvis_features, and wicked_zerg_challenger/utils). Whichever gets cached
    in sys.modules["utils"] first "wins" for every later `from utils import x`
    in the same process (see REMAINING_ISSUES.md). Loading by file path sidesteps
    that ambiguity entirely so this test is correct regardless of suite ordering.
    """
    spec = importlib.util.spec_from_file_location(
        "position_utils_under_test", POSITION_UTILS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeUnit:
    def __init__(self, x, y, health=100, supply_cost=1):
        self.position = FakePoint(x, y)
        self.health = health
        self.supply_cost = supply_cost


class FakePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class TestGetCenterPosition(unittest.TestCase):
    def setUp(self):
        self.mod = _load_position_utils_from_file()

    def test_empty_returns_origin(self):
        center = self.mod.get_center_position([])
        self.assertEqual((center.x, center.y), (0, 0))

    def test_single_unit_returns_its_position(self):
        unit = FakeUnit(3, 4)
        center = self.mod.get_center_position([unit])
        self.assertIs(center, unit.position)

    def test_geometric_center_of_multiple_units(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0), FakeUnit(5, 10)]
        center = self.mod.get_center_position(units)
        self.assertAlmostEqual(center.x, 5.0)
        self.assertAlmostEqual(center.y, 10 / 3)


class TestGetWeightedCenter(unittest.TestCase):
    def setUp(self):
        self.mod = _load_position_utils_from_file()

    def test_health_weighted_biases_toward_higher_health(self):
        units = [FakeUnit(0, 0, health=1), FakeUnit(10, 0, health=99)]
        center = self.mod.get_weighted_center(units, weight_by_health=True)
        self.assertGreater(center.x, 5.0)

    def test_falls_back_to_geometric_center_when_total_health_zero(self):
        units = [FakeUnit(0, 0, health=0), FakeUnit(10, 0, health=0)]
        center = self.mod.get_weighted_center(units, weight_by_health=True)
        self.assertAlmostEqual(center.x, 5.0)


class TestImportsWithoutSc2Package(unittest.TestCase):
    """position_utils must degrade gracefully like its sibling utils modules."""

    def test_module_imports_when_sc2_is_unavailable(self):
        blocked = {
            name for name in sys.modules if name == "sc2" or name.startswith("sc2.")
        }
        saved = {name: sys.modules.pop(name) for name in blocked}

        class _BlockSc2:
            def find_module(self, name, path=None):
                if name == "sc2" or name.startswith("sc2."):
                    return self
                return None

            def load_module(self, name):
                raise ImportError(f"sc2 blocked for test: {name}")

        blocker = _BlockSc2()
        sys.meta_path.insert(0, blocker)
        try:
            module = _load_position_utils_from_file()
            center = module.get_center_position([FakeUnit(2, 4)])
            self.assertEqual((center.x, center.y), (2, 4))
        finally:
            sys.meta_path.remove(blocker)
            for name, mod in saved.items():
                sys.modules[name] = mod


if __name__ == "__main__":
    unittest.main()
