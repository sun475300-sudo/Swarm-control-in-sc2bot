# -*- coding: utf-8 -*-
"""
Reward Shaping - 보상 셰이핑 시스템 (#113)

기존 ZergRewardSystem(reward_system.py)을 보완하는
보상 셰이핑(Potential-Based Reward Shaping) 시스템입니다.

구현 완료:
- 잠재 함수 기반 보상 셰이핑 (F = gamma * Phi(s') - Phi(s))
- 구성요소별 세부 보상 계산 (combat, economy, tech, map_control 등)
- 보상 정규화 및 클리핑
- 보상 통계 추적
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("RewardShaping")


class RewardComponent(Enum):
    """보상 구성요소"""

    COMBAT = "combat"  # 전투 보상
    ECONOMY = "economy"  # 경제 보상
    TECH = "tech"  # 테크 보상
    MAP_CONTROL = "map_control"  # 맵 컨트롤 보상
    TIMING = "timing"  # 타이밍 보상
    EXPLORATION = "exploration"  # 탐색 보상
    SURVIVAL = "survival"  # 생존 보상


class PotentialFunction:
    """
    잠재 함수 (스텁)

    상태 기반 잠재 함수를 정의하여 보상 셰이핑에 사용합니다.
    """

    def __init__(self, name: str, gamma: float = 0.99):
        """
        Args:
            name: 잠재 함수 이름
            gamma: 할인 계수
        """
        self.name = name
        self.gamma = gamma
        self._last_potential: float = 0.0

    def compute(self, state: Dict[str, Any]) -> float:
        """
        잠재 값 계산 — 상태의 '좋은 정도'를 스칼라로 표현.

        군집 점수: workers/66 * 0.3 + army_supply/100 * 0.4 + tech_level * 0.2 + bases/4 * 0.1
        """
        workers = state.get("workers", 0)
        army = state.get("army_supply", 0)
        tech = state.get("tech_level", 0.0)
        bases = state.get("bases", 1)

        potential = (
            min(workers / 66.0, 1.0) * 0.3
            + min(army / 100.0, 1.0) * 0.4
            + float(tech) * 0.2
            + min(bases / 4.0, 1.0) * 0.1
        )
        return potential

    def get_shaping_reward(self, current_state: Dict[str, Any]) -> float:
        """
        셰이핑 보상 계산 (F = gamma * Phi(s') - Phi(s))

        Args:
            current_state: 현재 상태

        Returns:
            셰이핑 보상
        """
        current_potential = self.compute(current_state)
        shaping = self.gamma * current_potential - self._last_potential
        self._last_potential = current_potential
        return shaping


class RewardShaper:
    """
    보상 셰이핑 시스템

    기존 ZergRewardSystem과 연동하여 보상을 정교화합니다.
    - 잠재 함수 기반 셰이핑 (F = gamma * Phi(s') - Phi(s))
    - 구성요소별 세부 보상 + 가중치 조절
    - 보상 통계 추적 + 정규화
    """

    def __init__(self, bot=None):
        self.bot = bot

        # 보상 구성요소 가중치
        self.weights: Dict[RewardComponent, float] = {
            RewardComponent.COMBAT: 1.0,
            RewardComponent.ECONOMY: 0.8,
            RewardComponent.TECH: 0.5,
            RewardComponent.MAP_CONTROL: 0.3,
            RewardComponent.TIMING: 0.4,
            RewardComponent.EXPLORATION: 0.2,
            RewardComponent.SURVIVAL: 0.6,
        }

        # 잠재 함수들 — 기본 잠재 함수 자동 등록
        self.potentials: Dict[str, PotentialFunction] = {}
        self.register_potential("default", PotentialFunction("default", gamma=0.99))

        # 보상 통계
        self.reward_history: List[float] = []
        self.component_history: Dict[str, List[float]] = {
            comp.value: [] for comp in RewardComponent
        }

        # 보상 정규화
        self._reward_mean: float = 0.0
        self._reward_std: float = 1.0
        self._normalize: bool = False

        logger.info("보상 셰이핑 시스템 초기화")

    def compute_shaped_reward(
        self, raw_reward: float, state: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        셰이핑된 보상 계산 (스텁)

        Args:
            raw_reward: 기존 보상 시스템의 원시 보상
            state: 현재 상태 (잠재 함수 계산용)

        Returns:
            셰이핑된 최종 보상
        """
        shaped = raw_reward

        # 잠재 함수 보상 추가
        if state:
            for name, potential in self.potentials.items():
                shaped += potential.get_shaping_reward(state)

        # 정규화
        if self._normalize:
            shaped = self._normalize_reward(shaped)

        self.reward_history.append(shaped)
        return shaped

    def compute_component_rewards(self, state: Dict[str, Any]) -> Dict[str, float]:
        """
        구성요소별 보상 계산 (스텁)

        Args:
            state: 현재 상태

        Returns:
            구성요소별 보상 딕셔너리
        """
        rewards: Dict[str, float] = {}

        workers = state.get("workers", 0)
        army = state.get("army_supply", 0)
        enemy_army = state.get("enemy_army", 0)
        minerals = state.get("minerals", 0)
        gas = state.get("vespene", 0)
        tech = state.get("tech_level", 0.0)
        bases = state.get("bases", 1)
        threat = state.get("threat", 0.0)

        # COMBAT: 아군 vs 적군 비율
        if enemy_army > 0:
            rewards[RewardComponent.COMBAT.value] = (
                min(army / max(enemy_army, 1), 2.0) - 1.0
            )
        else:
            rewards[RewardComponent.COMBAT.value] = 0.5 if army > 20 else 0.0

        # ECONOMY: 일꾼 포화도 (66 최적) + 자원 밸런스
        # Penalize banking on either resource — both indicate failed spend.
        worker_score = 1.0 - abs(workers - 66) / 66.0
        bank_penalty = (-0.1 if minerals > 1000 else 0.0) + (
            -0.1 if gas > 1000 else 0.0
        )
        rewards[RewardComponent.ECONOMY.value] = max(worker_score + bank_penalty, -1.0)

        # TECH: 기술 레벨 진행도
        rewards[RewardComponent.TECH.value] = float(tech)

        # MAP_CONTROL: 기지 수 기반
        rewards[RewardComponent.MAP_CONTROL.value] = min(bases / 4.0, 1.0) - 0.25

        # TIMING: 적절한 타이밍에 군대 보유 (위협 대비)
        if threat > 0.5 and army < 30:
            rewards[RewardComponent.TIMING.value] = -0.5
        elif threat < 0.3 and army > 50:
            rewards[RewardComponent.TIMING.value] = 0.3
        else:
            rewards[RewardComponent.TIMING.value] = 0.0

        # EXPLORATION: 기지 확장 보너스
        rewards[RewardComponent.EXPLORATION.value] = 0.2 * max(bases - 1, 0)

        # SURVIVAL: 생존 보상 (위협 낮을수록 좋음)
        rewards[RewardComponent.SURVIVAL.value] = max(1.0 - threat, 0.0)

        # 가중치 적용 및 히스토리 기록
        for comp in RewardComponent:
            val = rewards.get(comp.value, 0.0) * self.weights.get(comp, 1.0)
            rewards[comp.value] = round(val, 4)
            self.component_history[comp.value].append(val)

        return rewards

    def set_weight(self, component: RewardComponent, weight: float) -> None:
        """보상 구성요소 가중치 설정"""
        self.weights[component] = max(0.0, weight)

    def register_potential(self, name: str, potential: PotentialFunction) -> None:
        """잠재 함수 등록"""
        self.potentials[name] = potential

    def enable_normalization(self, enable: bool = True) -> None:
        """보상 정규화 활성화/비활성화"""
        self._normalize = enable

    def _normalize_reward(self, reward: float) -> float:
        """보상 정규화 (스텁)"""
        if self._reward_std < 1e-8:
            return reward
        return (reward - self._reward_mean) / self._reward_std

    def update_statistics(self) -> None:
        """보상 통계 업데이트 (스텁)"""
        if len(self.reward_history) < 2:
            return
        self._reward_mean = float(np.mean(self.reward_history[-100:]))
        self._reward_std = float(np.std(self.reward_history[-100:])) + 1e-8

    def get_stats(self) -> Dict[str, Any]:
        """보상 통계 반환"""
        return {
            "total_rewards": len(self.reward_history),
            "mean_reward": round(self._reward_mean, 4),
            "std_reward": round(self._reward_std, 4),
            "weights": {k.value: v for k, v in self.weights.items()},
            "potential_count": len(self.potentials),
            "normalize_enabled": self._normalize,
        }
