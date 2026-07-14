#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard tests for RLAgent.save_experience_data (PLAN-NIGHTLY P2.4).

Covers the failure modes the atomic-save implementation is meant to
survive: a mid-write disk-full error and an interrupted rename. In both
cases save_experience_data() must return False and must never leave the
final `path` pointing at a partial/corrupt file.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


class TestRLAgentSaveExperienceGuard(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(
            os.path.join(os.path.dirname(__file__), "_tmp_rl_agent_save_guard")
        )
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.tmp_dir / "unused_model.npz"
        self.agent = RLAgent(model_path=str(self.model_path))
        self.agent.states = [[0.0] * 16]
        self.agent.actions = [0]
        self.agent.rewards = [1.0]

    def tearDown(self):
        for f in self.tmp_dir.glob("*"):
            f.unlink()
        self.tmp_dir.rmdir()

    def test_successful_save_returns_true_and_writes_target(self):
        target = self.tmp_dir / "experience.npz"
        ok = self.agent.save_experience_data(str(target))
        self.assertTrue(ok)
        self.assertTrue(target.exists())
        # no leftover temp artifact
        leftovers = list(self.tmp_dir.glob("*.tmp*"))
        self.assertEqual(leftovers, [])

    def test_disk_full_during_write_returns_false_and_leaves_no_target(self):
        target = self.tmp_dir / "experience.npz"
        with patch(
            "local_training.rl_agent.np.savez_compressed",
            side_effect=OSError("No space left on device"),
        ):
            ok = self.agent.save_experience_data(str(target))
        self.assertFalse(ok)
        self.assertFalse(target.exists())
        leftovers = list(self.tmp_dir.glob("*.tmp*"))
        self.assertEqual(leftovers, [])

    def test_interrupted_rename_returns_false_and_does_not_corrupt_existing_target(self):
        target = self.tmp_dir / "experience.npz"
        # Seed an existing "good" file so we can prove it isn't clobbered
        # by a save that fails partway through the rename step.
        target.write_bytes(b"previous-good-data")

        with patch(
            "local_training.rl_agent.os.replace",
            side_effect=OSError("Interrupted system call"),
        ):
            ok = self.agent.save_experience_data(str(target))

        self.assertFalse(ok)
        # The old file must survive an interrupted rename untouched.
        self.assertEqual(target.read_bytes(), b"previous-good-data")


if __name__ == "__main__":
    unittest.main()
