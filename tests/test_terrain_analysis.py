"""Tests for wicked_zerg_challenger/combat/terrain_analysis.py.

Pure-Python tests — no SC2 game instance needed.  We use a tiny Point2-like
class and stub ramps to exercise the ChokePointDetector.
"""
from __future__ import annotations

from math import hypot
from types import SimpleNamespace

import pytest

from wicked_zerg_challenger.combat.terrain_analysis import ChokePointDetector


class P:
    """Minimal Point2 stand-in with `.x`, `.y`, `.distance_to`."""

    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        return hypot(self.x - other.x, self.y - other.y)

    def __repr__(self):  # pragma: no cover - debug helper
        return f"P({self.x}, {self.y})"


def _make_ramp(top: P, bottom: P) -> SimpleNamespace:
    return SimpleNamespace(top_center=top, bottom_center=bottom)


def _make_bot(ramps=None) -> SimpleNamespace:
    return SimpleNamespace(game_info=SimpleNamespace(map_ramps=list(ramps or [])))


# ---------------------------------------------------------------------------
# update_chokepoints
# ---------------------------------------------------------------------------

def test_update_collects_ramp_top_and_bottom_centers():
    bot = _make_bot([_make_ramp(P(10, 10), P(12, 12))])
    detector = ChokePointDetector(bot)
    detector.update_chokepoints(100)
    assert len(detector.chokepoints) == 2  # top + bottom


def test_update_throttled_by_cache_interval():
    bot = _make_bot([_make_ramp(P(10, 10), P(12, 12))])
    detector = ChokePointDetector(bot, cache_update_interval=100)
    detector.update_chokepoints(100)
    # mutate bot's ramps and call within interval — should NOT refresh
    bot.game_info.map_ramps.append(_make_ramp(P(20, 20), P(22, 22)))
    detector.update_chokepoints(150)
    assert len(detector.chokepoints) == 2  # still old value


def test_update_refreshes_after_interval():
    bot = _make_bot([_make_ramp(P(10, 10), P(12, 12))])
    detector = ChokePointDetector(bot, cache_update_interval=100)
    detector.update_chokepoints(100)
    bot.game_info.map_ramps.append(_make_ramp(P(20, 20), P(22, 22)))
    detector.update_chokepoints(250)
    assert len(detector.chokepoints) == 4  # 2 ramps × 2 centers


def test_update_no_game_info_attribute_is_noop():
    bot = SimpleNamespace()  # no game_info
    detector = ChokePointDetector(bot)
    detector.update_chokepoints(100)
    assert detector.chokepoints == []


def test_update_ramp_without_centers_is_skipped():
    bot = _make_bot([SimpleNamespace()])  # no top_center / bottom_center
    detector = ChokePointDetector(bot)
    detector.update_chokepoints(100)
    assert detector.chokepoints == []


# ---------------------------------------------------------------------------
# is_in_chokepoint
# ---------------------------------------------------------------------------

def test_is_in_chokepoint_true_when_within_radius():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot, chokepoint_radius=5.0)
    detector.update_chokepoints(100)
    assert detector.is_in_chokepoint(P(2, 2)) is True  # near (0, 0)


def test_is_in_chokepoint_false_when_outside_radius():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot, chokepoint_radius=5.0)
    detector.update_chokepoints(100)
    assert detector.is_in_chokepoint(P(50, 50)) is False


def test_is_in_chokepoint_no_chokepoints_returns_false():
    detector = ChokePointDetector(_make_bot())
    assert detector.is_in_chokepoint(P(0, 0)) is False


def test_is_in_chokepoint_none_position_returns_false():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot)
    detector.update_chokepoints(100)
    assert detector.is_in_chokepoint(None) is False


def test_is_in_chokepoint_with_broken_position_does_not_raise():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot)
    detector.update_chokepoints(100)
    broken = SimpleNamespace()  # no distance_to method
    # Should return False, not raise
    assert detector.is_in_chokepoint(broken) is False


