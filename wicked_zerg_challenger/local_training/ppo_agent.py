# -*- coding: utf-8 -*-
"""
PPO Agent - Proximal Policy Optimization 강화학습 에이전트 (#101)

PyTorch 기반 PPO 알고리즘으로 SC2 저그 봇의 전략적 의사결정을 학습합니다.

주요 기능:
1. Actor-Critic 네트워크 (정책 + 가치 함수)
2. PPO Clipped Objective로 안정적인 학습
3. GAE (Generalized Advantage Estimation)
4. 상태: 자원, 유닛 수, 적 유닛 수, 공급, 시간
5. 행동: 빌드 선택, 공격/수비, 확장 타이밍
6. 보상: 승리+1, 패배-1, 자원효율 보너스
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.distributions import Categorical
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None


# ============================================================
# 상태/행동 정의
# ============================================================

# 상태 차원: [미네랄, 가스, 서플라이_사용, 서플라이_상한, 드론_수,
#             저글링_수, 바퀴_수, 히드라_수, 적_유닛_수, 적_건물_수,
#             기지_수, 게임_시간_분, 업그레이드_수, 스코어, 위협_레벨]
STATE_DIM = 15

# 행동 공간: [경제집중, 공격적운영, 수비적운영, 테크업, 올인공격,
#             확장, 업그레이드우선, 견제]
ACTION_DIM = 8
ACTION_LABELS = [
    "ECONOMY",       # 드론 우선 생산
    "AGGRESSIVE",    # 공격적 유닛 생산 + 공격
    "DEFENSIVE",     # 수비 유닛 + 방어 건물
    "TECH_UP",       # 테크 건물 우선
    "ALL_IN",        # 전 병력 공격
    "EXPAND",        # 확장 기지 건설
    "UPGRADE",       # 업그레이드 우선
    "HARASS",        # 소규모 견제
]


class ActorCriticNetwork(nn.Module):
    """
    Actor-Critic 신경망 (PPO용)

    Actor (정책 네트워크): 상태 -> 행동 확률 분포
    Critic (가치 네트워크): 상태 -> 상태 가치 (V(s))

    공유 레이어를 통해 특징을 추출하고, 별도의 헤드로 분기합니다.
    """

    def __init__(self, state_dim: int = STATE_DIM, action_dim: int = ACTION_DIM,
                 hidden_dim: int = 128):
        """
        Args:
            state_dim: 상태 벡터 차원
            action_dim: 행동 공간 크기
            hidden_dim: 은닉층 차원
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch가 설치되지 않았습니다. pip install torch 로 설치하세요.")

        super().__init__()

        # 공유 특징 추출 레이어
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        # Actor 헤드 (정책)
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim),
            nn.Softmax(dim=-1),
        )

        # Critic 헤드 (가치 함수)
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

        # 가중치 초기화
        self._init_weights()

    def _init_weights(self):
        """직교 초기화 (PPO 권장)"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=np.sqrt(2))
                nn.init.constant_(module.bias, 0.0)

        # Actor 마지막 레이어는 작은 gain
        actor_last = list(self.actor.children())[-2]  # Softmax 전 Linear
        if isinstance(actor_last, nn.Linear):
            nn.init.orthogonal_(actor_last.weight, gain=0.01)

        # Critic 마지막 레이어도 작은 gain
        critic_last = list(self.critic.children())[-1]
        if isinstance(critic_last, nn.Linear):
            nn.init.orthogonal_(critic_last.weight, gain=1.0)

    def forward(self, state: "torch.Tensor") -> Tuple["torch.Tensor", "torch.Tensor"]:
        """
        순전파

        Args:
            state: 상태 텐서 [batch_size, state_dim]

        Returns:
            (action_probs, state_value): 행동 확률과 상태 가치
        """
        shared_features = self.shared(state)
        action_probs = self.actor(shared_features)
        state_value = self.critic(shared_features)
        return action_probs, state_value


class PPOMemory:
    """
    PPO 경험 버퍼

    에피소드 동안 수집한 (상태, 행동, 보상, 로그확률, 가치) 저장
    """

    def __init__(self):
        """메모리 초기화"""
        self.states: List[np.ndarray] = []
        self.actions: List[int] = []
        self.rewards: List[float] = []
        self.log_probs: List[float] = []
        self.values: List[float] = []
        self.dones: List[bool] = []

    def store(self, state: np.ndarray, action: int, reward: float,
              log_prob: float, value: float, done: bool = False) -> None:
        """경험 하나를 버퍼에 저장"""
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.log_probs.append(log_prob)
        self.values.append(value)
        self.dones.append(done)

    def clear(self) -> None:
        """버퍼 초기화"""
        self.states.clear()
        self.actions.clear()
        self.rewards.clear()
        self.log_probs.clear()
        self.values.clear()
        self.dones.clear()

    def __len__(self) -> int:
        return len(self.states)

    def get_batches(self, batch_size: int = 64) -> List[Dict[str, Any]]:
        """
        미니배치로 분할하여 반환

        Args:
            batch_size: 미니배치 크기

        Returns:
            미니배치 리스트
        """
        n = len(self.states)
        indices = np.random.permutation(n)
        batches = []

        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch_indices = indices[start:end]
            batches.append({
                "states": np.array([self.states[i] for i in batch_indices], dtype=np.float32),
                "actions": np.array([self.actions[i] for i in batch_indices], dtype=np.int64),
                "rewards": np.array([self.rewards[i] for i in batch_indices], dtype=np.float32),
                "log_probs": np.array([self.log_probs[i] for i in batch_indices], dtype=np.float32),
                "values": np.array([self.values[i] for i in batch_indices], dtype=np.float32),
                "dones": np.array([self.dones[i] for i in batch_indices], dtype=np.float32),
            })

        return batches


class PPOAgent:
    """
    PPO (Proximal Policy Optimization) 강화학습 에이전트

    SC2 저그 봇의 전략적 의사결정을 학습합니다.
    - 상태: 자원, 유닛 수, 적 유닛 수, 공급, 시간 등 15차원
    - 행동: 빌드 선택, 공격/수비, 확장 타이밍 등 8가지
    - 보상: 승리+1, 패배-1, 자원효율 보너스

    PPO의 핵심:
    - Clipped surrogate objective로 정책 업데이트 제한
    - GAE로 분산 감소된 어드밴티지 추정
    - 엔트로피 보너스로 탐험 유지
    """

    def __init__(
        self,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        entropy_coeff: float = 0.01,
        value_coeff: float = 0.5,
        max_grad_norm: float = 0.5,
        ppo_epochs: int = 4,
        batch_size: int = 64,
        model_path: Optional[str] = None,
    ):
        """
        PPO 에이전트 초기화

        Args:
            learning_rate: 학습률
            gamma: 할인율
            gae_lambda: GAE 람다 (편향-분산 트레이드오프)
            clip_epsilon: PPO 클리핑 범위
            entropy_coeff: 엔트로피 보너스 계수
            value_coeff: 가치 함수 손실 계수
            max_grad_norm: 그래디언트 클리핑 최대 노름
            ppo_epochs: PPO 업데이트 에폭 수
            batch_size: 미니배치 크기
            model_path: 모델 저장/로드 경로
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch가 필요합니다. pip install torch 로 설치하세요.")

        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.entropy_coeff = entropy_coeff
        self.value_coeff = value_coeff
        self.max_grad_norm = max_grad_norm
        self.ppo_epochs = ppo_epochs
        self.batch_size = batch_size

        # 모델 경로
        if model_path:
            self.model_path = Path(model_path)
        else:
            self.model_path = Path(__file__).parent / "models" / "ppo_agent.pt"

        # 디바이스 설정
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 네트워크
        self.network = ActorCriticNetwork(STATE_DIM, ACTION_DIM).to(self.device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=learning_rate, eps=1e-5)

        # 경험 버퍼
        self.memory = PPOMemory()

        # 보상 버퍼 (중간 보상 누적)
        self.reward_buffer: float = 0.0

        # 통계
        self.episode_count = 0
        self.total_reward = 0.0
        self.training_history: List[Dict[str, float]] = []

        # 행동 라벨
        self.action_labels = ACTION_LABELS

        # 모델 로드 시도
        self._load_model()

        print(f"[PPO_AGENT] 초기화 완료 (device={self.device}, "
              f"state_dim={STATE_DIM}, action_dim={ACTION_DIM})")

    def get_state_from_bot(self, bot) -> np.ndarray:
        """
        봇 객체에서 상태 벡터를 추출합니다.

        Args:
            bot: SC2 봇 인스턴스

        Returns:
            15차원 상태 벡터
        """
        try:
            minerals = getattr(bot, "minerals", 0) / 1000.0
            vespene = getattr(bot, "vespene", 0) / 1000.0
            supply_used = getattr(bot, "supply_used", 0) / 200.0
            supply_cap = getattr(bot, "supply_cap", 0) / 200.0
            game_time = getattr(bot, "time", 0) / 600.0  # 10분 정규화

            # 유닛 카운트
            drone_count = 0
            zergling_count = 0
            roach_count = 0
            hydra_count = 0
            if hasattr(bot, "units"):
                for unit in bot.units:
                    name = getattr(unit.type_id, "name", "").upper()
                    if name == "DRONE":
                        drone_count += 1
                    elif name == "ZERGLING":
                        zergling_count += 1
                    elif name == "ROACH":
                        roach_count += 1
                    elif name == "HYDRALISK":
                        hydra_count += 1

            # 적 유닛/건물 수
            enemy_unit_count = 0
            enemy_structure_count = 0
            if hasattr(bot, "enemy_units"):
                enemy_unit_count = len(bot.enemy_units)
            if hasattr(bot, "enemy_structures"):
                enemy_structure_count = len(bot.enemy_structures)

            # 기지 수
            base_count = 0
            if hasattr(bot, "townhalls"):
                base_count = bot.townhalls.amount

            # 업그레이드 수
            upgrade_count = 0
            if hasattr(bot, "state") and hasattr(bot.state, "upgrades"):
                upgrade_count = len(bot.state.upgrades)

            # 스코어
            score = getattr(bot, "state", None)
            score_val = 0.0
            if score and hasattr(score, "score"):
                score_val = score.score.score_float / 10000.0

            # 위협 레벨 (0~1)
            threat_level = 0.0
            if hasattr(bot, "intel") and bot.intel:
                if hasattr(bot.intel, "get_threat_level"):
                    threat_level = bot.intel.get_threat_level()

            state = np.array([
                minerals, vespene, supply_used, supply_cap,
                drone_count / 80.0, zergling_count / 100.0,
                roach_count / 50.0, hydra_count / 50.0,
                enemy_unit_count / 100.0, enemy_structure_count / 20.0,
                base_count / 5.0, game_time,
                upgrade_count / 10.0, score_val, threat_level
            ], dtype=np.float32)

            return state

        except Exception as e:
            print(f"[PPO_AGENT] 상태 추출 실패: {e}")
            return np.zeros(STATE_DIM, dtype=np.float32)

    def get_action(self, state: np.ndarray, training: bool = True) -> Tuple[int, str, float]:
        """
        상태에서 행동 선택

        Args:
            state: 게임 상태 벡터
            training: 학습 모드 여부

        Returns:
            (action_idx, action_label, log_probability)
        """
        # 상태 전처리
        if len(state) < STATE_DIM:
            state = np.concatenate([state, np.zeros(STATE_DIM - len(state))])
        state = state[:STATE_DIM].astype(np.float32)

        # NaN/Inf 방어
        state = np.nan_to_num(state, nan=0.0, posinf=1.0, neginf=-1.0)

        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action_probs, state_value = self.network(state_tensor)

        dist = Categorical(action_probs)

        if training:
            action = dist.sample()
        else:
            action = torch.argmax(action_probs, dim=-1)

        action_idx = action.item()
        log_prob = dist.log_prob(action).item()
        value = state_value.item()

        # 메모리에 저장 (학습 모드)
        if training:
            reward = self.reward_buffer
            self.reward_buffer = 0.0
            self.memory.store(state, action_idx, reward, log_prob, value)

        return action_idx, self.action_labels[action_idx], log_prob

    def update_reward(self, reward: float) -> None:
        """
        보상 누적 (다음 get_action 호출 시 메모리에 저장됨)

        Args:
            reward: 보상 값
        """
        self.reward_buffer += reward
        self.total_reward += reward

    def calculate_game_reward(self, won: bool, game_time: float,
                              resource_efficiency: float = 0.0) -> float:
        """
        게임 종료 시 최종 보상 계산

        Args:
            won: 승리 여부
            game_time: 게임 시간 (초)
            resource_efficiency: 자원 효율 (0~1)

        Returns:
            최종 보상 값
        """
        reward = 0.0

        # 승리/패배 기본 보상
        if won:
            reward += 1.0
            # 빠른 승리 보너스
            if game_time < 300:  # 5분 이내
                reward += 0.5
            elif game_time < 600:  # 10분 이내
                reward += 0.2
        else:
            reward -= 1.0
            # 오래 버틴 경우 패널티 감소
            if game_time > 900:  # 15분 이상
                reward += 0.3

        # 자원 효율 보너스
        reward += resource_efficiency * 0.3

        return reward

    def _compute_gae(self, rewards: np.ndarray, values: np.ndarray,
                     dones: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        GAE (Generalized Advantage Estimation) 계산

        Args:
            rewards: 보상 배열
            values: 상태 가치 배열
            dones: 종료 플래그 배열

        Returns:
            (advantages, returns): 어드밴티지와 리턴
        """
        n = len(rewards)
        advantages = np.zeros(n, dtype=np.float32)
        last_gae = 0.0

        for t in reversed(range(n)):
            if t == n - 1:
                next_value = 0.0
            else:
                next_value = values[t + 1]

            delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - values[t]
            last_gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * last_gae
            advantages[t] = last_gae

        returns = advantages + values
        return advantages, returns

    def end_episode(self, final_reward: float = 0.0) -> Dict[str, float]:
        """
        에피소드 종료 및 PPO 학습 수행

        Args:
            final_reward: 최종 보상 (승리/패배)

        Returns:
            학습 통계
        """
        # 남은 보상 버퍼 처리
        if self.reward_buffer != 0.0 and len(self.memory) > 0:
            self.memory.rewards[-1] += self.reward_buffer
            self.reward_buffer = 0.0

        if len(self.memory) == 0:
            return {"loss": 0.0, "avg_reward": 0.0, "episode": self.episode_count}

        # 최종 보상 추가
        if final_reward != 0.0:
            self.memory.rewards[-1] += final_reward
        self.memory.dones[-1] = True

        # 데이터 변환
        rewards = np.array(self.memory.rewards, dtype=np.float32)
        values = np.array(self.memory.values, dtype=np.float32)
        dones = np.array(self.memory.dones, dtype=np.float32)

        # GAE 계산
        advantages, returns = self._compute_gae(rewards, values, dones)

        # 어드밴티지 정규화
        if len(advantages) > 1:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # PPO 업데이트
        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0
        update_count = 0

        # 전체 데이터를 텐서로 변환
        all_states = np.array(self.memory.states, dtype=np.float32)
        all_actions = np.array(self.memory.actions, dtype=np.int64)
        all_old_log_probs = np.array(self.memory.log_probs, dtype=np.float32)

        for epoch in range(self.ppo_epochs):
            # 미니배치 인덱스 생성
            n = len(all_states)
            indices = np.random.permutation(n)

            for start in range(0, n, self.batch_size):
                end = min(start + self.batch_size, n)
                batch_idx = indices[start:end]

                # 텐서 변환
                states_t = torch.FloatTensor(all_states[batch_idx]).to(self.device)
                actions_t = torch.LongTensor(all_actions[batch_idx]).to(self.device)
                old_log_probs_t = torch.FloatTensor(all_old_log_probs[batch_idx]).to(self.device)
                advantages_t = torch.FloatTensor(advantages[batch_idx]).to(self.device)
                returns_t = torch.FloatTensor(returns[batch_idx]).to(self.device)

                # 현재 정책으로 평가
                action_probs, state_values = self.network(states_t)
                dist = Categorical(action_probs)
                new_log_probs = dist.log_prob(actions_t)
                entropy = dist.entropy().mean()

                # PPO Clipped Objective
                ratio = torch.exp(new_log_probs - old_log_probs_t)
                surr1 = ratio * advantages_t
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages_t
                policy_loss = -torch.min(surr1, surr2).mean()

                # 가치 함수 손실
                value_loss = nn.functional.mse_loss(state_values.squeeze(), returns_t)

                # 총 손실
                loss = (policy_loss
                        + self.value_coeff * value_loss
                        - self.entropy_coeff * entropy)

                # 역전파
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
                self.optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += entropy.item()
                update_count += 1

        # 통계 계산
        avg_policy_loss = total_policy_loss / max(update_count, 1)
        avg_value_loss = total_value_loss / max(update_count, 1)
        avg_entropy = total_entropy / max(update_count, 1)

        stats = {
            "episode": self.episode_count,
            "avg_reward": float(np.mean(rewards)),
            "episode_return": float(np.sum(rewards)),
            "policy_loss": avg_policy_loss,
            "value_loss": avg_value_loss,
            "entropy": avg_entropy,
            "steps": len(rewards),
        }

        self.training_history.append(stats)
        self.memory.clear()
        self.episode_count += 1

        print(f"[PPO_AGENT] Episode {self.episode_count}: "
              f"return={stats['episode_return']:.3f}, "
              f"policy_loss={avg_policy_loss:.4f}, "
              f"value_loss={avg_value_loss:.4f}")

        return stats

    def save_model(self, path: Optional[str] = None) -> bool:
        """
        모델 저장

        Args:
            path: 저장 경로 (None이면 기본 경로)

        Returns:
            저장 성공 여부
        """
        save_path = Path(path) if path else self.model_path
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                "network_state_dict": self.network.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "episode_count": self.episode_count,
                "total_reward": self.total_reward,
                "training_history": self.training_history[-100:],  # 최근 100개만
            }, str(save_path))
            print(f"[PPO_AGENT] 모델 저장 완료: {save_path}")
            return True
        except Exception as e:
            print(f"[PPO_AGENT] 모델 저장 실패: {e}")
            return False

    def _load_model(self) -> bool:
        """모델 로드"""
        try:
            if self.model_path.exists():
                checkpoint = torch.load(str(self.model_path), map_location=self.device)
                self.network.load_state_dict(checkpoint["network_state_dict"])
                self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
                self.episode_count = checkpoint.get("episode_count", 0)
                self.total_reward = checkpoint.get("total_reward", 0.0)
                self.training_history = checkpoint.get("training_history", [])
                print(f"[PPO_AGENT] 모델 로드 완료: {self.model_path} (episode={self.episode_count})")
                return True
        except Exception as e:
            print(f"[PPO_AGENT] 모델 로드 실패: {e}")
        return False

    def get_stats(self) -> Dict[str, Any]:
        """학습 통계 반환"""
        recent = self.training_history[-10:] if self.training_history else []
        avg_reward = np.mean([s["avg_reward"] for s in recent]) if recent else 0.0
        return {
            "episode_count": self.episode_count,
            "total_reward": self.total_reward,
            "avg_reward_last_10": float(avg_reward),
            "device": str(self.device),
            "memory_size": len(self.memory),
        }

    def is_trained(self) -> bool:
        """최소 학습 완료 여부 판단"""
        return self.episode_count >= 50

    def is_ready_for_deployment(self) -> Tuple[bool, str]:
        """
        배포 가능 여부 판단

        Returns:
            (ready, reason)
        """
        if self.episode_count < 100:
            return False, f"학습 부족 ({self.episode_count}/100 에피소드)"

        if len(self.training_history) >= 10:
            recent_returns = [h["episode_return"] for h in self.training_history[-10:]]
            avg_return = np.mean(recent_returns)
            if avg_return < -0.5:
                return False, f"학습 성능 부족 (avg_return={avg_return:.3f})"

        return True, "배포 준비 완료"
