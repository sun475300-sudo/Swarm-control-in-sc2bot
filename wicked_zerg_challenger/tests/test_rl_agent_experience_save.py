#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for RLAgent.save_experience_data() atomic-save guarantees (PLAN-NIGHTLY P2.4)."""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


def _agent_with_data():
    agent = RLAgent()
    agent.states = [[0.0] * agent.policy.input_dim for _ in range(3)]
    agent.actions = [0, 1, 2]
    agent.rewards = [1.0, -1.0, 2.0]
    return agent


def test_save_experience_data_succeeds_and_leaves_no_tmp_file():
    agent = _agent_with_data()
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "episode.npz"
        assert agent.save_experience_data(str(target)) is True
        assert target.exists()
        assert not (Path(tmp_dir) / "episode.tmp.npz").exists()


def test_save_experience_data_overwrites_existing_file_atomically():
    agent = _agent_with_data()
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "episode.npz"
        target.write_bytes(b"stale-data")

        assert agent.save_experience_data(str(target)) is True
        assert target.exists()
        assert target.read_bytes() != b"stale-data"
        assert not (Path(tmp_dir) / "episode.tmp.npz").exists()


def test_save_experience_data_failure_does_not_corrupt_or_leak_tmp_file():
    agent = _agent_with_data()
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "episode.npz"
        target.write_bytes(b"original-good-data")

        with mock.patch(
            "local_training.rl_agent.np.savez_compressed",
            side_effect=OSError("disk full"),
        ):
            assert agent.save_experience_data(str(target)) is False

        # Original file must survive an interrupted save (no corruption / data loss).
        assert target.read_bytes() == b"original-good-data"
        # No stray temp artifact left behind.
        assert not (Path(tmp_dir) / "episode.tmp.npz").exists()
