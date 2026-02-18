# -*- coding: utf-8 -*-
"""
Reward Shaping - 보상 셰이핑 시스템 (#113) [스텁]

기존 ZergRewardSystem(reward_system.py)을 보완하는
보상 셰이핑(Potential-Based Reward Shaping) 시스템입니다.

TODO: 전체 구현 예정
- 잠재 함수 기반 보상 셰이핑
- 호기심 기반 탐색 보상 (Curiosity-Driven)
- 히든 보상 감지 (자원 효율, 맵 컨트롤)
- 보상 정규화 및 클리핑
"""

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import numpy as np


class RewardComponent(Enum):
    """보상 구성요소"""
    COMBAT = "combat"                    # 전투 보상
    ECONOMY = "economy"                  # 경제 보상
    TECH = "tech"                        # 테크 보상
    MAP_CONTROL = "map_control"          # 맵 컨트롤 보상
    TIMING = "timing"                    # 타이밍 보상
    EXPLORATION = "exploration"          # 탐색 보상
    SURVIVAL = "survival"               # 생존 보상


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
        잠재 값 계산 (스텁)

        Args:
            state: 현재 상태 딕셔너리

        Returns:
            잠재 값
        """
        # TODO: 상태 기반 잠재 값 계산
        return 0.0

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
    보상 셰이핑 시스템 (스텁)

    기존 ZergRewardSystem과 연동하여 보상을 정교화합니다.

    TODO: 구현 예정
    - 잠재 함수 기반 셰이핑
    - 보상 구성요소별 가중치 조절
    - 보상 통계 추적
    - 적응적 보상 스케일링
    """

    def __init__(self, bot=None):
        """
        Args:
            bot: SC2 봇 인스턴스 (선택)
        """
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

        # 잠재 함수들
        self.potentials: Dict[str, PotentialFunction] = {}

        # 보상 통계
        self.reward_history: List[float] = []
        self.component_history: Dict[str, List[float]] = {}

        # 보상 정규화
        self._reward_mean: float = 0.0
        self._reward_std: float = 1.0
        self._normalize: bool = False

        print("[REWARD_SHAPING] 보상 셰이핑 시스템 초기화 (스텁)")

    def compute_shaped_reward(self, raw_reward: float,
                               state: Optional[Dict[str, Any]] = None) -> float:
        """
        셰이핑된 보상 계산 (스텁)

        Args:
            raw_reward: 기존 보상 시스템의 원시 보상
            state: 현재 상태 (잠재 함수 계산용)

        Returns:
            셰이핑된 최종 보상
        """
        # TODO: 잠재 함수 기반 셰이핑 적용
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
        # TODO: 각 구성요소별 세부 보상 계산
        return {comp.value: 0.0 for comp in RewardComponent}

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
