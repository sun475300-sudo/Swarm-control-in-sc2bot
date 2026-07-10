"""RL agent save-experience guard tests (PLAN-NIGHTLY P2.4).

Locks down `RLAgent.save_experience_data`'s atomic-save behaviour under two
failure modes that can happen on a real training box:

  1. Disk-full while writing the temp file (np.savez_compressed raises).
  2. Interrupted rename while replacing an existing, previously-valid file
     (os.replace raises after the temp file was written successfully).

In both cases the method must:
  - return False instead of raising
  - leave any pre-existing valid experience file untouched (no data loss)
  - not leave an orphaned `.tmp.npz` file behind
"""

from __future__ import annotations

import os
from unittest.mock import patch

import numpy as np

import pytest

try:
    from wicked_zerg_challenger.local_training.rl_agent import RLAgent

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK, reason="rl_agent not importable (numpy required)"
)


@pytest.fixture
def agent_with_experience(tmp_path):
    agent = RLAgent(model_path=str(tmp_path / "model.npz"))
    agent.states = [np.zeros(15, dtype=np.float32)]
    agent.actions = [0]
    agent.rewards = [1.0]
    return agent


def test_save_succeeds_and_is_loadable(agent_with_experience, tmp_path):
    path = tmp_path / "exp.npz"
    assert agent_with_experience.save_experience_data(str(path)) is True
    assert path.exists()

    data = np.load(str(path))
    assert len(data["states"]) == 1
    assert len(data["rewards"]) == 1
    # no leftover temp artifacts
    assert sorted(os.listdir(tmp_path)) == [
        "exp.npz",
        "model.npz",
    ] or "exp.tmp.npz" not in os.listdir(tmp_path)


def test_disk_full_during_write_leaves_no_partial_file(agent_with_experience, tmp_path):
    path = tmp_path / "exp.npz"

    with patch(
        "numpy.savez_compressed", side_effect=OSError("No space left on device")
    ):
        result = agent_with_experience.save_experience_data(str(path))

    assert result is False
    assert not path.exists()
    assert "exp.tmp.npz" not in os.listdir(tmp_path)


def test_interrupted_rename_preserves_previous_valid_file(
    agent_with_experience, tmp_path
):
    path = tmp_path / "exp.npz"

    # First save succeeds and produces a valid file.
    assert agent_with_experience.save_experience_data(str(path)) is True
    original_bytes = path.read_bytes()

    # Second save's rename step is interrupted (e.g. AV lock / disk full mid-rename).
    with patch("os.replace", side_effect=OSError("Interrupted")):
        result = agent_with_experience.save_experience_data(str(path))

    assert result is False
    # The previous, valid experience data must survive -- this is the whole
    # point of an atomic save.
    assert path.read_bytes() == original_bytes
    # No orphaned temp file left behind for repeated failures to pile up.
    assert "exp.tmp.npz" not in os.listdir(tmp_path)


def test_interrupted_rename_with_no_prior_file_cleans_up_temp(
    agent_with_experience, tmp_path
):
    path = tmp_path / "exp.npz"

    with patch("os.replace", side_effect=OSError("Interrupted")):
        result = agent_with_experience.save_experience_data(str(path))

    assert result is False
    assert not path.exists()
    assert "exp.tmp.npz" not in os.listdir(tmp_path)
