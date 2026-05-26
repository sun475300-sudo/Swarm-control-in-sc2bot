# -*- coding: utf-8 -*-
"""MicroFocusMode 단위 테스트.

전투 상황 감지(평화/경계/전투/위급), 실행 간격 계산, prioritize 결정.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from micro_focus_mode import MicroFocusMode


class _Pos:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance_to(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class _TypeId:
    def __init__(self, name):
        self.name = name


class _Unit:
    def __init__(self, x, y, name="ZERGLING"):
        self.position = _Pos(x, y)
        self.type_id = _TypeId(name)


class _Townhall:
    def __init__(self, x, y):
        self.position = _Pos(x, y)


class _StubBot:
    def __init__(self, time=0.0, townhalls=None, units=None, enemy=None):
        self.time = time
        self.townhalls = townhalls or []
        self.units = units or []
        self.enemy_units = enemy or []


class TestEnemyNearBaseCount(unittest.TestCase):
    def test_no_townhalls_returns_zero(self):
        bot = _StubBot(enemy=[_Unit(10, 10)])
        m = MicroFocusMode(bot)
        self.assertEqual(m._count_enemies_near_bases(), 0)

    def test_one_enemy_near_base(self):
        bot = _StubBot(townhalls=[_Townhall(0, 0)], enemy=[_Unit(5, 5)])
        m = MicroFocusMode(bot)
        self.assertEqual(m._count_enemies_near_bases(), 1)

    def test_enemy_far_from_base(self):
        bot = _StubBot(townhalls=[_Townhall(0, 0)], enemy=[_Unit(50, 50)])
        m = MicroFocusMode(bot)
        self.assertEqual(m._count_enemies_near_bases(), 0)


class TestArmyInCombatCount(unittest.TestCase):
    def test_zergling_near_enemy(self):
        bot = _StubBot(units=[_Unit(0, 0, "ZERGLING")], enemy=[_Unit(5, 5)])
        m = MicroFocusMode(bot)
        self.assertEqual(m._count_army_in_combat(), 1)

    def test_non_army_units_excluded(self):
        # DRONE은 army_types에 없음
        bot = _StubBot(units=[_Unit(0, 0, "DRONE")], enemy=[_Unit(5, 5)])
        m = MicroFocusMode(bot)
        self.assertEqual(m._count_army_in_combat(), 0)

    def test_no_enemy_short_circuit(self):
        bot = _StubBot(units=[_Unit(0, 0, "ROACH")], enemy=[])
        m = MicroFocusMode(bot)
        self.assertEqual(m._count_army_in_combat(), 0)


class TestFocusLevelClassification(unittest.TestCase):
    def test_normal_no_enemies(self):
        bot = _StubBot(townhalls=[_Townhall(0, 0)], enemy=[])
        m = MicroFocusMode(bot)
        level = m._analyze_combat_situation()
        self.assertEqual(level, 0)

    def test_critical_5plus_enemies_at_base(self):
        bot = _StubBot(
            townhalls=[_Townhall(0, 0)],
            enemy=[_Unit(x, x) for x in range(5)],
        )
        m = MicroFocusMode(bot)
        self.assertEqual(m._analyze_combat_situation(), 3)

    def test_combat_3_enemies_at_base(self):
        bot = _StubBot(
            townhalls=[_Townhall(0, 0)],
            enemy=[_Unit(x, x) for x in range(3)],
        )
        m = MicroFocusMode(bot)
        self.assertEqual(m._analyze_combat_situation(), 2)

    def test_alert_1_enemy_at_base(self):
        bot = _StubBot(townhalls=[_Townhall(0, 0)], enemy=[_Unit(5, 5)])
        m = MicroFocusMode(bot)
        self.assertEqual(m._analyze_combat_situation(), 1)


class TestIntervalMapping(unittest.TestCase):
    def test_get_current_interval(self):
        m = MicroFocusMode(_StubBot())
        m.focus_level = 0
        self.assertEqual(m.get_current_interval(), m.normal_interval)
        m.focus_level = 1
        self.assertEqual(m.get_current_interval(), m.alert_interval)
        m.focus_level = 2
        self.assertEqual(m.get_current_interval(), m.combat_interval)
        m.focus_level = 3
        self.assertEqual(m.get_current_interval(), m.critical_interval)


class TestPrioritization(unittest.TestCase):
    def test_prioritize_micro_in_combat(self):
        m = MicroFocusMode(_StubBot())
        m.focus_level = 2
        self.assertTrue(m.should_prioritize_micro())
        m.focus_level = 3
        self.assertTrue(m.should_prioritize_micro())

    def test_no_prioritize_in_alert_or_normal(self):
        m = MicroFocusMode(_StubBot())
        m.focus_level = 0
        self.assertFalse(m.should_prioritize_micro())
        m.focus_level = 1
        self.assertFalse(m.should_prioritize_micro())


class TestUpdateActivation(unittest.TestCase):
    """update()는 combat_check_interval(11) 보다 큰 iteration이 들어와야
    실제 분석을 수행한다 (rate-limit). 따라서 iteration >= 11 사용."""

    def test_is_active_in_combat(self):
        bot = _StubBot(
            townhalls=[_Townhall(0, 0)],
            enemy=[_Unit(x, x) for x in range(3)],
        )
        m = MicroFocusMode(bot)
        m.update(12)
        self.assertTrue(m.is_active)

    def test_not_active_in_alert(self):
        bot = _StubBot(townhalls=[_Townhall(0, 0)], enemy=[_Unit(5, 5)])
        m = MicroFocusMode(bot)
        m.update(12)
        self.assertFalse(m.is_active)


if __name__ == "__main__":
    unittest.main()
