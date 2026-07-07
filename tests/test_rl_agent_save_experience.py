# -*- coding: utf-8 -*-
"""
Unit Tests -- RLAgent.save_experience_data atomic-save guard (PLAN-NIGHTLY P2.4)

Covers:
1. Normal save round-trips states/actions/rewards correctly.
2. A failure during the write step (e.g. disk full) does not leave a
   partial/corrupt file at the destination path and returns False instead
   of raising.
3. A failure during the atomic rename step is reported as a failure and
   does not silently drop data.
"""

import os
import sys
from unittest.mock import patch

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
    import numpy as np
    from local_training.rl_agent import RLAgent
except ImportError:
    pytest.skip("RLAgent not available", allow_module_level=True)


def _agent_with_data(tmp_path):
    agent = RLAgent(model_path=str(tmp_path / "model.npz"))
    agent.states = [
        np.zeros(agent.policy.input_dim, dtype=np.float32) for _ in range(3)
    ]
    agent.actions = [0, 1, 2]
    agent.rewards = [1.0, -0.5, 2.0]
    return agent


class TestSaveExperienceDataSuccess:
    def test_round_trip(self, tmp_path):
        agent = _agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        assert agent.save_experience_data(str(out_path)) is True
        assert out_path.exists()

        loaded = np.load(str(out_path))
        assert len(loaded["states"]) == 3
        assert list(loaded["actions"]) == [0, 1, 2]
        assert list(loaded["rewards"]) == [1.0, -0.5, 2.0]

    def test_no_leftover_tmp_file(self, tmp_path):
        agent = _agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        agent.save_experience_data(str(out_path))

        leftovers = [p for p in tmp_path.iterdir() if ".tmp" in p.name]
        assert leftovers == []


class TestSaveExperienceDataFailure:
    def test_disk_full_during_write_returns_false_and_keeps_no_partial_file(
        self, tmp_path
    ):
        agent = _agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        with patch(
            "local_training.rl_agent.np.savez_compressed",
            side_effect=OSError("No space left on device"),
        ):
            result = agent.save_experience_data(str(out_path))

        assert result is False
        assert not out_path.exists()

    def test_replace_failure_returns_false_without_raising(self, tmp_path):
        agent = _agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        with patch(
            "local_training.rl_agent.os.replace",
            side_effect=OSError("Interrupted rename"),
        ):
            result = agent.save_experience_data(str(out_path))

        assert result is False
        assert not out_path.exists()

    def test_replace_failure_preserves_existing_destination(self, tmp_path):
        """os.replace() only swaps on success, so a failed replace must not
        touch (let alone delete) a pre-existing destination file — unlike the
        old remove()-then-rename() approach, which had a data-loss window."""
        agent = _agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        assert agent.save_experience_data(str(out_path)) is True
        original_bytes = out_path.read_bytes()

        with patch(
            "local_training.rl_agent.os.replace",
            side_effect=OSError("Interrupted rename"),
        ):
            result = agent.save_experience_data(str(out_path))

        assert result is False
        assert out_path.read_bytes() == original_bytes

    def test_existing_destination_preserved_when_write_fails(self, tmp_path):
        """A prior successful save must survive a subsequent failed save attempt."""
        agent = _agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        assert agent.save_experience_data(str(out_path)) is True
        original_bytes = out_path.read_bytes()

        with patch(
            "local_training.rl_agent.np.savez_compressed",
            side_effect=OSError("No space left on device"),
        ):
            result = agent.save_experience_data(str(out_path))

        assert result is False
        assert out_path.read_bytes() == original_bytes
