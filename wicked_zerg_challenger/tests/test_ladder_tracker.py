# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Load scripts.ladder_tracker by absolute path so prior tests that injected
# wicked_zerg_challenger/ into sys.path don't shadow the top-level scripts/
# namespace package.
import importlib.util as _ilu

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LADDER_PATH = _REPO_ROOT / "scripts" / "ladder_tracker.py"
_MODNAME = "scripts_ladder_tracker"
_spec = _ilu.spec_from_file_location(_MODNAME, _LADDER_PATH)
_mod = _ilu.module_from_spec(_spec)
sys.modules[_MODNAME] = _mod  # dataclasses needs the module registered
_spec.loader.exec_module(_mod)
LadderTracker = _mod.LadderTracker


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
