# -*- coding: utf-8 -*-
"""Tests for swarm behavior modules (behavior_01 ~ behavior_30)."""

import math
import sys
import pytest

# Make src importable
sys.path.insert(0, "src")

from bot.swarm.formation_controller import FormationController


# ---------------------------------------------------------------------------
# FormationController unit tests
# ---------------------------------------------------------------------------

class TestFormationController:
    def setup_method(self):
        self.ctrl = FormationController(formation_radius=3.0)

    def test_maintain_formation_empty(self):
        assert self.ctrl.maintain_formation([]) == []

    def test_maintain_formation_single(self):
        result = self.ctrl.maintain_formation([(5.0, 5.0)])
        assert result == [(5.0, 5.0)]

    def test_maintain_formation_count(self):
        positions = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
        result = self.ctrl.maintain_formation(positions)
        assert len(result) == 3

    def test_maintain_formation_on_ring(self):
        """All returned positions should be on the formation ring."""
        positions = [(float(i), 0.0) for i in range(4)]
        targets = self.ctrl.maintain_formation(positions)
        cx = sum(p[0] for p in positions) / len(positions)
        cy = sum(p[1] for p in positions) / len(positions)
        for tx, ty in targets:
            dist = math.hypot(tx - cx, ty - cy)
            assert abs(dist - 3.0) < 1e-6

    def test_spread_formation(self):
        positions = [(0.0, 0.0), (1.0, 0.0)]
        targets = self.ctrl.spread_formation(positions, spread=6.0)
        assert len(targets) == 2
        cx = sum(p[0] for p in positions) / len(positions)
        cy = sum(p[1] for p in positions) / len(positions)
        for tx, ty in targets:
            dist = math.hypot(tx - cx, ty - cy)
            assert abs(dist - 6.0) < 1e-6

    def test_line_formation_count(self):
        positions = [(float(i), 0.0) for i in range(5)]
        targets = self.ctrl.line_formation(positions, direction=0.0)
        assert len(targets) == 5

    def test_wedge_formation_count(self):
        positions = [(float(i), 0.0) for i in range(6)]
        targets = self.ctrl.wedge_formation(positions, direction=0.0)
        assert len(targets) == 6


# ---------------------------------------------------------------------------
# Generic behavior tick contract
# ---------------------------------------------------------------------------

def _load_behavior(n: int):
    """Dynamically import and instantiate BehaviorNN."""
    mod_name = f"bot.swarm.behavior_{n:02d}"
    cls_name = f"Behavior{n:02d}"
    import importlib
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    return cls()


SAMPLE_POSITIONS_SETS = [
    [],
    [(0.0, 0.0)],
    [(0.0, 0.0), (2.0, 0.0)],
    [(0.0, 0.0), (3.0, 0.0), (1.5, 2.6)],
    [(float(i), float(j)) for i in range(3) for j in range(3)],
]


@pytest.mark.parametrize("behavior_num", range(1, 31))
class TestBehaviorContract:
    """All 30 behaviors must satisfy the basic API contract."""

    def test_has_name(self, behavior_num):
        b = _load_behavior(behavior_num)
        assert isinstance(b.name, str) and len(b.name) > 0

    def test_repr(self, behavior_num):
        b = _load_behavior(behavior_num)
        assert "Behavior" in repr(b)

    @pytest.mark.parametrize("positions", SAMPLE_POSITIONS_SETS)
    def test_tick_returns_list(self, behavior_num, positions):
        b = _load_behavior(behavior_num)
        result = b.tick(positions)
        assert isinstance(result, list)

    @pytest.mark.parametrize("positions", SAMPLE_POSITIONS_SETS)
    def test_tick_preserves_count(self, behavior_num, positions):
        b = _load_behavior(behavior_num)
        result = b.tick(positions)
        assert len(result) == len(positions)

    @pytest.mark.parametrize("positions", SAMPLE_POSITIONS_SETS)
    def test_tick_returns_float_tuples(self, behavior_num, positions):
        b = _load_behavior(behavior_num)
        result = b.tick(positions)
        for pos in result:
            assert len(pos) == 2
            x, y = pos
            assert isinstance(x, float)
            assert isinstance(y, float)
            assert math.isfinite(x) and math.isfinite(y)

    def test_multiple_ticks_stable(self, behavior_num):
        """Behaviors should not crash on repeated ticks."""
        b = _load_behavior(behavior_num)
        positions = [(float(i), float(i)) for i in range(5)]
        for _ in range(10):
            positions = b.tick(positions)
        assert len(positions) == 5


# ---------------------------------------------------------------------------
# Behavior-specific smoke tests
# ---------------------------------------------------------------------------

class TestBehavior01CircularFormation:
    def test_ring_radius(self):
        from bot.swarm.behavior_01 import Behavior01
        b = Behavior01()
        positions = [(float(i), 0.0) for i in range(6)]
        targets = b.tick(positions)
        cx = sum(p[0] for p in positions) / len(positions)
        cy = sum(p[1] for p in positions) / len(positions)
        for tx, ty in targets:
            dist = math.hypot(tx - cx, ty - cy)
            assert abs(dist - 3.0) < 0.01


class TestBehavior02Boids:
    def test_separation_pushes_apart(self):
        from bot.swarm.behavior_02 import Behavior02
        b = Behavior02()
        # Two units very close together should be pushed apart
        close_positions = [(0.0, 0.0), (0.1, 0.0)]
        result = b.tick(close_positions)
        # After one tick, x-distance should increase
        dist_before = abs(close_positions[1][0] - close_positions[0][0])
        dist_after = abs(result[1][0] - result[0][0])
        assert dist_after >= dist_before
