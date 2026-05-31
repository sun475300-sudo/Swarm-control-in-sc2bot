# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import importlib.util as _importlib_util

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _PROJECT_ROOT)

_LADDER_PATH = os.path.join(_PROJECT_ROOT, "scripts", "ladder_tracker.py")
_spec = _importlib_util.spec_from_file_location("scripts_ladder_tracker", _LADDER_PATH)
_mod = _importlib_util.module_from_spec(_spec)
sys.modules["scripts_ladder_tracker"] = _mod
_spec.loader.exec_module(_mod)
LadderTracker = _mod.LadderTracker


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
