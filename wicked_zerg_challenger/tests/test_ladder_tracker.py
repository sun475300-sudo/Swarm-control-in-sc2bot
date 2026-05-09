# -*- coding: utf-8 -*-
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _load_ladder_tracker():
    # 다른 테스트가 ``sys.path`` 순서를 바꾸면 ``scripts`` namespace package가
    # 잘못된 디렉토리에 캐시되어 ``scripts.ladder_tracker``를 찾지 못하는 경우가
    # 있다. 파일 경로로 직접 로드해 그 경합을 우회한다. ``dataclasses``는 모듈을
    # ``sys.modules``에서 조회하므로 exec 전에 등록해두어야 한다.
    mod_name = "scripts_ladder_tracker"
    src = os.path.join(_PROJECT_ROOT, "scripts", "ladder_tracker.py")
    spec = importlib.util.spec_from_file_location(mod_name, src)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {src}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module.LadderTracker


LadderTracker = _load_ladder_tracker()


class TestLadderTracker(unittest.TestCase):
    def test_record_match_updates_winrate_and_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = LadderTracker(tmp)
            tracker.record_match("MediumAI", "Terran", "Simple64", "win", our_elo_after=1016)
            tracker.record_match("MediumAI", "Terran", "Simple64", "loss", our_elo_after=1000)

            stats = tracker.get_winrate(vs_race="Terran")

            self.assertEqual(stats["total"], 2)
            self.assertEqual(stats["wins"], 1)
            self.assertEqual(stats["winrate"], 50.0)
            self.assertTrue(Path(tmp, "analytics.json").exists())

    def test_weakness_report_tracks_losses(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = LadderTracker(tmp)
            tracker.record_match("BioAI", "Terran", "MapA", "loss", crash_reason="")
            tracker.record_match("SkytossAI", "Protoss", "MapB", "crash", crash_reason="timeout")

            report = tracker.get_weakness_report()

            self.assertIn(report["worst_matchup"], {"Terran", "Protoss"})
            self.assertIn("timeout", report["crash_reasons"])


if __name__ == "__main__":
    unittest.main()
