# -*- coding: utf-8 -*-
"""MapManager 단위 테스트.

맵 선택 모드(sequential/single/random/weighted), 통계 기록/조회,
지속화(_save_stats / _load_stats) 검증. tempfile로 격리.
"""

import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from map_manager import MAP_CHARACTERISTICS, TRAINING_MAPS, MapManager


def _new_manager():
    tmp = tempfile.mkdtemp(prefix="map_mgr_test_")
    path = Path(tmp) / "stats.json"
    return MapManager(stats_file=str(path)), path


class TestTrainingMapsManifest(unittest.TestCase):
    def test_training_maps_in_characteristics(self):
        # 각 TRAINING_MAPS 항목은 MAP_CHARACTERISTICS에 메타데이터가 있어야 한다.
        for m in TRAINING_MAPS:
            self.assertIn(m, MAP_CHARACTERISTICS, f"missing meta for {m}")

    def test_characteristics_keys_complete(self):
        for m, meta in MAP_CHARACTERISTICS.items():
            for key in ("description", "focus", "difficulty"):
                self.assertIn(key, meta, f"{m} missing {key}")


class TestSelection(unittest.TestCase):
    def test_sequential_rotates(self):
        mgr, _ = _new_manager()
        seen = [mgr.select_map("sequential") for _ in range(7)]
        # 7개 맵을 모두 한 번씩 거쳐야 한다(TRAINING_MAPS와 길이 일치)
        self.assertEqual(len(set(seen)), len(TRAINING_MAPS))

    def test_single_always_first(self):
        mgr, _ = _new_manager()
        a = mgr.select_map("single")
        b = mgr.select_map("single")
        self.assertEqual(a, b)

    def test_random_returns_known_map(self):
        random.seed(42)
        mgr, _ = _new_manager()
        result = mgr.select_map("random")
        self.assertIn(result, mgr.get_available_maps())

    def test_unknown_mode_defaults_to_sequential(self):
        mgr, _ = _new_manager()
        # 알 수 없는 mode → sequential 처럼 동작 (current_map_index 증가)
        before = mgr.current_map_index
        mgr.select_map("???")
        self.assertEqual(mgr.current_map_index, before + 1)


class TestRecordAndStats(unittest.TestCase):
    def test_record_wins_and_losses(self):
        mgr, _ = _new_manager()
        mgr.record_result("LeyLinesAIE_v3", win=True)
        mgr.record_result("LeyLinesAIE_v3", win=True)
        mgr.record_result("LeyLinesAIE_v3", win=False)
        stats = mgr.get_map_stats("LeyLinesAIE_v3")
        self.assertEqual(stats["wins"], 2)
        self.assertEqual(stats["losses"], 1)

    def test_unknown_map_returns_zero_stats(self):
        mgr, _ = _new_manager()
        self.assertEqual(mgr.get_map_stats("Nowhere"), {"wins": 0, "losses": 0})


class TestPersistence(unittest.TestCase):
    def test_save_and_reload(self):
        mgr, path = _new_manager()
        mgr.record_result("HardwireAIE", win=True)
        mgr.record_result("HardwireAIE", win=False)
        # 같은 파일을 새 MapManager로 다시 로드
        mgr2 = MapManager(stats_file=str(path))
        self.assertEqual(mgr2.get_map_stats("HardwireAIE")["wins"], 1)
        self.assertEqual(mgr2.get_map_stats("HardwireAIE")["losses"], 1)

    def test_corrupt_json_returns_empty(self):
        tmp = tempfile.mkdtemp(prefix="map_mgr_corrupt_")
        path = Path(tmp) / "stats.json"
        path.write_text("{not valid json")
        mgr = MapManager(stats_file=str(path))
        self.assertEqual(mgr.stats, {})


class TestWeightedSelection(unittest.TestCase):
    def test_lower_win_rate_higher_weight(self):
        """승률이 낮은 맵에 더 높은 가중치를 주어 학습 균형 유지."""
        mgr, _ = _new_manager()
        # 한 맵에 압도적 승리 누적 → 가중치 낮아져야 함
        for _ in range(50):
            mgr.record_result("LeyLinesAIE_v3", win=True)
        # 다른 맵은 패배 누적 → 가중치 높음
        for _ in range(50):
            mgr.record_result("HardwireAIE", win=False)
        # seed 고정 후 weighted 선택을 여러 번 → HardwireAIE가 더 자주 등장
        random.seed(0)
        picks = [mgr.select_map("weighted") for _ in range(200)]
        hardwire = picks.count("HardwireAIE")
        leylines = picks.count("LeyLinesAIE_v3")
        self.assertGreater(hardwire, leylines)


if __name__ == "__main__":
    unittest.main()