# ---------------------------------------------------------------------------
# get_cohesion_modifier
# ---------------------------------------------------------------------------

def test_cohesion_modifier_reduced_in_chokepoint():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot, chokepoint_radius=5.0)
    detector.update_chokepoints(100)
    assert detector.get_cohesion_modifier(P(1, 1)) == 0.25


def test_cohesion_modifier_full_outside_chokepoint():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot, chokepoint_radius=5.0)
    detector.update_chokepoints(100)
    assert detector.get_cohesion_modifier(P(50, 50)) == 1.0


# ---------------------------------------------------------------------------
# get_nearest_chokepoint
# ---------------------------------------------------------------------------

def test_nearest_chokepoint_picks_closest():
    bot = _make_bot(
        [_make_ramp(P(0, 0), P(50, 50)), _make_ramp(P(100, 100), P(200, 200))]
    )
    detector = ChokePointDetector(bot)
    detector.update_chokepoints(100)
    pos = P(5, 5)
    nearest = detector.get_nearest_chokepoint(pos)
    # the closest of the 4 chokepoints (0,0), (50,50), (100,100), (200,200) to (5,5) is (0,0)
    assert nearest.x == 0 and nearest.y == 0


def test_nearest_chokepoint_empty_cache_returns_none():
    detector = ChokePointDetector(_make_bot())
    assert detector.get_nearest_chokepoint(P(0, 0)) is None


def test_nearest_chokepoint_none_position_returns_none():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot)
    detector.update_chokepoints(100)
    assert detector.get_nearest_chokepoint(None) is None


def test_nearest_chokepoint_with_broken_position_returns_none():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot)
    detector.update_chokepoints(100)
    # broken position → distance_to raises for every choke → nearest stays None
    broken = SimpleNamespace()
    assert detector.get_nearest_chokepoint(broken) is None


# ---------------------------------------------------------------------------
# get_chokepoint_avoidance_vector
# ---------------------------------------------------------------------------

def test_avoidance_vector_points_away_from_choke():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot, chokepoint_radius=10.0)
    detector.update_chokepoints(100)
    # Position to the right of choke at (0, 0) → vector should push further right (+x)
    vx, vy = detector.get_chokepoint_avoidance_vector(P(3, 0))
    assert vx > 0
    assert vy == pytest.approx(0)


def test_avoidance_vector_zero_when_no_chokes():
    detector = ChokePointDetector(_make_bot())
    vx, vy = detector.get_chokepoint_avoidance_vector(P(0, 0))
    assert (vx, vy) == (0.0, 0.0)


def test_avoidance_vector_zero_when_outside_all_radii():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot, chokepoint_radius=5.0)
    detector.update_chokepoints(100)
    # Far from both chokepoints
    vx, vy = detector.get_chokepoint_avoidance_vector(P(50, 50))
    assert (vx, vy) == (0.0, 0.0)


def test_avoidance_weight_scales_vector():
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot, chokepoint_radius=10.0)
    detector.update_chokepoints(100)
    vx1, _ = detector.get_chokepoint_avoidance_vector(P(3, 0), avoidance_weight=1.0)
    vx2, _ = detector.get_chokepoint_avoidance_vector(P(3, 0), avoidance_weight=2.0)
    assert vx2 == pytest.approx(vx1 * 2)


def test_avoidance_vector_skips_broken_choke():
    """If one choke entry lacks .x / .y, that one is skipped, others still work."""
    bot = _make_bot([_make_ramp(P(0, 0), P(100, 100))])
    detector = ChokePointDetector(bot, chokepoint_radius=10.0)
    detector.update_chokepoints(100)
    # Inject a broken choke; valid ones should still contribute
    detector.chokepoints.append(SimpleNamespace())  # no .x / .y
    vx, vy = detector.get_chokepoint_avoidance_vector(P(3, 0))
    assert vx > 0  # valid choke still contributes
