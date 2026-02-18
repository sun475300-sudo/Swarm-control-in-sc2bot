# -*- coding: utf-8 -*-
"""
Composition Optimizer - 유닛 조합 최적화 시스템 (#105)

적 유닛 조합을 분석하여 최적의 카운터 유닛 조합을 추천합니다.

주요 기능:
1. 적 조합 분석 (유닛 타입별 카운트 및 비율)
2. 카운터 유닛 매트릭스 기반 최적 조합 계산
3. 비용 효율 (cost-efficiency) 계산
4. 현재 보유 유닛 대비 추가 생산 추천
5. 가스/미네랄 비율 최적화
"""

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    UnitTypeId = None


class UnitRole(Enum):
    """유닛 역할 분류"""
    GROUND_MELEE = "ground_melee"       # 근접 지상
    GROUND_RANGED = "ground_ranged"     # 원거리 지상
    ANTI_AIR = "anti_air"              # 대공
    AIR_FIGHTER = "air_fighter"         # 공중 전투기
    SIEGE = "siege"                     # 공성
    SUPPORT = "support"                 # 지원
    WORKER = "worker"                   # 일꾼


class ZergUnit:
    """저그 유닛 정보"""

    def __init__(self, name: str, mineral: int, gas: int, supply: int,
                 role: UnitRole, dps: float = 0.0, hp: float = 0.0,
                 can_attack_air: bool = False):
        """
        Args:
            name: 유닛 이름
            mineral: 미네랄 비용
            gas: 가스 비용
            supply: 서플라이 비용
            role: 유닛 역할
            dps: 초당 데미지
            hp: 체력
            can_attack_air: 대공 가능 여부
        """
        self.name = name
        self.mineral = mineral
        self.gas = gas
        self.supply = supply
        self.role = role
        self.dps = dps
        self.hp = hp
        self.can_attack_air = can_attack_air
        self.total_cost = mineral + gas * 1.5  # 가스는 1.5배 가중치

    @property
    def cost_efficiency(self) -> float:
        """비용 대비 효율 (DPS * HP / 총비용)"""
        if self.total_cost == 0:
            return 0.0
        return (self.dps * self.hp) / self.total_cost


# 저그 유닛 데이터베이스
ZERG_UNITS = {
    "zergling": ZergUnit("zergling", 25, 0, 0.5, UnitRole.GROUND_MELEE,
                          dps=10.5, hp=35),
    "baneling": ZergUnit("baneling", 50, 25, 0.5, UnitRole.GROUND_MELEE,
                          dps=80.0, hp=30),  # 자폭 데미지
    "roach": ZergUnit("roach", 75, 25, 2, UnitRole.GROUND_RANGED,
                       dps=11.2, hp=145),
    "ravager": ZergUnit("ravager", 100, 75, 3, UnitRole.GROUND_RANGED,
                          dps=14.0, hp=120),
    "hydralisk": ZergUnit("hydralisk", 100, 50, 2, UnitRole.GROUND_RANGED,
                            dps=20.0, hp=90, can_attack_air=True),
    "mutalisk": ZergUnit("mutalisk", 100, 100, 2, UnitRole.AIR_FIGHTER,
                           dps=12.6, hp=120, can_attack_air=True),
    "corruptor": ZergUnit("corruptor", 150, 100, 2, UnitRole.AIR_FIGHTER,
                            dps=11.4, hp=200, can_attack_air=True),
    "infestor": ZergUnit("infestor", 100, 150, 2, UnitRole.SUPPORT,
                           dps=0.0, hp=90),
    "viper": ZergUnit("viper", 100, 200, 3, UnitRole.SUPPORT,
                        dps=0.0, hp=150, can_attack_air=True),
    "ultralisk": ZergUnit("ultralisk", 300, 200, 6, UnitRole.GROUND_MELEE,
                            dps=57.3, hp=500),
    "lurker": ZergUnit("lurker", 150, 150, 3, UnitRole.SIEGE,
                         dps=20.0, hp=200),
    "brood_lord": ZergUnit("brood_lord", 300, 250, 4, UnitRole.SIEGE,
                             dps=22.4, hp=225),
    "queen": ZergUnit("queen", 150, 0, 2, UnitRole.SUPPORT,
                        dps=11.2, hp=175, can_attack_air=True),
}


