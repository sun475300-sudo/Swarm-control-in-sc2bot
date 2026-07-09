# -*- coding: utf-8 -*-
"""
RLAgent.save_model / save_experience_data atomic-save guard tests.

Regression coverage for two bugs found in wicked_zerg_challenger/local_training/rl_agent.py:

1. save_model() computed its temp path with `save_path.with_suffix(".tmp")`
   (e.g. "model.npz" -> "model.tmp"), but np.savez() auto-appends ".npz" to
   any name that doesn't already end in ".npz", so the file numpy actually
   wrote was "model.tmp.npz". The subsequent `tmp_path.exists()` check
   always saw the wrong path, silently skipped the rename, and the
   function still returned True -- every "successful" save was a no-op
   that left the real model file untouched and leaked a stray .tmp.npz.

2. save_experience_data() used `os.remove(path_str)` followed by
   `os.rename(temp_actual, path_str)`. If the process died or the rename
   failed in the gap between those two calls, the original file was
   already gone and the new one was never put in its place -- a full
   data-loss window. Both methods now use os.replace(), which is atomic
   on POSIX and Windows and overwrites the destination in a single step.
"""

import os

import numpy as np

import pytest
from wicked_zerg_challenger.local_training.rl_agent import RLAgent


@pytest.fixture
def agent(tmp_path):
    return RLAgent(model_path=str(tmp_path / "unused_default_model.npz"))


class TestSaveModel:
    def test_save_model_actually_writes_the_target_file(self, agent, tmp_path):
        target = tmp_path / "model.npz"
        assert not target.exists()

        ok = agent.save_model(str(target))

        assert ok is True
        assert target.exists()

    def test_save_model_leaves_no_orphan_tmp_file(self, agent, tmp_path):
        target = tmp_path / "model.npz"
        agent.save_model(str(target))

        leftover = [p.name for p in tmp_path.iterdir() if "tmp" in p.name]
        assert leftover == []

    def test_save_model_round_trips_weights(self, agent, tmp_path):
        target = tmp_path / "model.npz"
        agent.policy.get_weights()["W1"][0, 0] = 12.5
        agent.save_model(str(target))

        with np.load(str(target)) as data:
            assert data["W1"][0, 0] == pytest.approx(12.5)
            assert int(data["episode_count"][0]) == agent.episode_count

    def test_save_model_overwrites_existing_file(self, agent, tmp_path):
        target = tmp_path / "model.npz"
        agent.save_model(str(target))
        first_mtime = target.stat().st_mtime_ns

        agent.episode_count += 1
        ok = agent.save_model(str(target))

        assert ok is True
        with np.load(str(target)) as data:
            assert int(data["episode_count"][0]) == agent.episode_count
        assert target.stat().st_mtime_ns >= first_mtime

    def test_save_model_failure_does_not_touch_existing_file(
        self, agent, tmp_path, monkeypatch
    ):
        target = tmp_path / "model.npz"
        agent.save_model(str(target))
        original_bytes = target.read_bytes()

        def boom(*_args, **_kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(np, "savez", boom)
        ok = agent.save_model(str(target))

        assert ok is False
        assert target.read_bytes() == original_bytes

    def test_save_model_cleans_up_tmp_on_replace_failure(
        self, agent, tmp_path, monkeypatch
    ):
        target = tmp_path / "model.npz"

        def boom_replace(*_args, **_kwargs):
            raise OSError("interrupted rename")

        monkeypatch.setattr(os, "replace", boom_replace)
        ok = agent.save_model(str(target))

        assert ok is False
        leftover = [p.name for p in tmp_path.iterdir() if "tmp" in p.name]
        assert leftover == []


class TestSaveExperienceData:
    def _seed_episode(self, agent):
        agent.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
        agent.actions = [0, 1, 2]
        agent.rewards = [1.0, -0.5, 2.0]

    def test_save_experience_data_creates_file_with_expected_arrays(
        self, agent, tmp_path
    ):
        self._seed_episode(agent)
        target = tmp_path / "experience.npz"

        ok = agent.save_experience_data(str(target))

        assert ok is True
        with np.load(str(target)) as data:
            assert len(data["states"]) == 3
            assert list(data["actions"]) == [0, 1, 2]

    def test_save_experience_data_leaves_no_orphan_tmp_file(self, agent, tmp_path):
        self._seed_episode(agent)
        target = tmp_path / "experience.npz"
        agent.save_experience_data(str(target))

        leftover = [p.name for p in tmp_path.iterdir() if "tmp" in p.name]
        assert leftover == []

    def test_save_experience_data_disk_full_preserves_previous_data(
        self, agent, tmp_path, monkeypatch
    ):
        self._seed_episode(agent)
        target = tmp_path / "experience.npz"
        assert agent.save_experience_data(str(target)) is True
        original_bytes = target.read_bytes()

        def boom(*_args, **_kwargs):
            raise OSError("No space left on device")

        monkeypatch.setattr(np, "savez_compressed", boom)
        ok = agent.save_experience_data(str(target))

        assert ok is False
        assert target.read_bytes() == original_bytes

    def test_save_experience_data_interrupted_replace_preserves_previous_data(
        self, agent, tmp_path, monkeypatch
    ):
        self._seed_episode(agent)
        target = tmp_path / "experience.npz"
        assert agent.save_experience_data(str(target)) is True
        original_bytes = target.read_bytes()

        def boom_replace(*_args, **_kwargs):
            raise OSError("interrupted rename")

        monkeypatch.setattr(os, "replace", boom_replace)
        ok = agent.save_experience_data(str(target))

        assert ok is False
        assert target.exists()
        assert target.read_bytes() == original_bytes
        # the half-written temp file must not be left behind either
        leftover = [p.name for p in tmp_path.iterdir() if "tmp" in p.name]
        assert leftover == []
