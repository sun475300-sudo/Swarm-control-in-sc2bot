# -*- coding: utf-8 -*-
"""
Unit tests for RLAgent.save_experience_data() atomic-save behaviour (P2.4).

Locks in two guarantees:
1. Happy path writes a loadable .npz with the buffered states/actions/rewards.
2. If the final rename/replace step is interrupted (disk full, process killed
   mid-rename, etc.), any pre-existing save at `path` must survive untouched
   rather than being deleted before the replacement is known to have landed.
"""

import os

import numpy as np
import pytest

try:
    from wicked_zerg_challenger.local_training.rl_agent import RLAgent
except ImportError:
    pytest.skip("RLAgent not importable", allow_module_level=True)


def _make_agent_with_buffer():
    agent = RLAgent()
    agent.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    agent.actions = [0, 1, 2]
    agent.rewards = [1.0, -0.5, 2.0]
    return agent


class TestSaveExperienceDataHappyPath:
    def test_save_creates_loadable_file(self, tmp_path):
        agent = _make_agent_with_buffer()
        target = tmp_path / "experience.npz"

        assert agent.save_experience_data(str(target)) is True
        assert target.exists()

        loaded = np.load(str(target))
        assert len(loaded["states"]) == 3
        assert list(loaded["actions"]) == [0, 1, 2]

    def test_save_creates_parent_directories(self, tmp_path):
        agent = _make_agent_with_buffer()
        target = tmp_path / "nested" / "dir" / "experience.npz"

        assert agent.save_experience_data(str(target)) is True
        assert target.exists()

    def test_save_no_temp_file_left_behind(self, tmp_path):
        agent = _make_agent_with_buffer()
        target = tmp_path / "experience.npz"

        agent.save_experience_data(str(target))

        leftovers = [p for p in tmp_path.iterdir() if p != target]
        assert leftovers == []


class TestSaveExperienceDataInterruptedReplace:
    def test_original_file_survives_interrupted_rename(self, tmp_path, monkeypatch):
        """
        Regression test: save_experience_data() used to os.remove(path) the
        existing save *before* os.rename()-ing the new temp file into place.
        If the rename step then failed (disk full, interrupted, etc.), the
        previous good save was already gone and nothing replaced it -- a
        full data loss. The fix uses os.replace(), which is atomic and never
        removes the destination unless the replacement is ready.

        Patches both os.rename and os.replace so this fails regardless of
        which rename primitive the implementation happens to call.
        """
        agent = _make_agent_with_buffer()
        target = tmp_path / "experience.npz"
        target.write_bytes(b"PREVIOUS_GOOD_SAVE")

        def boom(*_args, **_kwargs):
            raise OSError("simulated disk-full / interrupted rename")

        monkeypatch.setattr(os, "replace", boom)
        monkeypatch.setattr(os, "rename", boom)

        result = agent.save_experience_data(str(target))

        assert result is False
        assert target.read_bytes() == b"PREVIOUS_GOOD_SAVE"

    def test_disk_full_during_write_leaves_original_untouched(
        self, tmp_path, monkeypatch
    ):
        agent = _make_agent_with_buffer()
        target = tmp_path / "experience.npz"
        target.write_bytes(b"PREVIOUS_GOOD_SAVE")

        def boom(*_args, **_kwargs):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(np, "savez_compressed", boom)

        result = agent.save_experience_data(str(target))

        assert result is False
        assert target.read_bytes() == b"PREVIOUS_GOOD_SAVE"
