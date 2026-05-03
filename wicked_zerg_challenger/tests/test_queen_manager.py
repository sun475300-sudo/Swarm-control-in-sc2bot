# -*- coding: utf-8 -*-
"""
Unit tests for QueenManager pure-logic surfaces.

Avoids exercising the full on_step orchestration (it requires too much
mocked state). Instead we verify:
- __init__ tunables (energy thresholds, cooldowns, max queens-per-base)
- _is_base_under_attack: range thresholds change with game_time
- _count_creep_tumors: counts only the three tumor types
- _is_valid_creep_position: behavior with/without bot.has_creep
- _collect_creep_targets: aggregates scout positions and expansions
- _score_creep_target: pure math
- _find_closest_queen / _find_queen_by_tag: static helpers
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from queen_manager import QueenManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


def _struct(type_id, position=Point2((0, 0))):
    s = Mock()
    s.type_id = type_id
    s.position = position
    s.distance_to = lambda p: position.distance_to(
        p if isinstance(p, Point2) else p.position
    )
    return s


def _enemy(position=Point2((0, 0)), tag=1):
    e = Mock()
    e.tag = tag
    e.position = position
    e.distance_to = lambda p: position.distance_to(
        p if isinstance(p, Point2) else p.position
    )
    return e


def _queen(position=Point2((0, 0)), tag=1, energy=50):
    q = Mock()
    q.tag = tag
    q.position = position
    q.energy = energy
    q.distance_to = lambda p: position.distance_to(
        p if isinstance(p, Point2) else getattr(p, "position", p)
    )
    return q


class TestInitDefaults(unittest.TestCase):
    def test_tunables(self):
        bot = Mock()
        m = QueenManager(bot)
        self.assertEqual(m.inject_energy_threshold, 25)
        self.assertAlmostEqual(m.inject_cooldown, 29.0)
        self.assertEqual(m.max_inject_distance, 8.0)
        self.assertEqual(m.creep_energy_threshold, 20)
        self.assertEqual(m.creep_spread_cooldown, 4.0)
        self.assertEqual(m.max_queens_per_base, 2)
        self.assertEqual(m.creep_queen_bonus, 4)
        self.assertEqual(m.transfuse_energy_threshold, 50)
        self.assertEqual(m.transfuse_health_threshold, 0.5)

    def test_tracking_defaults_empty(self):
        bot = Mock()
        m = QueenManager(bot)
        self.assertEqual(m.inject_assignments, {})
        self.assertEqual(m.last_inject_time, {})
        self.assertEqual(m.last_creep_time, {})
        self.assertEqual(m.assigned_queen_tags, set())
        self.assertEqual(m.dedicated_creep_queens, set())


class TestIsBaseUnderAttack(unittest.TestCase):
    def test_no_townhalls_returns_false(self):
        bot = Mock(spec=[])
        m = QueenManager(bot)
        self.assertFalse(m._is_base_under_attack())

    def test_no_enemies_returns_false(self):
        bot = Mock()
        bot.townhalls = [_struct(UnitTypeId.HATCHERY, Point2((10, 10)))]
        bot.enemy_units = []
        bot.time = 100
        m = QueenManager(bot)
        self.assertFalse(m._is_base_under_attack())

    def test_close_enemy_triggers_under_attack_early_game(self):
        bot = Mock()
        bot.townhalls = [_struct(UnitTypeId.HATCHERY, Point2((10, 10)))]
        bot.enemy_units = [_enemy(Point2((20, 10)))]  # 10 away, < 20
        bot.time = 60  # early game, range 20
        m = QueenManager(bot)
        self.assertTrue(m._is_base_under_attack())

    def test_far_enemy_no_attack(self):
        bot = Mock()
        bot.townhalls = [_struct(UnitTypeId.HATCHERY, Point2((10, 10)))]
        bot.enemy_units = [_enemy(Point2((100, 10)))]  # 90 away
        bot.time = 60
        m = QueenManager(bot)
        self.assertFalse(m._is_base_under_attack())

    def test_late_game_uses_smaller_range(self):
        # At t>=180 the range drops from 20 to 18
        bot = Mock()
        bot.townhalls = [_struct(UnitTypeId.HATCHERY, Point2((10, 10)))]
        bot.enemy_units = [_enemy(Point2((29, 10)))]  # 19 away
        bot.time = 60  # 19 < 20, so triggers
        m = QueenManager(bot)
        self.assertTrue(m._is_base_under_attack())
        bot.time = 200  # 19 > 18, so does NOT trigger
        self.assertFalse(m._is_base_under_attack())


class TestCountCreepTumors(unittest.TestCase):
    def test_no_structures_attr_returns_zero(self):
        bot = Mock(spec=[])
        m = QueenManager(bot)
        self.assertEqual(m._count_creep_tumors(), 0)

    def test_counts_all_three_tumor_types(self):
        bot = Mock()
        bot.structures = [
            _struct(UnitTypeId.CREEPTUMOR),
            _struct(UnitTypeId.CREEPTUMOR),
            _struct(UnitTypeId.CREEPTUMORBURROWED),
            _struct(UnitTypeId.CREEPTUMORQUEEN),
            _struct(UnitTypeId.HATCHERY),  # not a tumor
        ]
        m = QueenManager(bot)
        self.assertEqual(m._count_creep_tumors(), 4)

    def test_swallows_iteration_errors(self):
        bot = Mock()

        class _Boom:
            def __iter__(self):
                raise RuntimeError("boom")

        bot.structures = _Boom()
        m = QueenManager(bot)
        self.assertEqual(m._count_creep_tumors(), 0)


class TestIsValidCreepPosition(unittest.TestCase):
    def test_none_target_invalid(self):
        bot = Mock()
        m = QueenManager(bot)
        self.assertFalse(m._is_valid_creep_position(None))

    def test_uses_bot_has_creep(self):
        bot = Mock()
        bot.has_creep = Mock(return_value=True)
        m = QueenManager(bot)
        self.assertTrue(m._is_valid_creep_position(Point2((10, 10))))
        bot.has_creep.return_value = False
        self.assertFalse(m._is_valid_creep_position(Point2((10, 10))))

    def test_no_has_creep_returns_false(self):
        bot = Mock(spec=[])
        m = QueenManager(bot)
        self.assertFalse(m._is_valid_creep_position(Point2((10, 10))))


class TestCollectCreepTargets(unittest.TestCase):
    def test_collects_scout_and_expansion_positions(self):
        bot = Mock()
        scout = Mock()
        scout.cached_positions = [Point2((10, 10)), Point2((20, 20))]
        scout.overlord_assignments = {1: Point2((30, 30)), 2: Point2((40, 40))}
        bot.scout = scout
        bot.expansion_locations_list = [Point2((50, 50))]
        m = QueenManager(bot)
        targets = m._collect_creep_targets()
        self.assertEqual(len(targets), 5)
        for p in (Point2((10, 10)), Point2((50, 50))):
            self.assertIn(p, targets)

    def test_filters_falsy_positions(self):
        bot = Mock()
        scout = Mock()
        scout.cached_positions = [Point2((10, 10)), None, 0]
        scout.overlord_assignments = {}
        bot.scout = scout
        bot.expansion_locations_list = []
        m = QueenManager(bot)
        targets = m._collect_creep_targets()
        self.assertEqual(targets, [Point2((10, 10))])

    def test_empty_when_nothing_set(self):
        bot = Mock(spec=[])
        m = QueenManager(bot)
        self.assertEqual(m._collect_creep_targets(), [])


class TestScoreCreepTarget(unittest.TestCase):
    def test_zero_direction_falls_back_to_distance(self):
        origin = Point2((0, 0))
        candidate = Point2((3, 4))
        # direction == origin
        score = QueenManager._score_creep_target(origin, candidate, origin)
        self.assertEqual(score, 5.0)

    def test_aligned_with_direction_higher_than_perpendicular(self):
        origin = Point2((0, 0))
        direction = Point2((10, 0))  # along +x
        # Candidate aligned with direction
        aligned = Point2((5, 0))
        # Candidate perpendicular to direction
        perp = Point2((0, 5))
        s_aligned = QueenManager._score_creep_target(origin, aligned, direction)
        s_perp = QueenManager._score_creep_target(origin, perp, direction)
        self.assertGreater(s_aligned, s_perp)


class TestFindClosestQueen(unittest.TestCase):
    def test_no_candidates_returns_none(self):
        result = QueenManager._find_closest_queen(Point2((0, 0)), [], set())
        self.assertIsNone(result)

    def test_excludes_specified_tags(self):
        q1 = _queen(Point2((1, 1)), tag=1)
        q2 = _queen(Point2((100, 100)), tag=2)
        result = QueenManager._find_closest_queen(Point2((0, 0)), [q1, q2], {1})
        self.assertEqual(result, q2)

    def test_returns_closest(self):
        q1 = _queen(Point2((10, 10)), tag=1)
        q2 = _queen(Point2((1, 1)), tag=2)
        result = QueenManager._find_closest_queen(Point2((0, 0)), [q1, q2], set())
        self.assertEqual(result, q2)


class TestFindQueenByTag(unittest.TestCase):
    def test_none_tag_returns_none(self):
        q = _queen(tag=1)
        self.assertIsNone(QueenManager._find_queen_by_tag([q], None))

    def test_returns_matching(self):
        q1 = _queen(tag=1)
        q2 = _queen(tag=2)
        self.assertEqual(QueenManager._find_queen_by_tag([q1, q2], 2), q2)

    def test_returns_none_when_not_found(self):
        q1 = _queen(tag=1)
        self.assertIsNone(QueenManager._find_queen_by_tag([q1], 99))


if __name__ == "__main__":
    unittest.main()
