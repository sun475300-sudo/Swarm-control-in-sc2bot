# -*- coding: utf-8 -*-
"""Unit tests for FormationController and swarm behavior modules."""

import math
import sys
import os

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.bot.swarm.formation_controller import FormationController, _to_xy


# ---------------------------------------------------------------------------
# _to_xy helper
# ---------------------------------------------------------------------------

class TestToXy:
    def test_tuple(self):
        assert _to_xy((1.0, 2.0)) == (1.0, 2.0)

    def test_list(self):
        assert _to_xy([3.0, 4.0]) == (3.0, 4.0)

    def test_object_with_xy(self):
        class Pos:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        assert _to_xy(Pos(5.0, 6.0)) == (5.0, 6.0)

    def test_integer_coords_cast_to_float(self):
        x, y = _to_xy((3, 7))
        assert isinstance(x, float)
        assert isinstance(y, float)


# ---------------------------------------------------------------------------
# FormationController — maintain_formation return length
# ---------------------------------------------------------------------------

class TestMaintainFormationLength:
    def test_empty_returns_empty(self):
        fc = FormationController()
        assert fc.maintain_formation([]) == []

    def test_single_unit(self):
        fc = FormationController()
        result = fc.maintain_formation([(0, 0)])
        assert len(result) == 1

    def test_matches_input_length(self):
        fc = FormationController()
        positions = [(i, i) for i in range(8)]
        assert len(fc.maintain_formation(positions)) == 8


# ---------------------------------------------------------------------------
# Circular formation
# ---------------------------------------------------------------------------

class TestCircularFormation:
    def test_all_targets_on_circle(self):
        """Each target should be exactly formation_radius away from centroid."""
        fc = FormationController(formation_radius=3.0, formation_type="circle")
        positions = [(0, 0), (2, 0), (1, 2)]
        centroid = (1.0, 2.0 / 3.0)
        targets = fc.maintain_formation(positions)
        for tx, ty in targets:
            dist = math.sqrt((tx - centroid[0]) ** 2 + (ty - centroid[1]) ** 2)
            assert abs(dist - 3.0) < 1e-9

    def test_angles_evenly_spaced(self):
        """For n units the angular gap between slots should be 2π/n."""
        fc = FormationController(formation_radius=5.0, formation_type="circle")
        n = 6
        positions = [(float(i), 0.0) for i in range(n)]
        centroid_x = sum(i for i in range(n)) / n
        targets = fc.maintain_formation(positions)
        angles = [
            math.atan2(ty - 0.0, tx - centroid_x)
            for tx, ty in targets
        ]
        angles.sort()
        expected_gap = 2.0 * math.pi / n
        for i in range(1, len(angles)):
            assert abs(angles[i] - angles[i - 1] - expected_gap) < 1e-9


# ---------------------------------------------------------------------------
# Line formation
# ---------------------------------------------------------------------------

class TestLineFormation:
    def test_all_on_same_y(self):
        """All line targets share the centroid y-coordinate."""
        fc = FormationController(formation_radius=2.0, formation_type="line")
        positions = [(0, 0), (4, 0), (2, 4)]
        centroid_y = 4.0 / 3.0
        targets = fc.maintain_formation(positions)
        for _, ty in targets:
            assert abs(ty - centroid_y) < 1e-9

    def test_uniform_x_spacing(self):
        """Adjacent slots are exactly formation_radius apart in x."""
        fc = FormationController(formation_radius=3.0, formation_type="line")
        positions = [(0, 0), (1, 0), (2, 0), (3, 0)]
        targets = fc.maintain_formation(positions)
        xs = sorted(tx for tx, _ in targets)
        for i in range(1, len(xs)):
            assert abs(xs[i] - xs[i - 1] - 3.0) < 1e-9

    def test_centred_on_centroid_x(self):
        """The line should be centred on the centroid x."""
        fc = FormationController(formation_radius=1.0, formation_type="line")
        positions = [(0, 0), (2, 0)]  # centroid x = 1.0
        targets = fc.maintain_formation(positions)
        xs = [tx for tx, _ in targets]
        assert abs((min(xs) + max(xs)) / 2 - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Spread formation
# ---------------------------------------------------------------------------

class TestSpreadFormation:
    def test_correct_count(self):
        fc = FormationController(formation_radius=2.0, formation_type="spread")
        positions = [(float(i), 0.0) for i in range(9)]
        targets = fc.maintain_formation(positions)
        assert len(targets) == 9

    def test_grid_spacing(self):
        """Adjacent grid slots differ by exactly formation_radius."""
        radius = 2.0
        fc = FormationController(formation_radius=radius, formation_type="spread")
        # 4 units → 2×2 grid
        positions = [(0, 0), (1, 0), (0, 1), (1, 1)]
        targets = fc.maintain_formation(positions)
        xs = sorted(set(round(tx, 6) for tx, _ in targets))
        ys = sorted(set(round(ty, 6) for _, ty in targets))
        assert len(xs) == 2
        assert len(ys) == 2
        assert abs(xs[1] - xs[0] - radius) < 1e-9
        assert abs(ys[1] - ys[0] - radius) < 1e-9


# ---------------------------------------------------------------------------
# Centroid invariant
# ---------------------------------------------------------------------------

class TestCentroidInvariant:
    """Formation centroid should match input centroid regardless of type."""

    @pytest.mark.parametrize("formation_type", ["circle", "line", "spread"])
    def test_centroid_matches(self, formation_type):
        fc = FormationController(formation_radius=4.0, formation_type=formation_type)
        positions = [(1.0, 2.0), (3.0, 4.0), (5.0, 0.0)]
        in_cx = sum(p[0] for p in positions) / len(positions)
        in_cy = sum(p[1] for p in positions) / len(positions)
        targets = fc.maintain_formation(positions)
        out_cx = sum(tx for tx, _ in targets) / len(targets)
        out_cy = sum(ty for _, ty in targets) / len(targets)
        assert abs(out_cx - in_cx) < 1e-9
        assert abs(out_cy - in_cy) < 1e-9


# ---------------------------------------------------------------------------
# Behavior module smoke tests
# ---------------------------------------------------------------------------

class TestBehaviorModules:
    """Verify every behavior module can be imported and ticked."""

    @pytest.mark.parametrize("num", range(1, 31))
    def test_behavior_tick(self, num):
        import importlib
        mod = importlib.import_module(f"src.bot.swarm.behavior_{num:02d}")
        cls = getattr(mod, f"Behavior{num:02d}")
        instance = cls()
        positions = [(float(i), float(i)) for i in range(4)]
        result = instance.tick(positions)
        assert isinstance(result, list)
        assert len(result) == len(positions)

    @pytest.mark.parametrize("num", range(1, 31))
    def test_behavior_repr(self, num):
        import importlib
        mod = importlib.import_module(f"src.bot.swarm.behavior_{num:02d}")
        cls = getattr(mod, f"Behavior{num:02d}")
        instance = cls()
        assert f"Behavior{num:02d}" in repr(instance)
