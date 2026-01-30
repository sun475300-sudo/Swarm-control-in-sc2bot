# -*- coding: utf-8 -*-
"""
Advanced Worker Optimizer - 고급 일꾼 최적화 시스템

자원 수집 효율 극대화:
1. 미네랄 패치별 최적 일꾼 배치
2. 가스 타이밍 최적화
3. 장거리 채광 최소화
4. 미네랄 고갈 감지 및 재배치
5. 동적 자원 밸런싱
"""

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass

try:
    from sc2.unit import Unit
    from sc2.units import Units
    from sc2.position import Point2
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    Unit = object
    Units = object
    Point2 = tuple
    UnitTypeId = None

from utils.logger import get_logger


@dataclass
class MineralPatchState:
    """미네랄 패치 상태"""
    tag: int
    position: Point2
    remaining_minerals: int
    assigned_workers: int
    optimal_workers: int  # 최적 일꾼 수 (보통 2)
    distance_from_base: float
    is_depleting: bool  # 고갈 중인지


@dataclass
class BaseEconomy:
    """기지 경제 상태"""
    base_tag: int
    position: Point2
    mineral_patches: List[MineralPatchState]
    gas_geysers: List[int]  # 가스 건물 태그
    assigned_mineral_workers: int
    assigned_gas_workers: int
    optimal_mineral_workers: int
    optimal_gas_workers: int
    saturation_ratio: float  # 포화도 (0.0 ~ 1.0)


