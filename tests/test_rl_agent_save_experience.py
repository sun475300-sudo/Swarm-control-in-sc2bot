"""Tests for RLAgent.save_experience_data atomicity guarantees.

Covers PLAN-NIGHTLY P2.4 (RL agent save-experience guard).

Skipped automatically when numpy is unavailable.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

np = pytest.importorskip("numpy")

# RLAgent doesn't import sc2 at module level, so we can load it directly.
from wicked_zerg_challenger.local_training.rl_agent import RLAgent


def _agent_with_buffer(n: int = 5) -> RLAgent:
    """Build an RLAgent whose episode buffer has `n` populated samples."""
    agent = RLAgent()
    agent.states = [
        np.zeros(agent.policy.input_dim, dtype=np.float32) for _ in range(n)
    ]
    agent.actions = [i % 5 for i in range(n)]
    agent.rewards = [float(i) for i in range(n)]
    return agent


class TestSaveExperienceHappyPath:
    def test_save_writes_file(self, tmp_path: Path):
        agent = _agent_with_buffer(n=4)
        out = tmp_path / "exp.npz"

        ok = agent.save_experience_data(str(out))

        assert ok is True
        assert out.exists()
        # Loaded data is round-trippable.
        with np.load(out) as data:
            assert data["states"].shape == (4, agent.policy.input_dim)
            assert list(data["actions"]) == [0, 1, 2, 3]
            assert list(data["rewards"]) == [0.0, 1.0, 2.0, 3.0]

    def test_save_overwrites_existing_file(self, tmp_path: Path):
        out = tmp_path / "exp.npz"
        out.write_bytes(b"stale")  # pre-existing payload

        agent = _agent_with_buffer(n=2)
        ok = agent.save_experience_data(str(out))

        assert ok is True
        with np.load(out) as data:
            assert data["states"].shape == (2, agent.policy.input_dim)

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        nested = tmp_path / "a" / "b" / "c" / "exp.npz"
        agent = _agent_with_buffer(n=1)

        ok = agent.save_experience_data(str(nested))

        assert ok is True
        assert nested.exists()


class TestSaveExperienceFailureGuards:
    def test_save_failure_does_not_orphan_temp_file(self, tmp_path: Path):
        """If os.replace raises, the temp `*.tmp.npz` must not be left behind.

        This is the bug the atomic-rename rewrite fixed: the previous
        `os.remove(dest); os.rename(tmp, dest)` left litter on partial failure.
        """
        agent = _agent_with_buffer(n=3)
        out = tmp_path / "exp.npz"
        temp_litter = tmp_path / "exp.tmp.npz"

        with patch(
            "wicked_zerg_challenger.local_training.rl_agent.os.replace",
            side_effect=OSError("disk full"),
        ):
            ok = agent.save_experience_data(str(out))

        assert ok is False
        assert not out.exists(), "destination must not exist on failure"
        assert (
            not temp_litter.exists()
        ), "orphaned `.tmp.npz` should be cleaned up on failure"

    def test_save_failure_preserves_existing_destination(self, tmp_path: Path):
        """If a save fails after a previous successful save, the old file stays."""
        agent = _agent_with_buffer(n=2)
        out = tmp_path / "exp.npz"

        # First save: success.
        assert agent.save_experience_data(str(out)) is True
        original_bytes = out.read_bytes()

        # Second save: induced failure.
        with patch(
            "wicked_zerg_challenger.local_training.rl_agent.os.replace",
            side_effect=PermissionError("locked"),
        ):
            ok = agent.save_experience_data(str(out))

        assert ok is False
        # Old file must still be intact — atomicity contract.
        assert out.exists()
        assert out.read_bytes() == original_bytes

    def test_save_path_without_npz_suffix_works(self, tmp_path: Path):
        """`np.savez_compressed` auto-appends `.npz`; both forms must work."""
        agent = _agent_with_buffer(n=1)
        out = tmp_path / "exp"  # no suffix

        ok = agent.save_experience_data(str(out))

        assert ok is True
        # Caller passed `exp`, so the final file is exactly `exp` (we strip+restore).
        assert out.exists() or (tmp_path / "exp.npz").exists()
