#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression tests for RLAgent.save_model / save_experience_data (PLAN-NIGHTLY P2.4).

Covers two real bugs found while auditing the atomic-save paths:

1. save_model() computed its temp path with `.with_suffix(".tmp")`, but
   np.savez() auto-appends ".npz" to any path that doesn't already end with
   it. The temp file numpy actually wrote was therefore "<name>.tmp.npz",
   while the code checked/renamed "<name>.tmp" -- a path that never existed.
   save_model() silently no-op'd (never touched the real model file) while
   still returning True.

2. Both save_model() and save_experience_data() previously deleted the
   destination file *before* attempting the rename/move of the temp file.
   If the rename step then failed (disk full, interrupted write, permission
   error), the original -- good -- file was already gone: permanent data
   loss. Replacing remove+rename with the atomic os.replace() closes that
   window on both POSIX and Windows.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


class TestSaveModelWritesRealFile(unittest.TestCase):
    """Regression test for bug #1: save_model() must produce save_path itself."""

    def test_save_model_creates_file_at_exact_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "rl_agent_model.npz"
            agent = RLAgent(model_path=str(model_path))

            ok = agent.save_model()

            self.assertTrue(ok)
            self.assertTrue(
                model_path.exists(), "save_model() must write to the exact model_path"
            )
            # No stray "<name>.tmp.npz" left behind on success.
            self.assertFalse((Path(tmp_dir) / "rl_agent_model.tmp.npz").exists())

    def test_save_model_output_is_loadable(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "rl_agent_model.npz"
            agent = RLAgent(model_path=str(model_path))
            agent.episode_count = 42

            self.assertTrue(agent.save_model())

            reloaded = RLAgent(model_path=str(model_path))
            self.assertTrue(reloaded._load_model())
            self.assertEqual(reloaded.episode_count, 42)


class TestSaveModelFailureLeavesOriginalIntact(unittest.TestCase):
    """Regression test for bug #2: a failed save must never destroy a good file."""

    def test_disk_full_during_savez_preserves_existing_model(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "rl_agent_model.npz"
            agent = RLAgent(model_path=str(model_path))
            self.assertTrue(agent.save_model())
            original_bytes = model_path.read_bytes()

            with patch(
                "local_training.rl_agent.np.savez",
                side_effect=OSError(28, "No space left on device"),
            ):
                ok = agent.save_model()

            self.assertFalse(ok)
            self.assertTrue(model_path.exists())
            self.assertEqual(model_path.read_bytes(), original_bytes)

    def test_interrupted_replace_preserves_existing_model(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "rl_agent_model.npz"
            agent = RLAgent(model_path=str(model_path))
            self.assertTrue(agent.save_model())
            original_bytes = model_path.read_bytes()

            with patch(
                "local_training.rl_agent.os.replace",
                side_effect=OSError("simulated interrupted rename"),
            ):
                ok = agent.save_model()

            self.assertFalse(ok)
            self.assertTrue(
                model_path.exists(), "original model must survive an interrupted rename"
            )
            self.assertEqual(model_path.read_bytes(), original_bytes)


class TestSaveExperienceDataFailureLeavesOriginalIntact(unittest.TestCase):
    def _make_agent_with_experience(self, tmp_dir):
        agent = RLAgent(model_path=str(Path(tmp_dir) / "unused_model.npz"))
        agent.states = [np.zeros(15, dtype=np.float32)]
        agent.actions = [0]
        agent.rewards = [1.0]
        return agent

    def test_save_experience_data_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_path = Path(tmp_dir) / "experience.npz"
            agent = self._make_agent_with_experience(tmp_dir)

            self.assertTrue(agent.save_experience_data(str(exp_path)))
            self.assertTrue(exp_path.exists())

    def test_disk_full_during_savez_preserves_existing_experience(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_path = Path(tmp_dir) / "experience.npz"
            agent = self._make_agent_with_experience(tmp_dir)
            self.assertTrue(agent.save_experience_data(str(exp_path)))
            original_bytes = exp_path.read_bytes()

            with patch(
                "local_training.rl_agent.np.savez_compressed",
                side_effect=OSError(28, "No space left on device"),
            ):
                ok = agent.save_experience_data(str(exp_path))

            self.assertFalse(ok)
            self.assertTrue(exp_path.exists())
            self.assertEqual(exp_path.read_bytes(), original_bytes)

    def test_interrupted_replace_preserves_existing_experience(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_path = Path(tmp_dir) / "experience.npz"
            agent = self._make_agent_with_experience(tmp_dir)
            self.assertTrue(agent.save_experience_data(str(exp_path)))
            original_bytes = exp_path.read_bytes()

            with patch(
                "local_training.rl_agent.os.replace",
                side_effect=OSError("simulated interrupted rename"),
            ):
                ok = agent.save_experience_data(str(exp_path))

            self.assertFalse(ok)
            self.assertTrue(
                exp_path.exists(),
                "original experience file must survive an interrupted rename",
            )
            self.assertEqual(exp_path.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
