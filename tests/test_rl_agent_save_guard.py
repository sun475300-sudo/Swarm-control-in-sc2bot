# -*- coding: utf-8 -*-
"""
Unit Tests -- RLAgent save-experience / save-model guard (PLAN-NIGHTLY P2.4)

Verifies that save_experience_data() and save_model() never destroy existing
on-disk data when the write is interrupted mid-way (disk full, rename failure,
etc). Both methods write to a temp file first and must only replace the real
target via an atomic os.replace() -- never delete-then-write, which leaves a
window where a failed write loses both the old and the new data.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from local_training.rl_agent import RLAgent
except ImportError:
    pytest.skip("rl_agent not importable", allow_module_level=True)


@pytest.fixture
def agent(tmp_path):
    a = RLAgent(model_path=str(tmp_path / "model.npz"))
    a.states = [[0.0] * a.policy.input_dim for _ in range(3)]
    a.actions = [0, 1, 2]
    a.rewards = [0.1, 0.2, 0.3]
    return a


class TestSaveExperienceData:
    def test_success_writes_file_and_no_leftover_temp(self, agent, tmp_path):
        target = tmp_path / "experience.npz"
        assert agent.save_experience_data(str(target)) is True
        assert target.exists()
        assert list(tmp_path.glob("*.tmp*")) == []

    def test_disk_full_during_write_preserves_existing_file(
        self, agent, tmp_path, monkeypatch
    ):
        target = tmp_path / "experience.npz"
        target.write_bytes(b"old-experience-data")

        def boom(*args, **kwargs):
            raise OSError("No space left on device")

        monkeypatch.setattr("local_training.rl_agent.np.savez_compressed", boom)

        assert agent.save_experience_data(str(target)) is False
        # Old data must survive a failed write attempt.
        assert target.read_bytes() == b"old-experience-data"
        assert list(tmp_path.glob("*.tmp*")) == []

    def test_interrupted_rename_preserves_existing_file(
        self, agent, tmp_path, monkeypatch
    ):
        target = tmp_path / "experience.npz"
        target.write_bytes(b"old-experience-data")

        real_replace = os.replace

        def boom(*args, **kwargs):
            raise OSError("simulated rename failure")

        monkeypatch.setattr("local_training.rl_agent.os.replace", boom)

        assert agent.save_experience_data(str(target)) is False
        # The old file must NOT have been deleted before the rename failed.
        assert target.read_bytes() == b"old-experience-data"

        monkeypatch.setattr("local_training.rl_agent.os.replace", real_replace)


class TestSaveModel:
    def test_success_writes_file_and_no_leftover_temp(self, agent, tmp_path):
        target = tmp_path / "model.npz"
        assert agent.save_model(str(target)) is True
        assert target.exists()
        assert not target.with_suffix(".tmp").exists()

    def test_interrupted_rename_preserves_existing_file(
        self, agent, tmp_path, monkeypatch
    ):
        target = tmp_path / "model.npz"
        target.write_bytes(b"old-model-data")

        def boom(*args, **kwargs):
            raise OSError("simulated rename failure")

        monkeypatch.setattr("local_training.rl_agent.os.replace", boom)

        assert agent.save_model(str(target)) is False
        # The old checkpoint must survive a failed rename -- losing a trained
        # model to a transient rename error would be a severe regression.
        assert target.read_bytes() == b"old-model-data"
