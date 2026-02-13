# -*- coding: utf-8 -*-
"""
Combat Execution - 전투 실행 시스템

기능:
1. 전투 실행 및 조율
2. 진형 형성 (Concave)
3. 기본 공격 로직
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


class CombatExecution:
    """
    전투 실행 시스템

    책임:
    - 전투 실행 조율
    - 타겟팅 및 마이크로 시스템 연동
    - 진형 형성 관리
    - 기본 공격 로직
    """

    def __init__(self, bot, targeting=None, micro_combat=None):
        self.bot = bot
        self.logger = get_logger("CombatExecution")

        # 연동 시스템
        self.targeting = targeting
        self.micro_combat = micro_combat

        # ★ Phase 22: Cache FormationManager instance ★
        self._formation_manager = None

    async def execute_combat(self, units, enemy_units):
        """
        전투 실행

        우선순위:
        1. 진형 형성 (원거리 유닛)
        2. 오버킬 분산 타겟 할당
        3. 집중 사격
        4. 키팅
        5. 기본 공격 (fallback)

        Args:
            units: 아군 유닛들
            enemy_units: 적 유닛들
        """
        try:
            # 0. 진형 형성 (원거리 유닛만)
            await self.form_formation(units, enemy_units)

            # 1. 오버킬 분산 타겟 할당
            if self.targeting and self.micro_combat:
                assignments = self.targeting.assign_targets(units, enemy_units)
                if assignments:
                    await self.micro_combat.attack_assigned_targets(units, assignments)
                    return

            # 2. 집중 사격 (타겟팅 시스템 사용)
            if self.targeting:
                focus_target = None
                if hasattr(self.targeting, "get_focus_fire_target"):
                    focus_target = self.targeting.get_focus_fire_target(units, enemy_units)
                elif hasattr(self.targeting, "select_focus_fire_target"):
                    focus_target = self.targeting.select_focus_fire_target(units, enemy_units)
                if focus_target:
                    if self.micro_combat:
                        await self.micro_combat.focus_fire(units, focus_target)
                    return

            # 3. 타겟팅 시스템 없으면 마이크로 키팅
            if self.micro_combat:
                await self.micro_combat.kiting(units, enemy_units)
            else:
                # 마이크로 전투도 없으면 기본 공격
                await self.basic_attack(units, enemy_units)

        except Exception as e:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 200 == 0:
                self.logger.warning(f"Combat execution error: {e}")
            # 에러 발생 시 기본 공격
            await self.basic_attack(units, enemy_units)

    async def form_formation(self, units, enemy_units):
        """
        진형 형성

        Concave 진형 및 길목 차단 로직

        Args:
            units: 아군 유닛들
            enemy_units: 적 유닛들
        """
        try:
            from combat.formation_manager import FormationManager

            # ★ Phase 22: Reuse cached instance ★
            if self._formation_manager is None:
                self._formation_manager = FormationManager(self.bot)
            formation_manager = self._formation_manager

            if not self._has_units(enemy_units) or not self._has_units(units):
                return

            # 적 중심 계산
            enemy_center = self._get_enemy_center(enemy_units)
            if enemy_center is None:
                return

            # 원거리 유닛만 진형 형성 (히드라, 바퀴, 파멸충)
            ranged_units = self._filter_units_by_type(
                units, ["HYDRALISK", "ROACH", "RAVAGER"]
            )

            if self._has_units(ranged_units) and self._units_amount(ranged_units) >= 3:
                # Concave 진형 형성
                formation_positions = formation_manager.form_concave(
                    ranged_units, enemy_center, formation_radius=8.0
                )

                # ★ Phase 22: Increased formation limit 10 -> 30 ★
                for unit, target_pos in formation_positions[:30]:
                    try:
                        self.bot.do(unit.move(target_pos))
                    except Exception:
                        pass

            # 길목 회피 확인
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                our_base = self.bot.townhalls.first.position
                chokepoint = formation_manager.find_chokepoint(enemy_units, our_base)

                if chokepoint and formation_manager.should_avoid_chokepoint(units, chokepoint, enemy_units):
                    # 넓은 곳으로 후퇴
                    retreat_pos = formation_manager.get_retreat_position(units, enemy_units, our_base)
                    if retreat_pos:
                        for unit in units[:30]:  # ★ Phase 22: 10 -> 30 ★
                            try:
                                self.bot.do(unit.move(retreat_pos))
                            except Exception:
                                pass

        except Exception as e:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 200 == 0:
                self.logger.warning(f"Formation error: {e}")

    async def basic_attack(self, units, enemy_units):
        """
        기본 공격 (fallback)

        특징:
        - 대공 유닛은 공중 적 우선 타겟팅
        - 나머지는 가장 가까운 적 공격

        Args:
            units: 아군 유닛들
            enemy_units: 적 유닛들
        """
        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            # Fallback: simple attack
            for unit in list(units)[:30]:
                target = self._closest_enemy(enemy_units, unit)
                if target:
                    self.bot.do(unit.attack(target))
            return

        # 대공 가능 유닛 타입
        can_shoot_up = {
            UnitTypeId.QUEEN, UnitTypeId.HYDRALISK,
            UnitTypeId.CORRUPTOR, UnitTypeId.MUTALISK,
            UnitTypeId.SPORECRAWLER
        }

        for unit in list(units)[:30]:  # 최대 30개만 처리
            target = None

            # 대공 가능 유닛은 공중 유닛 우선 타겟팅
            if hasattr(unit, 'type_id') and unit.type_id in can_shoot_up:
                air_enemies = [e for e in enemy_units if getattr(e, "is_flying", False)]
                if air_enemies:
                    target = min(air_enemies, key=lambda e: e.distance_to(unit))

            # 공중 유닛 없으면 가장 가까운 적
            if not target:
                target = self._closest_enemy(enemy_units, unit)

            if target:
                self.bot.do(unit.attack(target))

    # ===== Helper Methods =====

    def _has_units(self, units) -> bool:
        """유닛이 존재하는지 확인"""
        if hasattr(units, "exists"):
            return bool(units.exists)
        return bool(units)

    def _units_amount(self, units) -> int:
        """유닛 수 반환"""
        if hasattr(units, "amount"):
            return int(units.amount)
        return len(units)

    def _filter_units_by_type(self, units, names):
        """유닛 타입으로 필터링"""
        if hasattr(units, "filter"):
            return units.filter(lambda u: u.type_id.name in names)
        return [u for u in units if getattr(u.type_id, "name", "") in names]

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

    def _closest_enemy(self, enemy_units, unit):
        """가장 가까운 적 찾기"""
        if hasattr(enemy_units, "closest_to"):
            try:
                return enemy_units.closest_to(unit.position)
            except Exception:
                return None

        closest_unit = None
        closest_dist = None
        for enemy in enemy_units:
            try:
                dist = unit.distance_to(enemy)
            except Exception:
                continue
            if closest_dist is None or dist < closest_dist:
                closest_unit = enemy
                closest_dist = dist
        return closest_unit
