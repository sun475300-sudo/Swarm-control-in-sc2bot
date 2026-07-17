#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for RLAgent.save_experience_data's atomic-save guarantee.

PLAN-NIGHTLY.md P2.4: save_experience_data must never destroy an existing
valid save file when the write is interrupted (disk full, permission error,
cross-device rename failure, crash mid-write, etc). The previous
remove-then-rename implementation deleted the destination file *before*
attempting the rename, so a failure on that last step lost both the old and
new data. This suite locks in the fix (os.replace) and its equivalent
behavior of not deleting the destination before the replace succeeds.
"""
import os
import sys

import numpy as np

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


def _make_agent_with_data(tmp_path, n=5):
    agent = RLAgent(model_path=str(tmp_path / "model.npz"))
    agent.states = [np.zeros(15, dtype=np.float32) for _ in range(n)]
    agent.actions = [0] * n
    agent.rewards = [1.0] * n
    return agent


def test_save_experience_data_round_trip(tmp_path):
    agent = _make_agent_with_data(tmp_path, n=5)
    dest = tmp_path / "experience.npz"

    assert agent.save_experience_data(str(dest)) is True
    assert dest.exists()

    loaded = np.load(dest)
    assert len(loaded["states"]) == 5


def test_save_experience_data_overwrites_existing_file(tmp_path):
    dest = tmp_path / "experience.npz"

    first = _make_agent_with_data(tmp_path, n=3)
    assert first.save_experience_data(str(dest)) is True

    second = _make_agent_with_data(tmp_path, n=8)
    assert second.save_experience_data(str(dest)) is True

    loaded = np.load(dest)
    assert len(loaded["states"]) == 8


def test_save_failure_leaves_existing_file_untouched(tmp_path, monkeypatch):
    """If np.savez_compressed raises mid-write, a pre-existing valid save
    file must survive untouched."""
    dest = tmp_path / "experience.npz"

    original_agent = _make_agent_with_data(tmp_path, n=3)
    assert original_agent.save_experience_data(str(dest)) is True
    original_bytes = dest.read_bytes()

    failing_agent = _make_agent_with_data(tmp_path, n=8)
    monkeypatch.setattr(
        "local_training.rl_agent.np.savez_compressed",
        lambda *a, **k: (_ for _ in ()).throw(OSError("simulated disk full")),
    )
    assert failing_agent.save_experience_data(str(dest)) is False
    assert dest.read_bytes() == original_bytes


def test_interrupted_rename_does_not_delete_existing_file(tmp_path, monkeypatch):
    """Regression for the remove-then-rename data-loss window: if the final
    atomic-replace step fails, the destination file must not have been
    deleted beforehand."""
    dest = tmp_path / "experience.npz"

    original_agent = _make_agent_with_data(tmp_path, n=3)
    assert original_agent.save_experience_data(str(dest)) is True
    original_bytes = dest.read_bytes()

    failing_agent = _make_agent_with_data(tmp_path, n=8)

    def failing_replace(*args, **kwargs):
        raise OSError("simulated cross-device rename failure")

    monkeypatch.setattr("local_training.rl_agent.os.replace", failing_replace)
    assert failing_agent.save_experience_data(str(dest)) is False
    assert dest.exists()
    assert dest.read_bytes() == original_bytes
