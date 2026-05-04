# -*- coding: utf-8 -*-
"""
Unit tests for game_config.py — central GameConfig class & profile presets.

Doesn't depend on sc2/burnysc2 — pure config logic.
"""

import json
import os
import sys
import tempfile
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game_config import AggressiveConfig, EconomicConfig, GameConfig, SafeConfig


class TestGameConfigConstants(unittest.TestCase):
    """Phase timing / threshold sanity checks — guard against accidental edits."""

    def test_phase_timings_monotonic(self):
        """오프닝 < 초반 < 중반 종료 시간이 단조 증가."""
        self.assertLess(GameConfig.OPENING_PHASE_END, GameConfig.EARLY_GAME_END)
        self.assertLess(GameConfig.EARLY_GAME_END, GameConfig.MID_GAME_END)

    def test_drone_limits_consistent(self):
        """가스 포함 드론 한도가 미네랄 한도보다 큼."""
        self.assertGreater(
            GameConfig.DRONE_LIMIT_PER_BASE_GAS, GameConfig.DRONE_LIMIT_PER_BASE
        )
        self.assertLessEqual(GameConfig.MIN_DRONES, GameConfig.MAX_DRONES)

    def test_mineral_thresholds_monotonic(self):
        """미네랄: banking < overflow < critical"""
        self.assertLess(
            GameConfig.MINERAL_BANKING_THRESHOLD, GameConfig.MINERAL_OVERFLOW
        )
        self.assertLess(GameConfig.MINERAL_OVERFLOW, GameConfig.MINERAL_CRITICAL)

    def test_gas_overflow_critical_relationship(self):
        """가스 overflow 임계값은 critical 보다 작다."""
        self.assertLess(GameConfig.GAS_OVERFLOW_THRESHOLD, GameConfig.GAS_CRITICAL)
        # GAS_CRITICAL == 800 회귀 가드 (Phase 16: 1000→800)
        self.assertEqual(GameConfig.GAS_CRITICAL, 800)

    def test_engage_retreat_ratio_sane(self):
        """RETREAT < ENGAGE 이어야 무한 진퇴 루프 방지."""
        self.assertLess(GameConfig.RETREAT_ARMY_RATIO, GameConfig.ENGAGE_ARMY_RATIO)

    def test_supply_buffer_increases_through_game(self):
        """opening = early ≤ mid (보급 여유분이 점진 증가 또는 유지)."""
        # opening/early 같은 값(6)이라 OK; mid 가 더 커야 한다 (블록 방지).
        self.assertEqual(
            GameConfig.SUPPLY_BUFFER_OPENING, GameConfig.SUPPLY_BUFFER_EARLY
        )
        self.assertGreater(GameConfig.SUPPLY_BUFFER_MID, GameConfig.SUPPLY_BUFFER_EARLY)


class TestGameConfigSerialization(unittest.TestCase):
    """to_dict/load_from_dict/save_to_file/load_from_file 동작 확인."""

    def test_to_dict_only_json_serializable(self):
        """to_dict 결과는 모두 JSON-serializable 한 타입."""
        d = GameConfig.to_dict()
        # 적어도 우리가 위에서 회귀 검사한 키들이 들어 있어야 함
        self.assertIn("OPENING_PHASE_END", d)
        self.assertIn("GAS_CRITICAL", d)
        # JSON 직렬화가 통과해야 함
        s = json.dumps(d)
        self.assertIsInstance(s, str)

    def test_load_from_dict_overrides(self):
        """load_from_dict 가 기존 값을 덮어쓴다."""
        original = GameConfig.OPENING_PHASE_END
        try:
            GameConfig.load_from_dict({"OPENING_PHASE_END": 999})
            self.assertEqual(GameConfig.OPENING_PHASE_END, 999)
        finally:
            # 원복 (다른 테스트에 영향 없도록)
            GameConfig.OPENING_PHASE_END = original

    def test_load_from_dict_ignores_unknown_keys(self):
        """없는 attribute 는 조용히 무시 (AttributeError 발생 X)."""
        before_attrs = set(vars(GameConfig).keys())
        GameConfig.load_from_dict({"DEFINITELY_NOT_A_REAL_KEY": 42})
        after_attrs = set(vars(GameConfig).keys())
        # 새 attribute 가 추가되지 않아야 함
        self.assertEqual(before_attrs, after_attrs)

    def test_save_and_load_roundtrip(self):
        """save_to_file → load_from_file 라운드트립."""
        original = GameConfig.MAX_DRONES
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                tmp_path = f.name

            GameConfig.MAX_DRONES = 77
            GameConfig.save_to_file(tmp_path)

            # 다른 값으로 변경한 뒤 다시 load 했을 때 77 로 복구
            GameConfig.MAX_DRONES = 1
            GameConfig.load_from_file(tmp_path)
            self.assertEqual(GameConfig.MAX_DRONES, 77)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            GameConfig.MAX_DRONES = original

    def test_save_to_file_handles_filename_only_path(self):
        """디렉토리 없는 파일명을 줘도 os.makedirs('') 로 크래시하지 않음 (#7 fix)."""
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                # 디렉토리 부분이 없는 순수 파일명
                GameConfig.save_to_file("config.json")
                self.assertTrue(os.path.exists(os.path.join(tmpdir, "config.json")))
            finally:
                os.chdir(cwd)

    def test_load_from_file_missing_path_is_noop(self):
        """존재하지 않는 파일은 조용히 경고 후 return."""
        # 예외 없이 끝나야 함
        GameConfig.load_from_file("/tmp/__definitely_not_exists__.json")


class TestGameConfigProfiles(unittest.TestCase):
    """공격/경제/안전 프로필 차이 확인."""

    def test_aggressive_has_smaller_drone_limit(self):
        """공격 프로필은 드론을 적게 모은다."""
        self.assertLess(
            AggressiveConfig.DRONE_LIMIT_PER_BASE, GameConfig.DRONE_LIMIT_PER_BASE
        )

    def test_economic_has_larger_drone_limit(self):
        """경제 프로필은 드론을 더 많이 모은다."""
        self.assertGreater(
            EconomicConfig.DRONE_LIMIT_PER_BASE, GameConfig.DRONE_LIMIT_PER_BASE
        )

    def test_economic_expands_earlier(self):
        """경제 프로필은 자연 확장이 빠르다."""
        self.assertLess(
            EconomicConfig.NATURAL_EXPANSION_TIMING,
            GameConfig.NATURAL_EXPANSION_TIMING,
        )

    def test_aggressive_expands_later(self):
        """공격 프로필은 자연 확장을 늦춘다."""
        self.assertGreater(
            AggressiveConfig.NATURAL_EXPANSION_TIMING,
            GameConfig.NATURAL_EXPANSION_TIMING,
        )

    def test_safe_has_more_early_zerglings(self):
        """안전 프로필은 초반 저글링 목표가 더 많다."""
        self.assertGreater(
            SafeConfig.EARLY_ZERGLING_TARGET_2MIN,
            GameConfig.EARLY_ZERGLING_TARGET_2MIN,
        )
        self.assertGreater(
            SafeConfig.EARLY_ZERGLING_TARGET_3MIN,
            GameConfig.EARLY_ZERGLING_TARGET_3MIN,
        )


if __name__ == "__main__":
    unittest.main()
