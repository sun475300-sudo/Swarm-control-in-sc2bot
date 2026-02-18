# -*- coding: utf-8 -*-
"""
Protoss Counter System - Advanced counter logic for Protoss opponents

프로토스 특화 대응 시스템:
1. 암흑 기사(DT) 긴급 대응 - 오버시어/포자 촉수
2. 오라클/불사조 견제 대응 - 일꾼 회피, 퀸 방어
3. 분열기 대응 - 유닛 분산 마이크로
4. 불멸자 카운터 - 저글링 포위 + 파멸충 담즙
5. 차원 분광기 저격 - 우선 타겟팅
6. 보호막 충전소 우선 타겟
7. 파수기/역장 대응 - 파멸충 담즙
"""

from typing import Dict, List, Optional, Set
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    UnitTypeId = None
    AbilityId = None
    Point2 = None


class ProtossCounterSystem:
    """프로토스 특화 대응 시스템"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("ProtossCounter")

        # 긴급 대응 상태 추적
        self.dt_detected = False
        self.dt_detection_time = 0
        self.oracle_detected = False
        self.phoenix_detected = False
        self.disruptor_detected = False
        self.warp_prism_detected = False
        self.immortal_count = 0

        # 긴급 건설 요청
        self.emergency_spore_requested = False
        self.emergency_overseer_requested = False

        # 일꾼 대피 상태
        self.workers_pulled = False
        self.worker_pull_time = 0

    async def on_step(self, iteration: int):
        """메인 업데이트 루프"""
        if not UnitTypeId:
            return

        game_time = getattr(self.bot, "time", 0)

        try:
            # 1. 프로토스 위협 유닛 감지
            await self._detect_protoss_threats()

            # 2. 암흑 기사 대응 (최우선)
            if self.dt_detected:
                await self._handle_dark_templar_threat(game_time, iteration)

            # 3. 오라클 견제 대응
            if self.oracle_detected:
                await self._handle_oracle_harassment(game_time, iteration)

            # 4. 불사조 대응
            if self.phoenix_detected:
                await self._handle_phoenix_threat(iteration)

            # 5. 분열기 대응
            if self.disruptor_detected:
                await self._handle_disruptor_threat(iteration)

            # 6. 차원 분광기 저격
            if self.warp_prism_detected:
                await self._handle_warp_prism(iteration)

            # 7. 불멸자 카운터
            if self.immortal_count >= 2:
                await self._handle_immortal_counter(iteration)

            # 8. 보호막 충전소/파수기 우선 타겟
            await self._priority_target_support_units(iteration)

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"Protoss counter error: {e}")

    async def _detect_protoss_threats(self):
        """프로토스 위협 유닛 감지"""
        if not hasattr(self.bot, "enemy_units"):
            return

        # 카운터 초기화
        self.dt_detected = False
        self.oracle_detected = False
        self.phoenix_detected = False
        self.disruptor_detected = False
        self.warp_prism_detected = False
        self.immortal_count = 0

        for enemy in self.bot.enemy_units:
            try:
                enemy_type = getattr(enemy.type_id, "name", "").upper()

                # 암흑 기사 감지 (은폐 유닛!)
                if enemy_type == "DARKTEMPLAR":
                    if not self.dt_detected:
                        self.dt_detected = True
                        self.dt_detection_time = self.bot.time
                        self.logger.warning(f"[{int(self.bot.time)}s] ★★★ DARK TEMPLAR DETECTED! ★★★")

                # 오라클 감지
                elif enemy_type == "ORACLE":
                    self.oracle_detected = True

                # 불사조 감지
                elif enemy_type == "PHOENIX":
                    self.phoenix_detected = True

                # 분열기 감지
                elif enemy_type == "DISRUPTOR":
                    if not self.disruptor_detected:
                        self.disruptor_detected = True
                        self.logger.warning(f"[{int(self.bot.time)}s] ★ DISRUPTOR DETECTED - SPLIT UNITS! ★")

                # 차원 분광기 감지
                elif enemy_type == "WARPPRISM" or enemy_type == "WARPPRISMPHASING":
                    if not self.warp_prism_detected:
                        self.warp_prism_detected = True
                        self.logger.warning(f"[{int(self.bot.time)}s] ★ WARP PRISM DETECTED! ★")

                # 불멸자 카운트
                elif enemy_type == "IMMORTAL":
                    self.immortal_count += 1

            except Exception:
                continue

    async def _handle_dark_templar_threat(self, game_time: float, iteration: int):
        """
        ★★★ 암흑 기사 긴급 대응 ★★★

        1. 긴급 오버시어 변태 요청
        2. 긴급 포자 촉수 건설
        3. 일꾼을 안전 지역으로 대피
        """
        # 1. 긴급 오버시어 변태 (레어가 있으면)
        if self._has_lair() and not self.emergency_overseer_requested:
            await self._emergency_overseer_morph()
            self.emergency_overseer_requested = True

        # 2. 긴급 포자 촉수 건설 (각 기지마다)
        if not self.emergency_spore_requested:
            await self._build_emergency_spore_crawlers()
            self.emergency_spore_requested = True

        # 3. 일꾼 대피 (DT가 미네랄 라인에 있을 때)
        dt_near_base = False
        for enemy in self.bot.enemy_units:
            if getattr(enemy.type_id, "name", "").upper() == "DARKTEMPLAR":
                # 본진/멀티 근처에 DT가 있는지 확인
                for th in self.bot.townhalls:
                    if enemy.distance_to(th) < 15:
                        dt_near_base = True
                        break

        if dt_near_base and not self.workers_pulled:
            await self._pull_workers_from_threat()
            self.workers_pulled = True
            self.worker_pull_time = game_time

        # 4. 10초 후 일꾼 복귀 (오버시어/포자가 있으면)
        if self.workers_pulled and game_time - self.worker_pull_time > 10:
            # 탐지기 확인
            overseers = self.bot.units(UnitTypeId.OVERSEER)
            spores = self.bot.structures(UnitTypeId.SPORECRAWLER).ready

            if overseers.amount > 0 or spores.amount > 0:
                self.workers_pulled = False  # 일꾼 복귀 허용

    async def _emergency_overseer_morph(self):
        """긴급 오버시어 변태 (최대 2기)"""
        if not self._has_lair():
            return

        overseers = self.bot.units(UnitTypeId.OVERSEER)
        if overseers.amount >= 2:
            return

        # 변태 가능한 오버로드 확인
        overlords = self.bot.units(UnitTypeId.OVERLORD).idle
        if not overlords.exists:
            overlords = self.bot.units(UnitTypeId.OVERLORD)

        if not overlords.exists:
            return

        # 자원 확인
        if not self.bot.can_afford(UnitTypeId.OVERSEER):
            return

        # 본진 근처 오버로드 우선
        target_overlord = overlords.closest_to(self.bot.start_location)

        try:
            self.bot.do(target_overlord(AbilityId.MORPH_OVERSEER))
            self.logger.info(f"[{int(self.bot.time)}s] ★ EMERGENCY OVERSEER MORPH vs DT! ★")
        except Exception as e:
            self.logger.error(f"Emergency overseer morph failed: {e}")

    async def _build_emergency_spore_crawlers(self):
        """긴급 포자 촉수 건설 (각 기지 미네랄 라인)"""
        # 스포닝 풀 필요
        pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not pools.exists:
            return

        # 각 기지마다 포자 촉수 1개씩
        for th in self.bot.townhalls.ready:
            # 기존 포자 촉수 확인
            nearby_spores = self.bot.structures(UnitTypeId.SPORECRAWLER).closer_than(10, th)
            if nearby_spores.amount > 0:
                continue

            # 건설 중인 포자 확인
            pending = self.bot.already_pending(UnitTypeId.SPORECRAWLER)
            if pending > 0:
                continue

            # 자원 확인
            if not self.bot.can_afford(UnitTypeId.SPORECRAWLER):
                return

            # 미네랄 필드 근처에 건설
            if hasattr(self.bot, "mineral_field"):
                minerals = self.bot.mineral_field.closer_than(10, th)
                if minerals.exists:
                    target_mineral = minerals.closest_to(th)
                    placement = target_mineral.position.towards(th.position, 3)

                    try:
                        await self.bot.build(UnitTypeId.SPORECRAWLER, near=placement)
                        self.logger.info(f"[{int(self.bot.time)}s] ★★★ EMERGENCY SPORE vs DT! ★★★")
                        return  # 한 번에 1개씩만
                    except Exception:
                        pass

    async def _pull_workers_from_threat(self):
        """일꾼을 위협 지역에서 대피"""
        # DT가 있는 위치 찾기
        dt_positions = []
        for enemy in self.bot.enemy_units:
            if getattr(enemy.type_id, "name", "").upper() == "DARKTEMPLAR":
                dt_positions.append(enemy.position)

        if not dt_positions:
            return

        # 각 DT 근처의 일꾼을 대피
        drones = self.bot.units(UnitTypeId.DRONE)
        for drone in drones:
            # DT와 가까우면 대피
            for dt_pos in dt_positions:
                if drone.distance_to(dt_pos) < 8:
                    # 가장 가까운 본진으로 대피
                    if self.bot.townhalls.exists:
                        safe_base = self.bot.townhalls.closest_to(drone)
                        self.bot.do(drone.move(safe_base.position))
                    break

        self.logger.warning(f"[{int(self.bot.time)}s] ★ WORKERS PULLED FROM DT THREAT! ★")

    async def _handle_oracle_harassment(self, game_time: float, iteration: int):
        """
        오라클 견제 대응

        1. 일꾼 대피 (오라클이 미네랄 라인에 있을 때)
        2. 퀸 대응
        3. 포자 촉수 건설
        """
        # 오라클 위치 확인
        oracles = [e for e in self.bot.enemy_units if getattr(e.type_id, "name", "").upper() == "ORACLE"]
        if not oracles:
            self.oracle_detected = False
            return

        # 본진 근처 오라클 확인
        for oracle in oracles:
            for th in self.bot.townhalls:
                if oracle.distance_to(th) < 15:
                    # 일꾼 대피
                    await self._pull_workers_from_oracle(oracle, th)

                    # 퀸 대응
                    await self._queens_attack_oracle(oracle)
                    break

    async def _pull_workers_from_oracle(self, oracle, townhall):
        """오라클로부터 일꾼 대피"""
        drones = self.bot.units(UnitTypeId.DRONE).closer_than(8, oracle)
        for drone in drones:
            # 오라클 반대 방향으로 도망
            flee_direction = drone.position.towards(oracle.position, -5)
            self.bot.do(drone.move(flee_direction))

    async def _queens_attack_oracle(self, oracle):
        """퀸으로 오라클 공격"""
        queens = self.bot.units(UnitTypeId.QUEEN).idle
        if not queens.exists:
            queens = self.bot.units(UnitTypeId.QUEEN)

        for queen in queens:
            if queen.distance_to(oracle) < 15:
                self.bot.do(queen.attack(oracle))

    async def _handle_phoenix_threat(self, iteration: int):
        """
        불사조 대응

        1. 유닛 분산 (들어올리기 방지)
        2. 히드라/퀸 대공
        """
        phoenixes = [e for e in self.bot.enemy_units if getattr(e.type_id, "name", "").upper() == "PHOENIX"]
        if not phoenixes or len(phoenixes) == 0:
            self.phoenix_detected = False
            return

        # 불사조가 2기 이상이면 유닛 분산
        if len(phoenixes) >= 2 and iteration % 20 == 0:
            await self._spread_units_vs_phoenix(phoenixes)

    async def _spread_units_vs_phoenix(self, phoenixes: List):
        """불사조 상대 유닛 분산"""
        # 퀸은 뭉쳐있기 (들어올리기 대상이지만 대공 필요)
        queens = self.bot.units(UnitTypeId.QUEEN)
        if queens.exists:
            for queen in queens:
                closest_phoenix = min(phoenixes, key=lambda p: p.distance_to(queen))
                if queen.distance_to(closest_phoenix) < 15:
                    self.bot.do(queen.attack(closest_phoenix))

        # 히드라 있으면 공격
        hydras = self.bot.units(UnitTypeId.HYDRALISK)
        if hydras.exists:
            for hydra in hydras:
                closest_phoenix = min(phoenixes, key=lambda p: p.distance_to(hydra))
                if hydra.distance_to(closest_phoenix) < 12:
                    self.bot.do(hydra.attack(closest_phoenix))

    async def _handle_disruptor_threat(self, iteration: int):
        """
        분열기 대응 - 유닛 분산

        분열구가 날아오면 유닛을 분산시켜 피해 최소화
        """
        # 분열기 위치 확인
        disruptors = [e for e in self.bot.enemy_units if getattr(e.type_id, "name", "").upper() == "DISRUPTOR"]
        if not disruptors:
            self.disruptor_detected = False
            return

        # 분열기 근처의 아군 유닛 분산
        if iteration % 10 == 0:  # 자주 체크
            for disruptor in disruptors:
                nearby_units = self.bot.units.closer_than(10, disruptor)
                if nearby_units.amount > 5:
                    # 유닛들을 방사형으로 분산
                    await self._spread_units_radial(nearby_units, disruptor.position)

    async def _spread_units_radial(self, units, center_pos):
        """유닛을 중심점으로부터 방사형으로 분산"""
        import math

        angle_step = (2 * math.pi) / max(len(units), 1)
        spread_distance = 3  # 3칸 거리로 분산

        for idx, unit in enumerate(units):
            angle = idx * angle_step
            offset_x = spread_distance * math.cos(angle)
            offset_y = spread_distance * math.sin(angle)

            target_pos = Point2((center_pos.x + offset_x, center_pos.y + offset_y))
            self.bot.do(unit.move(target_pos))

    async def _handle_warp_prism(self, iteration: int):
        """
        차원 분광기 우선 저격

        차원 분광기를 발견하면 즉시 병력을 보내 파괴
        """
        warp_prisms = [
            e for e in self.bot.enemy_units
            if getattr(e.type_id, "name", "").upper() in ["WARPPRISM", "WARPPRISMPHASING"]
        ]

        if not warp_prisms:
            self.warp_prism_detected = False
            return

        # 가장 가까운 병력을 차원 분광기로 보냄
        for prism in warp_prisms:
            # 본진 근처면 즉시 대응
            if self.bot.townhalls.exists:
                closest_base = self.bot.townhalls.closest_to(prism)
                if prism.distance_to(closest_base) < 20:
                    # 근처 모든 병력을 차원 분광기로
                    nearby_army = self.bot.units.closer_than(15, prism).exclude_type(
                        [UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.LARVA]
                    )

                    for unit in nearby_army:
                        self.bot.do(unit.attack(prism))

                    self.logger.warning(f"[{int(self.bot.time)}s] ★ ATTACKING WARP PRISM! ★")

    async def _handle_immortal_counter(self, iteration: int):
        """
        불멸자 카운터 (저글링 포위 + 파멸충 담즙)

        ★ CRITICAL: 바퀴는 불멸자에게 약함! 저글링 + 파멸충 사용 ★
        """
        # ★ DynamicCounter가 이미 IMMORTAL 대응 중이면 생산 비율 수정 스킵 ★
        blackboard = getattr(self.bot, "blackboard", None)
        if blackboard and blackboard.get("dynamic_counter_active", False):
            dynamic_counter = getattr(self.bot, "dynamic_counter", None)
            if dynamic_counter and "IMMORTAL" in getattr(dynamic_counter, "active_counters", {}):
                return  # DynamicCounter가 Blackboard를 통해 이미 대응 중

        # 전략 매니저에 불멸자 카운터 요청
        if hasattr(self.bot, "strategy_manager"):
            strategy = self.bot.strategy_manager
            if hasattr(strategy, "_adjust_unit_ratio"):
                # 저글링 비율 증가 (포위용)
                strategy._adjust_unit_ratio("zergling", 0.4)
                # 파멸충 비율 증가 (담즙 공격)
                strategy._adjust_unit_ratio("ravager", 0.35)
                # ★ 바퀴 비율 감소 (불멸자에게 약함)
                strategy._adjust_unit_ratio("roach", 0.05)

    async def _priority_target_support_units(self, iteration: int):
        """
        보호막 충전소, 파수기 우선 타겟

        전투 시 지원 유닛을 먼저 제거
        """
        if not hasattr(self.bot, "enemy_units"):
            return

        # 보호막 충전소, 파수기 찾기
        priority_targets = []
        for enemy in self.bot.enemy_structures:
            enemy_type = getattr(enemy.type_id, "name", "").upper()
            if enemy_type == "SHIELDBATTERY":
                priority_targets.append(enemy)

        for enemy in self.bot.enemy_units:
            enemy_type = getattr(enemy.type_id, "name", "").upper()
            if enemy_type == "SENTRY":
                priority_targets.append(enemy)

        # 우선 타겟이 있으면 근처 병력을 집중
        if priority_targets and iteration % 20 == 0:
            for target in priority_targets:
                nearby_army = self.bot.units.closer_than(15, target).exclude_type(
                    [UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.LARVA, UnitTypeId.QUEEN]
                )

                for unit in nearby_army:
                    self.bot.do(unit.attack(target))

    def _has_lair(self) -> bool:
        """레어/하이브 확인"""
        if not hasattr(self.bot, "structures"):
            return False

        lairs = self.bot.structures.filter(
            lambda s: getattr(s.type_id, "name", "").upper() in ["LAIR", "HIVE"]
        )
        return lairs.ready.exists

    def get_status_report(self) -> Dict:
        """상태 보고서 (디버깅용)"""
        return {
            "dt_detected": self.dt_detected,
            "oracle_detected": self.oracle_detected,
            "phoenix_detected": self.phoenix_detected,
            "disruptor_detected": self.disruptor_detected,
            "warp_prism_detected": self.warp_prism_detected,
            "immortal_count": self.immortal_count,
            "emergency_spore_requested": self.emergency_spore_requested,
            "emergency_overseer_requested": self.emergency_overseer_requested,
        }
