# -*- coding: utf-8 -*-
"""
Expansion Defense - 확장 기지 방어 시스템

기능:
1. 확장 기지 공격 감지
2. 확장 기지 파괴 감지
3. 방어 병력 자동 파견
4. 파괴 후 반격
"""

from typing import Dict, Set, TYPE_CHECKING

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


class ExpansionDefense:
    """
    확장 기지 방어 시스템

    책임:
    - 확장 기지 공격 감지
    - 방어 병력 파견
    - 확장 기지 파괴 감지
    - 파괴 후 반격
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("ExpansionDefense")

        # Expansion defense state
        self._expansion_under_attack: Dict[int, float] = {}  # base_tag -> attack_start_time
        self._expansion_destroyed_positions = []
        self._last_expansion_defense_check = 0
        self._expansion_defense_check_interval = 10
        self._expansion_defense_force_size = 8

    async def check_expansion_defense(self, iteration: int):
        """
        확장 기지 방어 체크

        기능:
        1. 확장 기지 파괴 감지 및 대응
        2. 확장 기지 공격 감지
        3. 방어 병력 파견
        """
        if not hasattr(self.bot, "townhalls"):
            return

        townhalls = self.bot.townhalls
        current_time = getattr(self.bot, "time", 0)
        enemy_units = getattr(self.bot, "enemy_units", [])

        if not enemy_units:
            return

        # STEP 1: 확장 기지 파괴 감지
        current_bases = set(th.tag for th in townhalls)
        previous_bases = set(self._expansion_under_attack.keys())

        destroyed_bases = previous_bases - current_bases
        if destroyed_bases:
            for base_tag in destroyed_bases:
                attack_start_time = self._expansion_under_attack.get(base_tag, current_time)

                print(f"[EXPANSION DESTROYED] [{int(current_time)}s] ★ WARNING ★ Expansion destroyed after {int(current_time - attack_start_time)}s!")

                # 파괴된 기지 정보 제거
                if base_tag in self._expansion_under_attack:
                    del self._expansion_under_attack[base_tag]

            # 대응: 반격 병력 투입
            await self.counterattack_after_base_loss(destroyed_bases, iteration)

        # STEP 2: 확장 기지 공격 감지
        if not townhalls.exists or len(townhalls) < 2:
            return

        # 메인 기지 제외한 확장들
        main_base = townhalls.first
        expansions = [th for th in townhalls if th.tag != main_base.tag]

        for expansion in expansions:
            expansion_tag = expansion.tag

            # 확장 기지 주변 30 거리 내 적 확인
            nearby_enemies = [e for e in enemy_units if e.distance_to(expansion.position) < 30]

            if nearby_enemies:
                # 공격받고 있음
                if expansion_tag not in self._expansion_under_attack:
                    # 처음 공격받음
                    self._expansion_under_attack[expansion_tag] = current_time
                    print(f"[EXPANSION DEFENSE] [{int(current_time)}s] ★ WARNING ★ Expansion under attack! {len(nearby_enemies)} enemies detected")

                # 방어 병력 파견
                await self.defend_expansion(expansion, nearby_enemies, iteration)

            else:
                # 공격받지 않음
                if expansion_tag in self._expansion_under_attack:
                    attack_duration = current_time - self._expansion_under_attack[expansion_tag]
                    print(f"[EXPANSION DEFENSE] [{int(current_time)}s] ✓ Expansion secured after {int(attack_duration)}s")
                    del self._expansion_under_attack[expansion_tag]

    async def defend_expansion(self, expansion, nearby_enemies, iteration: int):
        """
        확장 기지 방어 병력 파견

        전략:
        1. 근처 유닛 8-12기 파견
        2. 퀸 우선 투입
        3. 고위협 유닛 집중 공격
        """
        if not hasattr(self.bot, "units"):
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            return

        army_units = self._filter_army_units(self.bot.units)
        if not army_units:
            return

        # 확장 기지에서 가까운 유닛들 찾기
        nearby_army = [u for u in army_units if u.distance_to(expansion.position) < 50]

        # 최소 8기, 최대 12기 파견
        defense_force = nearby_army[:12] if len(nearby_army) >= 8 else nearby_army

        if not defense_force:
            # 근처에 병력이 없으면 멀리서라도 파견
            defense_force = sorted(army_units, key=lambda u: u.distance_to(expansion.position))[:8]

        if not defense_force:
            return

        # 고위협 유닛 우선 타겟
        high_priority_targets = {
            "SIEGETANK", "SIEGETANKSIEGED", "COLOSSUS", "IMMORTAL",
            "THOR", "BATTLECRUISER", "ARCHON", "DISRUPTOR"
        }

        priority_target = None
        for enemy in nearby_enemies:
            enemy_type = getattr(enemy.type_id, "name", "").upper()
            if enemy_type in high_priority_targets:
                priority_target = enemy
                break

        # 적 중심 위치
        threat_center = self._get_enemy_center(nearby_enemies)

        # 퀸 우선 투입
        queens = [u for u in defense_force if hasattr(u, 'type_id') and u.type_id == UnitTypeId.QUEEN]
        other_units = [u for u in defense_force if u not in queens]

        # 퀸 방어
        for queen in queens:
            try:
                target = priority_target if priority_target else threat_center
                if queen.distance_to(expansion.position) < 15:
                    self.bot.do(queen.attack(target))
                else:
                    self.bot.do(queen.move(expansion.position))
            except Exception:
                continue

        # 다른 유닛 방어
        for unit in other_units:
            try:
                target = priority_target if priority_target else threat_center
                self.bot.do(unit.attack(target))
            except Exception:
                continue

        # 로그 (5초마다)
        if iteration % 110 == 0:
            current_time = getattr(self.bot, "time", 0)
            print(f"[EXPANSION DEFENSE] [{int(current_time)}s] {len(defense_force)} units defending expansion")

    async def counterattack_after_base_loss(self, destroyed_base_tags: Set[int], iteration: int):
        """
        확장 기지 파괴 후 반격

        파괴된 확장 근처의 적을 섬멸하기 위해 병력 투입
        """
        if not hasattr(self.bot, "units"):
            return

        army_units = self._filter_army_units(self.bot.units)
        if not army_units:
            return

        # 적 유닛이 있으면 반격
        enemy_units = getattr(self.bot, "enemy_units", [])
        if not enemy_units:
            return

        # 모든 병력을 적 위치로 보냄
        enemy_center = self._get_enemy_center(enemy_units)
        if not enemy_center:
            return

        for unit in army_units:
            try:
                self.bot.do(unit.attack(enemy_center))
            except Exception:
                continue

        current_time = getattr(self.bot, "time", 0)
        print(f"[COUNTERATTACK] [{int(current_time)}s] ★ REVENGE! ★ {len(army_units)} units counterattacking after base loss!")

    # ===== Helper Methods =====

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

    def _get_enemy_center(self, enemy_units):
        """적 유닛들의 중심 위치 계산"""
        if not enemy_units:
            return None

        items = list(enemy_units)
        if not items:
            return None

        count = len(items)
        x_sum = sum(u.position.x for u in items)
        y_sum = sum(u.position.y for u in items)

        try:
            from sc2.position import Point2
            return Point2((x_sum / count, y_sum / count))
        except ImportError:
            return items[0].position
