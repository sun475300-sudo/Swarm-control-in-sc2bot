# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Load by file path: other tests in this repo insert
# ``wicked_zerg_challenger/local_training`` into ``sys.path`` first,
# and that subtree contains a *regular* ``scripts`` package with an
# ``__init__.py`` — which then shadows the project-root ``scripts``
# namespace package that exposes ``ladder_tracker``. Going through the
# importlib file-path loader keeps the test order-independent.
import importlib.util as _ilu

_LT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "ladder_tracker.py")
)
_LT_SPEC = _ilu.spec_from_file_location("scripts_ladder_tracker", _LT_PATH)
_LT_MOD = _ilu.module_from_spec(_LT_SPEC)
sys.modules[_LT_SPEC.name] = _LT_MOD
_LT_SPEC.loader.exec_module(_LT_MOD)
LadderTracker = _LT_MOD.LadderTracker


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
