# -*- coding: utf-8 -*-
"""PLAN-NIGHTLY P2.4: RL agent save-experience guard.

Exercises RLAgent.save_experience_data / save_model under simulated
disk-full and interrupted-rename conditions, verifying they fail
gracefully (return False, no orphaned temp files) instead of crashing
or silently reporting success without actually writing the file.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


def _make_agent(model_path):
    agent = RLAgent(model_path=model_path)
    agent.states = [[0.0] * 15]
    agent.actions = [0]
    agent.rewards = [1.0]
    return agent


class TestSaveExperienceDataGuard(unittest.TestCase):
    def test_succeeds_and_leaves_only_the_final_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "exp.npz")
            agent = _make_agent(os.path.join(d, "model.npz"))

            self.assertTrue(agent.save_experience_data(path))
            self.assertEqual(os.listdir(d), ["exp.npz"])

    def test_disk_full_during_write_returns_false_without_orphans(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "exp.npz")
            agent = _make_agent(os.path.join(d, "model.npz"))

            with patch(
                "numpy.savez_compressed",
                side_effect=OSError(28, "No space left on device"),
            ):
                self.assertFalse(agent.save_experience_data(path))
            self.assertEqual(os.listdir(d), [])

    def test_interrupted_rename_returns_false_without_orphans(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "exp.npz")
            agent = _make_agent(os.path.join(d, "model.npz"))

            with patch("os.rename", side_effect=OSError("simulated rename failure")):
                self.assertFalse(agent.save_experience_data(path))
            # the compressed temp file must not be left behind on disk
            self.assertEqual(os.listdir(d), [])


class TestSaveModelGuard(unittest.TestCase):
    def test_succeeds_and_model_is_reloadable(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "model.npz")
            agent = RLAgent(model_path=path)

            self.assertTrue(agent.save_model(path))
            self.assertEqual(os.listdir(d), ["model.npz"])

            reloaded = RLAgent(model_path=path)
            self.assertEqual(reloaded.baseline, agent.baseline)

    def test_disk_full_during_write_returns_false_without_orphans(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "model.npz")
            agent = RLAgent(model_path=path)

            with patch(
                "numpy.savez", side_effect=OSError(28, "No space left on device")
            ):
                self.assertFalse(agent.save_model(path))
            self.assertEqual(os.listdir(d), [])

    def test_interrupted_move_falls_back_to_copy(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "model.npz")
            agent = RLAgent(model_path=path)

            with patch("shutil.move", side_effect=OSError("simulated interrupted rename")):
                self.assertTrue(agent.save_model(path))
            self.assertEqual(os.listdir(d), ["model.npz"])

    def test_move_and_copy_both_failing_returns_false_without_orphans(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "model.npz")
            agent = RLAgent(model_path=path)

            with patch("shutil.move", side_effect=OSError("move fails")), patch(
                "shutil.copy", side_effect=OSError("copy also fails")
            ):
                self.assertFalse(agent.save_model(path))
            self.assertEqual(os.listdir(d), [])


if __name__ == "__main__":
    unittest.main()
