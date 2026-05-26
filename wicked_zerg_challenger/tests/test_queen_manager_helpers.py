# -*- coding: utf-8 -*-
"""
QueenManager 정적 헬퍼 메서드 단위 테스트.

테스트 대상:
- _score_creep_target: 거리 + 방향 정렬 점수
- _find_closest_queen: 제외 집합을 고려한 가장 가까운 퀸 탐색
- _find_queen_by_tag: 태그 기반 퀸 검색
"""

import os
import sys
import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from queen_manager import QueenManager


@dataclass
class _Pt:
    x: float
    y: float


def _queen(tag: int, pos: _Pt):
    q = MagicMock()
    q.tag = tag
    q.position = pos
    q.distance_to = lambda other: (
        (q.position.x - other.x) ** 2 + (q.position.y - other.y) ** 2
    ) ** 0.5
    return q


class TestScoreCreepTarget(unittest.TestCase):
    def test_direction_alignment_scored_higher(self):
        origin = _Pt(0, 0)
        target_in_direction = _Pt(10, 0)
        target_off_direction = _Pt(0, 10)
        direction = _Pt(20, 0)  # +x 방향

        # Origin과 direction을 보고 +x 방향이면 점수 더 큼
        score_inline = QueenManager._score_creep_target(
            origin, target_in_direction, direction
        )
        score_orthogonal = QueenManager._score_creep_target(
            origin, target_off_direction, direction
        )
        self.assertGreater(score_inline, score_orthogonal)

    def test_zero_direction_returns_pure_distance(self):
        origin = _Pt(0, 0)
        candidate = _Pt(3, 4)
        direction = _Pt(0, 0)  # 길이 0
        score = QueenManager._score_creep_target(origin, candidate, direction)
        self.assertAlmostEqual(score, 5.0)  # sqrt(3^2 + 4^2)

    def test_same_point_zero_score(self):
        origin = _Pt(5, 5)
        candidate = _Pt(5, 5)
        direction = _Pt(10, 10)
        score = QueenManager._score_creep_target(origin, candidate, direction)
        self.assertEqual(score, 0.0)


class TestFindClosestQueen(unittest.TestCase):
    def test_returns_closest(self):
        queens = [
            _queen(1, _Pt(0, 0)),
            _queen(2, _Pt(10, 0)),
            _queen(3, _Pt(5, 0)),
        ]
        result = QueenManager._find_closest_queen(_Pt(6, 0), queens, set())
        self.assertEqual(result.tag, 3)

    def test_skips_excluded(self):
        queens = [
            _queen(1, _Pt(0, 0)),
            _queen(2, _Pt(10, 0)),
            _queen(3, _Pt(5, 0)),
        ]
        result = QueenManager._find_closest_queen(_Pt(6, 0), queens, excluded_tags={3})
        # 3이 제외되면 2 (거리 4) vs 1 (거리 6) → 2가 가까움
        self.assertEqual(result.tag, 2)

    def test_returns_none_when_all_excluded(self):
        queens = [_queen(1, _Pt(0, 0))]
        result = QueenManager._find_closest_queen(_Pt(5, 5), queens, excluded_tags={1})
        self.assertIsNone(result)

    def test_returns_none_for_empty_queens(self):
        result = QueenManager._find_closest_queen(_Pt(0, 0), [], set())
        self.assertIsNone(result)


class TestFindQueenByTag(unittest.TestCase):
    def test_finds_matching_tag(self):
        queens = [
            _queen(10, _Pt(0, 0)),
            _queen(20, _Pt(1, 1)),
            _queen(30, _Pt(2, 2)),
        ]
        result = QueenManager._find_queen_by_tag(queens, 20)
        self.assertIsNotNone(result)
        self.assertEqual(result.tag, 20)

    def test_returns_none_for_missing_tag(self):
        queens = [_queen(10, _Pt(0, 0))]
        self.assertIsNone(QueenManager._find_queen_by_tag(queens, 999))

    def test_returns_none_for_none_tag(self):
        queens = [_queen(10, _Pt(0, 0))]
        self.assertIsNone(QueenManager._find_queen_by_tag(queens, None))

    def test_returns_none_for_empty_queens(self):
        self.assertIsNone(QueenManager._find_queen_by_tag([], 10))


if __name__ == "__main__":
    unittest.main()
