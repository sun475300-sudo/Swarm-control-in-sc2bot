# -*- coding: utf-8 -*-
"""
Unit tests -- RLAgent.save_experience_data atomicity (PLAN-NIGHTLY P2.4).

Guards against a regression where the old "remove-then-rename" save
sequence could permanently delete existing experience data if the
process was interrupted (or the rename failed, e.g. disk full)
between the remove() and rename() calls.
"""

import os
import sys

import numpy as np

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

from local_training.rl_agent import RLAgent


@pytest.fixture
def agent_with_data(tmp_path):
    agent = RLAgent(model_path=str(tmp_path / "model.npz"))
    agent.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    agent.actions = [0, 1, 2]
    agent.rewards = [1.0, 0.5, -1.0]
    return agent


def test_save_experience_data_writes_file(agent_with_data, tmp_path):
    target = tmp_path / "exp_ep1.npz"
    assert agent_with_data.save_experience_data(str(target)) is True
    assert target.exists()

    loaded = np.load(str(target))
    assert len(loaded["states"]) == 3
    assert len(loaded["rewards"]) == 3


def test_save_experience_data_overwrites_atomically(agent_with_data, tmp_path):
    target = tmp_path / "exp_ep1.npz"
    assert agent_with_data.save_experience_data(str(target)) is True

    agent_with_data.rewards = [9.0, 9.0, 9.0]
    assert agent_with_data.save_experience_data(str(target)) is True

    loaded = np.load(str(target))
    assert list(loaded["rewards"]) == [9.0, 9.0, 9.0]


def test_save_experience_data_preserves_existing_file_on_interrupted_rename(
    agent_with_data, tmp_path, monkeypatch
):
    """If the atomic rename fails partway (e.g. disk full), the previously
    saved experience file must survive -- not be deleted with nothing to
    replace it."""
    target = tmp_path / "exp_ep1.npz"
    assert agent_with_data.save_experience_data(str(target)) is True
    original_bytes = target.read_bytes()

    def boom(*args, **kwargs):
        raise OSError("simulated disk full during rename")

    monkeypatch.setattr(os, "replace", boom)

    agent_with_data.rewards = [-5.0, -5.0, -5.0]
    result = agent_with_data.save_experience_data(str(target))

    assert result is False
    assert target.exists()
    assert target.read_bytes() == original_bytes
