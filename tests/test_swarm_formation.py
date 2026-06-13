"""Tests for src.bot.swarm.FormationController and behavior loader."""

import math

import pytest
from src.bot.swarm import (
    BEHAVIORS,
    NUM_BEHAVIORS,
    FormationController,
    all_behaviors,
)


class TestFormationControllerBasics:
    def test_empty_positions_returns_empty(self):
        fc = FormationController()
        assert fc.maintain_formation([]) == []

    def test_centroid_of_empty_is_origin(self):
        assert FormationController.centroid([]) == (0.0, 0.0)

    def test_centroid_average(self):
        cx, cy = FormationController.centroid([(0.0, 0.0), (4.0, 6.0)])
        assert cx == pytest.approx(2.0)
        assert cy == pytest.approx(3.0)

    def test_invalid_cohesion(self):
        with pytest.raises(ValueError):
            FormationController(cohesion=-0.1)
        with pytest.raises(ValueError):
            FormationController(cohesion=1.5)

    def test_invalid_spacing(self):
        with pytest.raises(ValueError):
            FormationController(min_spacing=-1.0)


class TestMaintainFormation:
    def test_zero_cohesion_keeps_positions_when_spacing_ok(self):
        fc = FormationController(cohesion=0.0, min_spacing=0.0)
        pts = [(0.0, 0.0), (10.0, 0.0), (5.0, 5.0)]
        assert fc.maintain_formation(pts) == pts

    def test_full_cohesion_collapses_to_centroid(self):
        fc = FormationController(cohesion=1.0, min_spacing=0.0)
        pts = [(0.0, 0.0), (4.0, 0.0)]
        result = fc.maintain_formation(pts)
        for x, y in result:
            assert x == pytest.approx(2.0)
            assert y == pytest.approx(0.0)

    def test_partial_cohesion_moves_toward_centroid(self):
        fc = FormationController(cohesion=0.5, min_spacing=0.0)
        pts = [(0.0, 0.0), (10.0, 0.0)]
        result = fc.maintain_formation(pts)
        # Centroid is (5, 0); halfway from each.
        assert result[0] == pytest.approx((2.5, 0.0))
        assert result[1] == pytest.approx((7.5, 0.0))

    def test_iterating_converges_to_centroid(self):
        fc = FormationController(cohesion=0.5, min_spacing=0.0)
        pts = [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]
        cx, cy = FormationController.centroid(pts)
        for _ in range(40):
            pts = fc.maintain_formation(pts)
        for x, y in pts:
            assert math.isclose(x, cx, abs_tol=1e-3)
            assert math.isclose(y, cy, abs_tol=1e-3)

    def test_min_spacing_separates_overlapping_units(self):
        fc = FormationController(cohesion=0.0, min_spacing=2.0)
        result = fc.maintain_formation([(0.0, 0.0), (0.0, 0.0)])
        a, b = result
        assert math.hypot(b[0] - a[0], b[1] - a[1]) == pytest.approx(2.0, abs=1e-9)

    def test_min_spacing_pushes_close_units_apart(self):
        fc = FormationController(cohesion=0.0, min_spacing=2.0)
        a, b = fc.maintain_formation([(0.0, 0.0), (1.0, 0.0)])
        assert math.hypot(b[0] - a[0], b[1] - a[1]) == pytest.approx(2.0)


class TestBehaviorRegistry:
    def test_registry_size(self):
        assert len(BEHAVIORS) == NUM_BEHAVIORS == 30

    def test_each_behavior_is_class(self):
        for index, cls in BEHAVIORS.items():
            assert isinstance(index, int)
            instance = cls()
            assert hasattr(instance, "tick")
            assert callable(instance.tick)

    def test_all_behaviors_returns_one_per_module(self):
        instances = all_behaviors()
        assert len(instances) == NUM_BEHAVIORS

    def test_behavior_tick_returns_targets(self):
        b = BEHAVIORS[1]()
        targets = b.tick([(0.0, 0.0), (4.0, 0.0)])
        assert len(targets) == 2
        for t in targets:
            assert len(t) == 2

    def test_behavior_repr(self):
        b = BEHAVIORS[15]()
        assert b.__class__.__name__ in repr(b)
