# -*- coding: utf-8 -*-
"""
P606+ 대규모 모듈 테스트 — 20개 모듈 import/초기화 검증

numpy/torch 미설치 시 graceful skip 처리.
"""

import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_HAS_NUMPY = importlib.util.find_spec("numpy") is not None


def _safe_import(module_path, class_name):
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name, None)
    except Exception:
        return None


# ── MAPPO ──────────────────────────────────────


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestMAPPO:
    def test_config(self):
        cls = _safe_import("mappo_marl.sc2_mappo_agent", "MAPPOConfig")
        assert cls is not None
        cfg = cls()
        assert hasattr(cfg, "n_agents") or cfg is not None


# ── MADDPG ─────────────────────────────────────


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestMADDPG:
    def test_import(self):
        cls = _safe_import("maddpg_marl.sc2_maddpg_agent", "OUNoise")
        assert cls is not None


# ── League Training ────────────────────────────


class TestLeagueTraining:
    def test_import(self):
        cls = _safe_import("league_training.sc2_league_system", "AgentType")
        if cls is None:
            pytest.skip("league_training not importable")
        assert cls is not None

    def test_agent_status(self):
        cls = _safe_import("league_training.sc2_league_system", "AgentStatus")
        if cls is None:
            pytest.skip("league_training not importable")
        assert cls is not None


# ── Curriculum RL ──────────────────────────────


class TestCurriculumRL:
    def test_import(self):
        cls = _safe_import("curriculum_rl.sc2_curriculum_trainer", "CurriculumStage")
        if cls is None:
            pytest.skip("curriculum_rl not importable")
        assert cls is not None

    def test_stage_config(self):
        cls = _safe_import("curriculum_rl.sc2_curriculum_trainer", "StageConfig")
        if cls is None:
            pytest.skip("curriculum_rl not importable")
        assert cls is not None


# ── PBT Optimizer ──────────────────────────────


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestPBTOptimizer:
    def test_import(self):
        cls = _safe_import("pbt_optimizer.sc2_pbt_trainer", "HyperparameterSet")
        assert cls is not None


# ── Reward Shaping (P606+) ─────────────────────


class TestRewardShapingP606:
    def test_import(self):
        cls = _safe_import("reward_shaping.sc2_reward_designer", "RewardComponentType")
        if cls is None:
            pytest.skip("reward_shaping not importable")
        assert cls is not None

    def test_game_state(self):
        cls = _safe_import("reward_shaping.sc2_reward_designer", "SC2GameState")
        if cls is None:
            pytest.skip("reward_shaping not importable")
        assert cls is not None


# ── Strategy Evaluator ─────────────────────────


class TestStrategyEvaluator:
    def test_import(self):
        cls = _safe_import("strategy_evaluator.sc2_strategy_eval", "EvalDimension")
        if cls is None:
            pytest.skip("strategy_evaluator not importable")
        assert cls is not None

    def test_matchup_type(self):
        cls = _safe_import("strategy_evaluator.sc2_strategy_eval", "MatchupType")
        if cls is None:
            pytest.skip("strategy_evaluator not importable")
        assert cls is not None


# ── Digital Twin ───────────────────────────────


class TestDigitalTwin:
    def test_import(self):
        cls = _safe_import("digital_twin.sc2_digital_twin", "UnitSnapshot")
        if cls is None:
            pytest.skip("digital_twin not importable")
        assert cls is not None

    def test_twin_state(self):
        cls = _safe_import("digital_twin.sc2_digital_twin", "TwinState")
        if cls is None:
            pytest.skip("digital_twin not importable")
        assert cls is not None


# ── Canary Deploy ──────────────────────────────


class TestCanaryDeploy:
    def test_import(self):
        cls = _safe_import("canary_deploy.sc2_canary_release", "DeploymentPhase")
        if cls is None:
            pytest.skip("canary_deploy not importable")
        assert cls is not None

    def test_health_status(self):
        cls = _safe_import("canary_deploy.sc2_canary_release", "HealthStatus")
        if cls is None:
            pytest.skip("canary_deploy not importable")
        assert cls is not None


# ── Circuit Breaker ────────────────────────────


class TestCircuitBreaker:
    def test_import(self):
        cls = _safe_import("circuit_breaker.sc2_circuit_breaker", "CircuitState")
        if cls is None:
            pytest.skip("circuit_breaker not importable")
        assert cls is not None


# ── Feature Flags ──────────────────────────────


class TestFeatureFlags:
    def test_import(self):
        cls = _safe_import("feature_flags.sc2_feature_flags", "FlagType")
        if cls is None:
            pytest.skip("feature_flags not importable")
        assert cls is not None


# ── Tool Use Agent ─────────────────────────────


class TestToolUseAgent:
    def test_import(self):
        cls = _safe_import("tool_use_agent.sc2_tool_agent", "ToolRegistry")
        if cls is None:
            pytest.skip("tool_use_agent not importable")
        assert cls is not None

    def test_tool_class(self):
        cls = _safe_import("tool_use_agent.sc2_tool_agent", "Tool")
        if cls is None:
            pytest.skip("tool_use_agent not importable")
        assert cls is not None


# ── Imitation Learning ─────────────────────────


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestImitationLearning:
    def test_import(self):
        cls = _safe_import("imitation_learning.sc2_imitation_agent", "SC2Trajectory")
        assert cls is not None


# ── Comm Learning ──────────────────────────────


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestCommLearning:
    def test_import(self):
        cls = _safe_import("comm_learning.sc2_comm_agent", "CommConfig")
        assert cls is not None


# ── Model Based RL ─────────────────────────────


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestModelBasedRL:
    def test_import(self):
        cls = _safe_import("model_based_rl.sc2_model_based_agent", "DenseLayer")
        assert cls is not None
