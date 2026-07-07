"""
Unit Tests for RLAgent.save_experience_data

Covers the atomic-save guarantee: a failure partway through the save
(disk-full during compression, or an interrupted rename/replace) must
never destroy a previously-saved experience file, and must return False
instead of raising.
"""

import os

import numpy as np

import pytest
from wicked_zerg_challenger.local_training.rl_agent import RLAgent


@pytest.fixture
def agent(tmp_path):
    a = RLAgent(model_path=str(tmp_path / "model.npz"))
    a.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    a.actions = [0, 1, 2]
    a.rewards = [1.0, -0.5, 2.0]
    return a


class TestSaveExperienceData:
    def test_successful_save_round_trip(self, agent, tmp_path):
        out_path = tmp_path / "experience.npz"

        assert agent.save_experience_data(str(out_path)) is True
        assert out_path.exists()

        data = np.load(str(out_path))
        assert len(data["states"]) == 3
        assert list(data["actions"]) == [0, 1, 2]
        assert list(data["rewards"]) == [1.0, -0.5, 2.0]

        # no leftover temp file
        assert not (tmp_path / "experience.tmp.npz").exists()

    def test_save_failure_during_compression_preserves_existing_file(
        self, agent, tmp_path, monkeypatch
    ):
        out_path = tmp_path / "experience.npz"
        assert agent.save_experience_data(str(out_path)) is True
        original_bytes = out_path.read_bytes()

        def boom(*args, **kwargs):
            raise OSError("simulated disk full")

        monkeypatch.setattr(np, "savez_compressed", boom)

        agent.rewards = [99.0, 99.0, 99.0]
        assert agent.save_experience_data(str(out_path)) is False

        # existing file must survive a failed write attempt untouched
        assert out_path.read_bytes() == original_bytes

    def test_interrupted_replace_does_not_delete_existing_file(
        self, agent, tmp_path, monkeypatch
    ):
        out_path = tmp_path / "experience.npz"
        assert agent.save_experience_data(str(out_path)) is True
        original_bytes = out_path.read_bytes()

        def boom(*args, **kwargs):
            raise OSError("simulated interrupted rename")

        monkeypatch.setattr(os, "replace", boom)

        agent.rewards = [42.0, 42.0, 42.0]
        assert agent.save_experience_data(str(out_path)) is False

        # os.replace is atomic: a failed replace must leave the original
        # file intact rather than deleting it before the swap completes.
        assert out_path.exists()
        assert out_path.read_bytes() == original_bytes

    def test_save_creates_parent_directories(self, agent, tmp_path):
        out_path = tmp_path / "nested" / "dir" / "experience.npz"
        assert agent.save_experience_data(str(out_path)) is True
        assert out_path.exists()
