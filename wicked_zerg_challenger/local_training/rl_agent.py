# -*- coding: utf-8 -*-
"""
RL Agent - Reinforcement Learning Agent for Zerg Bot

REINFORCE 알고리즘 기반의 정책 학습 에이전트입니다.
보상 시스템에서 계산된 보상을 받아 신경망을 업데이트합니다.

주요 기능:
1. 보상 수집 및 저장
2. 정책 그래디언트 계산
3. 신경망 가중치 업데이트
4. 모델 저장/로드
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class PolicyNetwork:
    """
    정책 신경망 (Numpy 기반)

    입력: 게임 상태 (15차원)
    출력: 행동 확률 (5차원: ECONOMY, AGGRESSIVE, DEFENSIVE, TECH, ALL_IN)
    """

    def __init__(self, input_dim: int = 15, hidden_dim: int = 64, output_dim: int = 5):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        # Xavier 초기화
        scale1 = np.sqrt(2.0 / (input_dim + hidden_dim))
        scale2 = np.sqrt(2.0 / (hidden_dim + hidden_dim))
        scale3 = np.sqrt(2.0 / (hidden_dim + output_dim))

        self.W1 = np.random.randn(input_dim, hidden_dim) * scale1
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, hidden_dim) * scale2
        self.b2 = np.zeros(hidden_dim)
        self.W3 = np.random.randn(hidden_dim, output_dim) * scale3
        self.b3 = np.zeros(output_dim)

        # 그래디언트 저장
        self.dW1 = np.zeros_like(self.W1)
        self.db1 = np.zeros_like(self.b1)
        self.dW2 = np.zeros_like(self.W2)
        self.db2 = np.zeros_like(self.b2)
        self.dW3 = np.zeros_like(self.W3)
        self.db3 = np.zeros_like(self.b3)

    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """순전파"""
        z1 = np.dot(x, self.W1) + self.b1
        a1 = np.maximum(0, z1)  # ReLU

        z2 = np.dot(a1, self.W2) + self.b2
        a2 = np.maximum(0, z2)  # ReLU

        z3 = np.dot(a2, self.W3) + self.b3
        probs = self._softmax(z3)

        cache = {
            'x': x, 'z1': z1, 'a1': a1,
            'z2': z2, 'a2': a2, 'z3': z3, 'probs': probs
        }
        return probs, cache

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        exp_x = np.exp(x - np.max(x))
        return exp_x / (np.sum(exp_x) + 1e-9)

    def backward(self, cache: Dict, action_idx: int, advantage: float) -> None:
        """역전파 (REINFORCE)"""
        probs = cache['probs']

        dz3 = probs.copy()
        dz3[action_idx] -= 1
        dz3 *= -advantage

        self.dW3 += np.outer(cache['a2'], dz3)
        self.db3 += dz3

        da2 = np.dot(dz3, self.W3.T)
        dz2 = da2 * (cache['z2'] > 0).astype(float)
        self.dW2 += np.outer(cache['a1'], dz2)
        self.db2 += dz2

        da1 = np.dot(dz2, self.W2.T)
        dz1 = da1 * (cache['z1'] > 0).astype(float)
        self.dW1 += np.outer(cache['x'], dz1)
        self.db1 += dz1

    def update_weights(self, learning_rate: float = 0.001) -> None:
        """가중치 업데이트"""
        for grad in [self.dW1, self.db1, self.dW2, self.db2, self.dW3, self.db3]:
            np.clip(grad, -1.0, 1.0, out=grad)

        self.W1 -= learning_rate * self.dW1
        self.b1 -= learning_rate * self.db1
        self.W2 -= learning_rate * self.dW2
        self.b2 -= learning_rate * self.db2
        self.W3 -= learning_rate * self.dW3
        self.b3 -= learning_rate * self.db3

        self.dW1.fill(0)
        self.db1.fill(0)
        self.dW2.fill(0)
        self.db2.fill(0)
        self.dW3.fill(0)
        self.db3.fill(0)

    def get_weights(self) -> Dict[str, np.ndarray]:
        return {
            'W1': self.W1, 'b1': self.b1,
            'W2': self.W2, 'b2': self.b2,
            'W3': self.W3, 'b3': self.b3
        }

    def set_weights(self, weights: Dict[str, np.ndarray]) -> None:
        self.W1 = weights['W1']
        self.b1 = weights['b1']
        self.W2 = weights['W2']
        self.b2 = weights['b2']
        self.W3 = weights['W3']
        self.b3 = weights['b3']


class RLAgent:
    """
    강화학습 에이전트 (REINFORCE 알고리즘)
    """

    def __init__(
        self,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        model_path: Optional[str] = None
    ):
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.model_path = Path(model_path) if model_path else Path("local_training/models/rl_agent_model.npz")

        self.policy = PolicyNetwork()

        # 에피소드 버퍼
        self.states: List[np.ndarray] = []
        self.actions: List[int] = []
        self.rewards: List[float] = []
        self.caches: List[Dict] = []

        # 베이스라인
        self.baseline = 0.0
        self.baseline_decay = 0.95

        # 통계
        self.episode_count = 0
        self.total_reward = 0.0
        self.training_history: List[Dict] = []

        self.action_labels = ["ECONOMY", "AGGRESSIVE", "DEFENSIVE", "TECH", "ALL_IN"]

        self._load_model()

    def get_action(self, state: np.ndarray) -> Tuple[int, str, float]:
        """상태에서 행동 선택"""
        if len(state) < self.policy.input_dim:
            state = np.concatenate([state, np.zeros(self.policy.input_dim - len(state))])
        state = state[:self.policy.input_dim].astype(np.float32)

        probs, cache = self.policy.forward(state)
        action_idx = np.random.choice(len(probs), p=probs)

        self.states.append(state)
        self.actions.append(action_idx)
        self.caches.append(cache)

        return action_idx, self.action_labels[action_idx], float(probs[action_idx])

    def update_reward(self, reward: float) -> None:
        """보상 업데이트"""
        self.rewards.append(reward)
        self.total_reward += reward

    def end_episode(self, final_reward: float = 0.0) -> Dict[str, float]:
        """에피소드 종료 및 학습"""
        if not self.rewards:
            return {"loss": 0.0, "avg_reward": 0.0}

        if final_reward != 0.0:
            self.rewards[-1] += final_reward

        # 리턴 계산
        returns = self._calculate_returns()

        # 베이스라인 업데이트
        avg_return = np.mean(returns)
        self.baseline = self.baseline_decay * self.baseline + (1 - self.baseline_decay) * avg_return

        # 어드밴티지
        advantages = returns - self.baseline
        if len(advantages) > 1:
            adv_std = np.std(advantages) + 1e-8
            advantages = (advantages - np.mean(advantages)) / adv_std

        # 역전파
        total_loss = 0.0
        for cache, action, advantage in zip(self.caches, self.actions, advantages):
            self.policy.backward(cache, action, advantage)
            total_loss += -np.log(cache['probs'][action] + 1e-9) * advantage

        self.policy.update_weights(self.learning_rate)

        stats = {
            "episode": self.episode_count,
            "avg_reward": float(np.mean(self.rewards)),
            "episode_return": float(np.sum(self.rewards)),
            "loss": float(total_loss / len(self.rewards)),
            "steps": len(self.rewards)
        }
        self.training_history.append(stats)

        self._clear_buffers()
        self.episode_count += 1

        return stats

    def _calculate_returns(self) -> np.ndarray:
        returns = np.zeros(len(self.rewards))
        R = 0.0
        for t in reversed(range(len(self.rewards))):
            R = self.rewards[t] + self.gamma * R
            returns[t] = R
        return returns

    def _clear_buffers(self) -> None:
        self.states.clear()
        self.actions.clear()
        self.rewards.clear()
        self.caches.clear()

    def save_model(self, path: Optional[str] = None) -> bool:
        """모델 저장"""
        save_path = Path(path) if path else self.model_path
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            weights = self.policy.get_weights()
            np.savez(
                str(save_path),
                W1=weights['W1'], b1=weights['b1'],
                W2=weights['W2'], b2=weights['b2'],
                W3=weights['W3'], b3=weights['b3'],
                baseline=np.array([self.baseline]),
                episode_count=np.array([self.episode_count])
            )
            print(f"[RL_AGENT] Model saved to {save_path}")
            return True
        except Exception as e:
            print(f"[RL_AGENT] Failed to save model: {e}")
            return False

    def _load_model(self) -> bool:
        try:
            if self.model_path.exists():
                data = np.load(str(self.model_path))
                weights = {
                    'W1': data['W1'], 'b1': data['b1'],
                    'W2': data['W2'], 'b2': data['b2'],
                    'W3': data['W3'], 'b3': data['b3']
                }
                self.policy.set_weights(weights)
                self.baseline = float(data['baseline'][0])
                self.episode_count = int(data['episode_count'][0])
                print(f"[RL_AGENT] Model loaded from {self.model_path}")
                return True
        except Exception as e:
            print(f"[RL_AGENT] Could not load model: {e}")
        return False

    def get_stats(self) -> Dict[str, Any]:
        recent = self.training_history[-10:] if self.training_history else []
        avg_reward = np.mean([s['avg_reward'] for s in recent]) if recent else 0.0
        return {
            "episode_count": self.episode_count,
            "total_reward": self.total_reward,
            "baseline": self.baseline,
            "avg_reward_last_10": float(avg_reward),
            "buffer_size": len(self.rewards)
        }
