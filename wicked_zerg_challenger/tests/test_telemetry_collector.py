# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from monitoring.telemetry_logger_atomic import TelemetryCollector


class TestTelemetryCollector(unittest.TestCase):
    def test_records_frame_and_writes_game_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = TelemetryCollector(output_dir=tmp, sample_interval=1)
            collector.start_game("game1", "Terran", "Simple64")
            bot = SimpleNamespace(
                time=10.0,
                minerals=300,
                vespene=50,
                supply_used=20,
                supply_cap=28,
                workers=[object()] * 14,
                supply_army=6,
                townhalls=[object()],
                enemy_units=[SimpleNamespace(health=45, shield=0)],
                units=[SimpleNamespace(health=100, shield=0, can_attack=True)],
                active_strategy="macro",
                game_phase="early",
            )

            collector.record_frame(bot, iteration=1, frame_time_ms=12.5)
            collector.record_event("expansion_started", {"base_count": 2})
            path = collector.end_game("Victory")

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["result"], "Victory")
            self.assertEqual(len(data["frames"]), 1)
            self.assertEqual(data["events"][0]["type"], "expansion_started")

    def test_record_frame_skips_when_no_game_started(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = TelemetryCollector(output_dir=tmp, sample_interval=1)
            collector.record_frame(SimpleNamespace(), iteration=1, frame_time_ms=1.0)

            self.assertIsNone(collector.end_game("Victory"))


if __name__ == "__main__":
    unittest.main()
