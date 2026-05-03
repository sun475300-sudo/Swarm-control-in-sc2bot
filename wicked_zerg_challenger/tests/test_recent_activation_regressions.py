# -*- coding: utf-8 -*-
"""Regression tests for recently activated dead-code paths.

이 테스트들은 최근 dead-code 정리 과정에서 활성화한 로직이 다시
무력화(미사용 변수 상태로 회귀)되는 것을 막는다.

대상:
- meta_game_analyzer: race/map_performance가 wins뿐 아니라 losses도
  누적되는지 + recommend_strategy 신뢰도가 표본 누적에 따라 조정되는지.
- proxy_detector: 적 본진과 멀리 떨어진 비-확장 빌딩을 0.95 confidence로
  마킹하는지.
- strategy_manager._adapt_zvz_strategy: ravager 4기+ 시 hydra 비중을
  올리는지.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestMetaGameAnalyzerLossesTracked(unittest.TestCase):
    def setUp(self):
        from meta_game_analyzer import MetaGameAnalyzer

        self.mga = MetaGameAnalyzer()

    def test_record_game_tracks_losses_for_race_and_map(self):
        # 패배 1판
        self.mga.record_game(
            {"strategy": "MACRO", "win": 0, "enemy_race": "terran", "map": "Cradle"}
        )
        self.assertEqual(self.mga.race_performance["terran"]["wins"], 0)
        self.assertEqual(self.mga.race_performance["terran"]["losses"], 1)
        self.assertEqual(self.mga.map_performance["Cradle"]["wins"], 0)
        self.assertEqual(self.mga.map_performance["Cradle"]["losses"], 1)

    def test_record_game_tracks_wins_for_race_and_map(self):
        self.mga.record_game(
            {"strategy": "MACRO", "win": 1, "enemy_race": "zerg", "map": "Pillars"}
        )
        self.assertEqual(self.mga.race_performance["zerg"]["wins"], 1)
        self.assertEqual(self.mga.race_performance["zerg"]["losses"], 0)

    def test_recommend_strategy_uses_race_and_map_history(self):
        # 동일 race/map 11판 100% 승률 누적 → confidence 상향
        for _ in range(11):
            self.mga.record_game(
                {
                    "strategy": "MACRO",
                    "win": 1,
                    "enemy_race": "terran",
                    "map": "Cradle",
                }
            )
        rec = self.mga.recommend_strategy("terran", "Cradle")
        self.assertGreater(rec["confidence"], 0.75)
        self.assertIn("race n=", rec["reasoning"])
        self.assertIn("map n=", rec["reasoning"])

    def test_recommend_strategy_uses_low_winrate_to_lower_confidence(self):
        # 동일 race 11판 0% 승률 → confidence 하향
        for _ in range(11):
            self.mga.record_game(
                {
                    "strategy": "MACRO",
                    "win": 0,
                    "enemy_race": "protoss",
                    "map": "Cradle",
                }
            )
        rec = self.mga.recommend_strategy("protoss", "Cradle")
        self.assertLess(rec["confidence"], 0.75)


class TestProxyDetectorDistanceBoost(unittest.TestCase):
    def setUp(self):
        from proxy_detector import ProxyDetector

        self.det = ProxyDetector()
        self.det.initialize_normal_expansions([(120, 120)])
        # _is_near_start은 (0,0)/(150,150)/(150,0)/(0,150) 중 가까운 곳을 검사.
        # _distance_to_enemy_base 도 동일 좌표 셋을 사용하므로 (75,75)는 양쪽
        # 모두에서 멀리 있는 위치다.

    def test_far_proxy_gets_high_confidence(self):
        # (75, 75)는 모든 start_location 후보로부터 멀리 떨어진 비-확장 위치.
        # 이 위치의 게이트웨이는 confidence ≥ 0.9로 분류되어야 한다.
        result = self.det.analyze_enemy_building((75, 75), "gateway")
        self.assertTrue(result.is_proxy)
        self.assertGreaterEqual(result.confidence, 0.9)


class TestZvZRavagerBranch(unittest.TestCase):
    def setUp(self):
        from strategy_manager import EnemyRace, GamePhase, StrategyManager

        self.bot = Mock()
        self.bot.time = 200.0
        self.bot.iteration = 0
        self.bot.minerals = 0
        self.bot.vespene = 0
        self.bot.supply_used = 30
        self.bot.supply_cap = 50
        self.bot.workers = Mock()
        self.bot.townhalls = Mock()
        # blackboard 호환 — None이면 기본값 사용 경로
        self.bot.blackboard = None

        self.sm = StrategyManager(self.bot)
        # ZvZ로 강제
        self.sm.detected_enemy_race = EnemyRace.ZERG
        self.sm.game_phase = GamePhase.MID
        # 적 컴포지션 캐시: 레이바저 5기
        self.sm._cached_enemy_composition = {
            "ZERGLING": 0,
            "BANELING": 0,
            "ROACH": 0,
            "MUTALISK": 0,
            "HYDRALISK": 0,
            "RAVAGER": 5,
        }

    def test_ravager_threshold_boosts_hydra_ratio(self):
        # 호출 후 hydra 비중이 zergling보다 커야 한다 (raised from 0).
        self.sm._counter_zerg_units()
        ratios = self.sm.race_unit_ratios.get(self.sm.detected_enemy_race, {}).get(
            self.sm.game_phase, {}
        )
        # _adjust_unit_ratio는 sum=1.0으로 정규화하므로 절대값은 의미가 없고
        # 상대 비율을 비교한다. hydra는 적어도 zergling 이상이어야 한다.
        self.assertGreaterEqual(
            ratios.get("hydra", 0),
            ratios.get("zergling", 0),
        )


if __name__ == "__main__":
    unittest.main()
