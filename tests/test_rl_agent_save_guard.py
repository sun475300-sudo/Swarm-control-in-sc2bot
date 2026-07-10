# -*- coding: utf-8 -*-
"""
Regression tests for RLAgent checkpoint persistence.

save_model() used to build its temp path as ``<name>.tmp`` and hand that
straight to ``np.savez()``. numpy appends ".npz" to any path that doesn't
already end with it, so the real file landed at ``<name>.tmp.npz`` while the
code checked ``<name>.tmp`` for existence -- that check was always False, the
rename never ran, and the function still logged success and returned True.
Every RL checkpoint save was a silent no-op.
"""

import os

import pytest

pytest.importorskip("numpy")

from wicked_zerg_challenger.local_training.rl_agent import RLAgent


class TestRLAgentSaveModel:
    def test_save_model_writes_to_target_path(self, tmp_path):
        model_path = tmp_path / "rl_agent_model.npz"
        agent = RLAgent(model_path=str(model_path))

        assert agent.save_model() is True
        assert model_path.exists()
        # No leftover temp artifacts.
        assert list(tmp_path.glob("*.tmp*")) == []

    def test_save_model_round_trips_through_load(self, tmp_path):
        model_path = tmp_path / "rl_agent_model.npz"
        agent = RLAgent(model_path=str(model_path))
        agent.baseline = 3.5
        agent.episode_count = 42

        assert agent.save_model() is True

        reloaded = RLAgent(model_path=str(model_path))
        assert reloaded._load_model() is True
        assert reloaded.baseline == pytest.approx(3.5)
        assert reloaded.episode_count == 42

    def test_save_model_explicit_path_overrides_default(self, tmp_path):
        default_path = tmp_path / "default.npz"
        override_path = tmp_path / "override.npz"
        agent = RLAgent(model_path=str(default_path))

        assert agent.save_model(str(override_path)) is True
        assert override_path.exists()
        assert not default_path.exists()

    def test_save_experience_data_writes_to_target_path(self, tmp_path):
        exp_path = tmp_path / "experience.npz"
        agent = RLAgent(model_path=str(tmp_path / "model.npz"))
        agent.states = [[0.0] * 15]
        agent.actions = [0]
        agent.rewards = [1.0]

        assert agent.save_experience_data(str(exp_path)) is True
        assert exp_path.exists()
        assert list(tmp_path.glob("*.tmp*")) == []
