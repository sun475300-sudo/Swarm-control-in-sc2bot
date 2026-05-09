# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.replay_to_training import ReplayToTrainingPipeline


class TestReplayToTrainingPipeline(unittest.TestCase):
    def test_process_replay_summaries_writes_training_data(self):
        with tempfile.TemporaryDirectory() as replay_dir, tempfile.TemporaryDirectory() as output_dir:
            summary = {
                "enemy_race": "Terran",
                "result": "Victory",
                "game_length_seconds": 600,
                "enemy_units_killed": 20,
                "resources_collected": 5000,
                "supply_blocks": 1,
            }
            Path(replay_dir, "game1.json").write_text(json.dumps(summary), encoding="utf-8")

            pipeline = ReplayToTrainingPipeline(replay_dir, output_dir)
            data = pipeline.process_replay_summaries()

            self.assertEqual(len(data), 1)
            self.assertGreater(data[0]["reward"], 0)
            self.assertTrue(Path(output_dir, "training_data.json").exists())

    def test_loss_tags_reduce_reward(self):
        pipeline = ReplayToTrainingPipeline(".", ".")
        clean = pipeline._compute_reward({"result": "loss"})
        tagged = pipeline._compute_reward({"result": "loss", "loss_tags": ["float", "late_expand"]})

        self.assertLess(tagged, clean)


if __name__ == "__main__":
    unittest.main()
