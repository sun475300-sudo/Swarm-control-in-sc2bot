"""Tests for RLAgent.save_experience_data atomic-write semantics.

Background: commit cf2d265 fixed an atomic-rename bug. The previous code
deleted the destination first and *then* renamed the temp file in, which
leaves a window where the destination is gone — if the process dies in
that window, the user has no save at all (not even the previous one).
The fix uses os.replace, which is atomic on both POSIX and Windows.

These tests pin that contract:
- A successful save produces exactly one .npz file at the requested path.
- A simulated crash mid-rename does NOT destroy a pre-existing save.
- Reload-after-save round-trips the data.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def agent():
    from wicked_zerg_challenger.local_training.rl_agent import RLAgent

    a = RLAgent()
    # Seed a tiny, deterministic episode so save has something to write.
    state = np.zeros(a.policy.input_dim, dtype=np.float32)
    a.states = [state, state]
    a.actions = [0, 1]
    a.rewards = [0.5, -0.25]
    return a


class TestAtomicSave:
    def test_save_creates_file(self, agent, tmp_path):
        target = tmp_path / "exp.npz"
        assert agent.save_experience_data(str(target)) is True
        assert target.exists()
        assert target.stat().st_size > 0

    def test_save_overwrites_existing(self, agent, tmp_path):
        target = tmp_path / "exp.npz"
        target.write_bytes(b"stale-content")
        assert agent.save_experience_data(str(target)) is True
        # New file is real numpy archive, not the stale bytes.
        assert target.read_bytes()[:4] != b"stal"

    def test_save_round_trips_arrays(self, agent, tmp_path):
        target = tmp_path / "exp.npz"
        assert agent.save_experience_data(str(target)) is True
        loaded = np.load(target)
        np.testing.assert_array_equal(loaded["actions"], np.array([0, 1]))
        np.testing.assert_allclose(loaded["rewards"], [0.5, -0.25])

    def test_no_temp_file_left_behind_on_success(self, agent, tmp_path):
        target = tmp_path / "exp.npz"
        agent.save_experience_data(str(target))
        # Walk parent dir; only the destination should remain.
        files = sorted(p.name for p in tmp_path.iterdir())
        assert files == ["exp.npz"]

    def test_crash_during_rename_preserves_existing_save(
        self, agent, tmp_path
    ):
        """Hard guarantee: if os.replace fails, the prior save is untouched.

        This regresses against the old buggy code, which did
            os.remove(target); os.rename(tmp, target)
        — a crash between the two left target gone forever.
        """
        target = tmp_path / "exp.npz"
        # Create a "previous good save".
        prev_bytes = b"PREVIOUS-GOOD-SAVE-DO-NOT-LOSE"
        target.write_bytes(prev_bytes)

        # Force the rename step to blow up.
        with patch(
            "wicked_zerg_challenger.local_training.rl_agent.os.replace",
            side_effect=OSError("simulated disk-full"),
        ):
            ok = agent.save_experience_data(str(target))

        assert ok is False, "save should report failure when rename fails"
        # Critical assertion: previous save is still present and untouched.
        assert target.exists()
        assert target.read_bytes() == prev_bytes

    def test_save_creates_parent_dirs(self, agent, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir" / "exp.npz"
        assert agent.save_experience_data(str(nested)) is True
        assert nested.exists()

    def test_does_not_use_unsafe_remove_then_rename(self):
        """Regression guard against re-introducing the buggy pattern.

        The fix in cf2d265 must NOT be reverted. We grep the source for
        the unsafe os.remove + os.rename combo within save_experience_data.
        """
        from wicked_zerg_challenger.local_training import rl_agent
        src = Path(rl_agent.__file__).read_text(encoding="utf-8")

        # Locate save_experience_data body.
        marker = "def save_experience_data"
        i = src.index(marker)
        end = src.index("\n    def ", i + len(marker))
        body = src[i:end]

        # Strip comment lines first — we're checking the call graph,
        # not prose. Without this, the doc comment that says "do NOT use
        # os.remove / os.rename" trips its own regex.
        code = "\n".join(
            line for line in body.splitlines()
            if not line.lstrip().startswith("#")
        )

        assert "os.replace(" in code, (
            "save_experience_data must use atomic os.replace()"
        )
        assert "os.rename(" not in code, (
            "save_experience_data must NOT call os.rename() "
            "(non-atomic on Windows when destination exists)"
        )
        assert "os.remove(" not in code, (
            "save_experience_data must NOT call os.remove() before rename "
            "(opens a crash window where no file exists)"
        )
