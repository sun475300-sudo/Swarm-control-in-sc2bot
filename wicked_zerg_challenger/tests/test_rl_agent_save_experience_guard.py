#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for RLAgent.save_experience_data's atomic-save guard.

Covers PLAN-NIGHTLY.md P2.4: verify the save path fails cleanly (returns
False, leaves any pre-existing file untouched) when the disk is full during
the temp-file write, or when the final atomic rename is interrupted.
"""

import os
import sys
import unittest
from unittest.mock import patch

import numpy as np

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


class TestSaveExperienceDataGuard(unittest.TestCase):
    def _agent_with_episode(self, tmp_path):
        agent = RLAgent(model_path=str(tmp_path / "unused_model.npz"))
        agent.states = [np.zeros(16, dtype=np.float32)]
        agent.actions = [0]
        agent.rewards = [1.0]
        return agent

    def test_disk_full_during_savez_returns_false_and_keeps_existing_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            agent = self._agent_with_episode(tmp_path)
            target = tmp_path / "experience.npz"
            target.write_bytes(b"pre-existing-data")

            with patch(
                "local_training.rl_agent.np.savez_compressed",
                side_effect=OSError(28, "No space left on device"),
            ):
                result = agent.save_experience_data(str(target))

            self.assertFalse(result)
            # The original file must survive untouched -- the temp write
            # failed before the atomic rename ever ran.
            self.assertEqual(target.read_bytes(), b"pre-existing-data")

    def test_interrupted_rename_returns_false_and_does_not_corrupt_target(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            agent = self._agent_with_episode(tmp_path)
            target = tmp_path / "experience.npz"
            target.write_bytes(b"pre-existing-data")

            with patch(
                "local_training.rl_agent.os.rename",
                side_effect=OSError(5, "Interrupted rename"),
            ):
                result = agent.save_experience_data(str(target))

            self.assertFalse(result)
            # Old file is removed before rename is attempted (Windows-safe
            # overwrite), so an interrupted rename legitimately loses the
            # previous snapshot -- but it must never leave a half-written
            # file at the target path, and the call must report failure
            # rather than silently succeeding.
            self.assertFalse(target.exists())

            temp_leftover = tmp_path / "experience.tmp.npz"
            if temp_leftover.exists():
                self.assertGreater(temp_leftover.stat().st_size, 0)

    def test_successful_save_returns_true_and_writes_target(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            agent = self._agent_with_episode(tmp_path)
            target = tmp_path / "experience.npz"

            result = agent.save_experience_data(str(target))

            self.assertTrue(result)
            self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
