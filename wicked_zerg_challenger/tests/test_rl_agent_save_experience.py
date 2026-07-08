# -*- coding: utf-8 -*-
"""
Unit tests -- RLAgent.save_experience_data atomic-save guard (PLAN-NIGHTLY P2.4)

Covers the disk-full / interrupted-rename scenarios: a failed save must
never destroy a pre-existing experience file, and must not leave a
half-written temp file behind.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from local_training.rl_agent import RLAgent


def _agent_with_data():
    agent = RLAgent()
    agent.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    agent.actions = [0, 1, 2]
    agent.rewards = [0.1, 0.2, 0.3]
    return agent


class TestSaveExperienceDataSuccess(unittest.TestCase):
    def test_round_trips_data_and_returns_true(self):
        agent = _agent_with_data()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "experience.npz")

            ok = agent.save_experience_data(target)

            self.assertTrue(ok)
            self.assertTrue(os.path.exists(target))
            loaded = np.load(target)
            self.assertEqual(len(loaded["states"]), 3)
            self.assertEqual(list(loaded["actions"]), [0, 1, 2])
            # No leftover temp file.
            self.assertFalse(os.path.exists(target[:-4] + ".tmp.npz"))


class TestSaveExperienceDataDiskFull(unittest.TestCase):
    def test_write_failure_preserves_existing_file_and_returns_false(self):
        agent = _agent_with_data()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "experience.npz")
            with open(target, "wb") as f:
                f.write(b"PRE-EXISTING-SENTINEL")

            with patch(
                "local_training.rl_agent.np.savez_compressed",
                side_effect=OSError("[Errno 28] No space left on device"),
            ):
                ok = agent.save_experience_data(target)

            self.assertFalse(ok)
            with open(target, "rb") as f:
                self.assertEqual(f.read(), b"PRE-EXISTING-SENTINEL")
            self.assertFalse(os.path.exists(target[:-4] + ".tmp.npz"))


class TestSaveExperienceDataInterruptedRename(unittest.TestCase):
    def test_replace_failure_preserves_existing_file_and_returns_false(self):
        agent = _agent_with_data()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "experience.npz")
            with open(target, "wb") as f:
                f.write(b"PRE-EXISTING-SENTINEL")

            with patch(
                "local_training.rl_agent.os.replace",
                side_effect=OSError("simulated interrupted rename"),
            ):
                ok = agent.save_experience_data(target)

            self.assertFalse(ok)
            # The old delete-then-rename implementation removed the
            # original before attempting the rename, so a failure here
            # used to destroy the caller's data. os.replace() is atomic,
            # so the original must survive a failed replace.
            with open(target, "rb") as f:
                self.assertEqual(f.read(), b"PRE-EXISTING-SENTINEL")

    def test_never_removes_destination_before_replacing(self):
        """Guards against regressing to the remove()-then-rename() pattern."""
        agent = _agent_with_data()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "experience.npz")
            with open(target, "wb") as f:
                f.write(b"PRE-EXISTING-SENTINEL")

            with patch("local_training.rl_agent.os.remove") as mock_remove:
                ok = agent.save_experience_data(target)

            self.assertTrue(ok)
            mock_remove.assert_not_called()


if __name__ == "__main__":
    unittest.main()
