"""Tests for src.bot.swarm._strategies primitives and BehaviorNN wrappers."""

import math

import pytest
from src.bot.swarm import BEHAVIORS, NUM_BEHAVIORS
from src.bot.swarm import _strategies as strategies


def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


class TestCohereScatter:
    def test_cohere_pulls_to_centroid(self):
        result = strategies.cohere([(0.0, 0.0), (10.0, 0.0)], factor=0.5)
        assert result == [(2.5, 0.0), (7.5, 0.0)]

    def test_scatter_pushes_outward(self):
        result = strategies.scatter([(0.0, 0.0), (10.0, 0.0)], factor=0.5)
        assert result == [(-2.5, 0.0), (12.5, 0.0)]

    def test_cohere_empty(self):
        assert strategies.cohere([]) == []


class TestAttackRetreat:
    def test_attack_move_steps_toward_target(self):
        result = strategies.attack_move([(0.0, 0.0)], target=(10.0, 0.0), step=1.0)
        assert result[0] == pytest.approx((1.0, 0.0))

    def test_attack_move_caps_at_target(self):
        result = strategies.attack_move([(0.0, 0.0)], target=(0.5, 0.0), step=1.0)
        assert result[0] == (0.5, 0.0)

    def test_retreat_pushes_from_threat(self):
        result = strategies.retreat([(1.0, 0.0)], threat=(0.0, 0.0), step=1.0)
        assert result[0] == pytest.approx((2.0, 0.0))

    def test_retreat_handles_overlap(self):
        result = strategies.retreat([(0.0, 0.0)], threat=(0.0, 0.0), step=1.0)
        assert result[0] == (1.0, 0.0)


class TestFormationStrategies:
    def test_circle_target_is_on_radius(self):
        pts = strategies.circle_target([(0, 0)] * 4, target=(0.0, 0.0), radius=3.0)
        for x, y in pts:
            assert math.isclose(math.hypot(x, y), 3.0, rel_tol=1e-9)

    def test_line_formation_x_axis(self):
        pts = strategies.line_formation([(0, 0)] * 3, origin=(0.0, 5.0), spacing=1.0)
        ys = {p[1] for p in pts}
        xs = sorted(p[0] for p in pts)
        assert ys == {5.0}
        assert xs == [-1.0, 0.0, 1.0]

    def test_line_formation_y_axis(self):
        pts = strategies.line_formation(
            [(0, 0)] * 2, origin=(5.0, 0.0), spacing=2.0, axis="y"
        )
        assert {p[0] for p in pts} == {5.0}
        assert sorted(p[1] for p in pts) == [-1.0, 1.0]

    def test_box_formation_centered_on_origin(self):
        pts = strategies.box_formation([(0, 0)] * 4, origin=(0.0, 0.0), spacing=2.0)
        cx, cy = _centroid(pts)
        assert cx == pytest.approx(0.0)
        assert cy == pytest.approx(0.0)

    def test_wedge_apex_at_tip(self):
        pts = strategies.wedge(
            [(0, 0)] * 3, tip=(0.0, 0.0), target=(10.0, 0.0), spacing=1.0
        )
        assert pts[0] == (0.0, 0.0)


class TestSpread:
    def test_spread_separates_overlapping(self):
        pts = strategies.spread([(0.0, 0.0), (0.0, 0.0)], min_distance=2.0)
        d = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        assert d >= 2.0 - 1e-9


class TestKiteAndLeapfrog:
    def test_kite_first_advances_then_retreats(self):
        result = strategies.kite(
            [(0.0, 0.0)], target=(10.0, 0.0), advance=2.0, retreat_step=1.0
        )
        # After +2 advance then -1 retreat, net +1.
        assert result[0] == pytest.approx((1.0, 0.0))

    def test_leapfrog_phase_zero_moves_even_indices(self):
        pts = [(0.0, 0.0), (0.0, 0.0)]
        result = strategies.leapfrog(pts, target=(10.0, 0.0), step=1.0, phase=0)
        assert result[0] != pts[0]
        assert result[1] == pts[1]

    def test_leapfrog_phase_one_moves_odd_indices(self):
        pts = [(0.0, 0.0), (0.0, 0.0)]
        result = strategies.leapfrog(pts, target=(10.0, 0.0), step=1.0, phase=1)
        assert result[0] == pts[0]
        assert result[1] != pts[1]


