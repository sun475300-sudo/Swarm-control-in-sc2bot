# -*- coding: utf-8 -*-
"""
Unit tests -- RLAgent.save_experience_data atomic-save guard (PLAN-NIGHTLY P2.4)

Guards against a regression where the old remove-then-rename implementation
deleted the pre-existing file before the rename, so a mid-rename failure
(disk full, interrupted process, permission error, ...) left no file at all.
"""

import glob
import os
import sys

import numpy as np
import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from local_training.rl_agent import RLAgent
except ImportError:
    pytest.skip("RLAgent not importable (numpy required)", allow_module_level=True)


def _make_agent_with_data(tmp_path):
    agent = RLAgent(model_path=str(tmp_path / "model.npz"))
    agent.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    agent.actions = [0, 1, 2]
    agent.rewards = [1.0, -1.0, 0.5]
    return agent


class TestSaveExperienceDataSuccess:
    def test_saves_and_reports_success(self, tmp_path):
        agent = _make_agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        assert agent.save_experience_data(str(out_path)) is True
        assert out_path.exists()

        data = np.load(str(out_path))
        assert len(data["states"]) == 3
        assert list(data["actions"]) == [0, 1, 2]

    def test_no_leftover_temp_file_on_success(self, tmp_path):
        agent = _make_agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        agent.save_experience_data(str(out_path))

        leftovers = glob.glob(str(tmp_path / "*.tmp*"))
        assert leftovers == []


class TestSaveExperienceDataFailureIsSafe:
    def test_existing_file_survives_a_failed_replace(self, tmp_path, monkeypatch):
        """
        A failure during the atomic rename step must NOT destroy the
        previously-saved (known-good) experience file.
        """
        agent = _make_agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        # Seed a pre-existing "known good" file.
        assert agent.save_experience_data(str(out_path)) is True
        original_bytes = out_path.read_bytes()

        # Now force the rename step to fail (simulates disk full / interrupted
        # rename / permission error) and try to overwrite with new data.
        agent.rewards = [99.0, 99.0, 99.0]
        monkeypatch.setattr(
            os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
        )

        assert agent.save_experience_data(str(out_path)) is False
        assert out_path.exists(), "existing file must not be deleted on failure"
        assert out_path.read_bytes() == original_bytes

    def test_cleans_up_temp_file_after_failed_replace(self, tmp_path, monkeypatch):
        agent = _make_agent_with_data(tmp_path)
        out_path = tmp_path / "experience.npz"

        monkeypatch.setattr(
            os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
        )

        assert agent.save_experience_data(str(out_path)) is False
        leftovers = glob.glob(str(tmp_path / "*.tmp*"))
        assert leftovers == [], f"temp file(s) left behind: {leftovers}"
