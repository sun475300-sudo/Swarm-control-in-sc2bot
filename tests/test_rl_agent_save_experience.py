"""
Unit tests for RLAgent.save_experience_data atomic-save behavior.

Covers the P2.4 nightly-plan item: guard save_experience against
disk-full / interrupted-rename failures without losing the previously
saved experience file.
"""

import os

import numpy as np

import pytest
from wicked_zerg_challenger.local_training.rl_agent import RLAgent


def _make_agent_with_data(tmp_path):
    agent = RLAgent(model_path=str(tmp_path / "model.npz"))
    agent.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    agent.actions = [0, 1, 2]
    agent.rewards = [1.0, 2.0, 3.0]
    return agent


def test_save_experience_data_success(tmp_path):
    agent = _make_agent_with_data(tmp_path)
    target = tmp_path / "episode.npz"

    assert agent.save_experience_data(str(target)) is True
    assert target.exists()
    # no leftover temp file
    assert not (tmp_path / "episode.tmp.npz").exists()

    data = np.load(str(target))
    assert len(data["states"]) == 3
    assert len(data["rewards"]) == 3


def test_save_experience_data_preserves_existing_file_on_rename_failure(
    tmp_path, monkeypatch
):
    """If os.replace() fails mid-save (disk full / interrupted rename), the
    previously saved experience file must NOT be deleted."""
    agent = _make_agent_with_data(tmp_path)
    target = tmp_path / "episode.npz"

    # Seed an existing "previous" save.
    assert agent.save_experience_data(str(target)) is True
    original_bytes = target.read_bytes()

    def failing_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", failing_replace)

    agent.rewards = [99.0, 99.0, 99.0]  # would-be new (different) data
    result = agent.save_experience_data(str(target))

    assert result is False
    # Original file must survive untouched — no remove-then-rename data-loss window.
    assert target.exists()
    assert target.read_bytes() == original_bytes


def test_save_experience_data_cleans_up_temp_file_on_failure(tmp_path, monkeypatch):
    agent = _make_agent_with_data(tmp_path)
    target = tmp_path / "episode.npz"

    def failing_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", failing_replace)

    result = agent.save_experience_data(str(target))

    assert result is False
    assert not target.exists()
    leftover = list(tmp_path.glob("*.tmp.npz"))
    assert leftover == []
