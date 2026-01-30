# -*- coding: utf-8 -*-
"""
Multitasking System - 멀티태스킹 관리

기능:
1. 작업 우선순위 관리
2. 유닛 할당 추적
3. 동시 작업 실행
"""

from typing import Dict, Optional, Set, List, Tuple, TYPE_CHECKING

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


class MultitaskingSystem:
    """
    멀티태스킹 시스템

    책임:
    - 여러 작업 동시 관리
    - 우선순위 기반 유닛 할당
    - 작업 실행 조율
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("Multitasking")

        # Task priorities (higher = more important)
        self.task_priorities = {
            "base_defense": 100,      # 기지 방어 - 최우선
            "worker_defense": 90,     # 일꾼 방어
            "expansion_denial": 90,   # 확장 견제
            "counter_attack": 70,     # 역공격
            "early_harass": 75,       # 초반 하라스
            "air_harass": 60,         # 공중 하라스
            "main_attack": 50,        # 메인 공격
            "scout": 50,              # 정찰
            "creep_denial": 35,       # 점막 제거
            "creep_spread": 30,       # 점막 확장
            "clear_rocks": 40,        # 암석 제거
            "rally": 20,              # 집결
        }

        # Active tasks and assigned units
        self._active_tasks: Dict[str, Dict] = {}  # task_name -> {"units": set(), "target": position}
        self._unit_assignments: Dict[int, str] = {}  # unit_tag -> task_name

        # Task cooldowns
        self._task_cooldowns: Dict[str, float] = {}

    def get_task_priority(self, task_name: str) -> int:
        """작업 우선순위 가져오기"""
        return self.task_priorities.get(task_name, 0)

    def adjust_priorities_for_strategy(self, strategy_mode: str):
        """
        전략 모드에 따라 우선순위 동적 조정

        Args:
            strategy_mode: "normal", "aggressive", "all_in" 등
        """
        # 기본 우선순위 복원
        self.task_priorities["base_defense"] = 100
        self.task_priorities["main_attack"] = 50

        # 공격 모드면 공격 우선순위 상향
        if strategy_mode in ["aggressive", "all_in"]:
            self.task_priorities["main_attack"] = 90
            self.task_priorities["base_defense"] = 45

            # ALL_IN이면 방어 더 낮춤
            if strategy_mode == "all_in":
                self.task_priorities["base_defense"] = 20

    def create_task_list(self, army_units, air_units, enemy_units, iteration: int) -> List[Tuple[str, any, int]]:
        """
        우선순위 기반 작업 리스트 생성

        Returns:
            List of (task_name, target, priority) tuples
        """
        tasks = []
        game_time = getattr(self.bot, "time", 0)

        # Import required for some tasks
        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            UnitTypeId = None

        # === TASK 1: Base Defense ===
        # (This would call BaseDefenseSystem.evaluate_base_threat)
        # Placeholder - will be filled by CombatManager

        # === TASK 2: Early Zergling Harass (1-7 minutes) ===
        if 60 <= game_time <= 420 and UnitTypeId:
            zerglings = [u for u in army_units if hasattr(u, 'type_id') and u.type_id == UnitTypeId.ZERGLING]
            if 6 <= len(zerglings) <= 24:
                # Will need harass target from elsewhere
                tasks.append(("early_harass", None, self.task_priorities["early_harass"]))

        # === TASK 3: Expansion Denial ===
        if hasattr(self.bot, "enemy_structures") and game_time > 180:
            townhall_types = {
                "NEXUS", "COMMANDCENTER", "COMMANDCENTERFLYING",
                "ORBITALCOMMAND", "ORBITALCOMMANDFLYING", "PLANETARYFORTRESS",
                "HATCHERY", "LAIR", "HIVE"
            }

            enemy_bases = [
                s for s in self.bot.enemy_structures
                if getattr(s.type_id, "name", "").upper() in townhall_types
            ]

            if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                enemy_start = self.bot.enemy_start_locations[0]

                expansions = [
                    base for base in enemy_bases
                    if base.distance_to(enemy_start) > 15
                ]

                if expansions and hasattr(self.bot, "start_location"):
                    target_expansion = min(expansions, key=lambda b: b.distance_to(self.bot.start_location))
                    tasks.append(("deny_expansion", target_expansion.position, self.task_priorities["expansion_denial"]))

        # === TASK 4: Creep Denial ===
        if hasattr(self.bot, "creep_denial") and self.bot.creep_denial:
            tasks.append(("creep_denial", None, self.task_priorities["creep_denial"]))

        # === TASK 5: Main Attack ===
        if army_units:
            tasks.append(("main_attack", None, self.task_priorities["main_attack"]))

        return tasks

    def assign_unit_to_task(self, unit_tag: int, task_name: str):
        """유닛을 작업에 할당"""
        self._unit_assignments[unit_tag] = task_name

        if task_name not in self._active_tasks:
            self._active_tasks[task_name] = {"units": set(), "target": None}

        self._active_tasks[task_name]["units"].add(unit_tag)

    def unassign_unit(self, unit_tag: int):
        """유닛 할당 해제"""
        if unit_tag in self._unit_assignments:
            task_name = self._unit_assignments[unit_tag]
            del self._unit_assignments[unit_tag]

            if task_name in self._active_tasks:
                self._active_tasks[task_name]["units"].discard(unit_tag)

    def get_unit_task(self, unit_tag: int) -> Optional[str]:
        """유닛의 현재 작업 가져오기"""
        return self._unit_assignments.get(unit_tag)

    def is_unit_assigned(self, unit_tag: int) -> bool:
        """유닛이 작업에 할당되었는지 확인"""
        return unit_tag in self._unit_assignments

    def cleanup_dead_units(self, current_units):
        """죽은 유닛 할당 정리"""
        if not hasattr(self.bot, "units"):
            return

        current_tags = {u.tag for u in current_units}
        dead_tags = [tag for tag in self._unit_assignments if tag not in current_tags]

        for tag in dead_tags:
            self.unassign_unit(tag)

    def get_task_units(self, task_name: str) -> Set[int]:
        """특정 작업에 할당된 유닛 태그 집합 반환"""
        if task_name in self._active_tasks:
            return self._active_tasks[task_name]["units"]
        return set()

    def clear_task(self, task_name: str):
        """작업 완전히 제거"""
        if task_name in self._active_tasks:
            # 할당된 모든 유닛 해제
            for unit_tag in list(self._active_tasks[task_name]["units"]):
                self.unassign_unit(unit_tag)

            del self._active_tasks[task_name]

    def get_available_units(self, units) -> List:
        """할당되지 않은 유닛 목록 반환"""
        return [u for u in units if not self.is_unit_assigned(u.tag)]

    def set_task_target(self, task_name: str, target):
        """작업 타겟 설정"""
        if task_name not in self._active_tasks:
            self._active_tasks[task_name] = {"units": set(), "target": None}

        self._active_tasks[task_name]["target"] = target

    def get_task_target(self, task_name: str):
        """작업 타겟 가져오기"""
        if task_name in self._active_tasks:
            return self._active_tasks[task_name]["target"]
        return None

    def get_active_tasks(self) -> List[str]:
        """현재 활성화된 작업 목록"""
        return list(self._active_tasks.keys())

    def get_task_count(self) -> int:
        """활성화된 작업 수"""
        return len(self._active_tasks)
