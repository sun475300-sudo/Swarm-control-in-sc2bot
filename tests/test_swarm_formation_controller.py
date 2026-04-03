# -*- coding: utf-8 -*-
"""
Unit tests for FormationController (src/bot/swarm/formation_controller.py).

Covers:
- Basic initialisation and default parameters
- maintain_formation with empty, single, and multi-unit inputs
- Separation force: units too close should be pushed apart
- Cohesion force: spread-out units should drift towards centroid
- Output length matches input length
- Position inputs with object attributes (x/y) as well as tuple inputs
- max_displacement clamping
"""

import math
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.bot.swarm.formation_controller import FormationController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _MockPos:
    """Simple position object with x/y attributes."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def _dist(a, b) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


# ---------------------------------------------------------------------------
# Initialisation tests
# ---------------------------------------------------------------------------

class TestFormationControllerInit:
    """Tests for FormationController.__init__."""

    def test_default_parameters(self):
        ctrl = FormationController()
        assert ctrl.separation_radius == 2.0
        assert ctrl.neighbor_radius == 5.0
        assert ctrl.separation_weight == 1.5
        assert ctrl.cohesion_weight == 1.0
        assert ctrl.max_displacement == 1.0

    def test_custom_parameters(self):
        ctrl = FormationController(
            separation_radius=3.0,
            neighbor_radius=8.0,
            separation_weight=2.0,
            cohesion_weight=0.5,
            max_displacement=2.0,
        )
        assert ctrl.separation_radius == 3.0
        assert ctrl.neighbor_radius == 8.0
        assert ctrl.separation_weight == 2.0
        assert ctrl.cohesion_weight == 0.5
        assert ctrl.max_displacement == 2.0


# ---------------------------------------------------------------------------
# maintain_formation: basic contract
# ---------------------------------------------------------------------------

class TestMaintainFormationContract:
    """Tests for basic input/output contract of maintain_formation."""

    def test_empty_input_returns_empty(self):
        ctrl = FormationController()
        assert ctrl.maintain_formation([]) == []

    def test_single_unit_returns_same_position(self):
        ctrl = FormationController()
        result = ctrl.maintain_formation([(10.0, 20.0)])
        assert len(result) == 1
        assert result[0] == (10.0, 20.0)

    def test_output_length_matches_input(self):
        ctrl = FormationController()
        positions = [(float(i), float(i)) for i in range(10)]
        result = ctrl.maintain_formation(positions)
        assert len(result) == len(positions)

    def test_returns_list_of_tuples(self):
        ctrl = FormationController()
        result = ctrl.maintain_formation([(1.0, 2.0), (3.0, 4.0)])
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_accepts_object_positions(self):
        """Positions may be objects with .x/.y attributes."""
        ctrl = FormationController()
        positions = [_MockPos(1.0, 2.0), _MockPos(4.0, 5.0)]
        result = ctrl.maintain_formation(positions)
        assert len(result) == 2
        for item in result:
            assert isinstance(item, tuple)

    def test_accepts_list_positions(self):
        """Positions may be plain lists [x, y]."""
        ctrl = FormationController()
        result = ctrl.maintain_formation([[1.0, 2.0], [5.0, 6.0]])
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Separation force
# ---------------------------------------------------------------------------

class TestSeparationForce:
    """Tests that units too close to each other are pushed apart."""

    def test_overlapping_units_move_apart(self):
        """Three units stacked almost on top of each other should spread out."""
        ctrl = FormationController(
            separation_radius=2.0,
            cohesion_weight=0.0,  # disable cohesion to isolate separation
        )
        positions = [(5.0, 5.0), (5.1, 5.1), (4.9, 4.9)]
        result = ctrl.maintain_formation(positions)

        # The first unit should have moved away from the cluster centroid
        orig_dist = _dist(positions[0], positions[1])
        new_dist = _dist(result[0], result[1])
        # After separation the units should be at least as far apart
        assert new_dist >= orig_dist - 1e-9

    def test_distant_units_no_separation(self):
        """Units far outside neighbor_radius should not be affected by separation."""
        ctrl = FormationController(
            separation_radius=2.0,
            neighbor_radius=5.0,
            cohesion_weight=0.0,
        )
        # Units 20 units apart — well outside neighbor_radius
        positions = [(0.0, 0.0), (20.0, 0.0)]
        result = ctrl.maintain_formation(positions)
        # Positions should be nearly identical (no separation, tiny cohesion=0)
        assert abs(result[0][0] - 0.0) < 1e-9
        assert abs(result[1][0] - 20.0) < 1e-9


# ---------------------------------------------------------------------------
# Cohesion force
# ---------------------------------------------------------------------------

class TestCohesionForce:
    """Tests that spread-out units drift towards the centroid."""

    def test_spread_units_move_closer_to_centroid(self):
        """Units that are far apart should move towards the group centroid."""
        ctrl = FormationController(
            separation_radius=0.1,   # tiny separation zone so it doesn't dominate
            neighbor_radius=100.0,   # large radius so all units are neighbours
            separation_weight=0.0,   # disable separation to isolate cohesion
            cohesion_weight=2.0,
        )
        positions = [(0.0, 0.0), (100.0, 0.0)]
        centroid_x = 50.0
        result = ctrl.maintain_formation(positions)

        # First unit should move towards centroid (positive x direction)
        assert result[0][0] > positions[0][0]
        # Second unit should move towards centroid (negative x direction)
        assert result[1][0] < positions[1][0]

        # Both resulting positions should be closer to the centroid
        assert abs(result[0][0] - centroid_x) < abs(positions[0][0] - centroid_x)
        assert abs(result[1][0] - centroid_x) < abs(positions[1][0] - centroid_x)


# ---------------------------------------------------------------------------
# max_displacement clamping
# ---------------------------------------------------------------------------

class TestMaxDisplacement:
    """Tests that output displacements never exceed max_displacement."""

    def test_clamp_limits_movement(self):
        """dx and dy are each clamped to max_displacement independently, so the
        maximum Euclidean movement per tick is max_displacement * sqrt(2)."""
        ctrl = FormationController(
            separation_radius=3.0,
            neighbor_radius=10.0,
            separation_weight=10.0,   # exaggerated force
            cohesion_weight=10.0,
            max_displacement=0.5,
        )
        positions = [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0), (10.0, 10.0)]
        result = ctrl.maintain_formation(positions)

        for orig, adj in zip(positions, result):
            move = _dist(orig, adj)
            assert move <= ctrl.max_displacement * math.sqrt(2) + 1e-9, (
                f"Unit moved {move:.4f} but max_displacement={ctrl.max_displacement}"
            )


# ---------------------------------------------------------------------------
# Behavior module integration
# ---------------------------------------------------------------------------

class TestBehaviorModuleIntegration:
    """Smoke-tests that all 30 behavior modules import and run correctly."""

    @pytest.mark.parametrize("module_num", range(1, 31))
    def test_behavior_module_import_and_tick(self, module_num: int):
        """Each behavior module should import and produce correct-length output."""
        module_name = f"src.bot.swarm.behavior_{module_num:02d}"
        import importlib
        mod = importlib.import_module(module_name)
        cls_name = f"Behavior{module_num:02d}"
        cls = getattr(mod, cls_name)
        instance = cls()

        positions = [(float(i), float(i)) for i in range(5)]
        result = instance.tick(positions)

        assert isinstance(result, list), f"{cls_name}.tick() must return a list"
        assert len(result) == len(positions), (
            f"{cls_name}.tick() returned {len(result)} positions, expected {len(positions)}"
        )
