"""Tests for RLAgent.save_experience_data's atomic-save guard (PLAN-NIGHTLY P2.4).

save_experience_data() writes to a temp file and os.rename()s it onto the
final path so a save can never leave a half-written file at the destination.
These tests exercise that guarantee directly: an interrupted rename or a
failed write (e.g. disk full) must leave any pre-existing destination file
untouched and must return False rather than raising.
"""

from __future__ import annotations

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

try:
    from rl_agent import RLAgent
except ImportError:
    pytest.skip("rl_agent not importable", allow_module_level=True)


@pytest.fixture
def agent(tmp_path):
    a = RLAgent(model_path=str(tmp_path / "model.npz"))
    a.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    a.actions = [0, 1, 2]
    a.rewards = [1.0, -1.0, 0.5]
    return a


def test_save_succeeds_and_data_is_loadable(agent, tmp_path):
    target = tmp_path / "experience.npz"
    assert agent.save_experience_data(str(target)) is True
    assert target.exists()

    loaded = np.load(target)
    assert loaded["actions"].tolist() == [0, 1, 2]
    assert loaded["rewards"].tolist() == pytest.approx([1.0, -1.0, 0.5])


def test_interrupted_rename_preserves_existing_file(agent, tmp_path):
    target = tmp_path / "experience.npz"
    target.write_bytes(b"PREVIOUS_GOOD_DATA")

    with patch("os.replace", side_effect=OSError("simulated interrupted rename")):
        result = agent.save_experience_data(str(target))

    assert result is False
    # The original file must survive untouched -- no partial/corrupt overwrite.
    assert target.read_bytes() == b"PREVIOUS_GOOD_DATA"


def test_write_failure_preserves_existing_file(agent, tmp_path):
    target = tmp_path / "experience.npz"
    target.write_bytes(b"PREVIOUS_GOOD_DATA")

    with patch("numpy.savez_compressed", side_effect=OSError("simulated disk full")):
        result = agent.save_experience_data(str(target))

    assert result is False
    assert target.read_bytes() == b"PREVIOUS_GOOD_DATA"
    # No leftover temp file from the failed write attempt.
    leftovers = [p for p in tmp_path.iterdir() if p.name != target.name]
    assert leftovers == []


def test_write_failure_with_no_existing_file_leaves_nothing_behind(agent, tmp_path):
    target = tmp_path / "experience.npz"

    with patch("numpy.savez_compressed", side_effect=OSError("simulated disk full")):
        result = agent.save_experience_data(str(target))

    assert result is False
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
