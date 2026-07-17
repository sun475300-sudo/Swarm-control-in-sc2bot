#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for RLAgent.save_experience_data atomic-save guarantees (PLAN-NIGHTLY P2.4).

Covers the "disk-full / interrupted-rename" scenario: a failure partway through
the save must never destroy a previously-saved file that hasn't been replaced yet.
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


class TestRlAgentSaveGuard(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rl_agent_save_test_")
        self.agent = RLAgent()
        self.agent.states = [np.zeros(15, dtype=np.float32)]
        self.agent.actions = [0]
        self.agent.rewards = [1.0]

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_succeeds_and_leaves_no_temp_file(self):
        target = Path(self.tmpdir) / "experience.npz"

        ok = self.agent.save_experience_data(str(target))

        self.assertTrue(ok)
        self.assertTrue(target.exists())
        self.assertFalse((Path(self.tmpdir) / "experience.tmp.npz").exists())

    def test_write_failure_leaves_previous_file_intact(self):
        """Simulated disk-full during np.savez_compressed must not touch the old file."""
        target = Path(self.tmpdir) / "experience.npz"
        target.write_bytes(b"previous-good-data")

        with patch(
            "local_training.rl_agent.np.savez_compressed",
            side_effect=OSError("No space left on device"),
        ):
            ok = self.agent.save_experience_data(str(target))

        self.assertFalse(ok)
        self.assertEqual(target.read_bytes(), b"previous-good-data")

    def test_interrupted_rename_does_not_delete_previous_file(self):
        """A failure during the rename step must not destroy the file it was replacing.

        Regression test for the old remove-then-rename sequence, which deleted the
        destination before attempting the rename -- an interruption there lost both
        the old and new data. os.replace() must be used instead so the destination is
        only ever atomically swapped, never removed up front.
        """
        target = Path(self.tmpdir) / "experience.npz"
        target.write_bytes(b"previous-good-data")

        with patch(
            "local_training.rl_agent.os.replace",
            side_effect=OSError("Interrupted rename"),
        ):
            ok = self.agent.save_experience_data(str(target))

        self.assertFalse(ok)
        # The previous file must survive an interrupted rename.
        self.assertTrue(target.exists())
        self.assertEqual(target.read_bytes(), b"previous-good-data")

    def test_save_overwrites_existing_file_on_success(self):
        target = Path(self.tmpdir) / "experience.npz"
        target.write_bytes(b"stale-data")

        ok = self.agent.save_experience_data(str(target))

        self.assertTrue(ok)
        self.assertNotEqual(target.read_bytes(), b"stale-data")


if __name__ == "__main__":
    unittest.main()
