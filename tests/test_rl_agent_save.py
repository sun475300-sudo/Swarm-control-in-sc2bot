"""Regression tests for ``RLAgent.save_experience_data``.

Background
----------
Commit ``cf2d265`` fixed an atomic-rename bug where ``np.savez_compressed``
auto-appends ``.npz`` to the temp basename, but the rename step was using
the basename without ``.npz``, leaving a half-written ``*.tmp.npz`` on
disk and never producing the final file.

These tests pin the contract:
    1. happy path produces a single ``.npz`` at the requested path.
    2. existing target file is replaced (atomic-overwrite semantics).
    3. arrays round-trip back through ``np.load``.
    4. tmp scratch file is cleaned up (no ``*.tmp.npz`` left behind).
    5. failed save (e.g. unwritable parent) returns ``False`` and does
       not corrupt any pre-existing target file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wicked_zerg_challenger.local_training.rl_agent import RLAgent  # noqa: E402


def _make_agent_with_episode() -> RLAgent:
    agent = RLAgent()
    rng = np.random.default_rng(0)
    for _ in range(8):
        agent.states.append(rng.standard_normal(15).astype(np.float32))
        agent.actions.append(int(rng.integers(0, 5)))
        agent.rewards.append(float(rng.standard_normal()))
    return agent


class TestAtomicSave:
    def test_creates_single_npz_at_target(self, tmp_path: Path) -> None:
        agent = _make_agent_with_episode()
        target = tmp_path / "exp.npz"

        assert agent.save_experience_data(str(target)) is True

        # exactly the requested file, no leftover tmp
        assert target.exists()
        leftovers = [p for p in tmp_path.iterdir() if p != target]
        assert leftovers == [], f"unexpected leftovers: {leftovers}"

    def test_payload_round_trips(self, tmp_path: Path) -> None:
        agent = _make_agent_with_episode()
        target = tmp_path / "exp.npz"
        agent.save_experience_data(str(target))

        with np.load(str(target)) as data:
            assert data["states"].shape == (8, 15)
            assert data["actions"].shape == (8,)
            assert data["rewards"].shape == (8,)
            assert data["actions"].dtype == np.int64
            assert data["rewards"].dtype == np.float32

    def test_overwrites_existing_target(self, tmp_path: Path) -> None:
        target = tmp_path / "exp.npz"
        target.write_bytes(b"old-corrupt-bytes")

        agent = _make_agent_with_episode()
        assert agent.save_experience_data(str(target)) is True

        # If atomic-rename worked, the file is a real npz now
        with np.load(str(target)) as data:
            assert data["states"].shape == (8, 15)

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        agent = _make_agent_with_episode()
        target = tmp_path / "nested" / "deeply" / "exp.npz"

        assert agent.save_experience_data(str(target)) is True
        assert target.exists()

    def test_failure_returns_false_without_raising(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        agent = _make_agent_with_episode()
        target = tmp_path / "exp.npz"

        # Force the rename step to blow up; save() must catch and return False
        # rather than letting the bot crash mid-game.
        import os
        original_rename = os.rename

        def boom(*_a, **_kw):
            raise OSError("simulated rename failure")

        monkeypatch.setattr(os, "rename", boom)
        try:
            ok = agent.save_experience_data(str(target))
        finally:
            monkeypatch.setattr(os, "rename", original_rename)

        assert ok is False
        assert not target.exists()
