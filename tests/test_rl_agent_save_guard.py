# -*- coding: utf-8 -*-
"""
Unit Tests -- RLAgent save-experience / save-model crash safety (PLAN-NIGHTLY P2.4)

save_experience_data() and save_model() write to a temp file first and then
publish it under the real path. These tests lock in that the publish step is
truly atomic: if it fails partway (disk full, interrupted rename, ...), the
pre-existing file at the real path must be left untouched rather than lost.
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

np = pytest.importorskip("numpy")

from local_training.rl_agent import RLAgent  # noqa: E402


@pytest.fixture
def agent(tmp_path):
    model_path = tmp_path / "rl_agent_model.npz"
    return RLAgent(model_path=str(model_path))


def test_save_experience_data_writes_new_file(agent, tmp_path):
    agent.states = [np.zeros(agent.policy.input_dim, dtype=np.float32)]
    agent.actions = [0]
    agent.rewards = [1.0]

    exp_path = tmp_path / "experience.npz"
    assert agent.save_experience_data(str(exp_path)) is True
    assert exp_path.exists()


def test_save_experience_data_preserves_existing_file_on_replace_failure(
    agent, tmp_path
):
    exp_path = tmp_path / "experience.npz"
    exp_path.write_bytes(b"previous-good-data")

    agent.states = [np.zeros(agent.policy.input_dim, dtype=np.float32)]
    agent.actions = [0]
    agent.rewards = [1.0]

    with patch("local_training.rl_agent.os.replace", side_effect=OSError("disk full")):
        result = agent.save_experience_data(str(exp_path))

    assert result is False
    # The interrupted publish must not have deleted the previously-saved data.
    assert exp_path.read_bytes() == b"previous-good-data"


def test_save_model_writes_new_file(agent, tmp_path):
    model_path = tmp_path / "model.npz"
    assert agent.save_model(str(model_path)) is True
    assert model_path.exists()


def test_save_model_preserves_existing_file_on_replace_failure(agent, tmp_path):
    model_path = tmp_path / "model.npz"
    model_path.write_bytes(b"previous-good-model")

    with patch("local_training.rl_agent.os.replace", side_effect=OSError("disk full")):
        result = agent.save_model(str(model_path))

    assert result is False
    # The interrupted publish must not have deleted the previously-saved model.
    assert model_path.read_bytes() == b"previous-good-model"
    # The leftover temp file should be cleaned up, not left behind forever.
    # np.savez() auto-appends ".npz", so the real temp file is "<name>.tmp.npz".
    tmp_actual = str(model_path)[: -len(".npz")] + ".tmp.npz"
    assert not os.path.exists(tmp_actual)
