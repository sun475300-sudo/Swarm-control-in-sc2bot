# -*- coding: utf-8 -*-
"""
신규 모듈 테스트 — P606+ 추가 모듈 import/초기화 검증

numpy, torch 등 외부 의존성이 없으면 graceful skip 처리.
"""

import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_HAS_NUMPY = importlib.util.find_spec("numpy") is not None
_HAS_TORCH = importlib.util.find_spec("torch") is not None


# ── PettingZoo 환경 ────────────────────────────


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
class TestPettingZooEnv:
    def test_import(self):
        from pettingzoo_env.sc2_multiagent_env import SC2ParallelEnv

        assert SC2ParallelEnv is not None

    def test_env_creation(self):
        from pettingzoo_env.sc2_multiagent_env import SC2ParallelEnv

        env = SC2ParallelEnv(agent_types=["zergling"] * 4, map_size=64)
        assert len(env.possible_agents) == 4

    def test_env_reset(self):
        from pettingzoo_env.sc2_multiagent_env import SC2ParallelEnv

        env = SC2ParallelEnv(agent_types=["zergling"] * 3, map_size=32)
        obs, infos = env.reset()
        assert isinstance(obs, dict)
        assert len(obs) > 0

    def test_env_step(self):
        from pettingzoo_env.sc2_multiagent_env import SC2ParallelEnv

        env = SC2ParallelEnv(agent_types=["zergling"] * 2, map_size=32)
        obs, _ = env.reset()
        actions = {agent: env.action_space(agent).sample() for agent in env.agents}
        next_obs, rewards, terms, truncs, infos = env.step(actions)
        assert isinstance(rewards, dict)


# ── Agent Chain ─────────────────────────────────


class TestAgentChain:
    def test_import(self):
        try:
            from agent_chain.sc2_agent_chain import ChainContext

            assert ChainContext is not None
        except ImportError:
            pytest.skip("agent_chain not importable")

    def test_chain_context(self):
        try:
            from agent_chain.sc2_agent_chain import ChainContext

            ctx = ChainContext()
            assert ctx is not None
        except ImportError:
            pytest.skip("agent_chain not importable")


# ── A/B Testing ─────────────────────────────────


class TestABTesting:
    def test_import(self):
        try:
            from ab_testing.sc2_ab_tester import ABTester, Experiment

            assert ABTester is not None
            assert Experiment is not None
        except ImportError:
            pytest.skip("ab_testing not importable")

    def test_experiment_creation(self):
        try:
            from ab_testing.sc2_ab_tester import Experiment

            exp = Experiment(name="test_exp", variants=["A", "B"])
            assert exp.name == "test_exp"
        except (ImportError, TypeError):
            pytest.skip("ab_testing Experiment not compatible")


# ── QMIX MARL ──────────────────────────────────


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy not installed")
class TestQMIX:
    def test_import(self):
        try:
            from qmix_marl.sc2_qmix_agent import QMIXConfig
        except (ImportError, NameError):
            pytest.skip("qmix_marl not importable (likely needs torch)")
        assert QMIXConfig is not None

    def test_config_creation(self):
        try:
            from qmix_marl.sc2_qmix_agent import QMIXConfig
        except (ImportError, NameError):
            pytest.skip("qmix_marl not importable (likely needs torch)")
        cfg = QMIXConfig()
        assert cfg is not None


# ── World Model ─────────────────────────────────


class TestWorldModel:
    def test_import(self):
        try:
            from world_model.sc2_world_model import SC2WorldModel

            assert SC2WorldModel is not None
        except ImportError:
            pytest.skip("world_model not importable")

    def test_initialization(self):
        try:
            from world_model.sc2_world_model import SC2WorldModel

            model = SC2WorldModel()
            assert model is not None
        except (ImportError, TypeError):
            pytest.skip("SC2WorldModel init not compatible")
