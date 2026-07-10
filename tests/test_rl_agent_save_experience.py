# -*- coding: utf-8 -*-
"""
Unit tests for RLAgent.save_experience_data (PLAN-NIGHTLY.md P2.4)

Covers the atomic-save contract: on success the target .npz exists and no
temp file is left behind; on failure the function returns False and any
pre-existing target file is left untouched (no partial/corrupt overwrite).
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "wicked_zerg_challenger", "local_training"
    ),
)

from local_training.rl_agent import RLAgent


@pytest.fixture
def agent(tmp_path):
    a = RLAgent(model_path=str(tmp_path / "model.npz"))
    a.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    a.actions = [0, 1, 2]
    a.rewards = [1.0, -0.5, 2.0]
    return a


def test_save_experience_data_success(agent, tmp_path):
    target = tmp_path / "experience.npz"

    result = agent.save_experience_data(str(target))

    assert result is True
    assert target.exists()
    # No leftover temp artifact from the atomic-rename dance.
    assert not (tmp_path / "experience.tmp.npz").exists()

    data = np.load(str(target))
    assert len(data["states"]) == 3
    assert len(data["rewards"]) == 3
    np.testing.assert_allclose(data["rewards"], [1.0, -0.5, 2.0])


def test_save_experience_data_creates_parent_dirs(agent, tmp_path):
    target = tmp_path / "nested" / "dir" / "experience.npz"

    result = agent.save_experience_data(str(target))

    assert result is True
    assert target.exists()


def test_save_experience_data_overwrite_replaces_contents(agent, tmp_path):
    target = tmp_path / "experience.npz"

    assert agent.save_experience_data(str(target)) is True

    agent.rewards = [9.0, 9.0, 9.0]
    assert agent.save_experience_data(str(target)) is True

    data = np.load(str(target))
    np.testing.assert_allclose(data["rewards"], [9.0, 9.0, 9.0])
    assert not (tmp_path / "experience.tmp.npz").exists()


def test_save_experience_data_failure_preserves_existing_file(agent, tmp_path):
    target = tmp_path / "experience.npz"
    assert agent.save_experience_data(str(target)) is True
    original_bytes = target.read_bytes()

    with patch(
        "local_training.rl_agent.np.savez_compressed",
        side_effect=OSError("disk full"),
    ):
        result = agent.save_experience_data(str(target))

    assert result is False
    # Original file must be untouched -- failure happens before the
    # remove+rename step, so a half-written save can't clobber good data.
    assert target.read_bytes() == original_bytes
    assert not (tmp_path / "experience.tmp.npz").exists()


def test_save_experience_data_failure_when_no_existing_file(agent, tmp_path):
    target = tmp_path / "experience.npz"

    with patch(
        "local_training.rl_agent.np.savez_compressed",
        side_effect=OSError("disk full"),
    ):
        result = agent.save_experience_data(str(target))

    assert result is False
    assert not target.exists()
