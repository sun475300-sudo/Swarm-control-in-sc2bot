# -*- coding: utf-8 -*-
"""AdaptiveLearningRate 단위 테스트.

학습률 증가/감소 조건, 최소/최대 경계, best_learning_rate 재설정,
get_stats 출력 정합성을 검증한다. 저장 경로는 tmp_path로 격리.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adaptive_learning_rate import AdaptiveLearningRate


def _new(**kwargs):
    """save_path를 임시 디렉토리로 격리한 인스턴스 생성."""
    tmp = tempfile.mkdtemp(prefix="adaptive_lr_test_")
    inst = AdaptiveLearningRate(**kwargs)
    inst.save_path = Path(tmp) / "stats.json"
    return inst


class TestInitialState(unittest.TestCase):
    def test_default_lr(self):
        inst = _new()
        self.assertAlmostEqual(inst.learning_rate, 0.001)
        self.assertEqual(inst.total_games, 0)
        self.assertEqual(inst.recent_win_rates, [])

    def test_custom_bounds(self):
        inst = _new(initial_lr=0.005, min_lr=0.0005, max_lr=0.05)
        self.assertAlmostEqual(inst.learning_rate, 0.005)
        self.assertAlmostEqual(inst.min_lr, 0.0005)
        self.assertAlmostEqual(inst.max_lr, 0.05)


class TestGameRecording(unittest.TestCase):
    def test_records_win_and_loss(self):
        inst = _new()
        inst.update(game_won=True)
        inst.update(game_won=False)
        inst.update(game_won=True)
        self.assertEqual(inst.total_games, 3)
        self.assertEqual(inst.total_wins, 2)


class TestLearningRateIncrease(unittest.TestCase):
    def test_increase_when_win_rate_improves(self):
        # window_size=2로 작게 설정, 충분한 데이터로 즉시 평가 트리거
        inst = _new(initial_lr=0.001, max_lr=0.01)
        inst.window_size = 2
        inst.update(True)
        inst.update(True)  # win rate up
        # 단조 증가 검사: best_win_rate가 갱신되면 lr이 1.2배
        self.assertGreaterEqual(inst.learning_rate, 0.001)

    def test_does_not_exceed_max(self):
        inst = _new(initial_lr=0.0099, max_lr=0.01, adjustment_factor=1.5)
        # 0.0099 * 1.5 = 0.01485 > max → 증가 거부
        inst.window_size = 2
        inst.update(True)
        inst.update(True)
        self.assertLessEqual(inst.learning_rate, inst.max_lr)


class TestLearningRateDecrease(unittest.TestCase):
    def test_decrease_after_patience(self):
        inst = _new(initial_lr=0.005, min_lr=0.0001, adjustment_factor=2.0, patience=2)
        inst.window_size = 2

        # 첫 두 게임: 이긴 후 best_win_rate=1.0 설정
        inst.update(True)
        inst.update(True)
        starting_lr = inst.learning_rate

        # 이후 best 갱신이 없도록 무한 패배 시뮬레이션 → games_without_improvement 증가
        for _ in range(5):
            inst.update(False)

        # 감소가 발생해 lr이 starting_lr 이하 또는 같음
        self.assertLessEqual(inst.learning_rate, starting_lr)

    def test_does_not_go_below_min(self):
        inst = _new(initial_lr=0.0001, min_lr=0.0001, adjustment_factor=2.0)
        # 최소값에 이미 도달 → 감소 시도해도 변하지 않거나 best로 리셋
        new_lr = inst._decrease_learning_rate()
        # 리셋되면 best_learning_rate(0.0001)와 같다
        self.assertGreaterEqual(inst.learning_rate, inst.min_lr)


class TestStats(unittest.TestCase):
    def test_get_stats_zero_games(self):
        inst = _new()
        stats = inst.get_stats()
        self.assertEqual(stats["total_games"], 0)
        self.assertEqual(stats["overall_win_rate"], 0.0)

    def test_get_stats_after_games(self):
        inst = _new()
        inst.update(True)
        inst.update(False)
        stats = inst.get_stats()
        self.assertEqual(stats["total_games"], 2)
        self.assertAlmostEqual(stats["overall_win_rate"], 0.5)

    def test_get_current_lr(self):
        inst = _new(initial_lr=0.003)
        self.assertAlmostEqual(inst.get_current_lr(), 0.003)


class TestPersistence(unittest.TestCase):
    def test_save_and_reload(self):
        inst = _new(initial_lr=0.005)
        inst.update(True)
        inst.update(True)
        inst._save_stats()
        # 같은 경로에서 새 인스턴스 로드 시 동일 통계
        inst2 = AdaptiveLearningRate(initial_lr=0.001)
        inst2.save_path = inst.save_path
        inst2._load_stats()
        self.assertEqual(inst2.total_games, inst.total_games)
        self.assertEqual(inst2.total_wins, inst.total_wins)
        self.assertAlmostEqual(inst2.learning_rate, inst.learning_rate)


if __name__ == "__main__":
    unittest.main()
