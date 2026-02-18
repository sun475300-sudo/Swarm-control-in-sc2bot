"""
유휴 유닛 관리 시스템 (Idle Unit Manager)

노는 병력이 없도록 모든 유닛을 자동으로 관리합니다.

기능:
1. 대기 중인 군사 유닛 → 주력 부대 합류
2. 고립된 유닛 → 집결지로 복귀
3. 부상당한 유닛 → 자동 후퇴
4. 소수 병력 → 자동 견제
"""

from typing import List, Optional, Set
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger


class IdleUnitManager:
    """유휴 유닛 자동 관리"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("IdleUnitManager")

        # 전투 유닛 타입
        self.combat_unit_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKERMP,
            UnitTypeId.MUTALISK,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.SWARMHOSTMP,
            UnitTypeId.INFESTOR,
            UnitTypeId.VIPER,
            UnitTypeId.ULTRALISK,
        }

        # 유닛 태그 추적
        self.managed_units: Set[int] = set()

        # 집결지
        self.rally_point: Optional[Point2] = None
        self.last_rally_update = 0

    def _is_unit_managed_by_other_system(self, unit_tag: int) -> bool:
        """★ 다른 시스템이 제어 중인 유닛인지 확인 ★"""
        # UnitAuthority 체크
        authority = getattr(self.bot, "unit_authority", None)
        if authority and unit_tag in authority.authorities:
            owner = authority.authorities[unit_tag].owner
            if owner != "IdleUnitManager":
                return True

        # HarassmentCoordinator squad 체크
        harass = getattr(self.bot, "harassment_coord", None)
        if harass:
            if unit_tag in getattr(harass, "zergling_runby_tags", set()):
                return True
            if unit_tag in getattr(harass, "mutalisk_harass_tags", set()):
                return True
            if unit_tag in getattr(harass, "roach_poke_tags", set()):
                return True
            if unit_tag in getattr(harass, "drop_unit_tags", set()):
                return True
            if unit_tag in getattr(harass, "locked_units", set()):
                return True

        # AdvancedScoutV2 체크
        scout = getattr(self.bot, "advanced_scout_v2", None)
        if scout and hasattr(scout, "active_scouts"):
            if unit_tag in scout.active_scouts:
                return True

        # RogueTactics 드랍 체크
        rogue = getattr(self.bot, "rogue_tactics", None)
        if rogue and unit_tag in getattr(rogue, "_drop_overlords", set()):
            return True

        return False

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 10프레임마다 집결지 업데이트
            if iteration - self.last_rally_update > 10:
                self._update_rally_point()
                self.last_rally_update = iteration

            # 유휴 유닛 관리
            await self._manage_idle_units()

            # 고립된 유닛 복귀
            await self._recall_isolated_units()

            # 부상당한 유닛 후퇴
            await self._retreat_wounded_units()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"Idle unit manager error: {e}")

    def _update_rally_point(self):
        """집결지 업데이트"""
        if not self.bot.townhalls.exists:
            return

        main_base = self.bot.townhalls.first.position

        # 맵 중심 방향으로 집결
        if hasattr(self.bot, 'game_info'):
            map_center = self.bot.game_info.map_center
            self.rally_point = main_base.towards(map_center, 10)
        else:
            self.rally_point = main_base

    async def _manage_idle_units(self):
        """
        대기 중인 군사 유닛을 자동으로 관리

        우선순위:
        1. 주력 부대에 합류
        2. 집결지로 이동
        3. 적 기지 공격
        """
        if not self.rally_point:
            return

        combat_units = self.bot.units.filter(
            lambda u: u.type_id in self.combat_unit_types
        )

        for unit in combat_units:
            # 이미 명령 받은 유닛은 제외
            if not unit.is_idle:
                continue

            # 건물 공격 중인 유닛 제외
            if unit.is_attacking:
                continue

            # ★ 다른 시스템이 제어 중인 유닛 제외 ★
            if self._is_unit_managed_by_other_system(unit.tag):
                continue

            # 주력 부대 찾기
            main_force = self._find_main_force()

            if main_force:
                # 주력 부대에 합류
                unit.move(main_force)
            elif self.bot.enemy_structures.exists:
                # 적 건물 공격
                target = self.bot.enemy_structures.closest_to(unit)
                unit.attack(target.position)
            else:
                # 집결지로 이동
                unit.move(self.rally_point)

    def _find_main_force(self) -> Optional[Point2]:
        """
        주력 부대 위치 찾기

        병력이 가장 많이 모인 위치를 반환합니다.
        """
        combat_units = self.bot.units.filter(
            lambda u: u.type_id in self.combat_unit_types
        )

        if not combat_units.exists:
            return None

        # 병력 중심 계산
        total_x = sum(u.position.x for u in combat_units)
        total_y = sum(u.position.y for u in combat_units)

        center_x = total_x / combat_units.amount
        center_y = total_y / combat_units.amount

        return Point2((center_x, center_y))

    async def _recall_isolated_units(self):
        """
        고립된 유닛을 집결지로 복귀

        주력 부대와 거리가 먼 소수 병력을 자동으로 복귀시킵니다.
        """
        if not self.rally_point:
            return

        main_force = self._find_main_force()
        if not main_force:
            return

        combat_units = self.bot.units.filter(
            lambda u: u.type_id in self.combat_unit_types
        )

        for unit in combat_units:
            # ★ 다른 시스템이 제어 중인 유닛 제외 ★
            if self._is_unit_managed_by_other_system(unit.tag):
                continue

            # 주력과의 거리
            distance_to_main = unit.distance_to(main_force)

            # 30거리 이상 떨어진 유닛
            if distance_to_main > 30:
                # 주변에 적이 없으면 복귀
                nearby_enemies = self.bot.enemy_units.closer_than(15, unit)

                if not nearby_enemies.exists:
                    unit.move(main_force)

    async def _retreat_wounded_units(self):
        """
        부상당한 유닛 자동 후퇴

        HP가 낮은 유닛을 자동으로 후퇴시킵니다.
        """
        if not self.bot.townhalls.exists:
            return

        main_base = self.bot.townhalls.first.position

        combat_units = self.bot.units.filter(
            lambda u: u.type_id in self.combat_unit_types
        )

        for unit in combat_units:
            # HP 비율 계산
            hp_ratio = unit.health / unit.health_max

            # HP 30% 이하면 후퇴
            if hp_ratio < 0.3:
                # 주변에 적이 있으면 후퇴
                nearby_enemies = self.bot.enemy_units.closer_than(10, unit)

                if nearby_enemies.exists:
                    # 가장 가까운 아군 기지로 후퇴
                    closest_base = self.bot.townhalls.closest_to(unit)
                    unit.move(closest_base.position)

                    # 퀸 트랜스퓨전 요청
                    if hasattr(self.bot, 'queen_manager'):
                        # 퀸 힐 우선순위 추가 (구현 필요)
                        pass

    def get_idle_count(self) -> int:
        """대기 중인 군사 유닛 수"""
        combat_units = self.bot.units.filter(
            lambda u: u.type_id in self.combat_unit_types and u.is_idle
        )
        return combat_units.amount

    def get_status_report(self) -> dict:
        """상태 보고"""
        combat_units = self.bot.units.filter(
            lambda u: u.type_id in self.combat_unit_types
        )

        idle_units = combat_units.filter(lambda u: u.is_idle)
        wounded_units = combat_units.filter(lambda u: u.health / u.health_max < 0.5)

        return {
            "total_combat_units": combat_units.amount,
            "idle_units": idle_units.amount,
            "wounded_units": wounded_units.amount,
            "rally_point": self.rally_point,
        }


# ==================== 확장: 소수 병력 자동 견제 ====================

class HarassmentManager:
    """
    소수 병력 자동 견제 시스템

    작은 부대를 자동으로 적 확장 기지나 일꾼 라인에 보내 견제합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("HarassmentManager")

        # 견제 유닛
        self.harassment_units: Set[int] = set()
        self.last_harassment = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 30초마다 견제 시도
            if iteration - self.last_harassment > 660:
                await self._send_harassment_squad()
                self.last_harassment = iteration

            # 견제 유닛 관리
            await self._manage_harassment_units()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"Harassment manager error: {e}")

    async def _send_harassment_squad(self):
        """
        소규모 견제 부대 파견

        뮤탈리스크, 저글링 등 빠른 유닛 3-5마리를 적 확장에 보냅니다.
        """
        # 뮤탈리스크 우선
        mutalisks = self.bot.units(UnitTypeId.MUTALISK).idle

        if mutalisks.amount >= 3:
            squad = mutalisks.take(3)
            target = await self._find_harassment_target()

            if target:
                for unit in squad:
                    self.harassment_units.add(unit.tag)
                    unit.attack(target)

                self.logger.info(f"[HARASSMENT] Sent 3 Mutalisks to {target}")
                return

        # 저글링 대안
        zerglings = self.bot.units(UnitTypeId.ZERGLING).idle

        if zerglings.amount >= 6:
            squad = zerglings.take(6)
            target = await self._find_harassment_target()

            if target:
                for unit in squad:
                    self.harassment_units.add(unit.tag)
                    unit.attack(target)

                self.logger.info(f"[HARASSMENT] Sent 6 Zerglings to {target}")

    async def _find_harassment_target(self) -> Optional[Point2]:
        """견제 목표 찾기"""
        # 1순위: 적 확장 기지
        enemy_expansions = self.bot.enemy_structures.filter(
            lambda s: s.type_id in {UnitTypeId.NEXUS, UnitTypeId.COMMANDCENTER, UnitTypeId.HATCHERY}
        )

        if enemy_expansions.exists:
            # 가장 먼 확장 (가장 약한 방어)
            if self.bot.townhalls.exists:
                farthest = enemy_expansions.furthest_to(self.bot.townhalls.first)
                return farthest.position

        # 2순위: 적 메인 기지
        if self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]

        return None

    async def _manage_harassment_units(self):
        """견제 유닛 관리"""
        # 죽은 유닛 제거
        alive_tags = {u.tag for u in self.bot.units}
        self.harassment_units &= alive_tags

        # 견제 유닛이 대기 상태면 다시 명령
        for tag in list(self.harassment_units):
            unit = self.bot.units.find_by_tag(tag)

            if unit and unit.is_idle:
                # 견제 재개 또는 복귀
                if unit.health / unit.health_max < 0.5:
                    # HP 낮으면 복귀
                    if self.bot.townhalls.exists:
                        unit.move(self.bot.townhalls.first.position)
                        self.harassment_units.remove(tag)
                else:
                    # 계속 견제
                    target = await self._find_harassment_target()
                    if target:
                        unit.attack(target)
