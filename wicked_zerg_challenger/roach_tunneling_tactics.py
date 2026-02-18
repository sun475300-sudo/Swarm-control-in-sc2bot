# -*- coding: utf-8 -*-
"""
Roach Tunneling Tactics - 바퀴 땅굴발톱 전술

땅굴발톱(Tunneling Claws) 업그레이드 후:
1. 잠복 이동 전술 활용
2. 적 후방 침투
3. 포위 기동
"""

from typing import Dict, Set
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from utils.logger import get_logger


class RoachTunnelingTactics:
    """바퀴 땅굴발톱 전술 시스템"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("RoachTunnel")

        # 땅굴발톱 업그레이드 추적
        self.tunneling_researched = False
        self.tunneling_requested = False

        # 잠복 이동 중인 바퀴
        self.tunneling_roaches: Set[int] = set()

        # 통계
        self.tunneling_attacks = 0
        self.flanking_maneuvers = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 22프레임(약 1초)마다 실행
            if iteration % 22 != 0:
                return

            game_time = self.bot.time

            # 1. 땅굴발톱 업그레이드 요청
            await self._request_tunneling_upgrade()

            # 2. 땅굴발톱 업그레이드 확인
            self._check_tunneling_upgrade()

            # 3. 땅굴발톱 전술 사용
            if self.tunneling_researched:
                await self._use_tunneling_tactics(game_time)

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[TUNNELING] Error: {e}")

    async def _request_tunneling_upgrade(self):
        """땅굴발톱 업그레이드 요청"""
        if self.tunneling_requested or self.tunneling_researched:
            return

        # 바퀴가 10마리 이상 있을 때 업그레이드
        roach_count = self.bot.units(UnitTypeId.ROACH).amount
        if roach_count < 10:
            return

        # Roach Warren 확인
        roach_warren = self.bot.structures(UnitTypeId.ROACHWARREN).ready
        if not roach_warren:
            return

        warren = roach_warren.first

        # 이미 연구 중인지 확인
        if warren.is_idle and self.bot.can_afford(UpgradeId.TUNNELINGCLAWS):
            abilities = await self.bot.get_available_abilities(warren)
            if AbilityId.RESEARCH_TUNNELINGCLAWS in abilities:
                self.bot.do(warren(AbilityId.RESEARCH_TUNNELINGCLAWS))
                self.tunneling_requested = True
                self.logger.info("[TUNNELING] Researching Tunneling Claws!")

    def _check_tunneling_upgrade(self):
        """땅굴발톱 업그레이드 완료 확인"""
        if not self.tunneling_researched:
            if UpgradeId.TUNNELINGCLAWS in self.bot.state.upgrades:
                self.tunneling_researched = True
                self.logger.info("[TUNNELING] Tunneling Claws completed! Roaches can now burrow move!")

    async def _use_tunneling_tactics(self, game_time: float):
        """땅굴발톱 전술 사용"""
        roaches = self.bot.units(UnitTypeId.ROACH)
        if not roaches:
            return

        # === 1. 후방 침투 전술 ===
        await self._rear_infiltration(roaches)

        # === 2. 포위 기동 ===
        await self._flanking_maneuver(roaches)

    async def _rear_infiltration(self, roaches):
        """후방 침투: 적 기지 뒤로 잠복 이동"""
        # 적 기지 확인
        enemy_bases = self.bot.enemy_structures.filter(
            lambda s: s.type_id in {
                UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND,
                UnitTypeId.NEXUS, UnitTypeId.HATCHERY
            }
        )

        if not enemy_bases:
            return

        # 체력 70% 이상인 바퀴만 사용
        healthy_roaches = roaches.filter(lambda r: r.health_percentage > 0.7)
        if healthy_roaches.amount < 5:
            return

        # 5마리의 바퀴를 후방 침투 부대로
        infiltration_squad = healthy_roaches.take(5)

        for roach in infiltration_squad:
            if roach.tag in self.tunneling_roaches:
                continue

            # 가장 가까운 적 기지
            closest_base = enemy_bases.closest_to(roach)

            # 기지 후방 위치 계산 (맵 중심 반대편)
            rear_position = closest_base.position.towards_with_random_angle(
                self.bot.game_info.map_center, -10
            )

            # 잠복 이동
            if not roach.is_burrowed:
                abilities = await self.bot.get_available_abilities(roach)
                if AbilityId.BURROWDOWN_ROACH in abilities:
                    self.bot.do(roach(AbilityId.BURROWDOWN_ROACH))
                    self.tunneling_roaches.add(roach.tag)
                    self.logger.info(f"[TUNNELING] Roach infiltrating to enemy rear")
                    self.tunneling_attacks += 1
            else:
                # 이미 잠복 상태면 이동
                self.bot.do(roach.move(rear_position))

    async def _flanking_maneuver(self, roaches):
        """포위 기동: 전투 중 측면 공격"""
        # 전투 중인 아군 유닛 확인
        fighting_units = self.bot.units.filter(
            lambda u: u.is_attacking and u.type_id != UnitTypeId.ROACH
        )

        if not fighting_units:
            return

        # 적 유닛 확인
        enemies = self.bot.enemy_units
        if not enemies:
            return

        # 건강한 바퀴
        healthy_roaches = roaches.filter(lambda r: r.health_percentage > 0.7 and not r.is_burrowed)
        if healthy_roaches.amount < 3:
            return

        # 3마리를 포위 부대로
        flanking_squad = healthy_roaches.take(3)

        for roach in flanking_squad:
            if roach.tag in self.tunneling_roaches:
                continue

            # 적 중심 위치
            enemy_center = enemies.center

            # 측면 위치 계산 (90도 회전)
            flank_position = enemy_center.towards_with_random_angle(
                self.bot.start_location, 8, max_difference=90
            )

            # 잠복 이동으로 측면 접근
            if not roach.is_burrowed:
                abilities = await self.bot.get_available_abilities(roach)
                if AbilityId.BURROWDOWN_ROACH in abilities:
                    self.bot.do(roach(AbilityId.BURROWDOWN_ROACH))
                    self.tunneling_roaches.add(roach.tag)
                    self.logger.info(f"[TUNNELING] Roach flanking maneuver")
                    self.flanking_maneuvers += 1
            else:
                # 이미 잠복 상태면 이동
                self.bot.do(roach.move(flank_position))

        # 도착 후 잠복 해제
        burrowed_roaches = self.bot.units(UnitTypeId.ROACHBURROWED)
        for roach in burrowed_roaches:
            if roach.tag in self.tunneling_roaches:
                # 적이 5거리 내에 있으면 잠복 해제
                nearby_enemies = enemies.closer_than(5, roach)
                if nearby_enemies:
                    abilities = await self.bot.get_available_abilities(roach)
                    if AbilityId.BURROWUP_ROACH in abilities:
                        self.bot.do(roach(AbilityId.BURROWUP_ROACH))
                        self.tunneling_roaches.remove(roach.tag)

    def get_statistics(self):
        """통계 반환"""
        return {
            "tunneling_researched": self.tunneling_researched,
            "infiltration_attacks": self.tunneling_attacks,
            "flanking_maneuvers": self.flanking_maneuvers
        }
