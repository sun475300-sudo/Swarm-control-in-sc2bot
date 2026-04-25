# -*- coding: utf-8 -*-
"""
PPO Trainer 의 torch 비의존 부분 검증 (Phase 348).

torch 가 없어도 통과하도록 모듈 import 자체에 가드를 둔다.
실제 ActorCritic / PPOTrainer 학습 경로는 torch 의존이라 별도 통합 테스트로 다룸.
"""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

if importlib.util.find_spec("torch") is None:
    pytest.skip("torch 미설치 — PPO 트레이너 테스트 스킵", allow_module_level=True)


@pytest.fixture(autouse=True)
def _ensure_repo_on_syspath():
    p = str(REPO_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)
    yield


def _import_ppo():
    return importlib.import_module("ppo_selfplay.ppo_trainer")


class TestPPOConfig:
    def test_defaults(self):
        mod = _import_ppo()
        cfg = mod.PPOConfig()
        assert cfg.lr == 3e-4
        assert 0 < cfg.gamma < 1
        assert 0 < cfg.gae_lambda <= 1
        assert cfg.clip_eps > 0
        assert cfg.n_steps > 0
        assert cfg.n_epochs > 0
        assert cfg.batch_size > 0
        assert cfg.obs_dim > 0
        assert cfg.action_dim > 0

    def test_custom_values_persist(self):
        mod = _import_ppo()
        cfg = mod.PPOConfig(lr=1e-3, n_steps=128, batch_size=32)
        assert cfg.lr == 1e-3
        assert cfg.n_steps == 128
        assert cfg.batch_size == 32


class TestPPOBuffer:
    def _make(self):
        mod = _import_ppo()
        return mod.PPOBuffer(n_steps=4, obs_dim=8, action_dim=3)

    def test_initial_state(self):
        b = self._make()
        assert b.ptr == 0
        assert not b.is_full()
        assert b.observations == []

    def test_add_increments_ptr(self):
        b = self._make()
        b.add(obs=[0.0] * 8, action=1, reward=0.5, value=0.0, log_prob=-1.0, done=False)
        assert b.ptr == 1
        assert len(b.actions) == 1
        assert b.actions[0] == 1
        assert b.rewards[0] == 0.5

    def test_is_full_at_capacity(self):
        b = self._make()
        for _ in range(4):
            b.add(obs=[0.0] * 8, action=0, reward=0.0, value=0.0, log_prob=0.0, done=False)
        assert b.is_full()

    def test_reset_clears_state(self):
        b = self._make()
        b.add(obs=[0.0] * 8, action=2, reward=1.0, value=0.5, log_prob=-0.5, done=True)
        assert b.ptr == 1
        b.reset()
        assert b.ptr == 0
        assert b.observations == []
        assert b.actions == []
        assert b.rewards == []
        assert not b.is_full()

    def test_action_mask_optional(self):
        b = self._make()
        b.add(obs=[0.0] * 8, action=0, reward=0.0, value=0.0, log_prob=0.0, done=False)
        # 기본값(None) 도 받아야 함
        assert b.action_masks[0] is None
        b.add(
            obs=[0.0] * 8,
            action=0,
            reward=0.0,
            value=0.0,
            log_prob=0.0,
            done=False,
            action_mask=[True, False, True],
        )
        assert b.action_masks[1] == [True, False, True]
