# -*- coding: utf-8 -*-
"""PersonalityModule 단위 테스트.

성격 모드 전환, 게임 단계 매핑, 우위 판단, 메시지 카테고리 무결성을
SC2 봇 없이 stub으로 검증.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from personality_module import GamePhase, PersonalityMode, PersonalityModule


class _Intel:
    def __init__(self, enemy_army_supply=0.0):
        self.enemy_army_supply = enemy_army_supply


class _Workers:
    def __init__(self, amount):
        self.amount = amount


class _StubBot:
    def __init__(self, supply_used=0, enemy_supply=0, intel=None, workers=12):
        self.supply_used = supply_used
        self.supply_used_by_enemy = enemy_supply
        self.intel = intel
        self.workers = _Workers(workers)


class TestPersonalityInit(unittest.TestCase):
    def test_default_mode_neutral(self):
        p = PersonalityModule(_StubBot())
        self.assertEqual(p.mode, PersonalityMode.NEUTRAL)

    def test_custom_mode(self):
        p = PersonalityModule(_StubBot(), mode=PersonalityMode.COCKY)
        self.assertEqual(p.mode, PersonalityMode.COCKY)


class TestGamePhaseMapping(unittest.TestCase):
    def setUp(self):
        self.p = PersonalityModule(_StubBot())

    def test_opening(self):
        self.assertEqual(self.p._get_game_phase(60.0), GamePhase.OPENING)
        self.assertEqual(self.p._get_game_phase(299.0), GamePhase.OPENING)

    def test_early(self):
        self.assertEqual(self.p._get_game_phase(300.0), GamePhase.EARLY)
        self.assertEqual(self.p._get_game_phase(599.0), GamePhase.EARLY)

    def test_mid(self):
        self.assertEqual(self.p._get_game_phase(600.0), GamePhase.MID)
        self.assertEqual(self.p._get_game_phase(899.0), GamePhase.MID)

    def test_late(self):
        self.assertEqual(self.p._get_game_phase(900.0), GamePhase.LATE)
        self.assertEqual(self.p._get_game_phase(3600.0), GamePhase.LATE)


class TestIsAhead(unittest.TestCase):
    def test_not_ahead_when_no_data(self):
        bot = _StubBot(supply_used=50, enemy_supply=50, workers=12)
        self.assertFalse(PersonalityModule(bot)._is_ahead())

    def test_ahead_by_supply_30pct(self):
        bot = _StubBot(supply_used=80, enemy_supply=50, workers=12)
        self.assertTrue(PersonalityModule(bot)._is_ahead())

    def test_ahead_by_army_via_intel(self):
        bot = _StubBot(
            supply_used=50,
            enemy_supply=50,
            intel=_Intel(enemy_army_supply=10),
            workers=12,
        )
        # our_army = 50 - 12 = 38, enemy=10, 38 > 10*1.3=13 -> ahead
        self.assertTrue(PersonalityModule(bot)._is_ahead())

    def test_zero_enemy_supply_not_ahead(self):
        bot = _StubBot(supply_used=50, enemy_supply=0, workers=12)
        # 0 인 경우 분기 → not ahead (intel 없음, supply 비교 가드)
        self.assertFalse(PersonalityModule(bot)._is_ahead())


class TestModeSwitch(unittest.TestCase):
    def test_set_mode(self):
        p = PersonalityModule(_StubBot())
        p.set_mode(PersonalityMode.SILENT)
        self.assertEqual(p.mode, PersonalityMode.SILENT)

    def test_reset_clears_flags(self):
        p = PersonalityModule(_StubBot())
        p.game_start_greeted = True
        p.taunt_count = 5
        p.messages_sent.extend(["a", "b"])
        p.reset()
        self.assertFalse(p.game_start_greeted)
        self.assertEqual(p.taunt_count, 0)
        self.assertEqual(p.messages_sent, [])


class TestMessageDatabaseShape(unittest.TestCase):
    """`_init_messages`가 모드별로 비어있지 않은 메시지를 보유하는지."""

    def setUp(self):
        self.p = PersonalityModule(_StubBot())

    def test_greeting_has_messages_for_all_real_modes(self):
        greet = self.p.messages.get("greeting", {})
        for mode in (
            PersonalityMode.POLITE,
            PersonalityMode.NEUTRAL,
            PersonalityMode.COCKY,
        ):
            self.assertIn(mode, greet, f"missing greeting for {mode}")
            self.assertGreater(len(greet[mode]), 0)


class TestStatistics(unittest.TestCase):
    def test_statistics_contains_mode(self):
        p = PersonalityModule(_StubBot(), mode=PersonalityMode.COCKY)
        stats = p.get_statistics()
        self.assertEqual(stats["mode"], "cocky")


if __name__ == "__main__":
    unittest.main()
