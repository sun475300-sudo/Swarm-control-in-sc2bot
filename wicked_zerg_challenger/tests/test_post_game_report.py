# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from monitoring.post_game_report import PostGameReport


class TestPostGameReport(unittest.TestCase):
    def test_generate_report_from_telemetry(self):
        telemetry = {
            "result": "Defeat",
            "enemy_race": "Protoss",
            "map_name": "Simple64",
            "performance": {"frames_over_320ms": 1},
            "events": [],
            "frames": [
                {
                    "game_time": 30,
                    "minerals": 200,
                    "worker_count": 14,
                    "base_count": 1,
                    "army_supply": 2,
                    "army_value": 100,
                },
                {
                    "game_time": 240,
                    "minerals": 1200,
                    "worker_count": 30,
                    "base_count": 2,
                    "army_supply": 20,
                    "army_value": 500,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "telemetry.json")
            path.write_text(json.dumps(telemetry), encoding="utf-8")

            report = PostGameReport().generate(str(path))

            self.assertEqual(report["summary"]["enemy_race"], "Protoss")
            self.assertEqual(report["economy"]["first_expansion_time"], 240)
            self.assertTrue(report["recommendations"])

    def test_empty_frames_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "empty.json")
            path.write_text(json.dumps({"frames": []}), encoding="utf-8")

            self.assertIn("error", PostGameReport().generate(str(path)))


if __name__ == "__main__":
    unittest.main()
