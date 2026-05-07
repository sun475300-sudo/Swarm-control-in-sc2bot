"""Pure-logic tests for QueenManager._score_creep_target.

The scoring helper picks creep tumor placements that lean toward an
enemy direction while penalizing distance. These tests validate the
direction-projection math; they need no SC2 game state.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

# Same path-prep convention as tests/test_medium_opening_stability.py.
_PKG = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

import pytest  # noqa: E402

try:
    from wicked_zerg_challenger.queen_manager import QueenManager  # noqa: E402
except ImportError as exc:  # pragma: no cover
    pytest.skip(f"queen_manager import failed: {exc}", allow_module_level=True)


def _pt(x, y):
    return SimpleNamespace(x=float(x), y=float(y))


# ---------------------------------------------------------------------------
# Sanity / degenerate cases
# ---------------------------------------------------------------------------


class TestScoreDegenerate:
    def test_origin_equals_direction_returns_distance(self):
        """If direction_target == origin, dir_len == 0 and the helper
        falls back to plain distance."""
        origin = _pt(0, 0)
        candidate = _pt(3, 4)  # dist = 5
        direction = _pt(0, 0)

        score = QueenManager._score_creep_target(origin, candidate, direction)
        assert score == pytest.approx(5.0)

    def test_candidate_at_origin_scores_zero(self):
        origin = _pt(10, 10)
        candidate = _pt(10, 10)
        direction = _pt(20, 20)

        score = QueenManager._score_creep_target(origin, candidate, direction)
        assert score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Directional preference
# ---------------------------------------------------------------------------


class TestDirectionalPreference:
    def test_forward_candidate_scores_higher_than_backward(self):
        """Two candidates equidistant from origin — the one along the
        direction vector must score above the one opposite."""
        origin = _pt(0, 0)
        forward = _pt(5, 0)  # toward (10, 0)
        backward = _pt(-5, 0)
        direction = _pt(10, 0)

        s_fwd = QueenManager._score_creep_target(origin, forward, direction)
        s_back = QueenManager._score_creep_target(origin, backward, direction)
        assert s_fwd > s_back

    def test_perpendicular_candidate_scores_below_aligned(self):
        origin = _pt(0, 0)
        aligned = _pt(5, 0)
        perpendicular = _pt(0, 5)
        direction = _pt(10, 0)

        s_aligned = QueenManager._score_creep_target(origin, aligned, direction)
        s_perp = QueenManager._score_creep_target(origin, perpendicular, direction)
        assert s_aligned > s_perp

    def test_score_includes_distance_penalty(self):
        """The 0.25*dist term means closer-aligned candidates win
        head-to-head against farther ones at the same projection."""
        origin = _pt(0, 0)
        near = _pt(2, 0)  # projection 2, dist 2 -> score 2.5
        far = _pt(2, 6)  # projection 2, dist sqrt(40) ~6.32 -> score ~3.58
        direction = _pt(10, 0)

        s_near = QueenManager._score_creep_target(origin, near, direction)
        s_far = QueenManager._score_creep_target(origin, far, direction)
        # Helper returns projection + 0.25*dist, so larger total = farther
        assert s_far > s_near


# ---------------------------------------------------------------------------
# Numerical sanity
# ---------------------------------------------------------------------------


class TestNumericalSanity:
    def test_known_score_value(self):
        """origin=(0,0), candidate=(3,0), direction=(10,0):
        projection = 3, dist = 3 -> score = 3 + 0.75 = 3.75"""
        origin = _pt(0, 0)
        candidate = _pt(3, 0)
        direction = _pt(10, 0)

        score = QueenManager._score_creep_target(origin, candidate, direction)
        assert score == pytest.approx(3.75)

    def test_diagonal_direction(self):
        """45° direction means projection of (3,0) onto unit (1/sqrt2, 1/sqrt2)
        gives 3 * 1/sqrt(2). Distance is 3.
        score = 3/sqrt(2) + 0.75 ≈ 2.121 + 0.75 ≈ 2.871"""
        origin = _pt(0, 0)
        candidate = _pt(3, 0)
        direction = _pt(10, 10)

        score = QueenManager._score_creep_target(origin, candidate, direction)
        expected = 3 / (2**0.5) + 0.25 * 3
        assert score == pytest.approx(expected, rel=1e-6)