# 카운터 매트릭스: counter_matrix[적유닛][아군유닛] = 효율 점수 (0~1)
COUNTER_MATRIX: Dict[str, Dict[str, float]] = {
    # 테란
    "MARINE": {"baneling": 0.95, "zergling": 0.7, "lurker": 0.9, "ultralisk": 0.85},
    "MARAUDER": {"zergling": 0.8, "mutalisk": 0.7, "hydralisk": 0.6},
    "SIEGETANK": {"ravager": 0.85, "mutalisk": 0.8, "zergling": 0.65},
    "SIEGETANKSIEGED": {"ravager": 0.9, "mutalisk": 0.85, "brood_lord": 0.8},
    "THOR": {"zergling": 0.7, "roach": 0.6, "infestor": 0.75},
    "MEDIVAC": {"corruptor": 0.9, "hydralisk": 0.8, "mutalisk": 0.75},
    "BATTLECRUISER": {"corruptor": 0.9, "viper": 0.85, "hydralisk": 0.6},
    "LIBERATOR": {"corruptor": 0.85, "hydralisk": 0.7, "mutalisk": 0.6},
    "HELLION": {"roach": 0.8, "queen": 0.6},
    "CYCLONE": {"zergling": 0.7, "roach": 0.6, "mutalisk": 0.65},
    "WIDOWMINE": {"zergling": 0.5, "roach": 0.7, "mutalisk": 0.3},

    # 프로토스
    "ZEALOT": {"roach": 0.75, "lurker": 0.8, "baneling": 0.7},
    "STALKER": {"zergling": 0.8, "roach": 0.65, "hydralisk": 0.6},
    "ADEPT": {"roach": 0.7, "zergling": 0.6},
    "IMMORTAL": {"zergling": 0.7, "ravager": 0.75, "mutalisk": 0.8},
    "COLOSSUS": {"corruptor": 0.95, "ravager": 0.8, "hydralisk": 0.5},
    "DISRUPTOR": {"zergling": 0.6, "mutalisk": 0.8, "roach": 0.5},
    "ARCHON": {"zergling": 0.4, "roach": 0.6, "hydralisk": 0.65, "lurker": 0.7},
    "HIGHTEMPLAR": {"zergling": 0.5, "mutalisk": 0.7, "ravager": 0.65},
    "VOIDRAY": {"hydralisk": 0.85, "corruptor": 0.8, "queen": 0.7},
    "CARRIER": {"corruptor": 0.9, "viper": 0.85, "hydralisk": 0.6},
    "PHOENIX": {"hydralisk": 0.7, "queen": 0.65},
    "TEMPEST": {"corruptor": 0.8, "viper": 0.9},

    # 저그
    "ZERGLING": {"baneling": 0.9, "roach": 0.7, "lurker": 0.85},
    "ROACH": {"roach": 0.5, "ravager": 0.6, "hydralisk": 0.55},
    "HYDRALISK": {"zergling": 0.7, "baneling": 0.75, "lurker": 0.7},
    "MUTALISK": {"hydralisk": 0.85, "corruptor": 0.8, "queen": 0.6},
    "ULTRALISK": {"roach": 0.4, "infestor": 0.6, "viper": 0.7},
    "BROODLORD": {"corruptor": 0.9, "hydralisk": 0.5},
    "LURKER": {"ravager": 0.8, "mutalisk": 0.7},
    "LURKERMP": {"ravager": 0.8, "mutalisk": 0.7},
}