class TestPursueAndJitter:
    def test_pursue_closest_picks_nearest_target(self):
        result = strategies.pursue_closest(
            [(0.0, 0.0)], targets=[(10.0, 0.0), (-1.0, 0.0)], step=1.0
        )
        assert result[0][0] < 0.0

    def test_pursue_closest_no_targets_is_identity(self):
        pts = [(1.0, 2.0), (3.0, 4.0)]
        assert strategies.pursue_closest(pts, targets=[]) == pts

    def test_random_jitter_seed_is_deterministic(self):
        a = strategies.random_jitter([(0.0, 0.0)] * 5, magnitude=1.0, seed=42)
        b = strategies.random_jitter([(0.0, 0.0)] * 5, magnitude=1.0, seed=42)
        assert a == b


class TestWallOff:
    def test_wall_off_endpoints(self):
        pts = strategies.wall_off([(0, 0)] * 3, choke_a=(0.0, 0.0), choke_b=(10.0, 0.0))
        assert pts[0] == (0.0, 0.0)
        assert pts[-1] == (10.0, 0.0)

    def test_wall_off_single_unit_midpoint(self):
        pts = strategies.wall_off([(0, 0)], choke_a=(0.0, 0.0), choke_b=(10.0, 0.0))
        assert pts == [(5.0, 0.0)]


class TestVortexAndRing:
    def test_vortex_preserves_distance_to_centroid(self):
        pts = [(1.0, 0.0), (-1.0, 0.0)]
        result = strategies.vortex(pts, angle=math.pi / 4)
        cx, cy = _centroid(pts)
        for (x, y), (rx, ry) in zip(pts, result):
            assert math.isclose(
                math.hypot(x - cx, y - cy), math.hypot(rx - cx, ry - cy), rel_tol=1e-9
            )

    def test_ring_expand_increases_radius(self):
        pts = [(1.0, 0.0), (-1.0, 0.0)]
        result = strategies.ring_expand(pts, factor=0.5)
        cx, cy = _centroid(pts)
        for (x, y), (rx, ry) in zip(pts, result):
            assert math.hypot(rx - cx, ry - cy) > math.hypot(x - cx, y - cy)


class TestZigzagBaitRally:
    def test_zigzag_advances_toward_target(self):
        pts = [(0.0, 0.0), (0.0, 0.0)]
        result = strategies.zigzag(pts, target=(10.0, 0.0), step=1.0, lateral=0.5)
        assert all(p[0] > 0 for p in result)

    def test_bait_first_moves_toward_target_others_retreat(self):
        pts = [(0.0, 0.0), (0.0, 0.0)]
        result = strategies.bait(pts, target=(10.0, 0.0), retreat_point=(-10.0, 0.0))
        assert result[0][0] > 0.0
        assert result[1][0] < 0.0

    def test_rally_moves_all_toward_rally_point(self):
        result = strategies.rally(
            [(0.0, 0.0), (10.0, 0.0)], rally_point=(5.0, 0.0), step=10.0
        )
        for p in result:
            assert p == (5.0, 0.0)


class TestSplitGroups:
    def test_split_groups_alternates_targets(self):
        pts = [(0.0, 0.0), (0.0, 0.0)]
        result = strategies.split_groups(
            pts, target_a=(10.0, 0.0), target_b=(-10.0, 0.0)
        )
        assert result[0][0] > 0.0
        assert result[1][0] < 0.0


class TestPatrolAndScout:
    def test_patrol_progress_zero_targets_a(self):
        pts = [(0.0, 0.0), (0.0, 0.0)]
        result = strategies.patrol(
            pts, waypoint_a=(0.0, 0.0), waypoint_b=(10.0, 0.0), progress=0.0
        )
        assert all(p == (0.0, 0.0) for p in result)

    def test_scout_distance_from_origin(self):
        pts = strategies.scout([(0, 0)] * 4, origin=(0.0, 0.0), distance=4.0)
        for x, y in pts:
            assert math.isclose(math.hypot(x, y), 4.0, rel_tol=1e-9)


class TestBehaviorWrappers:
    def test_each_behavior_returns_same_length(self):
        pts = [(0.0, 0.0), (3.0, 4.0), (-2.0, 5.0)]
        for index in range(1, NUM_BEHAVIORS + 1):
            behavior = BEHAVIORS[index]()
            result = behavior.tick(pts)
            assert len(result) == len(pts), f"behavior {index} changed length"
            for point in result:
                assert len(point) == 2

    def test_each_behavior_has_strategy_name(self):
        for index in range(1, NUM_BEHAVIORS + 1):
            behavior = BEHAVIORS[index]()
            assert hasattr(behavior, "strategy")
            assert callable(getattr(strategies, behavior.strategy))

    def test_behavior_repr_includes_strategy(self):
        b = BEHAVIORS[4]()
        r = repr(b)
        assert "Behavior04" in r
        assert "attack_move" in r