class AdvancedWorkerOptimizer:
    """
    고급 일꾼 최적화 시스템

    목표:
    - 자원 수집 효율 최대화
    - 일꾼 이동 거리 최소화
    - 자원 밸런스 유지 (미네랄:가스 = 2:1)

    학습 목표:
    - 최적 일꾼 분배 학습
    - 가스 타이밍 최적화
    - 기지별 우선순위 학습
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("AdvancedWorkerOptimizer")

        # 기지별 경제 상태
        self.base_economies: Dict[int, BaseEconomy] = {}  # base_tag -> BaseEconomy

        # 일꾼 할당 추적
        self.worker_assignments: Dict[int, str] = {}  # worker_tag -> "mineral" or "gas"
        self.worker_base_assignment: Dict[int, int] = {}  # worker_tag -> base_tag

        # 최적화 설정
        self.optimal_workers_per_mineral = 2  # 미네랄 패치당 최적 일꾼
        self.optimal_workers_per_gas = 3  # 가스 건물당 최적 일꾼
        self.target_mineral_gas_ratio = 2.0  # 미네랄:가스 비율 (2:1)

        # 학습 데이터
        self.income_history = []  # [(time, mineral_income, gas_income, worker_count)]
        self.efficiency_metrics = []  # [(time, efficiency_score)]

        # 성능 메트릭
        self.total_worker_moves = 0
        self.unnecessary_moves = 0

        # 마지막 최적화 시간
        self.last_optimization = 0
        self.optimization_interval = 22  # ~1초마다

        # 고갈 감지
        self.depleting_patches: Set[int] = set()
        self.last_depletion_check = 0

    async def on_step(self, iteration: int) -> None:
        """매 프레임 호출"""
        game_time = getattr(self.bot, "time", 0)

        # 기지 경제 상태 업데이트 (1초마다)
        if iteration % 22 == 0:
            self._update_base_economies()

        # 일꾼 최적화 (1초마다)
        if iteration - self.last_optimization >= self.optimization_interval:
            await self._optimize_worker_distribution()
            self.last_optimization = iteration

        # 미네랄 고갈 감지 (3초마다)
        if iteration % 66 == 0:
            self._detect_depleting_minerals()

        # 대기 일꾼 즉시 할당 (매 프레임)
        await self._assign_idle_workers()

        # 장거리 채광 감지 및 수정 (2초마다)
        if iteration % 44 == 0:
            await self._fix_long_distance_mining()

        # 가스 밸런싱 (1.5초마다)
        if iteration % 33 == 0:
            await self._balance_gas_workers()

        # 학습 데이터 수집 (5초마다)
        if iteration % 110 == 0:
            self._collect_learning_data(game_time)

    def _update_base_economies(self) -> None:
        """기지 경제 상태 업데이트"""
        if not hasattr(self.bot, "townhalls"):
            return

        for base in self.bot.townhalls.ready:
            # 미네랄 패치 분석
            mineral_patches = []
            nearby_minerals = self.bot.mineral_field.closer_than(10, base)

            for mineral in nearby_minerals:
                assigned_workers = self._count_workers_on_mineral(mineral.tag)
                distance = base.distance_to(mineral)

                # 미네랄이 적으면 고갈 중으로 표시
                is_depleting = mineral.mineral_contents < 200

                mineral_patches.append(MineralPatchState(
                    tag=mineral.tag,
                    position=mineral.position,
                    remaining_minerals=mineral.mineral_contents,
                    assigned_workers=assigned_workers,
                    optimal_workers=self.optimal_workers_per_mineral,
                    distance_from_base=distance,
                    is_depleting=is_depleting
                ))

            # 가스 건물 분석
            gas_geysers = []
            if hasattr(self.bot, "gas_buildings"):
                nearby_gas = self.bot.gas_buildings.ready.closer_than(10, base)
                gas_geysers = [g.tag for g in nearby_gas]

            # 일꾼 수 계산
            assigned_mineral_workers = sum(p.assigned_workers for p in mineral_patches)
            assigned_gas_workers = sum(
                self._count_workers_on_gas(g) for g in gas_geysers
            )

            # 최적 일꾼 수 계산
            optimal_mineral_workers = len(mineral_patches) * self.optimal_workers_per_mineral
            optimal_gas_workers = len(gas_geysers) * self.optimal_workers_per_gas

            # 포화도 계산
            total_assigned = assigned_mineral_workers + assigned_gas_workers
            total_optimal = optimal_mineral_workers + optimal_gas_workers
            saturation_ratio = total_assigned / total_optimal if total_optimal > 0 else 0.0

            # BaseEconomy 업데이트
            self.base_economies[base.tag] = BaseEconomy(
                base_tag=base.tag,
                position=base.position,
                mineral_patches=mineral_patches,
                gas_geysers=gas_geysers,
                assigned_mineral_workers=assigned_mineral_workers,
                assigned_gas_workers=assigned_gas_workers,
                optimal_mineral_workers=optimal_mineral_workers,
                optimal_gas_workers=optimal_gas_workers,
                saturation_ratio=saturation_ratio
            )

    async def _optimize_worker_distribution(self) -> None:
        """일꾼 분배 최적화"""
        if not self.base_economies:
            return

        # 1. 과포화 기지 감지 및 일꾼 이전
        await self._transfer_excess_workers()

        # 2. 과소 기지 감지 및 일꾼 요청
        await self._request_additional_workers()

        # 3. 미네랄 패치별 일꾼 밸런싱
        await self._balance_mineral_patches()

    async def _transfer_excess_workers(self) -> None:
        """과포화 기지에서 일꾼 이전"""
        oversaturated_bases = [
            base for base in self.base_economies.values()
            if base.saturation_ratio > 1.2  # 120% 초과
        ]

        undersaturated_bases = [
            base for base in self.base_economies.values()
            if base.saturation_ratio < 0.8  # 80% 미만
        ]

        if not oversaturated_bases or not undersaturated_bases:
            return

        # 과포화 기지에서 일꾼 선택
        source_base = max(oversaturated_bases, key=lambda b: b.saturation_ratio)
        target_base = min(undersaturated_bases, key=lambda b: b.saturation_ratio)

        # 이전할 일꾼 수 계산
        excess_workers = int((source_base.saturation_ratio - 1.0) * source_base.optimal_mineral_workers)
        transfer_count = min(excess_workers, 3)  # 한 번에 최대 3명

        if transfer_count <= 0:
            return

        # 일꾼 이전
        workers_near_source = self.bot.workers.closer_than(10, Point2(source_base.position))
        transferred = 0

        for worker in workers_near_source:
            if transferred >= transfer_count:
                break

            # 미네랄 채광 중인 일꾼만 이전
            if worker.is_gathering or worker.is_carrying_minerals:
                # 목표 기지로 이전
                target_minerals = self.bot.mineral_field.closer_than(10, Point2(target_base.position))
                if target_minerals:
                    self.bot.do(worker.gather(target_minerals.closest_to(worker)))
                    transferred += 1
                    self.total_worker_moves += 1

                    self.logger.debug(
                        f"[WORKER] Transferred worker from base {source_base.base_tag} "
                        f"to {target_base.base_tag}"
                    )

    async def _request_additional_workers(self) -> None:
        """과소 기지에 추가 일꾼 요청"""
        # 여유 일꾼이 있는지 확인
        if not hasattr(self.bot, "workers"):
            return

        idle_workers = self.bot.workers.idle
        if not idle_workers:
            return

        # 가장 과소한 기지 찾기
        undersaturated_bases = [
            base for base in self.base_economies.values()
            if base.saturation_ratio < 0.5
        ]

        if not undersaturated_bases:
            return

        target_base = min(undersaturated_bases, key=lambda b: b.saturation_ratio)

        # 여유 일꾼을 해당 기지로 배치
        for worker in idle_workers:
            target_minerals = self.bot.mineral_field.closer_than(10, Point2(target_base.position))
            if target_minerals:
                self.bot.do(worker.gather(target_minerals.closest_to(worker)))
                self.total_worker_moves += 1
                break

    async def _balance_mineral_patches(self) -> None:
        """미네랄 패치별 일꾼 밸런싱"""
        for base_economy in self.base_economies.values():
            # 과할당된 패치와 과소 패치 찾기
            overassigned = [p for p in base_economy.mineral_patches if p.assigned_workers > p.optimal_workers]
            underassigned = [p for p in base_economy.mineral_patches if p.assigned_workers < p.optimal_workers and not p.is_depleting]

            if not overassigned or not underassigned:
                continue

            # 과할당 패치에서 일꾼 이동
            for over_patch in overassigned:
                excess = over_patch.assigned_workers - over_patch.optimal_workers
                if excess <= 0:
                    continue

                # 해당 패치에서 일하는 일꾼 찾기
                workers_on_patch = self._get_workers_on_mineral(over_patch.tag)

                moved = 0
                for worker in workers_on_patch:
                    if moved >= excess:
                        break

                    # 과소 패치로 이동
                    if underassigned:
                        target_patch_state = underassigned[0]
                        target_mineral = self._get_mineral_by_tag(target_patch_state.tag)

                        if target_mineral:
                            self.bot.do(worker.gather(target_mineral))
                            moved += 1
                            self.total_worker_moves += 1

                            # 과소 패치 업데이트
                            target_patch_state.assigned_workers += 1
                            if target_patch_state.assigned_workers >= target_patch_state.optimal_workers:
                                underassigned.pop(0)

    async def _balance_gas_workers(self) -> None:
        """가스 일꾼 밸런싱"""
        current_minerals = getattr(self.bot, "minerals", 0)
        current_gas = getattr(self.bot, "vespene", 0)

        # 현재 미네랄:가스 비율
        if current_gas > 0:
            current_ratio = current_minerals / current_gas
        else:
            current_ratio = float('inf')

        # 비율이 목표보다 너무 낮으면 (미네랄 부족) 가스 일꾼 줄이기
        if current_ratio < self.target_mineral_gas_ratio * 0.5:
            await self._reduce_gas_workers()

        # 비율이 목표보다 너무 높으면 (가스 부족) 가스 일꾼 늘리기
        elif current_ratio > self.target_mineral_gas_ratio * 2.0:
            await self._increase_gas_workers()

    async def _reduce_gas_workers(self) -> None:
        """가스 일꾼 줄이기"""
        if not hasattr(self.bot, "gas_buildings"):
            return

        gas_buildings = self.bot.gas_buildings.ready

        for gas_building in gas_buildings:
            if gas_building.assigned_harvesters > 1:  # 최소 1명은 유지
                # 가스 일꾼 1명을 미네랄로 이동
                workers = self.bot.workers.filter(
                    lambda w: w.order_target == gas_building.tag or w.is_carrying_vespene
                )

                if workers:
                    worker = workers.first
                    nearby_minerals = self.bot.mineral_field.closer_than(10, gas_building)
                    if nearby_minerals:
                        self.bot.do(worker.gather(nearby_minerals.closest_to(worker)))
                        self.total_worker_moves += 1
                        self.logger.debug("[WORKER] Reduced gas worker (excess gas)")
                        break

    async def _increase_gas_workers(self) -> None:
        """가스 일꾼 늘리기"""
        if not hasattr(self.bot, "gas_buildings"):
            return

        gas_buildings = self.bot.gas_buildings.ready

        for gas_building in gas_buildings:
            if gas_building.assigned_harvesters < self.optimal_workers_per_gas:
                # 미네랄 일꾼을 가스로 이동
                nearby_workers = self.bot.workers.closer_than(10, gas_building).filter(
                    lambda w: w.is_gathering and not w.is_carrying_vespene
                )

                if nearby_workers:
                    worker = nearby_workers.first
                    self.bot.do(worker.gather(gas_building))
                    self.total_worker_moves += 1
                    self.logger.debug("[WORKER] Increased gas worker (gas shortage)")
                    break

    async def _assign_idle_workers(self) -> None:
        """대기 일꾼 즉시 할당"""
        if not hasattr(self.bot, "workers"):
            return

        idle_workers = self.bot.workers.idle

        for worker in idle_workers:
            # 가장 가까운 기지 찾기
            if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.ready:
                continue

            closest_base = self.bot.townhalls.ready.closest_to(worker)

            # 가장 가까운 미네랄 패치로 보내기
            nearby_minerals = self.bot.mineral_field.closer_than(10, closest_base)
            if nearby_minerals:
                self.bot.do(worker.gather(nearby_minerals.closest_to(worker)))
                self.total_worker_moves += 1

    async def _fix_long_distance_mining(self) -> None:
        """장거리 채광 수정"""
        if not hasattr(self.bot, "workers") or not hasattr(self.bot, "townhalls"):
            return

        for worker in self.bot.workers:
            if not (worker.is_gathering or worker.is_carrying_minerals):
                continue

            # 가장 가까운 기지 찾기
            if not self.bot.townhalls.ready:
                continue

            closest_base = self.bot.townhalls.ready.closest_to(worker)

            # 일꾼이 기지에서 너무 멀리 떨어진 곳에서 채광 중인 경우
            if worker.distance_to(closest_base) > 12:
                # 가까운 미네랄로 재할당
                nearby_minerals = self.bot.mineral_field.closer_than(10, closest_base)
                if nearby_minerals:
                    best_mineral = self._find_best_mineral_patch(nearby_minerals, closest_base)
                    if best_mineral:
                        self.bot.do(worker.gather(best_mineral))
                        self.total_worker_moves += 1
                        self.logger.debug("[WORKER] Fixed long distance mining")

    def _find_best_mineral_patch(self, minerals: Units, base: Unit) -> Optional[Unit]:
        """최적 미네랄 패치 찾기"""
        if not minerals:
            return None

        # 고갈되지 않고, 일꾼이 적게 할당된 패치 우선
        best_mineral = None
        best_score = -1

        for mineral in minerals:
            if mineral.mineral_contents < 100:  # 거의 고갈
                continue

            assigned = self._count_workers_on_mineral(mineral.tag)
            distance = base.distance_to(mineral)

            # 점수: 할당 일꾼이 적을수록, 거리가 가까울수록 높음
            score = (self.optimal_workers_per_mineral - assigned) * 10 - distance

            if score > best_score:
                best_score = score
                best_mineral = mineral

        return best_mineral if best_mineral else minerals.closest_to(base)

    def _detect_depleting_minerals(self) -> None:
        """미네랄 고갈 감지"""
        if not hasattr(self.bot, "mineral_field"):
            return

        for mineral in self.bot.mineral_field:
            if mineral.mineral_contents < 200 and mineral.tag not in self.depleting_patches:
                self.depleting_patches.add(mineral.tag)
                self.logger.info(f"[WORKER] Mineral patch {mineral.tag} is depleting (<200)")

    def _count_workers_on_mineral(self, mineral_tag: int) -> int:
        """특정 미네랄 패치에 할당된 일꾼 수"""
        if not hasattr(self.bot, "workers"):
            return 0

        return sum(
            1 for w in self.bot.workers
            if w.order_target == mineral_tag or
            (w.is_carrying_minerals and w.distance_to(self._get_mineral_position(mineral_tag)) < 2)
        )

    def _count_workers_on_gas(self, gas_tag: int) -> int:
        """특정 가스 건물에 할당된 일꾼 수"""
        gas_building = self._get_gas_building_by_tag(gas_tag)
        if gas_building:
            return gas_building.assigned_harvesters
        return 0

    def _get_workers_on_mineral(self, mineral_tag: int) -> Units:
        """특정 미네랄 패치에서 일하는 일꾼들"""
        if not hasattr(self.bot, "workers"):
            return Units([], self.bot)

        mineral_pos = self._get_mineral_position(mineral_tag)
        if not mineral_pos:
            return Units([], self.bot)

        return self.bot.workers.filter(
            lambda w: w.order_target == mineral_tag or
            (w.is_carrying_minerals and w.distance_to(mineral_pos) < 2)
        )

    def _get_mineral_by_tag(self, mineral_tag: int) -> Optional[Unit]:
        """태그로 미네랄 찾기"""
        if not hasattr(self.bot, "mineral_field"):
            return None

        for mineral in self.bot.mineral_field:
            if mineral.tag == mineral_tag:
                return mineral
        return None

    def _get_mineral_position(self, mineral_tag: int) -> Optional[Point2]:
        """미네랄 위치 가져오기"""
        mineral = self._get_mineral_by_tag(mineral_tag)
        return mineral.position if mineral else None

    def _get_gas_building_by_tag(self, gas_tag: int) -> Optional[Unit]:
        """태그로 가스 건물 찾기"""
        if not hasattr(self.bot, "gas_buildings"):
            return None

        for gas in self.bot.gas_buildings:
            if gas.tag == gas_tag:
                return gas
        return None

    def _collect_learning_data(self, game_time: float) -> None:
        """학습 데이터 수집"""
        if not hasattr(self.bot, "workers"):
            return

        # 수입 추적
        worker_count = len(self.bot.workers)
        mineral_income = getattr(self.bot, "minerals", 0)
        gas_income = getattr(self.bot, "vespene", 0)

        self.income_history.append((game_time, mineral_income, gas_income, worker_count))

        # 효율성 점수 계산
        if worker_count > 0:
            efficiency = (mineral_income + gas_income * 1.5) / worker_count
            self.efficiency_metrics.append((game_time, efficiency))

        # 최근 300개 데이터만 유지
        if len(self.income_history) > 300:
            self.income_history = self.income_history[-300:]
        if len(self.efficiency_metrics) > 300:
            self.efficiency_metrics = self.efficiency_metrics[-300:]

    def get_efficiency_report(self) -> str:
        """효율성 보고서"""
        report = "[WORKER OPTIMIZER]\n"

        total_bases = len(self.base_economies)
        report += f"Active Bases: {total_bases}\n"

        if self.base_economies:
            avg_saturation = sum(b.saturation_ratio for b in self.base_economies.values()) / total_bases
            report += f"Avg Saturation: {avg_saturation:.1%}\n"

        report += f"Worker Moves: {self.total_worker_moves}\n"
        report += f"Depleting Patches: {len(self.depleting_patches)}\n"

        # 기지별 상세 정보
        for base in self.base_economies.values():
            report += f"  Base {base.base_tag}: {base.assigned_mineral_workers}m/{base.assigned_gas_workers}g "
            report += f"(Saturation: {base.saturation_ratio:.1%})\n"

        return report
