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

from typing import Any, Dict, List, Optional
import numpy as np

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
                enemy_race=self._normalize_enemy_race(
                    getattr(bot, "enemy_race", None)
                ),
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
            if override_strategy and bot.iteration % 220 == 0 and final_mode != rule_based_decision:
                 print(f"[RL_OVERRIDE] RL 결정: {final_mode} (Rule: {rule_based_decision})")

            # 3. 순수 전략 결정 반환 (직접 실행하지 않음)
            return {
                "strategy_mode": final_mode,
                "author": "RLAgent" if override_strategy else "RuleBasedCommander",
                "timestamp": getattr(bot, "time", 0)
            }

        except Exception as e:
            # 오류 발생 시 기본 경제 모드 반환
            # error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            # print(f"[WARNING] Hierarchical RL step error: {error_msg}")
            return {"strategy_mode": "ECONOMY", "error": str(e)}

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
