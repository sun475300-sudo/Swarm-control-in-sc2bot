#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for RLAgent.save_experience_data's atomic-save guarantees (PLAN-NIGHTLY P2.4)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


def _make_agent_with_episode():
    agent = RLAgent()
    agent.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    agent.actions = [0, 1, 2]
    agent.rewards = [1.0, -0.5, 2.0]
    return agent


class TestSaveExperienceDataSuccess(unittest.TestCase):
    def test_saves_and_is_loadable(self):
        agent = _make_agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "episode.npz"
            self.assertTrue(agent.save_experience_data(str(target)))
            self.assertTrue(target.exists())
            data = np.load(target)
            self.assertEqual(len(data["states"]), 3)
            self.assertEqual(len(data["rewards"]), 3)

    def test_no_leftover_temp_file_on_success(self):
        agent = _make_agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "episode.npz"
            agent.save_experience_data(str(target))
            leftovers = [p for p in Path(tmp).iterdir() if p.name != target.name]
            self.assertEqual(leftovers, [])


class TestSaveExperienceDataDiskFull(unittest.TestCase):
    """Simulates a disk-full error while writing the temp file."""

    def test_returns_false_and_raises_nothing(self):
        agent = _make_agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "episode.npz"
            with patch(
                "numpy.savez_compressed",
                side_effect=OSError("No space left on device"),
            ):
                result = agent.save_experience_data(str(target))
            self.assertFalse(result)

    def test_existing_file_survives_a_failed_write(self):
        agent = _make_agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "episode.npz"
            # A prior, already-saved episode is at `target`.
            np.savez_compressed(str(target).removesuffix(".npz"), states=np.zeros(1))
            original_bytes = target.read_bytes()

            with patch(
                "numpy.savez_compressed",
                side_effect=OSError("No space left on device"),
            ):
                result = agent.save_experience_data(str(target))

            self.assertFalse(result)
            self.assertTrue(target.exists())
            self.assertEqual(target.read_bytes(), original_bytes)

    def test_no_leftover_temp_file_on_failure(self):
        agent = _make_agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "episode.npz"
            with patch(
                "numpy.savez_compressed",
                side_effect=OSError("No space left on device"),
            ):
                agent.save_experience_data(str(target))
            self.assertEqual(list(Path(tmp).iterdir()), [])


class TestSaveExperienceDataInterruptedRename(unittest.TestCase):
    """Simulates the process dying/erroring between writing the temp file and
    the atomic rename (e.g. a cross-device os.replace() failure)."""

    def test_returns_false_and_preserves_existing_file(self):
        agent = _make_agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "episode.npz"
            np.savez_compressed(str(target).removesuffix(".npz"), states=np.zeros(1))
            original_bytes = target.read_bytes()

            with patch("os.replace", side_effect=OSError("Invalid cross-device link")):
                result = agent.save_experience_data(str(target))

            self.assertFalse(result)
            # The previous, valid episode data must not be destroyed just
            # because the new save couldn't complete its rename.
            self.assertTrue(target.exists())
            self.assertEqual(target.read_bytes(), original_bytes)

    def test_temp_file_left_for_inspection_when_rename_fails(self):
        # os.replace() failing means the freshly-written temp file is never
        # cleaned up automatically -- that's fine (it's evidence for
        # debugging), it just must not overwrite `target`.
        agent = _make_agent_with_episode()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "episode.npz"
            with patch("os.replace", side_effect=OSError("Invalid cross-device link")):
                result = agent.save_experience_data(str(target))
            self.assertFalse(result)
            self.assertFalse(target.exists())
            leftovers = list(Path(tmp).iterdir())
            self.assertEqual(len(leftovers), 1)
            self.assertTrue(leftovers[0].name.endswith(".tmp.npz"))


if __name__ == "__main__":
    unittest.main()
