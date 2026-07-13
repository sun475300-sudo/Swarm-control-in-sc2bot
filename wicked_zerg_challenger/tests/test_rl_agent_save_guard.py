#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for RLAgent save-experience / save-model robustness.

Covers PLAN-NIGHTLY.md P2.4: verify save_experience_data() and save_model()
degrade gracefully (return False, keep any pre-existing file intact) when
the write or the atomic rename step fails, instead of silently losing data.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


class TestSaveExperienceDataGuard(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.agent = RLAgent(model_path=os.path.join(self.tmpdir.name, "model.npz"))
        self.agent.states = [np.zeros(15, dtype=np.float32)]
        self.agent.actions = [0]
        self.agent.rewards = [1.0]
        self.exp_path = os.path.join(self.tmpdir.name, "experience.npz")

    def test_save_succeeds_and_is_loadable(self):
        ok = self.agent.save_experience_data(self.exp_path)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(self.exp_path))
        data = np.load(self.exp_path)
        self.assertEqual(len(data["rewards"]), 1)

    def test_disk_full_during_write_preserves_existing_file(self):
        # Seed an existing save so we can tell if it survives a failed write.
        self.assertTrue(self.agent.save_experience_data(self.exp_path))
        original_mtime = os.path.getmtime(self.exp_path)

        with patch(
            "local_training.rl_agent.np.savez_compressed",
            side_effect=OSError("disk full"),
        ):
            ok = self.agent.save_experience_data(self.exp_path)

        self.assertFalse(ok)
        self.assertTrue(os.path.exists(self.exp_path))
        self.assertEqual(os.path.getmtime(self.exp_path), original_mtime)

    def test_interrupted_rename_preserves_existing_file(self):
        self.assertTrue(self.agent.save_experience_data(self.exp_path))
        original_mtime = os.path.getmtime(self.exp_path)

        with patch(
            "local_training.rl_agent.os.replace",
            side_effect=OSError("interrupted rename"),
        ):
            ok = self.agent.save_experience_data(self.exp_path)

        self.assertFalse(ok)
        # The old file must still be there -- the previous remove-then-rename
        # implementation deleted it before attempting the rename, so a failed
        # rename left no file behind at all.
        self.assertTrue(os.path.exists(self.exp_path))
        self.assertEqual(os.path.getmtime(self.exp_path), original_mtime)


class TestSaveModelGuard(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.model_path = os.path.join(self.tmpdir.name, "model.npz")
        self.agent = RLAgent(model_path=self.model_path)

    def test_save_succeeds_and_is_loadable(self):
        ok = self.agent.save_model()
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(self.model_path))

    def test_disk_full_during_write_preserves_existing_file(self):
        self.assertTrue(self.agent.save_model())
        original_mtime = os.path.getmtime(self.model_path)

        with patch(
            "local_training.rl_agent.np.savez",
            side_effect=OSError("disk full"),
        ):
            ok = self.agent.save_model()

        self.assertFalse(ok)
        self.assertTrue(os.path.exists(self.model_path))
        self.assertEqual(os.path.getmtime(self.model_path), original_mtime)
        # No leftover temp file after a failed write.
        self.assertFalse(Path(self.model_path).with_suffix(".tmp").exists())

    def test_interrupted_rename_preserves_existing_file_and_cleans_temp(self):
        self.assertTrue(self.agent.save_model())
        original_mtime = os.path.getmtime(self.model_path)

        with patch(
            "local_training.rl_agent.os.replace",
            side_effect=OSError("interrupted rename"),
        ):
            ok = self.agent.save_model()

        self.assertFalse(ok)
        self.assertTrue(os.path.exists(self.model_path))
        self.assertEqual(os.path.getmtime(self.model_path), original_mtime)
        tmp_path = Path(self.model_path).parent / (
            Path(self.model_path).stem + ".tmp.npz"
        )
        self.assertFalse(tmp_path.exists())

    def test_temp_file_matches_npz_auto_suffix_behavior(self):
        # Regression guard: np.savez() appends ".npz" to any filename that
        # doesn't already end with it, so a naive ".tmp" suffix on the temp
        # path silently writes "<stem>.tmp.npz" and the rename step then
        # never finds it (save_model would return True without ever writing
        # the real destination file). Assert no such orphan is left behind.
        ok = self.agent.save_model()
        self.assertTrue(ok)
        orphan = Path(self.model_path).with_suffix(".tmp")
        self.assertFalse(orphan.exists())
        self.assertTrue(os.path.exists(self.model_path))


if __name__ == "__main__":
    unittest.main()
