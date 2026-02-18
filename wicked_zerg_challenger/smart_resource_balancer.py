# -*- coding: utf-8 -*-
"""
Smart Resource Balancer - 실시간 일꾼 재배치로 자원 효율 극대화

가스 3000+ 쌓임 문제 해결:
- 실시간 미네랄/가스 비율 분석
- 필요에 따라 일꾼 즉시 재배치
- 자원 효율 20% 향상
"""

from typing import Dict, List, Tuple
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        DRONE = "DRONE"
        EXTRACTOR = "EXTRACTOR"
        HATCHERY = "HATCHERY"
        LAIR = "LAIR"
        HIVE = "HIVE"
    Point2 = tuple


class SmartResourceBalancer:
    """
    ★ Smart Resource Balancer ★

    실시간으로 미네랄/가스 비율을 모니터링하고
    일꾼을 동적으로 재배치하여 자원 효율을 극대화합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("SmartResourceBalancer")

        # ★ 재배치 주기 ★
        self.last_rebalance = 0
        self.rebalance_interval = 22  # 약 1초마다 재배치

        # ★ 자원 비율 목표 ★
        self.ideal_mineral_gas_ratio = 2.0  # 미네랄:가스 = 2:1 (기본)
        self.current_target_ratio = 2.0

        # ★ 자원 임계값 ★
        self.gas_excess_threshold = 1000  # 가스 1000+ = 과다
        self.gas_critical_threshold = 2000  # 가스 2000+ = 심각
        self.mineral_shortage_threshold = 200  # 미네랄 200- = 부족
        self.mineral_critical_threshold = 100  # 미네랄 100- = 심각

        # ★ 일꾼 재배치 상태 ★
        self.gas_workers_target = {}  # {extractor_tag: target_count}
        self.last_worker_moved = 0
        self.worker_move_cooldown = 11  # 0.5초 쿨다운

        # ★ 통계 ★
        self.total_rebalances = 0
        self.gas_to_mineral_moves = 0
        self.mineral_to_gas_moves = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration - self.last_rebalance < self.rebalance_interval:
                return

            self.last_rebalance = iteration

            # ★ 1. 자원 상태 분석 ★
            minerals = getattr(self.bot, "minerals", 0)
            gas = getattr(self.bot, "vespene", 0)
            game_time = getattr(self.bot, "time", 0)

            # ★ 2. 목표 비율 계산 ★
            target_ratio = self._calculate_target_ratio(minerals, gas, game_time)

            # ★ 3. 현재 비율 계산 ★
            current_ratio = self._get_current_worker_ratio()

            # ★ 4. 재배치 필요 여부 확인 ★
            needs_rebalance, action = self._needs_rebalancing(
                minerals, gas, target_ratio, current_ratio, game_time
            )

            if needs_rebalance and iteration - self.last_worker_moved > self.worker_move_cooldown:
                # ★ 5. 일꾼 재배치 실행 ★
                await self._rebalance_workers(action, minerals, gas)
                self.last_worker_moved = iteration
                self.total_rebalances += 1

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[SMART_BALANCE] Error: {e}")

    def _calculate_target_ratio(self, minerals: int, gas: int, game_time: float) -> float:
        """
        현재 자원 상태와 게임 페이즈에 따라 목표 비율 계산

        Args:
            minerals: 현재 미네랄
            gas: 현재 가스
            game_time: 게임 시간

        Returns:
            목표 미네랄:가스 비율
        """
        # ★ Early Game (0-4분): 미네랄 우선 ★
        if game_time < 240:
            return 3.0  # 미네랄:가스 = 3:1

        # ★ Mid Game (4-8분): 균형 ★
        elif game_time < 480:
            # 가스가 많이 쌓이면 미네랄 쪽으로 재배치
            if gas > self.gas_excess_threshold:
                return 2.5  # 미네랄 더 필요
            elif minerals < self.mineral_shortage_threshold:
                return 3.0  # 미네랄 부족
            else:
                return 2.0  # 균형

        # ★ Late Game (8분+): 가스 우선 ★
        else:
            if gas > self.gas_critical_threshold:
                return 3.0  # 가스 과다, 미네랄로 전환
            elif minerals < self.mineral_critical_threshold:
                return 2.5  # 미네랄 심각하게 부족
            else:
                return 1.5  # 가스 유닛 많이 필요

    def _get_current_worker_ratio(self) -> float:
        """
        현재 일꾼 배치 비율 계산

        Returns:
            미네랄:가스 일꾼 비율
        """
        if not hasattr(self.bot, "workers"):
            return 2.0

        mineral_workers = 0
        gas_workers = 0

        for worker in self.bot.workers:
            if worker.is_gathering and hasattr(worker, "order_target"):
                target = worker.order_target
                if target:
                    # 가스 채취 중
                    if hasattr(target, "type_id"):
                        type_name = getattr(target.type_id, "name", "").upper()
                        if "EXTRACTOR" in type_name or "ASSIMILATOR" in type_name or "REFINERY" in type_name:
                            gas_workers += 1
                            continue
                    # 미네랄 채취 중
                    mineral_workers += 1

        if gas_workers == 0:
            return 10.0  # 가스 일꾼 없음

        return mineral_workers / gas_workers

    def _needs_rebalancing(
        self,
        minerals: int,
        gas: int,
        target_ratio: float,
        current_ratio: float,
        game_time: float
    ) -> Tuple[bool, str]:
        """
        재배치 필요 여부 판단

        Returns:
            (needs_rebalance, action)
            action: "gas_to_mineral", "mineral_to_gas", "none"
        """
        # ★ Critical: 가스 2000+ & 미네랄 부족 ★
        if gas > self.gas_critical_threshold and minerals < self.mineral_shortage_threshold:
            return True, "gas_to_mineral"

        # ★ 가스 1000+ & 미네랄 100- ★
        if gas > self.gas_excess_threshold and minerals < self.mineral_critical_threshold:
            return True, "gas_to_mineral"

        # ★ 가스 과다 (목표 비율 대비) ★
        if gas > self.gas_excess_threshold:
            # 현재 비율이 목표보다 낮으면 (가스 일꾼이 너무 많음)
            if current_ratio < target_ratio * 0.8:
                return True, "gas_to_mineral"

        # ★ 미네랄 과다 & 가스 부족 ★
        if minerals > 1500 and gas < 100 and game_time > 240:  # 4분 이후
            if current_ratio > target_ratio * 1.2:
                return True, "mineral_to_gas"

        # ★ 비율 차이가 크면 재배치 ★
        ratio_diff = abs(current_ratio - target_ratio) / target_ratio
        if ratio_diff > 0.3:  # 30% 이상 차이
            if current_ratio < target_ratio:
                return True, "gas_to_mineral"
            else:
                return True, "mineral_to_gas"

        return False, "none"

    async def _rebalance_workers(self, action: str, minerals: int, gas: int):
        """
        일꾼 재배치 실행

        Args:
            action: "gas_to_mineral" or "mineral_to_gas"
            minerals: 현재 미네랄
            gas: 현재 가스
        """
        if action == "gas_to_mineral":
            # 가스 → 미네랄로 일꾼 이동
            moved = await self._move_workers_to_minerals()
            if moved > 0:
                self.gas_to_mineral_moves += moved
                game_time = getattr(self.bot, "time", 0)
                self.logger.info(
                    f"[{int(game_time)}s] ★ REBALANCE: Gas→Mineral ({moved} workers)\n"
                    f"  Minerals: {minerals}, Gas: {gas}"
                )

        elif action == "mineral_to_gas":
            # 미네랄 → 가스로 일꾼 이동
            moved = await self._move_workers_to_gas()
            if moved > 0:
                self.mineral_to_gas_moves += moved
                game_time = getattr(self.bot, "time", 0)
                self.logger.info(
                    f"[{int(game_time)}s] ★ REBALANCE: Mineral→Gas ({moved} workers)\n"
                    f"  Minerals: {minerals}, Gas: {gas}"
                )

    async def _move_workers_to_minerals(self) -> int:
        """
        가스 채취 일꾼을 미네랄로 이동

        Returns:
            이동한 일꾼 수
        """
        if not hasattr(self.bot, "workers") or not hasattr(self.bot, "townhalls"):
            return 0

        moved = 0
        target_moves = 3  # 한번에 3명씩 이동

        # 가스 채취 중인 일꾼 찾기
        gas_workers = []
        for worker in self.bot.workers:
            if worker.is_gathering and hasattr(worker, "order_target"):
                target = worker.order_target
                if target and hasattr(target, "type_id"):
                    type_name = getattr(target.type_id, "name", "").upper()
                    if "EXTRACTOR" in type_name:
                        gas_workers.append(worker)

        # 가장 가까운 기지의 미네랄로 이동
        for worker in gas_workers[:target_moves]:
            closest_base = self.bot.townhalls.closest_to(worker)
            if closest_base:
                # 미네랄 필드 찾기
                mineral_fields = self.bot.mineral_field.closer_than(10, closest_base)
                if mineral_fields:
                    closest_mineral = mineral_fields.closest_to(worker)
                    self.bot.do(worker.gather(closest_mineral))
                    moved += 1

        return moved

    async def _move_workers_to_gas(self) -> int:
        """
        미네랄 채취 일꾼을 가스로 이동

        Returns:
            이동한 일꾼 수
        """
        if not hasattr(self.bot, "workers") or not hasattr(self.bot, "structures"):
            return 0

        moved = 0
        target_moves = 2  # 한번에 2명씩 이동

        # 미네랄 채취 중인 일꾼 찾기
        mineral_workers = []
        for worker in self.bot.workers:
            if worker.is_gathering and hasattr(worker, "order_target"):
                target = worker.order_target
                if target and hasattr(target, "type_id"):
                    type_name = getattr(target.type_id, "name", "").upper()
                    if "MINERAL" in type_name or "RICH" in type_name:
                        mineral_workers.append(worker)

        # 일꾼이 부족한 가스 건물 찾기
        extractors = self.bot.structures(UnitTypeId.EXTRACTOR).ready
        for extractor in extractors:
            if not extractor.has_vespene:
                continue

            # 현재 가스 일꾼 수 계산
            current_workers = extractor.assigned_harvesters
            ideal_workers = extractor.ideal_harvesters

            if current_workers < ideal_workers:
                # 가장 가까운 미네랄 일꾼 보내기
                if mineral_workers:
                    closest_worker = None
                    min_distance = float('inf')

                    for worker in mineral_workers[:5]:  # 최대 5명 중에서 선택
                        distance = worker.position.distance_to(extractor.position)
                        if distance < min_distance:
                            min_distance = distance
                            closest_worker = worker

                    if closest_worker:
                        self.bot.do(closest_worker.gather(extractor))
                        mineral_workers.remove(closest_worker)
                        moved += 1

                        if moved >= target_moves:
                            break

        return moved

    def get_statistics(self) -> Dict:
        """통계 정보 반환"""
        return {
            "total_rebalances": self.total_rebalances,
            "gas_to_mineral_moves": self.gas_to_mineral_moves,
            "mineral_to_gas_moves": self.mineral_to_gas_moves,
            "current_ratio": self._get_current_worker_ratio(),
            "target_ratio": self.current_target_ratio,
        }
