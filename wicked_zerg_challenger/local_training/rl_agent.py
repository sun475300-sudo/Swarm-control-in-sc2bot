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
import shutil
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
    강화학습 에이전트 (REINFORCE 알고리즘 + Epsilon-Greedy)
    """

    def __init__(
        self,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        model_path: Optional[str] = None
    ):
        self.learning_rate = learning_rate
        self.initial_learning_rate = learning_rate
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

        # Epsilon-Greedy 파라미터
        self.epsilon = 1.0  # 초기 탐험률 100%
        self.epsilon_min = 0.05  # 최소 탐험률 5%
        self.epsilon_decay = 0.995  # 감쇠율

        # 통계
        self.episode_count = 0
        self.total_reward = 0.0
        self.training_history: List[Dict] = []
        self.validation_scores: List[float] = []

        # 보상 정규화
        self.reward_mean = 0.0
        self.reward_std = 1.0
        self.reward_count = 0

        # ★★★ FIX: Reward buffer for dimension matching ★★★
        self.reward_buffer: float = 0.0  # Accumulate rewards between state samples

        self.action_labels = ["ECONOMY", "AGGRESSIVE", "DEFENSIVE", "TECH", "ALL_IN"]

        self._load_model()

    def get_action(self, state: np.ndarray, training: bool = True) -> Tuple[int, str, float]:
        """
        상태에서 행동 선택 (Epsilon-Greedy)

        Args:
            state: 게임 상태 벡터
            training: 학습 모드 여부

        Returns:
            (action_idx, action_label, probability)
        """
        if len(state) < self.policy.input_dim:
            state = np.concatenate([state, np.zeros(self.policy.input_dim - len(state))])
        state = state[:self.policy.input_dim].astype(np.float32)

        probs, cache = self.policy.forward(state)

        # Epsilon-Greedy 전략
        if training and np.random.rand() < self.epsilon:
            # 탐험: 랜덤 행동
            action_idx = np.random.randint(len(probs))
        else:
            # 활용: 학습된 정책 사용
            if training:
                # 학습 중: 확률적 샘플링
                action_idx = np.random.choice(len(probs), p=probs)
            else:
                # 추론 모드: greedy (최선의 행동)
                action_idx = np.argmax(probs)

        if training:
            self.states.append(state)
            self.actions.append(action_idx)
            self.caches.append(cache)

            # ★★★ FIX: Store accumulated reward from buffer ★★★
            self.rewards.append(self.reward_buffer)
            self.reward_buffer = 0.0  # Reset buffer after storing

        return action_idx, self.action_labels[action_idx], float(probs[action_idx])

    def update_reward(self, reward: float) -> None:
        """
        보상 업데이트

        ★★★ FIX: Accumulate to buffer instead of appending to list ★★★
        Rewards are stored only when get_action() is called (state/action sampling)
        This ensures dimension matching: len(states) == len(actions) == len(rewards)
        """
        self.reward_buffer += reward  # Accumulate to buffer
        self.total_reward += reward

    def end_episode(self, final_reward: float = 0.0, save_experience: bool = True) -> Dict[str, float]:
        """에피소드 종료 및 학습"""
        if not self.rewards:
            return {"loss": 0.0, "avg_reward": 0.0, "epsilon": self.epsilon}

        if final_reward != 0.0:
            self.rewards[-1] += final_reward

        # 보상 정규화 (Running Mean/Std)
        self._update_reward_stats(self.rewards)

        # 리턴 계산
        returns = self._calculate_returns()

        # 베이스라인 업데이트
        avg_return = np.mean(returns)
        self.baseline = self.baseline_decay * self.baseline + (1 - self.baseline_decay) * avg_return

        # 어드밴티지 (보상 정규화 적용)
        advantages = returns - self.baseline
        if len(advantages) > 1:
            adv_std = np.std(advantages) + 1e-8
            advantages = (advantages - np.mean(advantages)) / adv_std

        # 역전파
        total_loss = 0.0
        for cache, action, advantage in zip(self.caches, self.actions, advantages):
            self.policy.backward(cache, action, advantage)
            total_loss += -np.log(cache['probs'][action] + 1e-9) * advantage

        # 학습률 스케줄링 적용
        current_lr = self._get_scheduled_learning_rate()
        self.policy.update_weights(current_lr)

        # 통계 저장
        stats = {
            "episode": self.episode_count,
            "avg_reward": float(np.mean(self.rewards)),
            "episode_return": float(np.sum(self.rewards)),
            "loss": float(total_loss / len(self.rewards)),
            "steps": len(self.rewards),
            "epsilon": float(self.epsilon),
            "learning_rate": float(current_lr)
        }
        self.training_history.append(stats)

        # 경험 데이터 저장 (Background Learning용)
        if save_experience and len(self.states) > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # CRITICAL FIX: Use absolute path to ensure correct save location
            from pathlib import Path
            buffer_dir = Path(__file__).parent / "data" / "buffer"
            buffer_dir.mkdir(parents=True, exist_ok=True)
            exp_path = buffer_dir / f"exp_{timestamp}_ep{self.episode_count}.npz"
            saved = self.save_experience_data(str(exp_path))
            if saved:
                print(f"[RL_AGENT] [OK] Experience data saved: {exp_path.name}")

        # Epsilon 감쇠
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

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

    def save_experience_data(self, path: str) -> bool:
        """현재 에피소드의 경험 데이터를 파일로 저장"""
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # NumPy 배열로 변환하여 저장
            np.savez_compressed(
                path,
                states=np.array(self.states),
                actions=np.array(self.actions),
                rewards=np.array(self.rewards)
            )
            print(f"[RL_AGENT] Experience saved: {len(self.states)} states, {len(self.rewards)} rewards")
            return True
        except Exception as e:
            print(f"[RL_AGENT] Failed to save experience data: {e}")
            import traceback
            traceback.print_exc()
            return False

    def train_from_batch(self, experiences: List[Dict[str, np.ndarray]]) -> Dict[str, float]:
        """외부 경험 데이터로 학습 (Offline Training)"""
        total_loss = 0.0
        total_steps = 0

        for exp in experiences:
            states = exp['states']
            actions = exp['actions']
            rewards = exp['rewards']

            if len(rewards) == 0:
                continue

            # 리턴 계산
            returns = np.zeros_like(rewards, dtype=np.float32)
            R = 0.0
            for t in reversed(range(len(rewards))):
                R = rewards[t] + self.gamma * R
                returns[t] = R

            # 어드밴티지 계산 (베이스라인 사용)
            # 배치 내 평균을 베이스라인으로 사용
            batch_baseline = np.mean(returns)
            advantages = returns - batch_baseline

            # 정규화
            if len(advantages) > 1:
                advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)

            # 배치 학습
            episode_loss = 0.0
            for i in range(len(states)):
                state = states[i]
                action = actions[i]
                advantage = advantages[i]

                # 상태 벡터 안전성 처리
                if len(state) < self.policy.input_dim:
                    state_input = np.concatenate([state, np.zeros(self.policy.input_dim - len(state))])
                else:
                    state_input = state[:self.policy.input_dim]
                state_input = state_input.astype(np.float32)

                # Forward
                probs, cache = self.policy.forward(state_input)

                # Backward
                self.policy.backward(cache, action, advantage)

                # Loss logging
                episode_loss += -np.log(probs[action] + 1e-9) * advantage

            total_loss += episode_loss
            total_steps += len(states)

        # 가중치 업데이트 (배치 전체에 대해 한 번 수행)
        # 그래디언트 스케일 보정: 배치 크기로 learning rate 조정
        if total_steps > 0:
            num_games = len(experiences)
            adjusted_lr = self.learning_rate / max(num_games, 1)
            self.policy.update_weights(adjusted_lr)

        return {
            "loss": float(total_loss / total_steps) if total_steps > 0 else 0.0,
            "steps": total_steps,
            "games": len(experiences),
            "adjusted_lr": float(adjusted_lr) if total_steps > 0 else 0.0
        }

    def save_model(self, path: Optional[str] = None) -> bool:
        """모델 저장 (Atomic Write)"""
        save_path = Path(path) if path else self.model_path
        tmp_path = save_path.with_suffix('.tmp')
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            weights = self.policy.get_weights()
            np.savez(
                str(tmp_path),
                W1=weights['W1'], b1=weights['b1'],
                W2=weights['W2'], b2=weights['b2'],
                W3=weights['W3'], b3=weights['b3'],
                baseline=np.array([self.baseline]),
                episode_count=np.array([self.episode_count])
            )
            
            # ★★★ FIX: Atomic rename with Windows compatibility ★★★
            if tmp_path.exists():
                try:
                    # Remove old file first on Windows (replace() can fail silently)
                    if save_path.exists():
                        save_path.unlink()
                    # Use shutil.move() for cross-platform compatibility
                    shutil.move(str(tmp_path), str(save_path))
                except Exception as move_error:
                    # Fallback: copy + delete
                    print(f"[RL_AGENT] Move failed, trying copy: {move_error}")
                    shutil.copy(str(tmp_path), str(save_path))
                    tmp_path.unlink()

            print(f"[RL_AGENT] Model saved to {save_path}")
            return True
        except Exception as e:
            print(f"[RL_AGENT] Failed to save model: {e}")
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except:
                    pass
            return False

    def _update_reward_stats(self, rewards: List[float]) -> None:
        """보상 통계 업데이트 (Running Mean/Std)"""
        for r in rewards:
            self.reward_count += 1
            delta = r - self.reward_mean
            self.reward_mean += delta / self.reward_count
            delta2 = r - self.reward_mean
            self.reward_std = np.sqrt((self.reward_std**2 * (self.reward_count - 1) + delta * delta2) / self.reward_count)

    def _get_scheduled_learning_rate(self) -> float:
        """학습률 스케줄링 (Cosine Annealing)"""
        max_episodes = 1000
        min_lr = 1e-5
        max_lr = self.initial_learning_rate

        if self.episode_count >= max_episodes:
            return min_lr

        # Cosine annealing
        progress = self.episode_count / max_episodes
        lr = min_lr + 0.5 * (max_lr - min_lr) * (1 + np.cos(np.pi * progress))
        return lr

    def is_trained(self) -> bool:
        """학습 완료 여부 판단 (최소 기준)"""
        # 최소 50 게임 + epsilon이 충분히 낮아짐
        return self.episode_count >= 50 and self.epsilon <= 0.2

    def is_ready_for_deployment(self) -> Tuple[bool, str]:
        """
        배포 가능 여부 판단

        Returns:
            (ready: bool, reason: str)
        """
        # 1. 최소 학습 게임 수
        min_games = 50
        if self.episode_count < min_games:
            return False, f"Not enough training games ({self.episode_count}/{min_games})"

        # 2. Epsilon이 충분히 낮아짐 (탐험 종료)
        if self.epsilon > 0.2:
            return False, f"Still exploring (ε={self.epsilon:.3f}, target<0.2)"

        # 3. 검증 점수 (있는 경우)
        if len(self.validation_scores) >= 10:
            avg_score = np.mean(self.validation_scores[-10:])
            if avg_score < 0.4:
                return False, f"Validation score too low: {avg_score:.3f}"

        # 4. 최근 학습이 안정적인지 확인
        if len(self.training_history) >= 10:
            recent_losses = [h['loss'] for h in self.training_history[-10:]]
            if np.mean(recent_losses) > 10.0:  # 손실이 너무 큼
                return False, f"Training unstable (avg loss={np.mean(recent_losses):.3f})"

        return True, "Model ready for deployment"

    def validate(self, game_won: bool, game_time: float) -> None:
        """
        게임 결과로 모델 검증

        Args:
            game_won: 게임 승리 여부
            game_time: 게임 시간 (초)
        """
        # 승리 = 1.0, 패배 = 0.0
        # 게임 시간 보너스: 빠른 승리에 높은 점수
        if game_won:
            time_bonus = max(0, 1.0 - game_time / 1800.0)  # 30분 기준
            score = 0.7 + 0.3 * time_bonus
        else:
            # 패배라도 오래 버틴 경우 약간의 점수
            time_bonus = min(1.0, game_time / 1800.0)
            score = 0.3 * time_bonus

        self.validation_scores.append(score)

        # 최근 50개만 유지
        if len(self.validation_scores) > 50:
            self.validation_scores.pop(0)
