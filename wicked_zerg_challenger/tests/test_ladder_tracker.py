# -*- coding: utf-8 -*-
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _REPO_ROOT)

# wicked_zerg_challenger/local_training/scripts is a *separate* regular
# package also named "scripts" (has __init__.py). When both it and the
# repo root are on sys.path, Python's import system resolves the regular
# package over this namespace package (PEP 420) regardless of sys.path
# order, so `from scripts.ladder_tracker import ...` can silently bind to
# the wrong package during full-suite collection. Load by explicit path
# instead of relying on "scripts" name resolution.
_spec = importlib.util.spec_from_file_location(
    "wzc_ladder_tracker_module", os.path.join(_REPO_ROOT, "scripts", "ladder_tracker.py")
)
_ladder_tracker_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _ladder_tracker_module
_spec.loader.exec_module(_ladder_tracker_module)
LadderTracker = _ladder_tracker_module.LadderTracker


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
