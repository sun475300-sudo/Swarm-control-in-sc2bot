#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for RLAgent.save_experience_data under disk-full / interrupted-rename
conditions (PLAN-NIGHTLY.md P2.4)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


def _agent_with_episode():
    agent = RLAgent()
    agent.states = [[0.0] * 15, [1.0] * 15]
    agent.actions = [0, 1]
    agent.rewards = [1.0, -1.0]
    return agent


class TestSaveExperienceData(unittest.TestCase):
    def test_save_succeeds_and_produces_readable_file(self):
        agent = _agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "episode.npz")

            ok = agent.save_experience_data(target)

            self.assertTrue(ok)
            self.assertTrue(os.path.exists(target))
            # No leftover temp file after a successful atomic rename.
            self.assertFalse(os.path.exists(target[:-4] + ".tmp.npz"))

    def test_disk_full_during_write_returns_false_and_leaves_no_target_file(self):
        agent = _agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "episode.npz")

            with patch(
                "local_training.rl_agent.np.savez_compressed",
                side_effect=OSError(28, "No space left on device"),
            ):
                ok = agent.save_experience_data(target)

            self.assertFalse(ok)
            self.assertFalse(os.path.exists(target))

    def test_interrupted_rename_returns_false_without_raising(self):
        agent = _agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "episode.npz")

            with patch(
                "local_training.rl_agent.os.rename",
                side_effect=OSError(5, "I/O error"),
            ):
                # Must not raise - callers treat this as a best-effort save.
                ok = agent.save_experience_data(target)

            self.assertFalse(ok)
            # The temp file written by savez_compressed is orphaned but the
            # final target path must never exist after a failed rename.
            self.assertFalse(os.path.exists(target))

    def test_save_overwrites_existing_target_atomically(self):
        agent = _agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "episode.npz")
            Path(target).write_bytes(b"stale-data")

            ok = agent.save_experience_data(target)

            self.assertTrue(ok)
            self.assertGreater(os.path.getsize(target), len(b"stale-data") - 1)
            with open(target, "rb") as f:
                self.assertNotEqual(f.read(), b"stale-data")


if __name__ == "__main__":
    unittest.main()
