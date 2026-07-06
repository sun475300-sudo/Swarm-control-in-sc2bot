"""RLAgent.save_experience_data robustness tests (PLAN-NIGHTLY P2.4).

`save_experience_data` writes to a `.tmp` file and atomically `os.rename`s it
onto the final path so a crash mid-write can never leave a corrupted/partial
experience file at `model_path`. These tests lock that guarantee in for:

  - the happy path (temp file is cleaned up, final file has the right data)
  - a disk-full-style failure during `np.savez_compressed` (no temp/final
    file left behind, method returns False instead of raising)
  - an interrupted `os.rename` (the write succeeded but the rename failed --
    the pre-existing final file, if any, must not be destroyed)
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import numpy as np

import pytest

try:
    from wicked_zerg_challenger.local_training.rl_agent import RLAgent

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="rl_agent module not importable")


@pytest.fixture
def agent(tmp_path):
    a = RLAgent(model_path=str(tmp_path / "model.npz"))
    a.states = [np.zeros(15, dtype=np.float32)]
    a.actions = [0]
    a.rewards = [1.0]
    return a


def test_save_experience_success_leaves_only_final_file(agent, tmp_path):
    out = tmp_path / "experience.npz"

    assert agent.save_experience_data(str(out)) is True
    assert out.exists()
    # no leftover temp file from the atomic-rename dance
    assert list(tmp_path.glob("*.tmp*")) == []

    data = np.load(str(out))
    assert data["states"].shape[0] == 1
    assert data["rewards"][0] == pytest.approx(1.0)


def test_save_experience_disk_full_during_write_is_handled(agent, tmp_path):
    out = tmp_path / "experience.npz"

    with patch(
        "wicked_zerg_challenger.local_training.rl_agent.np.savez_compressed",
        side_effect=OSError("No space left on device"),
    ):
        result = agent.save_experience_data(str(out))

    assert result is False
    assert not out.exists()
    assert list(tmp_path.glob("*.tmp*")) == []


def test_save_experience_interrupted_rename_preserves_existing_file(agent, tmp_path):
    out = tmp_path / "experience.npz"
    out.write_bytes(b"previous-episode-data")

    with patch(
        "wicked_zerg_challenger.local_training.rl_agent.os.replace",
        side_effect=OSError("interrupted rename"),
    ):
        result = agent.save_experience_data(str(out))

    assert result is False
    # the previous episode's data must survive an interrupted replace --
    # losing it silently would be worse than the save simply failing.
    assert out.read_bytes() == b"previous-episode-data"
