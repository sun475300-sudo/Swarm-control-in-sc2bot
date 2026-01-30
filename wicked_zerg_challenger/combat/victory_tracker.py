# -*- coding: utf-8 -*-
"""
Victory Tracker - 승리 조건 추적 시스템

기능:
1. 적 건물 수 추적
2. 적 확장 기지 발견
3. 승리 푸시 모드 활성화
4. 전력 공격 실행
"""

from typing import Optional, Set, TYPE_CHECKING

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


class VictoryTracker:
    """
    승리 조건 추적 시스템

    책임:
    - 적 건물 파괴 추적
    - 적 확장 기지 발견
    - 승리 푸시 활성화 판단
    - 승리 푸시 실행
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("VictoryTracker")

        # Victory tracking
        self._victory_push_active = False
        self._last_enemy_structure_count = 0
        self._enemy_structures_destroyed = 0
        self._last_victory_check = 0
        self._victory_check_interval = 110
        self._endgame_push_threshold = 360  # 6분 이후

        # Expansion tracking
        self._known_enemy_expansions: Set = set()
        self._last_expansion_check = 0

    @property
    def is_victory_push_active(self) -> bool:
        """승리 푸시 모드가 활성화되어 있는지 확인"""
        return self._victory_push_active

    async def check_victory_conditions(self, iteration: int):
        """
        승리 조건 추적 및 승리 푸시 활성화

        기능:
        1. 적 건물 수 추적
        2. 적 확장 발견
        3. 승리 푸시 활성화 조건 판단
        """
        game_time = getattr(self.bot, "time", 0)

        # 적 건물 수 추적
        enemy_structures = getattr(self.bot, "enemy_structures", [])
        current_structure_count = len(enemy_structures) if enemy_structures else 0

        # 적 확장 추적 (30초마다)
        if iteration - self._last_expansion_check > 660:
            await self.track_enemy_expansions()
            self._last_expansion_check = iteration

        # 건물이 파괴되었는지 확인
        if current_structure_count < self._last_enemy_structure_count:
            destroyed = self._last_enemy_structure_count - current_structure_count
            self._enemy_structures_destroyed += destroyed
            print(f"[VICTORY] {destroyed} enemy structures destroyed! Total: {self._enemy_structures_destroyed}")

        self._last_enemy_structure_count = current_structure_count

        # 승리 푸시 활성화 조건
        our_army_supply = self.get_army_supply()

        should_activate_victory_push = (
            game_time > self._endgame_push_threshold  # 6분 이후
            and current_structure_count <= 10  # 적 건물 10개 이하
            and our_army_supply >= 30  # 우리 병력 충분
        )

        # 승리 푸시 활성화
        if should_activate_victory_push and not self._victory_push_active:
            self._victory_push_active = True
            print(f"[VICTORY PUSH] ACTIVATED! Enemy structures: {current_structure_count}, Army: {our_army_supply}")

        # 승리 푸시 비활성화 조건
        if self._victory_push_active and (current_structure_count > 10 or our_army_supply < 20):
            self._victory_push_active = False
            print(f"[VICTORY PUSH] Deactivated - regroup needed")

        # 로그 (30초마다)
        if iteration % 660 == 0:
            expansion_count = len(self._known_enemy_expansions)
            status = "ACTIVE" if self._victory_push_active else "STANDBY"
            print(f"[VICTORY] [{int(game_time)}s] Enemy: {current_structure_count} structures, "
                  f"{expansion_count} expansions | Status: {status}")

    async def track_enemy_expansions(self):
        """
        적 확장 기지 추적

        발견한 적 확장 위치를 기록
        """
        if not hasattr(self.bot, "enemy_structures"):
            return

        enemy_structures = self.bot.enemy_structures
        if not enemy_structures:
            return

        # 타운홀 타입
        townhall_types = {
            "NEXUS", "COMMANDCENTER", "ORBITALCOMMAND", "PLANETARYFORTRESS",
            "HATCHERY", "LAIR", "HIVE"
        }

        # 적 타운홀 찾기
        for struct in enemy_structures:
            struct_type = getattr(struct.type_id, "name", "").upper()
            if struct_type in townhall_types:
                pos = struct.position
                if pos not in self._known_enemy_expansions:
                    self._known_enemy_expansions.add(pos)
                    print(f"[VICTORY] New enemy expansion discovered at ({pos.x:.1f}, {pos.y:.1f})")

    async def execute_victory_push(self, iteration: int, attack_target_finder):
        """
        승리 푸시 실행

        승리가 가까워졌을 때 전력을 다해 적 건물 파괴

        Args:
            iteration: 현재 반복 횟수
            attack_target_finder: 공격 타겟을 찾는 함수
        """
        game_time = getattr(self.bot, "time", 0)

        # 모든 전투 유닛 동원
        army_units = self._filter_army_units(getattr(self.bot, "units", []))
        if not army_units:
            return

        # 최우선 목표: 적 건물
        attack_target = attack_target_finder()
        if not attack_target:
            return

        # 승리 푸시: 모든 병력 투입
        for unit in army_units:
            try:
                if unit.is_idle or not getattr(unit, "is_attacking", False):
                    self.bot.do(unit.attack(attack_target))
            except Exception:
                continue

        # 로그 (10초마다)
        if iteration % 220 == 0:
            target_str = f"({attack_target.x:.1f}, {attack_target.y:.1f})" if hasattr(attack_target, 'x') else str(attack_target)
            print(f"[VICTORY PUSH] [{int(game_time)}s] {len(army_units)} units attacking {target_str}")

    def get_army_supply(self) -> int:
        """현재 아군 병력의 supply 합계 계산"""
        if not hasattr(self.bot, "units"):
            return 0

        army_units = self._filter_army_units(self.bot.units)
        total_supply = 0

        for unit in army_units:
            try:
                supply = getattr(unit, "supply", 0)
                if isinstance(supply, (int, float)):
                    total_supply += supply
            except Exception:
                continue

        return int(total_supply)

    def _filter_army_units(self, units):
        """전투 유닛 필터링"""
        army_types = [
            "ZERGLING", "ROACH", "HYDRALISK", "MUTALISK",
            "CORRUPTOR", "BROODLORD", "BANELING", "RAVAGER",
            "ULTRALISK", "LURKER", "INFESTOR", "VIPER"
        ]

        if hasattr(units, "filter"):
            return units.filter(lambda u: u.type_id.name in army_types)
        return [u for u in units if getattr(u.type_id, "name", "") in army_types]
