# -*- coding: utf-8 -*-
"""
Multi-Base Defense System - Automatic defense for multiple expansions

다중 기지 방어 시스템:
1. 각 확장 기지마다 스파인 크롤러 자동 배치
2. 위협 레벨에 따른 방어 구조물 수 조정
3. 퀸 배치 및 방어 유닛 할당
4. 공격 받는 기지 우선 방어
"""

from typing import Dict, List, Optional
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    UnitTypeId = None
    Point2 = None


class MultiBaseDefense:
    """다중 기지 방어 관리자"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("MultiBaseDefense")

        # 기지별 방어 상태 추적
        self.base_defense_status: Dict[int, Dict] = {}
        self.last_defense_check = 0
        self.defense_check_interval = 44  # ~2초마다 체크

        # 방어 건물 목표 (기지별)
        self.spine_per_base = 2   # 기지당 스파인 크롤러
        self.spore_per_base = 1   # 기지당 포자 촉수

        # 퀸 할당 (각 기지마다)
        self.queens_per_base = 2  # 기지당 퀸 2마리

    async def on_step(self, iteration: int):
        """메인 업데이트 루프"""
        if not UnitTypeId:
            return

        if iteration - self.last_defense_check < self.defense_check_interval:
            return

        self.last_defense_check = iteration
        game_time = getattr(self.bot, "time", 0)

        try:
            # 1. 각 기지의 방어 상태 업데이트
            await self._update_base_defense_status()

            # 2. 방어 구조물 건설 (우선순위: 공격 받는 기지 > 멀티)
            await self._build_base_defenses(game_time, iteration)

            # 3. 퀸 재배치 (필요한 기지에 퀸 할당)
            if iteration % 88 == 0:  # 4초마다
                await self._redistribute_queens()

            # 4. 긴급 방어 (기지가 공격 받고 있을 때)
            await self._emergency_base_defense(iteration)

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"Multi-base defense error: {e}")

    async def _update_base_defense_status(self):
        """각 기지의 방어 상태 업데이트"""
        if not hasattr(self.bot, "townhalls"):
            return

        for th in self.bot.townhalls.ready:
            base_tag = th.tag

            # 기지 주변 방어 구조물 카운트
            nearby_spines = self.bot.structures(UnitTypeId.SPINECRAWLER).closer_than(12, th)
            nearby_spores = self.bot.structures(UnitTypeId.SPORECRAWLER).closer_than(12, th)
            nearby_queens = self.bot.units(UnitTypeId.QUEEN).closer_than(15, th)

            # 위협 레벨 계산
            threat_level = self._calculate_threat_level(th)

            self.base_defense_status[base_tag] = {
                "position": th.position,
                "spine_count": nearby_spines.amount,
                "spore_count": nearby_spores.amount,
                "queen_count": nearby_queens.amount,
                "threat_level": threat_level,
                "under_attack": threat_level >= 2,
            }

    def _calculate_threat_level(self, townhall) -> int:
        """
        기지 위협 레벨 계산

        Returns:
            0: 안전
            1: 경미한 위협 (1-3 적 유닛)
            2: 중간 위협 (4-8 적 유닛)
            3: 심각한 위협 (9+ 적 유닛)
        """
        if not hasattr(self.bot, "enemy_units"):
            return 0

        # 기지 근처 적 유닛 카운트
        nearby_enemies = self.bot.enemy_units.closer_than(15, townhall)
        enemy_count = nearby_enemies.amount

        if enemy_count == 0:
            return 0
        elif enemy_count <= 3:
            return 1
        elif enemy_count <= 8:
            return 2
        else:
            return 3

    async def _build_base_defenses(self, game_time: float, iteration: int):
        """
        각 기지에 방어 구조물 건설

        우선순위:
        1. 공격 받는 기지 (threat_level >= 2)
        2. 멀티 기지 (본진 아닌 기지)
        3. 본진
        """
        # 스포닝 풀 확인
        pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not pools.exists:
            return

        # 기지 우선순위 정렬 (위협 레벨 높은 순)
        sorted_bases = sorted(
            self.base_defense_status.items(),
            key=lambda x: (-x[1]["threat_level"], x[1]["spine_count"])
        )

        for base_tag, status in sorted_bases:
            # 스파인 크롤러 건설
            if status["spine_count"] < self.spine_per_base:
                await self._build_spine_at_base(status["position"], iteration)
                return  # 한 번에 하나씩만

            # 포자 촉수 건설 (3분 이후, 대공 방어)
            if game_time >= 180 and status["spore_count"] < self.spore_per_base:
                await self._build_spore_at_base(status["position"], iteration)
                return

    async def _build_spine_at_base(self, base_position, iteration: int):
        """기지에 스파인 크롤러 건설"""
        # 자원 확인
        if not self.bot.can_afford(UnitTypeId.SPINECRAWLER):
            return

        # 이미 건설 중인지 확인
        pending = self.bot.already_pending(UnitTypeId.SPINECRAWLER)
        if pending >= 2:  # 최대 2개까지 동시 건설
            return

        # 건설 위치: 기지 앞쪽 (맵 중앙 방향)
        if hasattr(self.bot, "game_info"):
            map_center = self.bot.game_info.map_center
            placement = base_position.towards(map_center, 7)

            try:
                await self.bot.build(UnitTypeId.SPINECRAWLER, near=placement)
                if iteration % 100 == 0:
                    self.logger.info(f"[{int(self.bot.time)}s] Building Spine Crawler at expansion")
            except Exception:
                pass

    async def _build_spore_at_base(self, base_position, iteration: int):
        """기지에 포자 촉수 건설"""
        # 자원 확인
        if not self.bot.can_afford(UnitTypeId.SPORECRAWLER):
            return

        # 이미 건설 중인지 확인
        pending = self.bot.already_pending(UnitTypeId.SPORECRAWLER)
        if pending >= 2:
            return

        # 건설 위치: 미네랄 라인 뒤쪽
        placement = base_position.towards(self.bot.start_location, 5)

        try:
            await self.bot.build(UnitTypeId.SPORECRAWLER, near=placement)
            if iteration % 100 == 0:
                self.logger.info(f"[{int(self.bot.time)}s] Building Spore Crawler at expansion")
        except Exception:
            pass

    async def _redistribute_queens(self):
        """퀸을 각 기지에 재배치"""
        if not hasattr(self.bot, "townhalls"):
            return

        queens = self.bot.units(UnitTypeId.QUEEN).idle
        if not queens.exists:
            return

        # 퀸이 부족한 기지 찾기
        for base_tag, status in self.base_defense_status.items():
            if status["queen_count"] < self.queens_per_base:
                # 가까운 퀸을 해당 기지로 보냄
                if queens.exists:
                    closest_queen = queens.closest_to(status["position"])
                    self.bot.do(closest_queen.move(status["position"]))
                    queens = queens - {closest_queen}

                    if not queens.exists:
                        break

    async def _emergency_base_defense(self, iteration: int):
        """
        긴급 기지 방어

        기지가 공격 받고 있을 때:
        1. 근처 모든 유닛을 방어에 투입
        2. 일꾼도 임시 방어에 참여 (심각한 위협일 때)
        """
        for base_tag, status in self.base_defense_status.items():
            if not status["under_attack"]:
                continue

            base_pos = status["position"]
            threat_level = status["threat_level"]

            # 근처 적 유닛 확인
            nearby_enemies = self.bot.enemy_units.closer_than(15, base_pos)
            if not nearby_enemies.exists:
                continue

            # 1. 근처 모든 군대 유닛을 방어에 투입
            nearby_army = self.bot.units.closer_than(20, base_pos).exclude_type(
                [UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.LARVA]
            )

            for unit in nearby_army:
                closest_enemy = nearby_enemies.closest_to(unit)
                self.bot.do(unit.attack(closest_enemy))

            # 2. 심각한 위협이면 일꾼도 투입 (threat_level >= 3)
            if threat_level >= 3:
                nearby_drones = self.bot.units(UnitTypeId.DRONE).closer_than(8, base_pos)
                drone_count = min(nearby_drones.amount, 5)  # 최대 5마리만

                for drone in nearby_drones[:drone_count]:
                    # ★ CRITICAL: 드론이 기지에서 12거리 이상 벗어나지 않도록 체크 ★
                    if drone.distance_to(base_pos) > 12:
                        # 너무 멀리 나갔으면 복귀
                        nearby_minerals = self.bot.mineral_field.closer_than(10, base_pos)
                        if nearby_minerals:
                            self.bot.do(drone.gather(nearby_minerals.closest_to(base_pos)))
                        continue

                    closest_enemy = nearby_enemies.closest_to(drone)
                    # 적이 기지 근처(12거리 이내)에 있을 때만 공격
                    if closest_enemy.distance_to(base_pos) < 12:
                        self.bot.do(drone.attack(closest_enemy))

            if iteration % 100 == 0:
                self.logger.warning(
                    f"[{int(self.bot.time)}s] ★ EMERGENCY BASE DEFENSE! Threat: {threat_level} ★"
                )

    def get_total_bases(self) -> int:
        """전체 기지 수 반환"""
        return len(self.base_defense_status)

    def get_defended_bases(self) -> int:
        """방어 구조물이 있는 기지 수 반환"""
        return sum(
            1 for status in self.base_defense_status.values()
            if status["spine_count"] > 0 or status["spore_count"] > 0
        )

    def get_bases_under_attack(self) -> int:
        """공격 받는 기지 수 반환"""
        return sum(1 for status in self.base_defense_status.values() if status["under_attack"])
