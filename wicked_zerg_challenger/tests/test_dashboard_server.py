# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from monitoring.dashboard import DashboardServer


class TestDashboardServer(unittest.TestCase):
    def test_generate_dashboard_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            telemetry = {
                "game_id": "game1",
                "result": "Victory",
                "enemy_race": "Zerg",
                "map_name": "Simple64",
                "start_time": "2026-05-09 10:00:00",
            }
            Path(tmp, "game1.json").write_text(json.dumps(telemetry), encoding="utf-8")

            server = DashboardServer(data_dir=tmp)
            html = server.generate_report()

            self.assertIn("<html", html.lower())
            self.assertIn("Victory", html)
            self.assertIn("100.0%", html)

    def test_save_dashboard_writes_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = DashboardServer(data_dir=tmp).save_dashboard()

            self.assertTrue(output.exists())
            self.assertIn("WickedZergBotPro", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
