# -*- coding: utf-8 -*-
"""
Threat Assessment - 위협 평가 시스템

기능:
1. 기지 공격 감지
2. 역공격 기회 판단
3. 적 병력 분석
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.units import Units
    from sc2.unit import Unit
    from sc2.position import Point2
else:
    try:
        from sc2.units import Units
        from sc2.unit import Unit
        from sc2.position import Point2
    except ImportError:
        Units = object
        Unit = object
        Point2 = tuple

from utils.logger import get_logger


class ThreatAssessment:
    """
    위협 평가 시스템

    책임:
    - 기지 공격 감지
    - 역공격 기회 판단
    - 적 병력 분석
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("ThreatAssessment")

        # Combat tracking
        self._last_combat_time = 0
        self._last_counter_attack_time = 0
        self._counter_attack_cooldown = 15  # 15 seconds

        # High threat unit types
        self.high_threat_names = {
            "ZERGLING", "MARINE", "ZEALOT", "REAPER", "ADEPT",
            "BANELING", "ROACH", "STALKER", "MARAUDER",
            "SIEGETANK", "SIEGETANKSIEGED", "WIDOWMINE"
        }

        # ★ Phase 22: Supply calculation cache ★
        self._cached_our_supply = 0
        self._cached_enemy_supply = 0
        self._supply_cache_time = -10  # Force first update

    def is_base_under_attack(self) -> bool:
        """
        기지가 공격받고 있는지 확인

        개선사항:
        - 1기 이상의 적도 위협으로 감지 (초반 러쉬 대응)
        - 게임 시간에 따른 동적 감지
        - 고위협 유닛은 더 넓은 범위에서 감지
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return False

        enemy_units = getattr(self.bot, "enemy_units", [])
        if not enemy_units:
            return False

        game_time = getattr(self.bot, "time", 0)

        for th in self.bot.townhalls:
            # 초반에 더 민감
            base_range = 25 if game_time >= 180 else 30

            # ★ Phase 22: Use optimized closer_than() instead of manual loop ★
            if hasattr(enemy_units, "closer_than"):
                nearby_enemies = enemy_units.closer_than(base_range, th.position)
                if nearby_enemies.exists:
                    return True

                # 고위협 적은 더 넓은 범위에서 확인
                extended_enemies = enemy_units.closer_than(base_range + 10, th.position)
                for e in extended_enemies:
                    if getattr(e.type_id, "name", "").upper() in self.high_threat_names:
                        return True
            else:
                # Fallback for non-Units collections
                nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < base_range]
                if len(nearby_enemies) >= 1:
                    return True

        return False

    def check_counterattack_opportunity(self, army_units, enemy_units, game_time: float) -> bool:
        """
        전투 후 역공격 기회 확인

        조건:
        1. 최근 교전이 있었음 (지난 5초 이내)
        2. 아군 서플라이 > 적 서플라이 * 1.4 (우위)
        3. 최소 서플라이 8 이상
        4. 쿨다운 지남 (15초)

        Returns:
            True if counter attack should be launched
        """
        # Track combat
        if enemy_units and len(list(enemy_units)) > 0:
            self._last_combat_time = game_time

        # Check if there was recent combat
        time_since_combat = game_time - self._last_combat_time
        if time_since_combat > 5:  # No recent combat in last 5 seconds
            return False

        # ★ Phase 22: Use cached supply calculations (updated every 2s) ★
        if game_time - self._supply_cache_time >= 2.0:
            self._cached_our_supply = sum(getattr(u, "supply_cost", 1) for u in army_units)
            self._cached_enemy_supply = sum(getattr(u, "supply_cost", 1) for u in enemy_units) if enemy_units else 0
            self._supply_cache_time = game_time
        our_supply = self._cached_our_supply
        enemy_supply = self._cached_enemy_supply

        # Check cooldown
        time_since_last_counter = game_time - self._last_counter_attack_time
        if time_since_last_counter < self._counter_attack_cooldown:
            return False

        # 카운터 어택 조건
        if our_supply >= 8 and our_supply > enemy_supply * 1.4:
            self._last_counter_attack_time = game_time
            return True

        # 적이 거의 없으면 바로 공격
        if our_supply >= 12 and enemy_supply <= 3:
            self._last_counter_attack_time = game_time
            return True

        return False

    def calculate_threat_score(self, enemy_units, position) -> int:
        """
        특정 위치에 대한 위협 점수 계산

        Returns:
            위협 점수 (높을수록 위험)
        """
        if not enemy_units:
            return 0

        threat_score = 0
        # ★ Phase 22: Use optimized closer_than() ★
        if hasattr(enemy_units, "closer_than"):
            nearby_enemies = enemy_units.closer_than(20, position)
        else:
            nearby_enemies = [e for e in enemy_units if e.distance_to(position) < 20]

        for enemy in nearby_enemies:
            enemy_type = getattr(enemy.type_id, "name", "").upper()

            # 고위협 유닛
            if enemy_type in self.high_threat_names:
                threat_score += 3
            # 공격 가능 유닛
            elif hasattr(enemy, "can_attack") and enemy.can_attack:
                threat_score += 2
            # 일반 유닛
            else:
                threat_score += 1

            # 공중 유닛 추가 점수
            if getattr(enemy, "is_flying", False):
                threat_score += 1

        return threat_score

    def get_army_power(self, units) -> float:
        """
        병력 전투력 계산

        Returns:
            전투력 점수 (서플라이 기반)
        """
        if not units:
            return 0.0

        power = 0.0
        for unit in units:
            supply_cost = getattr(unit, "supply_cost", 1)
            health_percentage = getattr(unit, "health_percentage", 1.0)

            # 기본 전투력 = 서플라이 * 체력 비율
            unit_power = supply_cost * health_percentage

            # 유닛 타입별 보정
            unit_type = getattr(unit.type_id, "name", "").upper()
            if unit_type in ["ULTRALISK", "BROODLORD"]:
                unit_power *= 1.5  # 고급 유닛
            elif unit_type in ["BANELING"]:
                unit_power *= 1.2  # 특수 유닛

            power += unit_power

        return power

    def should_retreat(self, army_units, enemy_units) -> bool:
        """
        후퇴 여부 판단

        조건:
        - 적 전투력이 아군의 2배 이상
        - 아군 병력이 너무 적음 (3기 이하)
        """
        if not army_units:
            return True

        our_power = self.get_army_power(army_units)
        enemy_power = self.get_army_power(enemy_units) if enemy_units else 0

        # 병력이 너무 적으면 후퇴
        if len(army_units) <= 3:
            return True

        # 적이 압도적으로 강하면 후퇴
        if enemy_power > our_power * 2:
            return True

        return False
