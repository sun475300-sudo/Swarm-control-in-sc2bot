#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for RLAgent's atomic save paths (PLAN-NIGHTLY P2.4).

save_experience_data() / save_model() used to remove/unlink the destination
file before renaming the freshly-written temp file into place. A crash or
disk-full error between those two steps destroyed the previous good file
with nothing to replace it. Both now use os.replace(), which atomically
swaps the destination on POSIX and Windows alike, so the original file is
never observably missing.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


class TestSaveExperienceDataAtomicity(unittest.TestCase):
    def setUp(self):
        self.agent = RLAgent()
        self.agent.states = [np.zeros(15, dtype=np.float32)]
        self.agent.actions = [0]
        self.agent.rewards = [1.0]

    def test_save_overwrites_existing_file(self, tmp_path=None):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "experience.npz"
            target.write_bytes(b"stale-data")

            ok = self.agent.save_experience_data(str(target))

            self.assertTrue(ok)
            self.assertTrue(target.exists())
            # New content replaced the stale placeholder.
            with np.load(target) as data:
                self.assertEqual(len(data["rewards"]), 1)

    def test_original_file_survives_a_failed_write(self):
        """If writing the temp file raises, the original must be untouched.

        This is the exact scenario a disk-full error produces: the write to
        the .tmp file fails partway, but save_experience_data must not have
        touched the real target file at all (no remove-then-rename race).
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "experience.npz"
            target.write_bytes(b"good-data-must-survive")

            with patch(
                "local_training.rl_agent.np.savez_compressed",
                side_effect=OSError("No space left on device"),
            ):
                ok = self.agent.save_experience_data(str(target))

            self.assertFalse(ok)
            self.assertEqual(target.read_bytes(), b"good-data-must-survive")

    def test_no_intermediate_state_where_target_is_missing(self):
        """os.replace must be the only filesystem call touching the target."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "experience.npz"
            target.write_bytes(b"original")

            observed_missing = []
            real_replace = os.replace

            def spying_replace(src, dst):
                observed_missing.append(os.path.exists(dst))
                return real_replace(src, dst)

            with patch(
                "local_training.rl_agent.os.replace", side_effect=spying_replace
            ):
                ok = self.agent.save_experience_data(str(target))

            self.assertTrue(ok)
            # The target existed right up until the atomic replace call.
            self.assertTrue(observed_missing[0])


class TestSaveModelAtomicity(unittest.TestCase):
    def setUp(self):
        self.agent = RLAgent()

    def test_save_model_overwrites_existing_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "model.npz"
            target.write_bytes(b"stale-model")

            ok = self.agent.save_model(str(target))

            self.assertTrue(ok)
            self.assertNotEqual(target.read_bytes(), b"stale-model")
            with np.load(target, allow_pickle=True) as data:
                self.assertIn("W1", data)

    def test_original_model_survives_a_failed_write(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "model.npz"
            target.write_bytes(b"good-model-must-survive")

            with patch(
                "local_training.rl_agent.np.savez",
                side_effect=OSError("No space left on device"),
            ):
                ok = self.agent.save_model(str(target))

            self.assertFalse(ok)
            self.assertEqual(target.read_bytes(), b"good-model-must-survive")
            # The failed .tmp.npz sibling must be cleaned up, not left behind.
            tmp_sibling = target.with_name(target.stem + ".tmp.npz")
            self.assertFalse(tmp_sibling.exists())


if __name__ == "__main__":
    unittest.main()