class CompositionOptimizer:
    """
    유닛 조합 최적화기

    적 유닛 조합을 분석하여 최적의 카운터 유닛 조합을 추천합니다.

    사용 예:
        optimizer = CompositionOptimizer(bot)
        recommendation = optimizer.get_optimal_composition()
        # recommendation = {"roach": 0.4, "hydralisk": 0.3, ...}
    """

    def __init__(self, bot):
        """
        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot

        # 캐시
        self._last_analysis_time: float = 0.0
        self._analysis_interval: float = 5.0  # 5초마다 분석
        self._cached_recommendation: Dict[str, float] = {}

        # 현재 보유 유닛 정보
        self.current_composition: Dict[str, int] = {}

        # 적 유닛 정보
        self.enemy_composition: Dict[str, int] = {}

        print("[COMPOSITION] 유닛 조합 최적화기 초기화 완료")

    def analyze_enemy_composition(self) -> Dict[str, int]:
        """
        적 유닛 조합 분석

        Returns:
            적 유닛 타입별 카운트
        """
        composition = {}

        if not hasattr(self.bot, "enemy_units"):
            return composition

        for unit in self.bot.enemy_units:
            try:
                unit_name = getattr(unit.type_id, "name", "UNKNOWN").upper()
                if unit_name not in ("SCV", "PROBE", "DRONE", "MULE"):
                    composition[unit_name] = composition.get(unit_name, 0) + 1
            except Exception:
                continue

        self.enemy_composition = composition
        return composition

    def analyze_current_composition(self) -> Dict[str, int]:
        """
        아군 유닛 조합 분석

        Returns:
            아군 유닛 타입별 카운트
        """
        composition = {}

        if not hasattr(self.bot, "units"):
            return composition

        for unit in self.bot.units:
            try:
                unit_name = getattr(unit.type_id, "name", "UNKNOWN").upper()
                if unit_name != "DRONE" and unit_name != "LARVA":
                    composition[unit_name] = composition.get(unit_name, 0) + 1
            except Exception:
                continue

        self.current_composition = composition
        return composition

    def get_optimal_composition(self, budget_minerals: int = 0,
                                 budget_gas: int = 0) -> Dict[str, float]:
        """
        적 조합 대비 최적 유닛 비율 계산

        Args:
            budget_minerals: 가용 미네랄 (0이면 비율만 반환)
            budget_gas: 가용 가스 (0이면 비율만 반환)

        Returns:
            유닛별 추천 생산 비율 (0~1)
        """
        game_time = getattr(self.bot, "time", 0.0)

        # 캐시 확인
        if game_time - self._last_analysis_time < self._analysis_interval:
            return self._cached_recommendation

        self._last_analysis_time = game_time

        # 적 조합 분석
        enemy_comp = self.analyze_enemy_composition()

        if not enemy_comp:
            # 적 정보 없으면 기본 조합
            self._cached_recommendation = self._get_default_composition()
            return self._cached_recommendation

        # 카운터 점수 계산
        counter_scores: Dict[str, float] = {}

        for enemy_unit, count in enemy_comp.items():
            if enemy_unit in COUNTER_MATRIX:
                for zerg_unit, efficiency in COUNTER_MATRIX[enemy_unit].items():
                    if zerg_unit not in counter_scores:
                        counter_scores[zerg_unit] = 0.0
                    # 적 유닛 수에 비례하여 가중치 부여
                    counter_scores[zerg_unit] += efficiency * count

        if not counter_scores:
            self._cached_recommendation = self._get_default_composition()
            return self._cached_recommendation

        # 비용 효율 반영
        for unit_name in counter_scores:
            if unit_name in ZERG_UNITS:
                cost_eff = ZERG_UNITS[unit_name].cost_efficiency
                counter_scores[unit_name] *= (1.0 + cost_eff * 0.1)

        # 대공 유닛 필요 여부 체크
        has_air_threat = any(
            unit_name in ("MUTALISK", "VOIDRAY", "CARRIER", "BATTLECRUISER",
                          "PHOENIX", "ORACLE", "LIBERATOR", "BANSHEE",
                          "BROODLORD", "CORRUPTOR", "TEMPEST")
            for unit_name in enemy_comp
        )

        if has_air_threat:
            # 대공 유닛 비율 보장
            for unit_name in ("hydralisk", "corruptor", "queen"):
                if unit_name in counter_scores:
                    counter_scores[unit_name] *= 1.5
                else:
                    counter_scores[unit_name] = 3.0

        # 정규화 (비율로 변환)
        total_score = sum(counter_scores.values())
        if total_score > 0:
            for unit_name in counter_scores:
                counter_scores[unit_name] /= total_score

        # 최소 비율 필터링 (5% 미만 유닛 제거)
        filtered = {k: v for k, v in counter_scores.items() if v >= 0.05}

        # 재정규화
        total = sum(filtered.values())
        if total > 0:
            for k in filtered:
                filtered[k] /= total

        self._cached_recommendation = filtered
        return filtered

    def get_production_recommendation(self) -> List[Tuple[str, int]]:
        """
        현재 자원 기반 생산 추천

        Returns:
            [(유닛이름, 추천생산수)] 리스트
        """
        optimal = self.get_optimal_composition()
        current = self.analyze_current_composition()

        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)
        supply_left = getattr(self.bot, "supply_left", 0)

        recommendations = []

        for unit_name, target_ratio in sorted(optimal.items(),
                                                key=lambda x: x[1], reverse=True):
            if unit_name not in ZERG_UNITS:
                continue

            unit_info = ZERG_UNITS[unit_name]

            # 현재 수
            current_name = unit_name.upper()
            current_count = current.get(current_name, 0)

            # 목표 수 (총 군대 서플라이 기준)
            army_supply = getattr(self.bot, "supply_army", 0)
            target_count = max(1, int(target_ratio * army_supply / max(unit_info.supply, 0.5)))

            # 추가 필요량
            need = max(0, target_count - current_count)
            if need == 0:
                continue

            # 자원 체크
            can_afford = min(
                minerals // max(unit_info.mineral, 1),
                gas // max(unit_info.gas, 1) if unit_info.gas > 0 else 999,
                int(supply_left / max(unit_info.supply, 0.5)),
            )

            produce = min(need, can_afford, 5)  # 한번에 최대 5기
            if produce > 0:
                recommendations.append((unit_name, produce))

        return recommendations

    def calculate_army_value(self) -> Dict[str, float]:
        """
        현재 아군 군대 가치 계산

        Returns:
            {"total_value": 총 가치, "mineral_value": 미네랄 가치, "gas_value": 가스 가치}
        """
        total_mineral = 0
        total_gas = 0

        for unit_name, count in self.current_composition.items():
            name_lower = unit_name.lower()
            if name_lower in ZERG_UNITS:
                info = ZERG_UNITS[name_lower]
                total_mineral += info.mineral * count
                total_gas += info.gas * count

        return {
            "total_value": total_mineral + total_gas,
            "mineral_value": total_mineral,
            "gas_value": total_gas,
        }

    def _get_default_composition(self) -> Dict[str, float]:
        """적 정보 없을 때 기본 조합"""
        enemy_race = getattr(self.bot, "enemy_race", None)

        if enemy_race is not None:
            race_str = str(enemy_race)
            if "Terran" in race_str:
                return {"roach": 0.35, "ravager": 0.15, "hydralisk": 0.3, "zergling": 0.2}
            elif "Protoss" in race_str:
                return {"roach": 0.3, "hydralisk": 0.35, "ravager": 0.15, "lurker": 0.1, "zergling": 0.1}
            elif "Zerg" in race_str:
                return {"roach": 0.4, "ravager": 0.2, "hydralisk": 0.2, "zergling": 0.2}

        return {"roach": 0.35, "hydralisk": 0.3, "zergling": 0.2, "ravager": 0.15}

    def get_status(self) -> Dict[str, Any]:
        """최적화 상태 반환"""
        return {
            "enemy_composition": self.enemy_composition,
            "current_composition": self.current_composition,
            "recommendation": self._cached_recommendation,
        }
