# -*- coding: utf-8 -*-
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Load by explicit file path (not `from scripts.ladder_tracker import ...`):
# `wicked_zerg_challenger/local_training/scripts/` is also a real package named
# `scripts`, so whichever one gets imported first wins the `scripts` name for
# the whole test session depending on collection order.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_spec = importlib.util.spec_from_file_location(
    "ladder_tracker_module", os.path.join(_repo_root, "scripts", "ladder_tracker.py")
)
_ladder_tracker_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _ladder_tracker_module  # dataclasses needs this registered
_spec.loader.exec_module(_ladder_tracker_module)
LadderTracker = _ladder_tracker_module.LadderTracker


class TestLadderTracker(unittest.TestCase):
    def test_record_match_updates_winrate_and_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = LadderTracker(tmp)
            tracker.record_match(
                "MediumAI", "Terran", "Simple64", "win", our_elo_after=1016
            )
            tracker.record_match(
                "MediumAI", "Terran", "Simple64", "loss", our_elo_after=1000
            )

            stats = tracker.get_winrate(vs_race="Terran")

            self.assertEqual(stats["total"], 2)
            self.assertEqual(stats["wins"], 1)
            self.assertEqual(stats["winrate"], 50.0)
            self.assertTrue(Path(tmp, "analytics.json").exists())

    def test_weakness_report_tracks_losses(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = LadderTracker(tmp)
            tracker.record_match("BioAI", "Terran", "MapA", "loss", crash_reason="")
            tracker.record_match(
                "SkytossAI", "Protoss", "MapB", "crash", crash_reason="timeout"
            )

            report = tracker.get_weakness_report()

            self.assertIn(report["worst_matchup"], {"Terran", "Protoss"})
            self.assertIn("timeout", report["crash_reasons"])


if __name__ == "__main__":
    unittest.main()
