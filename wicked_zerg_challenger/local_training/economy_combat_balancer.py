# -*- coding: utf-8 -*-
"""
Economy-Combat Balancer - 경제/전투 균형 제어

개선 사항:
1. 드론 목표 수치 상향 (중반 60, 후반 80)
2. 결정론적 비율 체크로 생산 편향 완화
"""

from typing import Dict

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        DRONE = "DRONE"
        QUEEN = "QUEEN"
        OVERLORD = "OVERLORD"


class EconomyCombatBalancer:
    def __init__(self, bot):
        self.bot = bot
        self.production_history = {"drones": 0, "army_units": 0, "total": 0}
        self.drone_targets = {"early": 30, "mid": 60, "late": 80}
        self.drones_per_base = 16

    def should_make_drone(self, current_drone_count: int, army_count: int) -> bool:
        if self._is_emergency_defense():
            return False

        target_drones = self._calculate_target_drones()
        if current_drone_count >= target_drones:
            return False

        total = self.production_history["total"]
        if total == 0:
            return True

        drone_ratio = self.production_history["drones"] / total
        target_ratio = self._calculate_target_drone_ratio()

        if drone_ratio < target_ratio - 0.1:
            return True
        if drone_ratio > target_ratio + 0.1:
            return False

        return current_drone_count < target_drones

    def record_production(self, unit_type: UnitTypeId) -> None:
        self.production_history["total"] += 1
        if unit_type == UnitTypeId.DRONE:
            self.production_history["drones"] += 1
        else:
            self.production_history["army_units"] += 1

    def _calculate_target_drones(self) -> int:
        try:
            game_time_minutes = self.bot.time / 60.0
            base_count = self.bot.townhalls.amount
            greedy_expand = self._is_greedy_expand()
            if game_time_minutes < 6:
                base_target = self.drone_targets["early"]
            elif game_time_minutes < 12:
                base_target = self.drone_targets["mid"]
            else:
                base_target = self.drone_targets["late"]
            if greedy_expand:
                base_target = max(base_target, 85)
            multi_target = base_count * self.drones_per_base
            return int(max(base_target, multi_target))
        except Exception:
            return 30

    def _calculate_target_drone_ratio(self) -> float:
        try:
            game_time_minutes = self.bot.time / 60.0
            if self._is_emergency_defense():
                return 0.0
            if self._is_greedy_expand():
                return 0.8
            if game_time_minutes < 6:
                return 0.7
            if game_time_minutes < 12:
                return 0.5
            return 0.3
        except Exception:
            return 0.5

    def _is_emergency_defense(self) -> bool:
        intel = getattr(self.bot, "intel", None)
        if not intel:
            return False
        strategy = None
        if hasattr(intel, "get_inferred_strategy"):
            strategy = intel.get_inferred_strategy()
        if strategy in {"12_pool_rush", "early_marine_rush", "proxy"}:
            return True
        if hasattr(intel, "is_under_attack") and intel.is_under_attack():
            return True
        if getattr(intel, "threat_level", 0.0) >= 0.7:
            return True
        return False

    def _is_greedy_expand(self) -> bool:
        intel = getattr(self.bot, "intel", None)
        if not intel:
            return False
        observed = getattr(intel, "observed_buildings", {})
        if not observed:
            return False
        expand_types = []
        for t in ["HATCHERY", "LAIR", "HIVE", "COMMANDCENTER", "ORBITALCOMMAND", "PLANETARYFORTRESS", "NEXUS"]:
            if hasattr(UnitTypeId, t):
                expand_types.append(getattr(UnitTypeId, t))
        enemy_bases = 0
        for ut in expand_types:
            enemy_bases += len(observed.get(ut, []))
        return enemy_bases >= 2
