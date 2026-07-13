# -*- coding: utf-8 -*-
"""
Improved Hierarchical Reinforcement Learning (개선된 계층적 강화학습)

Role: Pure Strategic Decision Maker (The Brain)
- Commander Agent: Analyzes state and selects high-level strategy
- Removed: CombatAgent, QueenAgent (These are now handled by Managers in the bot)

변경 사항:
- CombatAgent, QueenAgent 클래스 삭제 (CombatManager, QueenManager와 충돌 방지)
- step() 메서드가 순수 전략 모드만 반환하도록 변경
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("ImprovedHierarchicalRl")


def _softmax_np(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values, axis=-1, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / (np.sum(exp_values, axis=-1, keepdims=True) + 1e-9)


class ActorCriticNetwork:
    """Small Actor-Critic network used by INFRA validation and RL experiments."""

    def __init__(
        self,
        obs_dim: int = 16,
        action_dim: int = 7,
        hidden_dim: int = 128,
        input_dim: Optional[int] = None,
    ):
        self.input_dim = int(input_dim or obs_dim)
        self.obs_dim = self.input_dim
        self.hidden_dim = int(hidden_dim)
        self.action_dim = int(action_dim)

        scale1 = np.sqrt(2.0 / (self.input_dim + self.hidden_dim))
        scale2 = np.sqrt(2.0 / (self.hidden_dim + self.action_dim))
        scale3 = np.sqrt(2.0 / (self.hidden_dim + 1))

        self.W_shared = (
            np.random.randn(self.input_dim, self.hidden_dim).astype(np.float32) * scale1
        )
        self.b_shared = np.zeros(self.hidden_dim, dtype=np.float32)
        self.W_actor = (
            np.random.randn(self.hidden_dim, self.action_dim).astype(np.float32)
            * scale2
        )
        self.b_actor = np.zeros(self.action_dim, dtype=np.float32)
        self.W_critic = np.random.randn(self.hidden_dim, 1).astype(np.float32) * scale3
        self.b_critic = np.zeros(1, dtype=np.float32)

        self.gamma = 0.99
        self.gae_lambda = 0.95

    def __call__(self, state):
        return self.forward(state)

    def forward(self, state):
        """Return (policy_probs, state_value) for numpy arrays or torch tensors."""
        module_name = type(state).__module__
        if module_name.startswith("torch"):
            import torch

            x = state.float()
            if x.ndim == 1:
                x = x.unsqueeze(0)
            device = x.device
            dtype = x.dtype
            w_shared = torch.as_tensor(self.W_shared, device=device, dtype=dtype)
            b_shared = torch.as_tensor(self.b_shared, device=device, dtype=dtype)
            w_actor = torch.as_tensor(self.W_actor, device=device, dtype=dtype)
            b_actor = torch.as_tensor(self.b_actor, device=device, dtype=dtype)
            w_critic = torch.as_tensor(self.W_critic, device=device, dtype=dtype)
            b_critic = torch.as_tensor(self.b_critic, device=device, dtype=dtype)
            shared = torch.relu(x.matmul(w_shared) + b_shared)
            policy = torch.softmax(shared.matmul(w_actor) + b_actor, dim=-1)
            value = shared.matmul(w_critic) + b_critic
            return policy, value

        x = np.asarray(state, dtype=np.float32)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        shared = np.maximum(0.0, np.dot(x, self.W_shared) + self.b_shared)
        policy = _softmax_np(np.dot(shared, self.W_actor) + self.b_actor)
        value = np.dot(shared, self.W_critic) + self.b_critic
        return policy, value

    def compute_gae(self, rewards, values, dones):
        """Compute generalized advantage estimates and returns."""
        rewards = np.asarray(rewards, dtype=np.float32)
        values = np.asarray(values, dtype=np.float32)
        dones = np.asarray(dones, dtype=np.float32)
        advantages = np.zeros_like(rewards, dtype=np.float32)
        last_gae = 0.0

        for step in reversed(range(len(rewards))):
            next_value = 0.0 if step == len(rewards) - 1 else values[step + 1]
            non_terminal = 1.0 - dones[step]
            delta = (
                rewards[step] + self.gamma * next_value * non_terminal - values[step]
            )
            last_gae = delta + self.gamma * self.gae_lambda * non_terminal * last_gae
            advantages[step] = last_gae

        returns = advantages + values
        return advantages, returns


class CommanderAgent:
    """
    사령관 에이전트 (Commander Agent)

    현재 게임 상태를 분석하여 최적의 전략 모드를 결정합니다.
    (확장할까? 공격할까? 방어할까?)

    Input: 자원, 인구, 상대 종족, 군사력 비율 등
    Output: StrategyMode (ALL_IN, AGGRESSIVE, DEFENSIVE, ECONOMY, TECH)
    """

    def __init__(self):
        """사령관 에이전트 초기화"""
        self.strategy_history: List[str] = []
        self.decision_confidence: float = 0.5

    def make_decision(
        self,
        minerals: int,
        vespene: int,
        supply_used: int,
        supply_cap: int,
        enemy_race: str,
        enemy_army_value: float,
        our_army_value: float,
        map_control: float,
        creep_coverage: float,
    ) -> str:
        """
        최적의 전략을 결정합니다.

        Args:
            minerals: 보유 미네랄
            vespene: 보유 가스
            supply_used: 사용 중인 보급품
            supply_cap: 최대 보급품
            enemy_race: 상대 종족
            enemy_army_value: 적 군사력 평가치
            our_army_value: 아군 군사력 평가치
            map_control: 맵 장악력 (0.0 ~ 1.0)
            creep_coverage: 점막 분포도 (0.0 ~ 1.0)

        Returns:
            전략 모드 문자열
        """
        # 1. 자원 비율 분석
        resource_ratio = vespene / (minerals + 1)  # 가스/미네랄 비율
        supply_ratio = supply_used / (supply_cap + 1)  # 보급품 비율

        # 2. 군사력 비율
        army_advantage = our_army_value / (enemy_army_value + 1)

        # 3. 맵 주도권
        map_advantage = map_control

        # 4. 전략 결정 로직 (규칙 기반)

        # ALL_IN: 군사력 우위 + 자원 부족 + 인구수 꽉 참
        if army_advantage > 1.5 and minerals < 500 and supply_ratio > 0.9:
            return "ALL_IN"

        # AGGRESSIVE: 군사력 우위 + 맵 주도권
        if army_advantage > 1.2 and map_advantage > 0.5 and supply_ratio > 0.7:
            return "AGGRESSIVE"

        # DEFENSIVE: 군사력 열세 또는 적 대규모 병력 감지
        if army_advantage < 0.8 and enemy_army_value > 1000:
            return "DEFENSIVE"

        # TECH: 자원 여유 + 인구수 여유
        if (
            minerals > 1000
            and vespene > 500
            and resource_ratio > 0.3
            and supply_ratio < 0.8
        ):
            return "TECH"

        # ECONOMY: 기본 상태 (확장 및 드론 확보)
        if minerals > 800 or supply_ratio < 0.6:
            return "ECONOMY"

        # 기본값: AGGRESSIVE (공격적인 운영 지향)
        return "AGGRESSIVE"


class HierarchicalRLSystem:
    """
    계층적 강화학습 시스템 (Hierarchical Reinforcement Learning)

    역할:
    - Commander Agent를 통해 상위 수준의 전략 결정 (Brain)
    - 하위 실행(Micro, Economy 등)은 각 Manager에게 위임 (Hands)
    """

    def __init__(self):
        """계층적 강화학습 시스템 초기화"""
        self.commander = CommanderAgent()
        self.curriculum_stage = 1
        self.stage3_transfer_initialized = False
        self.stage3_initial_weights: Dict[str, Any] = {}
        # CombatAgent와 QueenAgent는 제거되었습니다. (각 Manager가 담당)

    @staticmethod
    def _normalize_enemy_race(value) -> str:
        """상대 종족 이름을 문자열로 정규화"""
        if value is None:
            return "Unknown"
        if hasattr(value, "name"):
            return str(value.name)
        text = str(value)
        if text.lower().startswith("race."):
            return text.split(".", 1)[1]
        return text

    def step(self, bot, override_strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        매 프레임 실행되어 전략적 결정을 내립니다.

        Args:
            bot: 봇 인스턴스
            override_strategy: 외부(RL Agent)에서 강제한 전략 (우선순위 높음)

        Returns:
            결정된 전략 모드가 담긴 딕셔너리
        """
        try:
            # 1. Commander Agent의 상황 판단 (규칙 기반)
            rule_based_decision = self.commander.make_decision(
                minerals=bot.minerals,
                vespene=bot.vespene,
                supply_used=bot.supply_used,
                supply_cap=bot.supply_cap,
                enemy_race=self._normalize_enemy_race(getattr(bot, "enemy_race", None)),
                enemy_army_value=(
                    self._calculate_army_value(bot.enemy_units)
                    if hasattr(bot, "enemy_units")
                    else 0
                ),
                our_army_value=(
                    self._calculate_army_value(bot.units)
                    if hasattr(bot, "units")
                    else 0
                ),
                map_control=self._calculate_map_control(bot),
                creep_coverage=self._calculate_creep_coverage(bot),
            )

            # 2. 최종 전략 결정 (RL Agent 오버라이드 적용)
            final_mode = override_strategy if override_strategy else rule_based_decision

            # 로깅 (오버라이드 발생 시)
            if (
                override_strategy
                and bot.iteration % 220 == 0
                and final_mode != rule_based_decision
            ):
                logger.info(f"RL 결정: {final_mode} (Rule: {rule_based_decision})")

            # 3. 순수 전략 결정 반환 (직접 실행하지 않음)
            return {
                "strategy_mode": final_mode,
                "author": "RLAgent" if override_strategy else "RuleBasedCommander",
                "timestamp": getattr(bot, "time", 0),
            }

        except Exception as e:
            # 오류 발생 시 기본 경제 모드 반환
            # error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            # print(f"[WARNING] Hierarchical RL step error: {error_msg}")
            return {"strategy_mode": "ECONOMY", "error": str(e)}

    def configure_stage3(
        self,
        stage1_weights: Optional[Dict[str, Any]] = None,
        stage2_weights: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Enable curriculum Stage 3 using Stage 1/2 weights as initialization."""
        self.curriculum_stage = 3
        self.stage3_initial_weights = self.initialize_stage3_from_previous(
            stage1_weights or {}, stage2_weights or {}
        )
        self.stage3_transfer_initialized = True
        return self.stage3_initial_weights

    def initialize_stage3_from_previous(
        self, stage1_weights: Dict[str, Any], stage2_weights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge Stage 1 macro and Stage 2 combat weights for Stage 3."""
        merged: Dict[str, Any] = {}
        for key in set(stage1_weights) | set(stage2_weights):
            left = stage1_weights.get(key)
            right = stage2_weights.get(key)
            if left is None:
                merged[key] = right
            elif right is None:
                merged[key] = left
            else:
                try:
                    merged[key] = (np.asarray(left) + np.asarray(right)) / 2.0
                except Exception:
                    merged[key] = {"stage1": left, "stage2": right}
        return merged

    @staticmethod
    def calculate_stage3_reward(
        game_won: Optional[bool] = None,
        enemy_units_killed: int = 0,
        resources_collected: float = 0.0,
        supply_block_count: int = 0,
    ) -> float:
        """ROADMAP Sprint 6 Stage 3 integrated reward function."""
        reward = 0.0
        if game_won is True:
            reward += 10.0
        elif game_won is False:
            reward -= 10.0
        reward += 0.1 * max(0, enemy_units_killed)
        reward += 0.01 * (max(0.0, float(resources_collected)) / 100.0)
        reward -= 0.5 * max(0, supply_block_count)
        return reward

    def _calculate_army_value(self, units) -> float:
        """군사력 가치 계산 (단순 유닛 수 * 100)"""
        if not units:
            return 0.0
        return len(units) * 100.0

    def _calculate_map_control(self, bot) -> float:
        """맵 장악력 계산 (기지 수 비율, 0.0 ~ 1.0)"""
        try:
            if not hasattr(bot, "townhalls"):
                return 0.0

            our_bases = len(bot.townhalls)
            enemy_bases = (
                len(bot.enemy_structures.townhall)
                if hasattr(bot, "enemy_structures")
                else 1
            )

            total_bases = our_bases + enemy_bases
            if total_bases == 0:
                return 0.5

            return our_bases / total_bases

        except Exception:
            return 0.5

    def _calculate_creep_coverage(self, bot) -> float:
        """점막 분포도 계산 (0.0 ~ 1.0)"""
        try:
            if not hasattr(bot, "state") or not hasattr(bot.state, "creep"):
                return 0.0

            map_width = bot.game_info.map_size[0]
            map_height = bot.game_info.map_size[1]
            total_map_area = map_width * map_height

            if total_map_area == 0:
                return 0.0

            creep_coverage = np.sum(bot.state.creep) / total_map_area
            return float(creep_coverage)

        except Exception:
            return 0.0
