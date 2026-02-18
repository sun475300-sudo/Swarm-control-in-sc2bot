# -*- coding: utf-8 -*-
"""
Economy Manager - deterministic worker production with macro hatcheries.
"""

from typing import Optional

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:  # Fallbacks for tooling environments

    class UnitTypeId:
        DRONE = "DRONE"
        OVERLORD = "OVERLORD"
        HATCHERY = "HATCHERY"

    Point2 = tuple  # Fallback for tooling


from local_training.economy_combat_balancer import EconomyCombatBalancer
from config.unit_configs import EconomyConfig


class EconomyManager:
    """
    Manages economy and larva production.

    Features:
    - Dynamic drone production based on base count
    - Auto supply management
    - Macro hatchery construction when resources stockpile
    - Prevents resource banking by expanding production capacity
    - Gold base prioritization for expansion
    """

    # Gold mineral patch threshold (normal patches have ~900, gold have ~1500+)
    GOLD_MINERAL_THRESHOLD = 1200

    def __init__(self, bot):
        self.bot = bot
        self.balancer = EconomyCombatBalancer(bot)

        # ★ Blackboard 연동 ★
        self.blackboard = getattr(bot, "blackboard", None)

        # ★ Config 연동 ★
        try:
            from game_config import config
            self.config = config
        except ImportError:
            self.config = None

        # ★ Resource thresholds for macro hatchery (Config 기반) ★
        if self.config:
            self.macro_hatchery_mineral_threshold = self.config.MINERAL_OVERFLOW
            self.macro_hatchery_larva_threshold = self.config.LARVA_CRITICAL
        else:
            self.macro_hatchery_mineral_threshold = 1500
            self.macro_hatchery_larva_threshold = 3

        self.last_macro_hatch_check = 0
        self.macro_hatch_check_interval = 50  # Check every 50 frames
        # Gold base tracking
        self._gold_bases_cache = []
        self._gold_cache_time = 0
        self._emergency_mode = False
        # 2026-01-25 FIX: Track Maynarding transfers
        self.transferred_hatcheries = set()
        # 2026-01-26 FIX: Prevent duplicate expansion attempts
        self._last_expansion_attempt_time = 0.0
        self._expansion_cooldown = 6.0  # 6초 쿨다운
        # ★ 미네랄 예약 시스템 (확장 우선순위) ★
        self._mineral_reserved_for_expansion = 0  # 확장 예약 미네랄
        self._expansion_reserved_until = 0.0  # 예약 만료 시간

        # ★ NEW: 자원 예약 시스템 ★
        self._reserved_minerals = 0
        self._reserved_gas = 0

        # ★★★ Phase 18: Gas Timing Optimization ★★★
        self.gas_timing_by_race = {
            "Terran": 90,  # 1분 30초 (중간 타이밍)
            "Protoss": 75,  # 1분 15초 (빠른 가스 - 프로토스는 초반 올인 많음)
            "Zerg": 105,  # 1분 45초 (느린 가스 - 저그는 드론 펌핑 우선)
            "Random": 90,
            "Unknown": 90,
        }

        self.gas_boost_mode = False  # 빠른 테크가 필요할 때 활성화
        self.gas_boost_start_time = 0
        self.gas_boost_duration = 120  # 2분간 가스 부스트

        self.dynamic_gas_workers_enabled = True  # 생산 큐 기반 가스 일꾼 조정
        self.gas_overflow_prevention_threshold = 3000  # 가스 3000+ 시 일꾼 회수

        self.last_gas_worker_adjustment = 0
        self.gas_worker_adjustment_interval = 110  # ~5초마다 조정

        # ★ Expansion Blocking (Phase 17) ★
        self.expansion_block_active = False
        self.expansion_block_worker_tag = None
        self.expansion_block_start_time = 50  # 50초에 출발
        self.expansion_block_duration = 45    # 45초간 방해

        # ★ Expansion Telemetry ★
        self.first_expansion_time = 0.0
        self.first_expansion_reported = False

    def set_emergency_mode(self, active: bool) -> None:
        """Set emergency mode validation."""
        self._emergency_mode = active

    def safeguard_resources(self) -> tuple:
        """
        Phase 17: Centralized Resource Safety Check
        Ensures available resources never report negative values.
        """
        # 1. Use centralized manager if available
        if hasattr(self.bot, 'resource_manager') and self.bot.resource_manager:
            mins, gas = self.bot.resource_manager.get_available_resources()
            return max(0, mins), max(0, gas)

        # 2. Local fallback with safety clamping
        current_mins = getattr(self.bot, "minerals", 0)
        current_gas = getattr(self.bot, "vespene", 0)

        available_mins = current_mins - self._reserved_minerals
        available_gas = current_gas - self._reserved_gas

        # Log warning on over-reservation (Logic Bug Detection)
        if available_mins < 0 and self.bot.iteration % 100 == 0:
            print(f"[ECONOMY_WARN] Negative minerals detected! ({available_mins}) Reserved: {self._reserved_minerals}")
        
        if available_gas < 0 and self.bot.iteration % 100 == 0:
             print(f"[ECONOMY_WARN] Negative gas detected! ({available_gas}) Reserved: {self._reserved_gas}")

        return max(0, available_mins), max(0, available_gas)

    async def on_step(self, iteration: int) -> None:
        if not hasattr(self.bot, "larva"):
            return

        # ★ Blackboard Sync ★
        if self.blackboard:
            from blackboard import AuthorityMode
            if self.blackboard.authority_mode == AuthorityMode.EMERGENCY:
                 self._emergency_mode = True
            else:
                 self._emergency_mode = False


        # 게임 시작 초반 일꾼 분할 (첫 10초)
        if iteration < 50:
            await self._optimize_early_worker_split()

        # ★★★ UNIFIED EXPANSION CHECK: 단일 진입점으로 모든 확장 의사결정 ★★★
        if iteration % 33 == 0:  # ~1.5초마다
            await self._unified_expansion_check(iteration)

        # 확장 체크 후 드론/오버로드 생산 (자원 확보 후 생산)
        await self._train_overlord_if_needed()
        await self._train_drone_if_needed()

        # ★ CRITICAL: 대기 일꾼 즉시 할당 (매 프레임 체크) ★
        await self._assign_idle_workers()

        # Distribute workers to gas (every 11 frames = ~0.5 seconds) - IMPROVED: 더 자주 재분배
        if iteration % 11 == 0:
            await self._distribute_workers_to_gas()

        # Redistribute mineral workers between bases (every 22 frames = ~1 second) - IMPROVED: 더 자주 재분배
        if iteration % 22 == 0:
            await self._redistribute_mineral_workers()

        # ★ Distance Mining: 드론을 가장 가까운 미네랄 패치에 재배정 (30초마다) ★
        if iteration % 660 == 0:
            await self._optimize_mineral_assignments()

        # Check for macro hatchery needs periodically
        if iteration - self.last_macro_hatch_check >= self.macro_hatch_check_interval:
            self.last_macro_hatch_check = iteration
            await self._build_macro_hatchery_if_needed()

        # ★ NEW: 자원 예약 관리 (스포어/레어 등) ★
        if iteration % 22 == 0:  # ~1초마다
            self._update_resource_reservations()

        # ★ NEW: 자원 낭비 방지 (미네랄/가스 과잉 시 대응) ★
        if iteration % 44 == 0:  # ~2초마다
            await self._prevent_resource_banking()

        # ★ NEW: 가스 타이밍 최적화 ★
        if iteration % 33 == 0:  # ~1.5초마다
            await self._optimize_gas_timing()

        # ★★★ Phase 18: Dynamic gas worker adjustment ★★★
        if iteration - self.last_gas_worker_adjustment >= self.gas_worker_adjustment_interval:
            await self._adjust_gas_workers_dynamically()
            self.last_gas_worker_adjustment = iteration

        # ★★★ Phase 18: Gas overflow prevention ★★★
        if iteration % 110 == 0:  # ~5초마다
            await self._prevent_gas_overflow()

        # ★ NEW: Maynarding (일꾼 미리 보내기) - Issue 7 ★
        if iteration % 22 == 0:
            await self._check_maynarding()

        # ★ NEW: 경제 회복 시스템 가동 (병력 생산 후 재건) ★
        if iteration % 22 == 0:
            await self.check_economic_recovery()

        # ★ NEW: 공중 위협 대응 시스템 (Anti-Air Response) ★
        if iteration % 44 == 0:
            await self._check_air_threat_response()

        # ★ NEW: Expansion Blocking (Phase 17) ★
        if iteration % 22 == 0:
            await self._manage_expansion_blocking()

        # ★ NEW: Expansion Telemetry (Phase 17) ★
        if not self.first_expansion_reported:
            self._check_first_expansion_timing()

        # ★ IMPROVED: Extreme Gas Imbalance Fix (덜 공격적) ★
        # Gas > 3000 and Minerals < 200 -> 일부 가스 일꾼만 미네랄로 이동
        if iteration % 88 == 0:  # 4초마다 (2초 → 4초, 덜 빈번하게)
            gas = getattr(self.bot, "vespene", 0)
            minerals = getattr(self.bot, "minerals", 0)

            # ★ 조건 완화: 가스 3000+ (2000→3000), 미네랄 200- (500→200) ★
            # 더 심각한 불균형일 때만 개입
            if gas > 3000 and minerals < 200:
                # 쿨다운 체크 (30초에 한 번만)
                if not hasattr(self, "_last_gas_cut_time"):
                    self._last_gas_cut_time = 0

                if self.bot.time - self._last_gas_cut_time < 30:
                    pass  # 30초 이내에 이미 실행됨
                elif hasattr(self.bot, "smart_balancer") and self.bot.smart_balancer:
                    pass  # SmartResourceBalancer가 처리
                else:
                    # ★ 일부 가스 일꾼만 이동 (50%만) ★
                    if hasattr(self.bot, "gas_buildings"):
                        for extractor in self.bot.gas_buildings.ready:
                            if extractor.assigned_harvesters > 0:
                                workers = self.bot.workers.filter(
                                    lambda w: w.is_carrying_vespene or w.order_target == extractor.tag
                                )
                                # 50%만 이동 (최대 3마리)
                                workers_to_move = min(len(workers) // 2 + 1, 3)
                                for w in workers[:workers_to_move]:
                                    nearby_minerals = self.bot.mineral_field.closer_than(10, w)
                                    if nearby_minerals:
                                        self.bot.do(w.gather(nearby_minerals.closest_to(w)))

                        self._last_gas_cut_time = self.bot.time
                        print(f"[ECONOMY] Reducing gas workers (Gas: {gas}, Min: {minerals})")

    async def _optimize_early_worker_split(self) -> None:
        """
        초반 일꾼 분할 최적화.

        게임 시작 시 12기의 일꾼을 8개의 미네랄 패치에 분배:
        - 4개 패치에 2명씩 (8명)
        - 4개 패치에 1명씩 (4명)

        이렇게 하면 멀리 있는 미네랄에도 일꾼이 배치됨.
        """
        if not hasattr(self.bot, "workers") or not hasattr(self.bot, "mineral_field"):
            return

        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return

        workers = self.bot.workers
        if not workers or workers.amount < 12:
            return

        # 이미 분배된 일꾼이 있으면 건너뜀
        if hasattr(self, "_early_split_done") and self._early_split_done:
            return

        main_base = self.bot.townhalls.first
        nearby_minerals = self.bot.mineral_field.closer_than(10, main_base)

        if not nearby_minerals or nearby_minerals.amount < 6:
            return

        # 미네랄을 거리순으로 정렬 (가까운 것부터)
        sorted_minerals = sorted(nearby_minerals, key=lambda m: m.distance_to(main_base))

        # 일꾼 목록 생성
        worker_list = list(workers)

        try:
            assigned_count = 0
            mineral_assignments = {m.tag: 0 for m in sorted_minerals}

            # 1단계: 각 미네랄에 1명씩 배치
            for mineral in sorted_minerals[:8]:  # 최대 8개 패치
                if assigned_count >= len(worker_list):
                    break
                worker = worker_list[assigned_count]
                self.bot.do(worker.gather(mineral))
                mineral_assignments[mineral.tag] = 1
                assigned_count += 1

            # 2단계: 남은 일꾼을 가까운 미네랄에 2번째로 배치
            for mineral in sorted_minerals[:4]:  # 가까운 4개 패치에 추가
                if assigned_count >= len(worker_list):
                    break
                if mineral_assignments[mineral.tag] < 2:
                    worker = worker_list[assigned_count]
                    self.bot.do(worker.gather(mineral))
                    mineral_assignments[mineral.tag] = 2
                    assigned_count += 1

            self._early_split_done = True
            print(f"[ECONOMY] Early worker split completed: {assigned_count} workers distributed")

        except Exception as e:
            print(f"[ECONOMY_WARN] Early worker split failed: {e}")

    async def _train_overlord_if_needed(self) -> None:
        # [FIX] Prevent execution multiple times per frame
        if getattr(self, "_overlord_checked_frame", -1) == self.bot.iteration:
             return
        self._overlord_checked_frame = self.bot.iteration

        if not hasattr(self.bot, "supply_left"):
            return

        # ★ 실효 보급 계산: pending 유닛이 소비할 보급 고려 ★
        pending_supply_cost = 0
        try:
            pending_supply_cost += self.bot.already_pending(UnitTypeId.DRONE) * 1
            pending_supply_cost += self.bot.already_pending(UnitTypeId.ZERGLING) * 1  # 2마리=1보급
            pending_supply_cost += self.bot.already_pending(UnitTypeId.ROACH) * 2
            pending_supply_cost += self.bot.already_pending(UnitTypeId.HYDRALISK) * 2
            pending_supply_cost += self.bot.already_pending(UnitTypeId.QUEEN) * 2
        except Exception:
            pending_supply_cost = 0
        effective_supply_left = self.bot.supply_left - pending_supply_cost

        # 이미 오버로드 생산 중이면 필요한 수만큼만 추가
        pending_overlords = self.bot.already_pending(UnitTypeId.OVERLORD)
        pending_overlord_supply = pending_overlords * 8

        # ★ Blackboard 기반 생산 (ProductionController가 자동 처리) ★
        # ProductionController가 이미 Overlord를 자동 생산하므로
        # EconomyManager는 추가 요청만 처리
        if self.blackboard:
            # Config 기반 보급 여유분 계산
            if self.config:
                game_time = self.bot.time
                if game_time < self.config.OPENING_PHASE_END:
                    supply_threshold = self.config.SUPPLY_BUFFER_OPENING
                elif game_time < self.config.EARLY_GAME_END:
                    supply_threshold = self.config.SUPPLY_BUFFER_EARLY
                else:
                    supply_threshold = self.config.SUPPLY_BUFFER_MID

                # 가스 많을 때 여유분 확대
                if self.bot.vespene > self.config.GAS_CRITICAL:
                    supply_threshold = self.config.SUPPLY_BUFFER_HIGH_GAS
            else:
                gas = getattr(self.bot, "vespene", 0)
                supply_threshold = 6 if gas < 1000 else 10

            # ★ 실효 보급 기반 체크 (pending 유닛 보급 포함) ★
            adjusted_supply = effective_supply_left + pending_overlord_supply
            if adjusted_supply >= supply_threshold:
                return

            # ★ 필요한 오버로드 수 계산 (1개가 아닌 부족분만큼) ★
            deficit = supply_threshold - adjusted_supply
            overlords_needed = max(1, (deficit + 7) // 8)  # 8보급당 1오버로드
            overlords_needed = min(overlords_needed, 3)  # 최대 3마리

            self.blackboard.request_production(
                unit_type=UnitTypeId.OVERLORD,
                count=overlords_needed,
                requester="EconomyManager"
            )
            return

        # ★ Blackboard 없을 때 폴백 (기존 로직) ★
        gas = getattr(self.bot, "vespene", 0)
        supply_threshold = 6 if gas < 1000 else 10

        # ★ 실효 보급 기반 체크 ★
        adjusted_supply = effective_supply_left + pending_overlord_supply
        if adjusted_supply >= supply_threshold:
            return

        if not self.bot.can_afford(UnitTypeId.OVERLORD):
            return

        larva_unit = self._get_first_larva()
        if not larva_unit:
            return

        try:
            if hasattr(self.bot, 'production') and self.bot.production:
                await self.bot.production._safe_train(larva_unit, UnitTypeId.OVERLORD)
            else:
                self.bot.do(larva_unit.train(UnitTypeId.OVERLORD))
        except (AttributeError, TypeError) as e:
            # Overlord production failed
            return

    async def _train_drone_if_needed(self) -> None:
        # === Worker Count Check ===
        worker_count = 0
        if hasattr(self.bot, "workers"):
            workers = self.bot.workers
            worker_count = workers.amount if hasattr(workers, "amount") else len(list(workers))

        # ★ 드론 절대 상한: 80마리 초과 금지 ★
        if worker_count >= 80:
            return

        # 기지 수 확인
        townhalls = self.bot.townhalls.ready if hasattr(self.bot, "townhalls") else []
        base_count = townhalls.amount if hasattr(townhalls, "amount") else 1

        # ★ Config 기반 최소 일꾼 목표 ★
        if self.config:
            min_workers_needed = base_count * self.config.DRONE_LIMIT_PER_BASE
            absolute_min = self.config.MIN_DRONES
        else:
            min_workers_needed = base_count * 16
            absolute_min = 22

        # ★ ULTRA-PRIORITY: 초반 3분은 일꾼 최우선 ★
        game_time = getattr(self.bot, "time", 0)
        early_game_drone_priority = game_time < 180  # 3분까지

        # ★ CRITICAL: 최소 일꾼 미달이면 무조건 생산 (밸런서 무시) ★
        below_minimum = worker_count < min_workers_needed or worker_count < absolute_min

        if not below_minimum and not early_game_drone_priority:
            # 일꾼이 충분하면 밸런서 판단 따름
            if not self.balancer.should_train_drone():
                return

        if hasattr(self.bot, "supply_left") and self.bot.supply_left <= 0:
            return

        # ★ Blackboard 기반 생산 ★
        if self.blackboard:
            from blackboard import AuthorityMode
            # EMERGENCY 모드에서는 최소 일꾼(22) 미만일 때만 생산 요청
            if self.blackboard.authority_mode == AuthorityMode.EMERGENCY:
                 if worker_count >= 22:
                     return

            # Blackboard에 드론 생산 요청
            self.blackboard.request_production(
                unit_type=UnitTypeId.DRONE,
                count=1,
                requester="EconomyManager"
            )
            return

        # ★ Blackboard 없을 때 폴백 (기존 로직) ★
        # ★ Phase 17: Centralized Resource Check ★
        available_minerals, available_gas = self.safeguard_resources()

        if available_minerals < 50:  # Drone 비용
            return

        if not self.bot.can_afford(UnitTypeId.DRONE):
            return

        larva_unit = self._get_first_larva()
        if not larva_unit:
            return

        try:
            if hasattr(self.bot, 'production') and self.bot.production:
                await self.bot.production._safe_train(larva_unit, UnitTypeId.DRONE)
            else:
                self.bot.do(larva_unit.train(UnitTypeId.DRONE))
        except Exception as e:
            game_time = getattr(self.bot, "time", 0.0)
            print(f"[ECONOMY_WARN] [{int(game_time)}s] Drone train failed: {e}")
            return

    async def _distribute_workers_to_gas(self) -> None:
        """
        Distribute workers to extractors.

        Ensures each extractor has 3 workers for optimal gas mining.
        """
        if not hasattr(self.bot, "gas_buildings"):
            return

        # ★ SmartResourceBalancer가 있으면 이 로직은 건너뜀 (권한 이양) ★
        if hasattr(self.bot, "smart_balancer") and self.bot.smart_balancer:
            return

        extractors = self.bot.gas_buildings.ready
        if not extractors:
            return

        if not hasattr(self.bot, "workers") or not self.bot.workers:
            return

        for extractor in extractors:
            # Check how many workers are assigned
            assigned_workers = extractor.assigned_harvesters
            ideal_workers = extractor.ideal_harvesters  # Usually 3

            if assigned_workers < ideal_workers:
                # Find idle or mineral-mining workers nearby
                workers_needed = ideal_workers - assigned_workers

                try:
                    # Get workers that are gathering minerals (not gas)
                    available_workers = self.bot.workers.filter(
                        lambda w: (
                            w.is_gathering and
                            not w.is_carrying_vespene and
                            w.distance_to(extractor) < 20
                        )
                    )

                    if not available_workers:
                        # Try idle workers
                        available_workers = self.bot.workers.filter(
                            lambda w: w.is_idle and w.distance_to(extractor) < 20
                        )

                    if available_workers:
                        # Assign closest workers to extractor
                        for _ in range(min(workers_needed, len(available_workers))):
                            worker = available_workers.closest_to(extractor)
                            if worker:
                                self.bot.do(worker.gather(extractor))
                                available_workers = available_workers.filter(
                                    lambda w: w.tag != worker.tag
                                )
                except (AttributeError, TypeError) as e:
                    # Worker filtering failed
                    continue

    async def _build_macro_hatchery_if_needed(self) -> None:
        """
        Build macro hatchery when resources are stockpiling.

        IMPROVED: 전투 중이면 더 공격적으로 매크로 해처리 건설

        Conditions:
        - Minerals > threshold (전투 중에는 더 낮은 임계값)
        - Average larva per base < threshold
        - Have at least 2 bases
        - Not already building a hatchery
        """
        if not hasattr(self.bot, "minerals") or not hasattr(self.bot, "townhalls"):
            return

        # ★ 전투 모드 체크 - 가스 과잉 시 더 공격적으로 매크로 해처리 건설 ★
        in_combat = False
        gas_overflow = False

        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and getattr(strategy, "emergency_active", False):
            in_combat = True

        # 가스 과잉 체크 (가스 > 1500이고 라바 < 5)
        gas = getattr(self.bot, "vespene", 0)
        total_larva = len(self.bot.larva) if hasattr(self.bot, "larva") else 0
        if gas > 1500 and total_larva < 5:
            gas_overflow = True

        # Check resource conditions (전투/가스 과잉 시 낮은 임계값)
        minerals = self.bot.minerals
        mineral_threshold = 800 if (in_combat or gas_overflow) else self.macro_hatchery_mineral_threshold

        if minerals < mineral_threshold:
            return

        # Check base count
        townhalls = self.bot.townhalls.ready
        if not townhalls or townhalls.amount < 2:
            return

        # Check larva availability
        avg_larva_per_base = total_larva / max(1, townhalls.amount)

        # 전투/가스 과잉 시 더 높은 라바 임계값 (더 많이 필요)
        larva_threshold = 5 if (in_combat or gas_overflow) else self.macro_hatchery_larva_threshold

        if avg_larva_per_base >= larva_threshold:
            return  # Have enough larva production

        # Check if already building hatchery
        if hasattr(self.bot, "already_pending"):
            pending = self.bot.already_pending(UnitTypeId.HATCHERY)
            # 전투/가스 과잉 시 여러 개 동시 건설 허용
            max_pending = 2 if (in_combat or gas_overflow) else 1
            if pending >= max_pending:
                return

        # Don't build if can't afford
        if not self.bot.can_afford(UnitTypeId.HATCHERY):
            return

        # Find safe build location near main base
        if not hasattr(self.bot, "start_location"):
            return

        main_base = townhalls.first
        build_location = await self._find_macro_hatch_location(main_base)

        if build_location:
            try:
                # Build macro hatchery
                worker = None
                if hasattr(self.bot, "workers") and self.bot.workers:
                    worker = self.bot.workers.closest_to(build_location)

                if worker:
                    self.bot.do(
                        worker.build(UnitTypeId.HATCHERY, build_location)
                    )
                    game_time = getattr(self.bot, "time", 0)
                    reason = "COMBAT/GAS_OVERFLOW" if (in_combat or gas_overflow) else "normal"
                    print(f"[ECONOMY] [{int(game_time)}s] Building MACRO HATCHERY ({reason}, gas: {gas}, larva: {total_larva})")
            except (AttributeError, TypeError, ValueError) as e:
                # Macro hatchery placement failed
                pass

    async def _find_macro_hatch_location(self, main_base):
        """Find safe location for macro hatchery near main base."""
        if not hasattr(self.bot, "can_place"):
            return None

        try:
            # Try positions around main base at distance 8-12
            import math

            for angle in range(0, 360, 45):
                for distance in [8, 10, 12]:
                    rad = math.radians(angle)
                    x_offset = distance * math.cos(rad)
                    y_offset = distance * math.sin(rad)

                    try:
                        # Create Point2 if available
                        if hasattr(main_base.position, "__add__"):
                            test_pos = main_base.position.offset(
                                (x_offset, y_offset)
                            )
                        else:
                            continue

                        # Check if we can place hatchery there
                        if await self.bot.can_place(UnitTypeId.HATCHERY, test_pos):
                            return test_pos
                    except (AttributeError, TypeError, ValueError) as e:
                        # Position check failed
                        continue

        except (AttributeError, TypeError, ValueError) as e:
            # Finding safe position failed
            pass

        return None

    async def _optimize_mineral_assignments(self) -> None:
        """
        Distance Mining: 각 기지에서 드론을 가장 가까운 미네랄 패치에 재배정.

        고갈 중인 패치(100 미네랄 미만)에서 드론을 재배치.
        """
        try:
            for townhall in self.bot.townhalls.ready:
                nearby_minerals = self.bot.mineral_field.closer_than(10, townhall)
                if not nearby_minerals:
                    continue

                # 고갈된 패치 감지 및 드론 재배정
                depleted = [m for m in nearby_minerals if m.mineral_contents < 100]
                if not depleted:
                    continue

                healthy = [m for m in nearby_minerals if m.mineral_contents >= 100]
                if not healthy:
                    continue

                # 가까운 순으로 정렬
                healthy_sorted = sorted(healthy, key=lambda m: m.distance_to(townhall))

                workers = self.bot.workers.closer_than(10, townhall)
                for worker in workers:
                    # 고갈된 패치로 가고 있는 드론만 재배정
                    if hasattr(worker, 'order_target') and worker.order_target:
                        for dep in depleted:
                            if worker.order_target == dep.tag:
                                # 가장 가까운 건강한 패치로 이동
                                closest = min(healthy_sorted, key=lambda m: m.distance_to(worker))
                                self.bot.do(worker.gather(closest))
                                break
        except Exception:
            pass

    async def _redistribute_mineral_workers(self) -> None:
        """
        Redistribute mineral workers between bases.

        - Move workers from over-saturated bases to under-saturated ones
        - Move workers from DEPLETED bases to other bases
        - Detect bases with low/no mineral patches
        - Keep only gas workers at depleted bases with extractors
        - Optimal: 16 workers per base for minerals (2 per patch)

        IMPROVED: 쿨다운 추가, 이동 중인 일꾼 제외, 고갈 조건 완화
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "workers"):
            return

        townhalls = self.bot.townhalls.ready
        if not townhalls or townhalls.amount < 2:
            return  # Need at least 2 bases

        workers = self.bot.workers
        if not workers:
            return

        # 쿨다운 체크 - ★ OPTIMIZED: 5초 → 2초 (더 빠른 재분배) ★
        current_time = getattr(self.bot, "time", 0)
        if not hasattr(self, "_last_redistribute_time"):
            self._last_redistribute_time = 0
        if current_time - self._last_redistribute_time < 2.0:  # ★ 5.0 → 2.0 ★
            return
        self._last_redistribute_time = current_time

        try:
            # First: Check for DEPLETED bases (완화: 미네랄 < 2개 또는 총량 < 300)
            depleted_bases = []
            active_bases = []

            for th in townhalls:
                # Count mineral patches near this base
                nearby_minerals = self.bot.mineral_field.closer_than(10, th)
                mineral_count = nearby_minerals.amount if hasattr(nearby_minerals, 'amount') else len(list(nearby_minerals))

                # Count total minerals remaining
                total_minerals = sum(m.mineral_contents for m in nearby_minerals) if nearby_minerals else 0

                # 완화된 조건: 미네랄 < 2개 또는 총량 < 300
                if mineral_count < 2 or total_minerals < 300:
                    # Base is depleted - move workers out
                    depleted_bases.append(th)
                else:
                    active_bases.append(th)

            # Move workers from depleted bases to active bases
            for depleted_th in depleted_bases:
                if not active_bases:
                    break

                # Get IDLE mineral workers at this depleted base (not moving, not carrying)
                # 개선: is_idle 또는 is_gathering하고 있고 가까이 있는 일꾼만
                nearby_workers = workers.filter(
                    lambda w: (w.distance_to(depleted_th) < 8 and  # 거리 줄임 (15 -> 8)
                              (w.is_idle or (w.is_gathering and not w.is_moving)) and
                              not w.is_carrying_vespene and
                              not any(e.distance_to(w) < 3 for e in self.bot.gas_buildings))
                )

                if not nearby_workers or nearby_workers.amount < 2:  # 최소 2명 이상만
                    continue

                # Find best target base (closest active base with capacity)
                best_target = None
                best_deficit = 0
                for active_th in active_bases:
                    assigned = active_th.assigned_harvesters
                    ideal = active_th.ideal_harvesters
                    deficit = ideal - assigned
                    if deficit > best_deficit:
                        best_deficit = deficit
                        best_target = active_th

                if not best_target:
                    # All bases full - use closest
                    best_target = min(active_bases, key=lambda th: th.distance_to(depleted_th))

                # Move workers to target base (최대 3명으로 줄임)
                workers_moved = 0
                for worker in nearby_workers:
                    if workers_moved >= 3:  # Max 3 at a time (5 -> 3)
                        break

                    minerals = self.bot.mineral_field.closer_than(10, best_target)
                    if minerals:
                        try:
                            self.bot.do(worker.gather(minerals.closest_to(best_target)))
                            workers_moved += 1
                        except (AttributeError, TypeError) as e:
                            # Worker command failed
                            continue

                if workers_moved > 0:
                    print(f"[ECONOMY] [{int(current_time)}s] Moved {workers_moved} workers from depleted base")

            # Second: Normal redistribution for over/under-saturated bases
            over_saturated = []
            under_saturated = []

            for th in active_bases:  # Only check active bases
                assigned = th.assigned_harvesters
                ideal = th.ideal_harvesters  # Usually 16 for minerals

                if assigned > ideal:  # Strict optimization (was ideal + 2)
                    over_saturated.append((th, assigned - ideal))
                elif assigned < ideal:  # Fill even small holes
                    under_saturated.append((th, ideal - assigned))

            # Move workers from over-saturated to under-saturated
            for over_th, excess in over_saturated:
                if not under_saturated:
                    break

                # Get workers near this townhall
                nearby_workers = workers.filter(
                    lambda w: w.distance_to(over_th) < 15 and w.is_gathering
                )

                for under_th, deficit in under_saturated[:]:
                    if excess <= 0 or deficit <= 0:
                        continue

                    # Move workers - ★ OPTIMIZED: 더 공격적인 재분배 ★
                    workers_to_move = min(excess, deficit, 8)  # ★ 5 → 8 (더 빠른 재분배) ★
                    for _ in range(workers_to_move):
                        if not nearby_workers:
                            break

                        worker = nearby_workers.furthest_to(over_th)
                        if worker:
                            # Find mineral field near target base
                            minerals = self.bot.mineral_field.closer_than(10, under_th)
                            if minerals:
                                self.bot.do(worker.gather(minerals.closest_to(under_th)))
                                nearby_workers = nearby_workers.filter(
                                    lambda w: w.tag != worker.tag
                                )
                                excess -= 1
                                deficit -= 1

                    # Update under-saturated list
                    if deficit <= 0:
                        under_saturated.remove((under_th, deficit))

        except (AttributeError, TypeError, ValueError) as e:
            # Worker balancing failed
            pass

    async def _prevent_resource_banking(self) -> None:
        """
        ★ Prevent resource banking by spending excess minerals ★

        Logic:
        1. If Minerals > Config.Threshold and Larva < Config.Threshold:
           - Build Extra Queens (Injects/Defense)
           - Build Static Defense (Spines/Spores) - ONLY AFTER 3+ BASES
        """
        if not hasattr(self.bot, "minerals"):
            return

        minerals = self.bot.minerals
        vespene = self.bot.vespene
        larva_count = len(self.bot.larva) if hasattr(self.bot, "larva") else 0
        game_time = getattr(self.bot, "time", 0)
        base_count = self.bot.townhalls.amount if hasattr(self.bot, "townhalls") else 1

        # ★ CRITICAL: 초반 (3분 이전) 또는 3베이스 이전에는 방어 건물 금지! ★
        # 확장이 최우선이므로 미네랄 낭비 방지 (Config 기반)
        can_build_defense = (
            (game_time >= EconomyConfig.BANKING_DEFENSE_TIME_REQ and base_count >= EconomyConfig.BANKING_DEFENSE_BASE_REQ) 
            or minerals > 2000
        )

        # 임계값: 미네랄 1000, 라바 부족 시 (Config 기반)
        if minerals > EconomyConfig.BANKING_MINERAL_THRESHOLD and larva_count < EconomyConfig.BANKING_LARVA_THRESHOLD:
            # 1. 퀸 추가 생산 (주사기 + 수비)
            if self.bot.supply_left >= 2 and self.bot.can_afford(UnitTypeId.QUEEN):
                 for th in self.bot.townhalls.ready.idle:
                     if not self.bot.units(UnitTypeId.QUEEN).closer_than(5, th).exists:
                         self.bot.do(th.train(UnitTypeId.QUEEN))
                         if minerals < 800: break

            # 2. 방어 건물 건설 (본진/멀티) - ★ 3베이스 이후에만! ★
            if can_build_defense and minerals > 1500 and hasattr(self.bot, "workers") and self.bot.workers:
                for th in self.bot.townhalls.ready:
                    # ★ 안전한 건설 위치: 미네랄 라인 근처 (맵 중앙 방향 X → 기지 뒤쪽) ★
                    mineral_fields = self.bot.mineral_field.closer_than(10, th)
                    if mineral_fields:
                        mineral_center = mineral_fields.center
                        base_pos = th.position

                        # 기지 당 포자촉수 1개 유지
                        spores = self.bot.structures(UnitTypeId.SPORECRAWLER).closer_than(10, th)
                        if not spores.exists and self.bot.can_afford(UnitTypeId.SPORECRAWLER):
                            # ★ 미네랄 라인 방향으로 건설 (안전한 위치) ★
                            pos = base_pos.towards(mineral_center, 4)
                            # ★ 안전 체크: 근처 적이 없는지 확인 ★
                            enemies_near = self.bot.enemy_units.closer_than(15, pos) if self.bot.enemy_units else []
                            if not enemies_near:
                                worker = self.bot.workers.closest_to(pos)
                                if worker:
                                    try:
                                        await self.bot.build(UnitTypeId.SPORECRAWLER, near=pos)
                                        minerals -= 75
                                    except Exception as e:
                                        print(f"[ECONOMY_WARN] Spore build failed: {e}")

                        # 기지 당 가시촉수 1개 유지 (미네랄 2000+ 일 때만)
                        if minerals > 2000:
                            spines = self.bot.structures(UnitTypeId.SPINECRAWLER).closer_than(10, th)
                            if not spines.exists and self.bot.can_afford(UnitTypeId.SPINECRAWLER):
                                # ★ 맵 중앙 방향으로 건설 (방어 최전방) ★
                                pos = base_pos.towards(self.bot.game_info.map_center, 6)
                                enemies_near = self.bot.enemy_units.closer_than(15, pos) if self.bot.enemy_units else []
                                if not enemies_near:
                                    worker = self.bot.workers.closest_to(pos)
                                    if worker:
                                        try:
                                            await self.bot.build(UnitTypeId.SPINECRAWLER, near=pos)
                                            minerals -= 100
                                        except Exception as e:
                                            print(f"[ECONOMY_WARN] Spine build failed: {e}")

    def _get_first_larva(self):
        larva = getattr(self.bot, "larva", None)
        if not larva:
            return None
        if hasattr(larva, "first"):
            return larva.first
        try:
            return next(iter(larva))
        except (StopIteration, AttributeError, TypeError) as e:
            # No larva available
            return None

    async def _assign_idle_workers(self) -> None:
        """
        ★ 대기(idle) 일꾼 즉시 자원 채취 할당 ★

        매 프레임 체크하여 놀고 있는 일꾼이 없도록 함.
        - idle 상태 일꾼 감지
        - 가장 가까운 미네랄/가스에 할당
        - 포화되지 않은 기지 우선
        
        OPTIMIZED: 불필요한 연산 최소화
        """
        if not hasattr(self.bot, "workers") or not self.bot.workers:
            return

        try:
            # 대기 일꾼 찾기 (가장 비용이 적은 필터)
            idle_workers = self.bot.workers.idle
            
            if not idle_workers:
                return  # 대기 일꾼 없음

            # 타운홀이 있는지 확인
            if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.ready:
                return
                
            townhalls = self.bot.townhalls.ready
            
            # 캐싱된 미네랄 필드 사용 (매번 closer_than 호출 방지)
            if not hasattr(self, "_cached_minerals_near_base"):
                self._cached_minerals_near_base = {}
                self._last_mineral_cache = 0
            
            current_frame = self.bot.iteration
            if current_frame - getattr(self, "_last_mineral_cache", 0) > 100:
                self._cached_minerals_near_base = {}
                self._last_mineral_cache = current_frame

            for worker in idle_workers:
                assigned = False

                # 1순위: 가스가 부족한 익스트랙터에 할당 (가장 급함)
                # 성능 최적화: 가스 건물이 적으므로 루프 돌아도 괜찮음
                if hasattr(self.bot, "gas_buildings"):
                    for extractor in self.bot.gas_buildings.ready:
                        if extractor.assigned_harvesters < extractor.ideal_harvesters:
                             # 거리 체크 없이 바로 할당해도 됨 (일단 채취가 중요)
                             self.bot.do(worker.gather(extractor))
                             assigned = True
                             break

                if assigned:
                    continue

                # 2순위: 가장 가까운 기지의 미네랄에 할당
                closest_th = townhalls.closest_to(worker)
                
                # 미네랄 찾기 (캐싱 활용)
                minerals = None
                if closest_th.tag in self._cached_minerals_near_base:
                    minerals = self._cached_minerals_near_base[closest_th.tag]
                else:
                    minerals = self.bot.mineral_field.closer_than(10, closest_th)
                    self._cached_minerals_near_base[closest_th.tag] = minerals
                
                if minerals:
                    target_mineral = minerals.closest_to(worker)
                    self.bot.do(worker.gather(target_mineral))
                else:
                    # 폴백: 맵 전체에서 찾기 (드문 경우)
                    if self.bot.mineral_field:
                        self.bot.do(worker.gather(self.bot.mineral_field.closest_to(worker)))

        except (AttributeError, TypeError) as e:
            # Idle worker assignment failed
            pass

    async def _unified_expansion_check(self, iteration: int) -> None:
        """
        ★★★ UNIFIED EXPANSION DECISION POINT ★★★

        모든 확장 로직을 단일 진입점으로 통합:
        1. 강제 확장 (타이밍 기반 - 최고 우선순위)
        2. 사전 확장 (타이밍 + 자원 기반)
        3. 자원 고갈 확장 (미네랄 부족 기반)
        4. 자원 과잉 확장 (미네랄 뱅킹 방지)

        쿨다운: 6초 (중복 확장 방지)
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "time"):
            return

        game_time = self.bot.time
        base_count = self.bot.townhalls.amount if hasattr(self.bot.townhalls, "amount") else 1

        # ★ 공통 쿨다운 체크 (모든 확장 시스템 공유) ★
        time_since_last = game_time - self._last_expansion_attempt_time
        if time_since_last < self._expansion_cooldown:
            return

        # ★ Blackboard 위협 체크: CRITICAL 위협 시 확장 중단 ★
        if self.blackboard:
            from blackboard import ThreatLevel
            if self.blackboard.threat.level >= ThreatLevel.CRITICAL:
                return

        # ★ PRIORITY 1: 강제 확장 (타이밍 초과 시) ★
        # 5초마다 한 번 (iteration % 110 ≈ 5초)
        if iteration % 110 == 0:
            await self._force_expansion_if_stuck()
            return  # 강제 확장 시도했으면 다른 확장 스킵

        # ★ PRIORITY 2: 타이밍 기반 사전 확장 ★
        await self._check_proactive_expansion()
        # proactive가 실제로 확장을 시도했는지 확인
        if game_time - self._last_expansion_attempt_time < 1.0:
            return  # 방금 확장 시도함

        # ★ PRIORITY 3: 자원 고갈 대비 확장 (3초마다) ★
        if iteration % 66 == 0:
            await self._check_expansion_on_depletion()
            if game_time - self._last_expansion_attempt_time < 1.0:
                return

        # ★ PRIORITY 4: 미래 자원 예측 확장 ★
        if iteration % 66 == 0:
            await self._predict_and_expand()

    async def _force_expansion_if_stuck(self) -> None:
        """
        ★ CRITICAL: 확장이 막혔을 때 강제 확장 ★
        
        Uses EconomyConfig.FORCE_EXPAND_TRIGGERS for table-driven logic.
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "time"):
            return

        game_time = self.bot.time
        townhalls = self.bot.townhalls
        base_count = townhalls.amount if hasattr(townhalls, "amount") else len(list(townhalls))
        minerals = getattr(self.bot, "minerals", 0)

        force_expand = False
        reason = ""

        # Table-driven check using EconomyConfig
        for time_req, min_req, target_bases in EconomyConfig.FORCE_EXPAND_TRIGGERS:
            # Check if condition met: Time passed AND Base count below target
            if game_time >= time_req and base_count < target_bases:
                # Check mineral requirement (0 means ignore minerals/critical)
                if min_req == 0 or minerals >= min_req:
                    force_expand = True
                    reason = f"{time_req}s Force Expand (Target: {target_bases} bases)"
                    # Keep checking later triggers? No, finding one valid trigger is enough logic-wise?
                    # The original code prioritized later (stricter) conditions, so we iterate all and keep the last one or just break?
                    # Actually, if any trigger matches, we force expand. The specific reason might matter for logging.
                    # We can pick the most urgent one. Since the list is sorted by time, later ones are more advanced.
                    # Let's use the matching one.
                    break 


        if not force_expand:
            return

        # ★ 비용 체크 (Config 기반) ★
        triggers = EconomyConfig.FORCE_EXPAND_TRIGGERS
        min_minerals = 300 # Default
        for time_req, min_req, target_bases in triggers:
             if game_time >= time_req and base_count < target_bases:
                 min_minerals = min_req

        if minerals < min_minerals:
            if int(game_time) % 30 == 0:
                print(f"[FORCE EXPAND] ★ {reason} BUT cannot afford (minerals: {minerals}/{min_minerals}) ★")
            return

        # ★ OPTIMIZED: 동시 확장 허용 (Config 기반) ★
        pending = getattr(self.bot, "already_pending", lambda x: 0)(UnitTypeId.HATCHERY)
        max_pending = EconomyConfig.MAX_PENDING_EXPANSIONS["DEFAULT"]
        
        if base_count < 2:
             if game_time > 60: max_pending = EconomyConfig.MAX_PENDING_EXPANSIONS["CRITICAL_RETRY"]
             else: max_pending = EconomyConfig.MAX_PENDING_EXPANSIONS["NATURAL_EMERGENCY"]
        elif base_count < 4 and game_time > 120:
             max_pending = EconomyConfig.MAX_PENDING_EXPANSIONS["DUAL_EXPAND"]
        elif game_time > 300:
             max_pending = EconomyConfig.MAX_PENDING_EXPANSIONS["TRIPLE_EXPAND"]

        # 이미 건설 중인 해처리가 max_pending 이상이면 중단
        if pending >= max_pending:
            if int(game_time) % 30 == 0:
                print(f"[FORCE EXPAND] {reason} but already expanding (pending: {pending}/{max_pending})")
            return

        # ★ 2026-01-26 FIX: 쿨다운 체크 (중복 시도 방지) ★
        time_since_last_attempt = game_time - self._last_expansion_attempt_time
        if time_since_last_attempt < self._expansion_cooldown:
            return  # 너무 최근에 시도했으면 스킵

        # ★ 강제 확장 실행 ★
        print(f"[FORCE EXPAND] ★★★ {reason} - FORCING EXPANSION NOW! ★★★")

        # ★ 2026-01-26 FIX: 확장 시도 시간 기록 ★
        self._last_expansion_attempt_time = game_time

        expansion_success = False
        try:
            if hasattr(self.bot, "expand_now"):
                result = await self.bot.expand_now()
                if result is not False:
                    print(f"[FORCE EXPAND] [{int(game_time)}s] {reason} - SUCCESS")
                    expansion_success = True
                else:
                    print(f"[FORCE EXPAND] expand_now returned False")
            else:
                # expand_now가 없으면 직접 위치 찾아서 건설
                # ★★★ USE GOLD PRIORITY ★★★
                expansion_locations = await self._get_best_expansion_with_gold_priority()
                if expansion_locations and hasattr(self.bot, "workers") and self.bot.workers:
                    worker = self.bot.workers.closest_to(expansion_locations)
                    if worker:
                        is_gold = self._is_gold_expansion(expansion_locations)
                        gold_marker = "💰 GOLD" if is_gold else ""
                        self.bot.do(worker.build(UnitTypeId.HATCHERY, expansion_locations))
                        print(f"[FORCE EXPAND] [{int(game_time)}s] Manual expansion {gold_marker} - SUCCESS")
                        expansion_success = True
        except Exception as e:
            print(f"[FORCE EXPAND] Failed: {e}")

        if not expansion_success:
            print(f"[FORCE EXPAND] ALL METHODS FAILED")

    async def _check_proactive_expansion(self) -> None:
        """
        Proactive expansion based on timing - 10분 안에 3베이스 확보.

        Timing targets:
        - Natural (2nd base): 30-60초 (드론 13-14마리 때)
        - 3rd base: 240-300초 (4-5분)
        - 4th base: 360-420초 (6-7분)

        Pro Zerg players expand PROACTIVELY, not reactively.
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "time"):
            return

        # ★ Blackboard Threat Check ★
        if self.blackboard:
            from blackboard import ThreatLevel
            # 위협이 높으면 확장 시도 중단 (안정성 우선)
            if self.blackboard.threat.level >= ThreatLevel.HIGH:
                if self.bot.iteration % 100 == 0:
                    print(f"[ECONOMY] Proactive expansion paused due to HIGH THREAT")
                return

        game_time = self.bot.time  # 게임 시간 (초)
        townhalls = self.bot.townhalls
        base_count = townhalls.amount if hasattr(townhalls, "amount") else len(list(townhalls))

        # ★★★ MAXIMUM FAST EXPANSION: 최대한 빠르고 많은 멀티 ★★★
        should_expand = False
        expand_reason = ""
        minerals = self.bot.minerals if hasattr(self.bot, "minerals") else 0

        # ★★★ CRITICAL: 4베이스 미만일 때 최우선 복구 (자원 균형 유지 필수) ★★★
        if base_count < 4 and game_time >= 120 and minerals >= 250:
            should_expand = True
            expand_reason = f"CRITICAL: Maintain 4+ bases! (current: {base_count}, time: {int(game_time)}s)"
            print(f"[ECONOMY_CRITICAL] {expand_reason}")
            # 바로 확장 실행 로직으로 이동 (아래 타이밍 조건 스킵)

        # 1베이스 → 2베이스 (내츄럴): ★★★ 빠르지만 안정적 (FAST & STABLE) ★★★
        if not should_expand and base_count == 1:
            worker_count = self.bot.workers.amount if hasattr(self.bot, "workers") else 0
            # ★★★ TARGET: 안정적인 확장 (자원 확보 후) ★★★
            # 해처리 건설 시간: 100초 (1분 40초)
            # 목표: 30초 안에 건설 시작 → 130초(2:10) 완성

            # ★ 개선: 미네랄 여유분 확보 후 확장 (350+ 또는 15드론+) ★
            if minerals >= 350:
                should_expand = True
                expand_reason = f"Natural with buffer @{int(game_time)}s (min 350+, workers: {worker_count})"
            # ★ 15드론 이상 + 미네랄 300+ (안정적 확장) ★
            elif worker_count >= 15 and minerals >= 300:
                should_expand = True
                expand_reason = f"15-Drone Natural @{int(game_time)}s (workers: {worker_count}, min 300+)"
            # ★ 30초 이후 + 미네랄 280+ (시간 기반 확장) ★
            elif game_time >= 30 and minerals >= 280:
                should_expand = True
                expand_reason = f"Timed Natural @{int(game_time)}s (min 280+, workers: {worker_count})"

        # ★ OPTIMIZED: 2베이스 → 3베이스 (1분 30초, 초공격적) ★
        elif not should_expand and base_count == 2:
            if game_time >= 90 or minerals >= 400:  # ★ 120→90, 500→400 ★
                should_expand = True
                expand_reason = f"3rd base ULTRA-FAST (time: {int(game_time)}s, minerals: {minerals})"

        # ★ CRITICAL: 3베이스 → 4베이스 (최소 4개 필수 - 자원 균형 유지) ★
        elif not should_expand and base_count == 3:
            # ★ 4베이스는 반드시 확보: 더 빠르고 공격적으로 ★
            if game_time >= 120 or minerals >= 400:  # ★ 135→120, 450→400 (더 빠르게) ★
                should_expand = True
                expand_reason = f"4th base CRITICAL (MINIMUM 4 BASES FOR BALANCE - time: {int(game_time)}s, minerals: {minerals})"

        # ★ OPTIMIZED: 4베이스 → 5베이스 (3분, 5베이스 경제) ★
        elif not should_expand and base_count == 4:
            if game_time >= 180 or minerals >= 500:  # ★ 240→180, 700→500 ★
                should_expand = True
                expand_reason = f"5th base FAST (time: {int(game_time)}s, minerals: {minerals})"

        # ★ OPTIMIZED: 5베이스 → 6베이스 (3분 30초) ★
        elif not should_expand and base_count == 5:
            if game_time >= 210 or minerals >= 550:  # ★ 270→210, 700→550 ★
                should_expand = True
                expand_reason = f"6th base MACRO (time: {int(game_time)}s, minerals: {minerals})"

        # ★ OPTIMIZED: 6베이스 → 7베이스 (4분) ★
        elif not should_expand and base_count == 6:
            if game_time >= 240 or minerals >= 600:  # ★ 330→240, 800→600 ★
                should_expand = True
                expand_reason = f"7th base MACRO (time: {int(game_time)}s, minerals: {minerals})"

        # ★ 7베이스 이상: 무한 확장 (60초마다 또는 미네랄 900+ 저장) ★
        elif not should_expand and base_count >= 7:
            # 마지막 확장 시간 추적
            if not hasattr(self, "_last_expansion_time"):
                self._last_expansion_time = game_time

            time_since_last = game_time - self._last_expansion_time
            if time_since_last >= 60 or minerals > 900:
                should_expand = True
                expand_reason = f"Infinite Expansion #{base_count + 1} (time: {int(game_time)}s, minerals: {minerals})"
                self._last_expansion_time = game_time

        if not should_expand:
            return

        # ★ 2026-01-26 FIX: 쿨다운 체크 (중복 시도 방지) ★
        time_since_last_attempt = game_time - self._last_expansion_attempt_time
        if time_since_last_attempt < self._expansion_cooldown:
            return  # 너무 최근에 시도했으면 스킵

        # ★ DEBUG: 확장 시도 로그 ★
        print(f"[EXPANSION] [{int(game_time)}s] Trying to expand: {expand_reason}")

        # ★ 2026-01-26 FIX: 확장 시도 시간 기록 (시도할 때마다) ★
        self._last_expansion_attempt_time = game_time

        # ★ ULTRA-FAST EXPANSION: 동시 확장 허용 - 앞마당은 무조건 우선 ★
        if hasattr(self.bot, "already_pending"):
            pending = self.bot.already_pending(UnitTypeId.HATCHERY)
            # 앞마당(1->2베이스)은 최대 2개까지 허용 (일꾼 사망 대비)
            # 그 외는 미네랄에 따라 동시 건설 허용
            if base_count == 1:
                max_pending = 2  # 앞마당은 2개까지 동시 시도
            else:
                max_pending = 3 if minerals > 1000 else 2 if minerals > 600 else 1
            if pending >= max_pending:
                print(f"[EXPANSION] [{int(game_time)}s] Already {pending} pending, max is {max_pending}")
                return

        # 비용 확인
        if not self.bot.can_afford(UnitTypeId.HATCHERY):
            # ★ 미네랄 부족 시 더 긴 쿨다운 설정 (20초) ★
            self._last_expansion_attempt_time = game_time + 14.0  # 6초 기본 + 14초 = 20초 총 대기
            # ★ 로그 스팸 방지: 30초마다만 출력 ★
            if int(game_time) % 30 < 2:  # 30초 주기로 2초 이내에만 출력
                print(f"[EXPANSION] [{int(game_time)}s] Cannot afford Hatchery (need 300 minerals, have {minerals}) - waiting 20s")
            return

        # ★ MACRO ECONOMY: 비상 모드여도 확장 계속 (매크로 최우선) ★
        # ★ 심각한 위협만 확장 차단: 본진 근처 15거리에 적 15+ 유닛 ★
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and getattr(strategy, "emergency_active", False):
            if hasattr(self.bot, "enemy_units") and self.bot.townhalls.exists:
                main_base = self.bot.townhalls.first
                nearby_enemies = self.bot.enemy_units.closer_than(15, main_base)
                # ★ 극심한 위협만 확장 차단 (적 15명 이상) ★
                if nearby_enemies.amount >= 15:
                    if int(game_time) % 30 == 0:  # 30초마다만 로그
                        print(f"[EXPANSION] [{int(game_time)}s] ★ SEVERE THREAT: {nearby_enemies.amount} enemies - expansion blocked ★")
                    return  # 심각한 위협: 확장 중단

        # ★ 그 외 모든 경우: 확장 계속 (매크로 경제 우선) ★

        # ★ 확장 실행 - bot.expand_now() 우선 사용 (안정적) ★
        expansion_success = False

        try:
            # 방법 1: expand_now 우선 사용 (가장 안정적)
            if hasattr(self.bot, "expand_now"):
                result = await self.bot.expand_now()
                # expand_now()가 성공하면 None 또는 True 반환
                if result is not False:  # False가 아니면 성공으로 간주
                    print(f"[PROACTIVE EXPAND] [{int(game_time)}s] {expand_reason} - SUCCESS")
                    expansion_success = True
                else:
                    print(f"[EXPAND] expand_now returned False (no valid location?)")
        except Exception as e:
            print(f"[EXPAND] expand_now failed: {e}")

        if not expansion_success:
            try:
                # 방법 2: 황금 기지 우선 확장 시도
                gold_pos = await self._get_best_expansion_with_gold_priority()
                if gold_pos and hasattr(self.bot, "workers") and self.bot.workers:
                    worker = self.bot.workers.closest_to(gold_pos)
                    if worker and not worker.is_constructing_scv:
                        worker.build(UnitTypeId.HATCHERY, gold_pos)
                        is_gold = self._is_gold_expansion(gold_pos)
                        gold_tag = " [GOLD!]" if is_gold else ""
                        print(f"[PROACTIVE EXPAND] [{int(game_time)}s] {expand_reason}{gold_tag} - SUCCESS")
                        expansion_success = True
            except Exception as e:
                print(f"[EXPAND] Gold expansion failed: {e}")

        if not expansion_success:
            print(f"[EXPAND] ALL METHODS FAILED - Check bot state")

    async def _get_hidden_expansion_location(self) -> Optional[Point2]:
        """
        Find a "Hidden Base" location far from enemy.
        """
        if not hasattr(self.bot, "expansion_locations_list") or not self.bot.expansion_locations_list:
            return None

        enemy_start = self.bot.enemy_start_locations[0] if self.bot.enemy_start_locations else self.bot.game_info.map_center
        start_loc = self.bot.start_location

        # Filter out taken bases
        available_bases = []
        for loc in self.bot.expansion_locations_list:
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.closer_than(4, loc).exists:
                continue # We already have this
            if hasattr(self.bot, "enemy_structures") and self.bot.enemy_structures.closer_than(10, loc).exists:
                continue # Enemy has this

            available_bases.append(loc)

        if not available_bases:
            return None

        # Score: Distance from enemy start + Distance from our start (to be "hidden" usually means far from action)
        # But for Rogue style, maybe just far from enemy?
        # Let's prioritize: Furthest from Enemy Start
        best_loc = max(available_bases, key=lambda p: p.distance_to(enemy_start))
        
        return best_loc

    async def _perform_smart_expansion(self, reason: str, force_hidden: bool = False) -> bool:
        """
        Execute expansion using smart logic.
        
        Priority:
        1. Hidden Base (if force_hidden is True)
        2. Gold Base (if safe)
        3. Standard Expansion
        """
        try:
            target_pos = None
            method = "Standard"

            # 1. Hidden Base
            if force_hidden:
                target_pos = await self._get_hidden_expansion_location()
                if target_pos:
                    method = "Hidden"
            
            # 2. Gold / Safe Base
            if not target_pos:
                target_pos = await self._get_best_expansion_with_gold_priority()
                if target_pos:
                    if self._is_gold_expansion(target_pos):
                        method = "Gold"
                    else:
                        method = "Safe/Standard"

            # 3. Fallback to default
            if not target_pos:
                target_pos = await self.bot.get_next_expansion()
                method = "Default"

            if target_pos:
                # ★ Reserve resources using ResourceManager (thread-safe) ★
                reserved = False
                if hasattr(self.bot, 'resource_manager') and self.bot.resource_manager:
                    reserved = await self.bot.resource_manager.try_reserve(
                        300, 0, "EconomyManager_Expansion"
                    )
                    if not reserved:
                        # Resources not available (reserved by other manager)
                        return False

                if await self.bot.can_place(UnitTypeId.HATCHERY, target_pos):
                    # Use TechCoordinator if available, else direct build
                    tech_coordinator = getattr(self.bot, "tech_coordinator", None)
                    if tech_coordinator:
                        tech_coordinator.request_structure(
                            UnitTypeId.HATCHERY,
                            target_pos,
                            priority=100, # High priority
                            requester="EconomyManager"
                        )
                    else:
                        worker = self.bot.workers.closest_to(target_pos)
                        if worker:
                            self.bot.do(worker.build(UnitTypeId.HATCHERY, target_pos))
                    
                    game_time = getattr(self.bot, "time", 0)
                    print(f"[ECONOMY] [{int(game_time)}s] ★ Expanding ({method}): {reason} @ {target_pos} ★")

                    # ★ Release resources after successful build command ★
                    if reserved and hasattr(self.bot, 'resource_manager') and self.bot.resource_manager:
                        await self.bot.resource_manager.release("EconomyManager_Expansion")

                    return True
                else:
                    # ★ Release resources if placement failed ★
                    if reserved and hasattr(self.bot, 'resource_manager') and self.bot.resource_manager:
                        await self.bot.resource_manager.release("EconomyManager_Expansion")

        except Exception as e:
            print(f"[ECONOMY] Smart expansion failed: {e}")
            # ★ Release resources on exception ★
            if hasattr(self.bot, 'resource_manager') and self.bot.resource_manager:
                try:
                    await self.bot.resource_manager.release("EconomyManager_Expansion")
                except Exception:
                    pass

        return False

    async def _check_expansion_on_depletion(self) -> None:
        """
        Check if we need to expand due to resource depletion.

        ★ IMPROVED: 자원 고갈 사전 감지 및 조기 확장 ★

        Triggers expansion if:
        - Total remaining minerals across bases < threshold
        - Worker saturation is high but income is dropping
        - No expansion currently pending
        - ★ NEW: 특정 기지의 미네랄이 50% 미만일 때 미리 확장
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "mineral_field"):
            return

        townhalls = self.bot.townhalls.ready
        if not townhalls:
            return

        try:
            # Calculate total remaining minerals across all bases
            total_remaining_minerals = 0
            depleted_base_count = 0
            low_mineral_base_count = 0  # ★ 미네랄 50% 미만 기지 ★

            for th in townhalls:
                nearby_minerals = self.bot.mineral_field.closer_than(10, th)
                base_minerals = sum(m.mineral_contents for m in nearby_minerals) if nearby_minerals else 0
                total_remaining_minerals += base_minerals

                if base_minerals < 500:  # Less than 500 minerals = depleted
                    depleted_base_count += 1
                elif base_minerals < 3000:  # ★ 3000 미만 = 50% 고갈 (full은 ~6000) ★
                    low_mineral_base_count += 1

            # Calculate threshold based on worker count
            worker_count = self.bot.workers.amount if hasattr(self.bot, "workers") else 0
            # Need ~1500 minerals per 16 workers for decent income
            mineral_threshold_per_worker = 100
            expansion_threshold = worker_count * mineral_threshold_per_worker

            # Check if we need to expand
            should_expand = False
            expand_reason = ""

            # ★ NEW: Reason 0: 미네랄 50% 미만 기지가 있으면 사전 확장 ★
            if low_mineral_base_count >= 1 and townhalls.amount >= 2:
                should_expand = True
                expand_reason = f"PREEMPTIVE: {low_mineral_base_count} bases below 50% minerals"

            # Reason 1: Total minerals running low
            if total_remaining_minerals < expansion_threshold and total_remaining_minerals < 5000:
                should_expand = True
                expand_reason = f"low minerals ({int(total_remaining_minerals)} remaining)"

            # Reason 2: Multiple depleted bases
            if depleted_base_count >= townhalls.amount // 2 and townhalls.amount > 1:
                should_expand = True
                expand_reason = f"{depleted_base_count}/{townhalls.amount} bases depleted"

            # Reason 3: High worker count but low base count
            # Optimal: ~16 workers per base
            optimal_bases = max(1, worker_count // 16)
            if townhalls.amount < optimal_bases:
                should_expand = True
                expand_reason = f"need more bases for {worker_count} workers"

            # ★ NEW: Reason 4: 일꾼이 포화인데 기지가 부족 ★
            if hasattr(self.bot, "townhalls"):
                total_ideal = sum(th.ideal_harvesters for th in townhalls)
                if worker_count >= total_ideal * 0.9 and townhalls.amount < 5:
                    should_expand = True
                    expand_reason = f"workers saturated ({worker_count}/{total_ideal}), need more bases"

            if not should_expand:
                return

            # ★ CRITICAL: 앞마당 없으면 무조건 확장 (시간 단축) ★
            game_time = getattr(self.bot, "time", 0)
            minerals = getattr(self.bot, "minerals", 0)

            # 2분 지났는데 앞마당 없으면 즉시 확장 (미네랄 600+ - 안정적 확장)
            if townhalls.amount < 2 and game_time > 120 and minerals >= 600:
                print(f"[ECONOMY] ★ CRITICAL EXPANSION: Forcing natural expansion @ {int(game_time)}s (minerals: {minerals}) ★")
                if hasattr(self.bot, "expand_now"):
                    try:
                        await self.bot.expand_now()
                        print(f"[ECONOMY] ★ Natural expansion started successfully! ★")
                    except Exception as e:
                        print(f"[ECONOMY] ★ Expansion failed: {e} ★")
                return

            # ★ FAST EXPANSION: 동시 확장 허용 ★
            # Check if already expanding (최대 2개까지 허용)
            pending = self.bot.already_pending(UnitTypeId.HATCHERY)
            minerals = self.bot.minerals if hasattr(self.bot, "minerals") else 0
            max_pending = 2 if minerals > 800 else 1
            if pending >= max_pending:
                return

            # Check if we can afford expansion (안정성: 600 미네랄 확보 후 확장)
            minerals = getattr(self.bot, "minerals", 0)
            if minerals < 600:
                return

            # ★ MACRO ECONOMY: 공격 받아도 확장 계속 (심각한 위협만 차단) ★
            strategy = getattr(self.bot, "strategy_manager", None)
            if strategy and getattr(strategy, "emergency_active", False):
                # 심각한 위협만 확장 차단 (본진에 적 10+ 유닛)
                if hasattr(self.bot, "enemy_units") and townhalls.exists:
                    main_base = townhalls.first
                    nearby_enemies = self.bot.enemy_units.closer_than(15, main_base)
                    if nearby_enemies.amount >= 10 and depleted_base_count < townhalls.amount // 2:
                        return  # 심각한 위협 + 자원 여유: 확장 중단
                # 경미한 위협 또는 자원 부족: 확장 계속

            # Check for hidden base condition (Late game + Pressure)
            force_hidden = False
            if game_time > 600 and depleted_base_count > 0:
                 force_hidden = True # Try to take a hidden base if we are losing main bases

            # Execute Smart Expansion
            await self._perform_smart_expansion(expand_reason, force_hidden=force_hidden)

        except (AttributeError, TypeError, ValueError) as e:
            # Smart expansion failed
            pass

    async def _manual_expansion(self, game_time: float, reason: str) -> None:
        """
        ★ 수동 확장: 직접 확장 위치를 찾아서 일꾼 보내기 ★

        expand_now()가 실패할 때 사용하는 폴백 방법
        ★★★ IMPROVED: Gold base priority ★★★
        """
        if not hasattr(self.bot, "workers") or not self.bot.workers:
            print(f"[MANUAL EXPAND] No workers available!")
            return

        # 확장 가능한 위치 찾기
        try:
            # ★★★ USE GOLD PRIORITY ★★★
            expansion_locations = await self._get_best_expansion_with_gold_priority()
            if not expansion_locations:
                print(f"[MANUAL EXPAND] No expansion locations found!")
                return

            # 가장 가까운 일꾼 찾기
            worker = self.bot.workers.closest_to(expansion_locations)
            if not worker:
                print(f"[MANUAL EXPAND] No worker found!")
                return

            # 해처리 건설 명령
            is_gold = self._is_gold_expansion(expansion_locations)
            gold_marker = "💰 GOLD" if is_gold else ""
            self.bot.do(worker.build(UnitTypeId.HATCHERY, expansion_locations))
            print(f"[MANUAL EXPAND] [{int(game_time)}s] ★ {reason} {gold_marker} ★ (Manual expansion)")

        except Exception as e:
            print(f"[MANUAL EXPAND] Exception: {e}")

    def _is_gold_expansion(self, position) -> bool:
        """
        Check if an expansion location has gold minerals.

        Gold patches have ~1500 minerals vs normal ~900.
        """
        if not hasattr(self.bot, "mineral_field"):
            return False

        try:
            nearby_minerals = self.bot.mineral_field.closer_than(10, position)
            if not nearby_minerals:
                return False

            # Check if any mineral patch is gold (>1200 minerals)
            for mineral in nearby_minerals:
                if mineral.mineral_contents > self.GOLD_MINERAL_THRESHOLD:
                    return True
            return False
        except (AttributeError, TypeError) as e:
            # Gold mineral check failed
            return False

    def _get_gold_expansion_locations(self) -> list:
        """
        Get all expansion locations with gold minerals.

        Returns list of (position, gold_mineral_count) tuples sorted by priority.
        """
        if not hasattr(self.bot, "expansion_locations_list"):
            return []

        current_time = getattr(self.bot, "time", 0)

        # 캐시 사용 (30초마다 갱신)
        if current_time - self._gold_cache_time < 30 and self._gold_bases_cache:
            return self._gold_bases_cache

        gold_expansions = []

        try:
            # Get already taken expansion positions
            taken_positions = set()
            if hasattr(self.bot, "townhalls"):
                for th in self.bot.townhalls:
                    taken_positions.add(th.position)

            # Check enemy bases
            enemy_expansions = set()
            if hasattr(self.bot, "enemy_structures"):
                for struct in self.bot.enemy_structures:
                    if hasattr(struct, "is_structure") and struct.is_structure:
                        enemy_expansions.add(struct.position)

            for exp_pos in self.bot.expansion_locations_list:
                # Skip already taken positions
                if any(exp_pos.distance_to(taken) < 5 for taken in taken_positions):
                    continue

                # Skip enemy positions
                if any(exp_pos.distance_to(enemy) < 10 for enemy in enemy_expansions):
                    continue

                # Check for gold minerals
                nearby_minerals = self.bot.mineral_field.closer_than(10, exp_pos)
                if not nearby_minerals:
                    continue

                gold_count = 0
                total_minerals = 0
                for mineral in nearby_minerals:
                    if mineral.mineral_contents > self.GOLD_MINERAL_THRESHOLD:
                        gold_count += 1
                    total_minerals += mineral.mineral_contents

                if gold_count > 0:
                    # Priority: gold count * 1000 + total minerals
                    priority = gold_count * 1000 + total_minerals
                    gold_expansions.append((exp_pos, gold_count, total_minerals, priority))

            # Sort by priority (highest first)
            gold_expansions.sort(key=lambda x: x[3], reverse=True)

            # Cache results
            self._gold_bases_cache = gold_expansions
            self._gold_cache_time = current_time

            return gold_expansions

        except (AttributeError, TypeError, ValueError) as e:
            # Finding gold expansions failed
            return []

    async def _get_best_expansion_with_gold_priority(self):
        """
        Get the best expansion location, prioritizing gold bases.

        Priority order:
        1. Gold base closest to our main base (safe gold)
        2. Normal expansion from get_next_expansion()
        """
        if not hasattr(self.bot, "start_location"):
            return None

        try:
            our_base = self.bot.start_location
            enemy_base = None
            if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                enemy_base = self.bot.enemy_start_locations[0]

            # Get gold expansion locations
            gold_expansions = self._get_gold_expansion_locations()

            if gold_expansions:
                # Calculate safety score for each gold base
                best_gold = None
                best_score = float('-inf')

                for exp_pos, gold_count, total_minerals, _ in gold_expansions:
                    # Safety score: closer to our base is safer
                    dist_to_us = exp_pos.distance_to(our_base)
                    dist_to_enemy = exp_pos.distance_to(enemy_base) if enemy_base else 100

                    # Score: prefer closer to us, farther from enemy
                    # Gold count bonus: +50 per gold patch
                    safety_score = (dist_to_enemy - dist_to_us) + (gold_count * 50)

                    # Early game (< 5 minutes): prioritize safety more
                    game_time = getattr(self.bot, "time", 0)
                    if game_time < 300:  # 5분 이전
                        # Only consider if closer to us than enemy
                        if dist_to_us < dist_to_enemy:
                            if safety_score > best_score:
                                best_score = safety_score
                                best_gold = exp_pos
                    else:
                        # After 5 minutes: can take riskier gold bases
                        if safety_score > best_score:
                            best_score = safety_score
                            best_gold = exp_pos

                if best_gold:
                    # Verify we can place hatchery there
                    if hasattr(self.bot, "can_place"):
                        if await self.bot.can_place(UnitTypeId.HATCHERY, best_gold):
                            return best_gold

            # Fallback: use standard expansion
            if hasattr(self.bot, "get_next_expansion"):
                return await self.bot.get_next_expansion()

            return None

        except (AttributeError, TypeError, ValueError) as e:
            # Finding safe expansion failed - fallback on error
            if hasattr(self.bot, "get_next_expansion"):
                return await self.bot.get_next_expansion()
            return None

    # ============================================================
    # ★★★ 자원 관리 최적화 시스템 ★★★
    # ============================================================

    async def _prevent_resource_banking(self) -> None:
        """
        ★ 자원 낭비 방지 ★

        미네랄/가스가 과잉 축적되면 추가 생산 구조물 건설:
        - 미네랄 1000+ & 라바 부족 → 매크로 해처리
        - 미네랄 2000+ → 확장 또는 테크 업그레이드
        - 가스 500+ & 미네랄 부족 → 가스 일꾼 감소
        """
        if not hasattr(self.bot, "minerals") or not hasattr(self.bot, "vespene"):
            return

        minerals = self.bot.minerals
        gas = self.bot.vespene
        game_time = getattr(self.bot, "time", 0)

        # ★ Blackboard Check for Safe Phase ★
        is_opening_unsafe = False
        if self.blackboard:
            from blackboard import GamePhase, ThreatLevel
            if self.blackboard.game_phase == GamePhase.OPENING:
                 if self.blackboard.threat.level >= ThreatLevel.MEDIUM:
                     is_opening_unsafe = True

        if is_opening_unsafe and minerals < 2000:
             return # 오프닝 위협 시 자원 보존 (방어 유닛용)

        try:
            # ★ 미네랄 과잉 (1000+) ★
            if minerals > 1000:
                # 라바 부족 체크
                larva_count = 0
                if hasattr(self.bot, "larva"):
                    larva_count = self.bot.larva.amount if hasattr(self.bot.larva, "amount") else len(self.bot.larva)

                hatch_count = self.bot.townhalls.amount if hasattr(self.bot, "townhalls") else 1
                avg_larva = larva_count / max(1, hatch_count)

                # 미네랄 과잉 로그 (30초마다)
                if int(game_time) % 30 == 0 and self.bot.iteration % 22 == 0:
                    print(f"[ECONOMY] [{int(game_time)}s] Resource banking: {minerals}M / {gas}G")
                    print(f"[ECONOMY]   Larva: {larva_count}, Avg per base: {avg_larva:.1f}")

                # ★★★ IMPROVED: 미네랄 과잉 → 스마트 확장 ★★★
                # 2000+ → 1500+ 로 완화하여 더 빨리 확장
                if minerals > 1500:
                    if hatch_count < 8 and self.bot.already_pending(UnitTypeId.HATCHERY) == 0:
                         await self._perform_smart_expansion(f"Resource banking (M:{minerals}/G:{gas})")

                # 미네랄 1500+ & 라바 부족 → 매크로 해처리
                elif minerals > 1500 and avg_larva < 3:
                    await self._build_macro_hatchery_if_needed()

            # ★ 가스 과잉 & 미네랄 부족 ★
            if gas > 500 and minerals < 300:
                # 가스 일꾼 감소 (3명 → 2명)
                await self._reduce_gas_workers()

            # ★★★ IMPROVED: 미네랄 과잉 & 가스 부족 → 가스 확장 + 전체 확장 ★★★
            if minerals > 800 and gas < 100:
                await self._build_extractors()

            # ★★★ NEW: 자원 비율 불균형 감지 (M/G 비율) ★★★
            # 미네랄:가스 비율이 10:1 이상이면 확장 또는 가스 추가
            if gas > 0 and minerals / max(1, gas) > 10:
                if minerals > 1000:
                    # 확장으로 전체 자원 증가
                    if hatch_count < 8 and self.bot.already_pending(UnitTypeId.HATCHERY) == 0:
                        await self._perform_smart_expansion(f"Resource ratio (M/G = {minerals}/{gas} = {minerals/max(1,gas):.1f})")

        except Exception as e:
            if self.bot.iteration % 200 == 0:
                print(f"[ECONOMY] Resource banking prevention error: {e}")

    def _update_resource_reservations(self) -> None:
        """
        자원 예약 업데이트

        NOTE: This uses legacy _reserved_minerals/_reserved_gas for fallback.
        For proper thread-safe reservation, use self.bot.resource_manager.try_reserve()
        in async contexts. This function is kept for backward compatibility.
        """
        game_time = getattr(self.bot, "time", 0)
        self._reserved_minerals = 0
        self._reserved_gas = 0

        # 2:50-3:10: 스포어 예약
        if 170 <= game_time < 190:
            spores = self.bot.structures(UnitTypeId.SPORECRAWLER)
            spore_count = spores.amount if hasattr(spores, "amount") else 0
            if spore_count == 0:
                self._reserved_minerals = 75

        # 3:20-3:40: 레어 예약
        elif 200 <= game_time < 220:
            lairs = self.bot.structures(UnitTypeId.LAIR)
            if not lairs.exists:
                self._reserved_minerals = 150
                self._reserved_gas = 100

    async def _reduce_gas_workers(self) -> None:
        """가스 일꾼 감소 (과잉 가스 방지)"""
        try:
            if not hasattr(self.bot, "gas_buildings") or not self.bot.gas_buildings.ready:
                return

            for extractor in self.bot.gas_buildings.ready:
                if extractor.assigned_harvesters >= 3:
                    # 가스에서 일꾼 1명 이동
                    workers_on_gas = self.bot.workers.filter(
                        lambda w: w.is_gathering and w.order_target == extractor.tag
                    )
                    if workers_on_gas:
                        worker = workers_on_gas.first
                        # 가까운 미네랄로 이동
                        closest_mineral = self.bot.mineral_field.closest_to(worker)
                        if closest_mineral:
                            self.bot.do(worker.gather(closest_mineral))
                            return  # 한 번에 하나만

        except (AttributeError, TypeError) as e:
            # Early expansion failed
            pass

    async def _build_extractors(self) -> None:
        """가스 익스트랙터 건설 (가스 부족 시)"""
        try:
            if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.ready:
                return

            if not self.bot.can_afford(UnitTypeId.EXTRACTOR):
                return

            for th in self.bot.townhalls.ready:
                # 해당 기지 근처 가스 체크
                vespene_geysers = self.bot.vespene_geyser.closer_than(10, th)

                for geyser in vespene_geysers:
                    # 이미 익스트랙터가 있는지 체크
                    if self.bot.gas_buildings.closer_than(1, geyser).exists:
                        continue

                    # 건설 가능 여부 체크
                    workers = self.bot.workers.closer_than(20, geyser)
                    if workers:
                        worker = workers.closest_to(geyser)
                        self.bot.do(worker.build_gas(geyser))
                        print(f"[ECONOMY] Building extractor (gas shortage)")
                        return  # 한 번에 하나만

        except (AttributeError, TypeError, ValueError) as e:
            # Extractor building failed
            pass

    async def _optimize_gas_timing(self) -> None:
        """
        ★★★ Phase 18: 가스 타이밍 최적화 (종족별) ★★★

        종족별 가스 타이밍:
        - vs Terran: 1분 30초 (중간)
        - vs Protoss: 1분 15초 (빠름 - 프로토스 초반 올인 대비)
        - vs Zerg: 1분 45초 (느림 - 드론 펌핑 우선)

        가스 부스트 모드: 빠른 테크가 필요할 때 (뮤탈, 히드라 등)
        가스 오버플로우 방지: 3000+ 가스 시 일꾼 회수
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.ready:
            return

        game_time = getattr(self.bot, "time", 0)

        # ★★★ Phase 18: 종족별 가스 타이밍 ★★★
        enemy_race = getattr(self.bot, "enemy_race", None)
        race_name = str(enemy_race).split(".")[-1] if enemy_race else "Unknown"

        optimal_gas_timing = self.gas_timing_by_race.get(race_name, 90)

        # ★★★ Phase 18: 가스 부스트 모드 ★★★
        if self.gas_boost_mode:
            optimal_gas_timing = max(60, optimal_gas_timing - 15)  # 15초 빠르게

        try:
            # ★ 첫 가스 타이밍 (종족별 최적화) ★
            if game_time >= optimal_gas_timing and game_time < optimal_gas_timing + 30:
                # 첫 가스 확인
                if not hasattr(self.bot, "gas_buildings") or self.bot.gas_buildings.amount == 0:
                    if self.bot.already_pending(UnitTypeId.EXTRACTOR) == 0:
                        if self.bot.can_afford(UnitTypeId.EXTRACTOR):
                            await self._build_extractors()
                            print(f"[ECONOMY] [{int(game_time)}s] ★ First gas timing (vs {race_name}) ★")

            # ★ 두 번째 가스 타이밍 (2분) ★
            elif game_time >= 120 and game_time < 150:  # 2분-2분30초
                gas_count = self.bot.gas_buildings.amount if hasattr(self.bot, "gas_buildings") else 0
                pending_gas = self.bot.already_pending(UnitTypeId.EXTRACTOR)

                if gas_count + pending_gas < 2:
                    if self.bot.can_afford(UnitTypeId.EXTRACTOR):
                        await self._build_extractors()
                        print(f"[ECONOMY] [{int(game_time)}s] ★ Second gas timing ★")

            # ★ 확장 가스 (4분 이후) ★
            elif game_time >= 240:
                # 모든 기지에 가스 건설 확인
                if hasattr(self.bot, "townhalls"):
                    for th in self.bot.townhalls.ready:
                        vespene_geysers = self.bot.vespene_geyser.closer_than(10, th)
                        extractors_near = self.bot.gas_buildings.closer_than(10, th) if hasattr(self.bot, "gas_buildings") else []

                        # 가이저가 있고 익스트랙터가 부족하면 건설
                        if vespene_geysers.amount > len(extractors_near):
                            if self.bot.can_afford(UnitTypeId.EXTRACTOR):
                                for geyser in vespene_geysers:
                                    if not self.bot.gas_buildings.closer_than(1, geyser).exists:
                                        workers = self.bot.workers.closer_than(20, geyser)
                                        if workers:
                                            worker = workers.closest_to(geyser)
                                            self.bot.do(worker.build_gas(geyser))
                                            return

        except Exception as e:
            pass

    def get_resource_status(self) -> dict:
        """현재 자원 상태 반환"""
        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)
        workers = self.bot.workers.amount if hasattr(self.bot, "workers") else 0
        bases = self.bot.townhalls.amount if hasattr(self.bot, "townhalls") else 0

        return {
            "minerals": minerals,
            "gas": gas,
            "workers": workers,
            "bases": bases,
            "mineral_income": workers * 40,  # 대략적 수입
            "gas_income": min(bases * 6, workers // 3) * 35,
            "is_banking": minerals > 1000 or gas > 500,
        }

    # ============================================================
    # ★★★ 경제 회복 시스템 (병력 생산 후 자원 재건) ★★★
    # ============================================================

    async def check_economic_recovery(self) -> None:
        """
        ★ 경제 회복 체크 ★

        병력 생산으로 자원이 소진되면:
        1. 드론 수 확인 → 부족하면 드론 생산 우선
        2. 확장 필요 여부 확인 → 포화 시 확장
        3. 미래 수입 예측 → 미리 확장/드론 생산

        호출 시점: 매 스텝 또는 전투 후
        """
        if not hasattr(self.bot, "workers") or not hasattr(self.bot, "townhalls"):
            return

        game_time = getattr(self.bot, "time", 0)
        workers = self.bot.workers
        bases = self.bot.townhalls.ready
        minerals = getattr(self.bot, "minerals", 0)

        # ★ 현재 경제 상태 분석 ★
        worker_count = workers.amount
        base_count = bases.amount
        ideal_workers = base_count * 16 + (base_count * 6)  # 미네랄 16 + 가스 6

        # ★ 드론 부족 감지 ★
        worker_deficit = ideal_workers - worker_count

        if worker_deficit > 5:
            # 드론 심각하게 부족 → 드론 생산 우선 모드
            self._economy_recovery_mode = True
            self._target_drone_count = min(ideal_workers, 75)

            if int(game_time) % 20 == 0 and self.bot.iteration % 22 == 0:
                print(f"[ECONOMY RECOVERY] [{int(game_time)}s] ★ Worker deficit: {worker_deficit} ★")
                print(f"[ECONOMY RECOVERY]   Current: {worker_count}, Ideal: {ideal_workers}")
                print(f"[ECONOMY RECOVERY]   Prioritizing drone production...")

        elif worker_deficit <= 0:
            # 드론 포화 → unified expansion이 처리
            self._economy_recovery_mode = False

    async def _trigger_expansion_for_growth(self) -> None:
        """
        포화 시 확장 건설

        ★★★ IMPROVED: Gold Base 우선순위 통합 ★★★
        - Gold base 최우선 선택
        - 전략적 위치 선정 (안전성 + 자원 가치)
        """
        if not hasattr(self.bot, "townhalls"):
            return

        game_time = getattr(self.bot, "time", 0)
        base_count = self.bot.townhalls.amount
        pending = self.bot.already_pending(UnitTypeId.HATCHERY)

        # 확장 제한: 최대 6베이스
        if base_count + pending >= 6:
            return

        # 자원 여유 체크 (확장 비용 300)
        if self.bot.minerals < 350:
            return

        try:
            # ★★★ USE GOLD PRIORITY EXPANSION LOGIC ★★★
            exp_pos = await self._get_best_expansion_with_gold_priority()
            if exp_pos:
                if await self.bot.can_place(UnitTypeId.HATCHERY, exp_pos):
                    # Check if it's a gold base
                    is_gold = self._is_gold_expansion(exp_pos)
                    gold_marker = "💰 GOLD" if is_gold else "Normal"

                    await self.bot.build(UnitTypeId.HATCHERY, exp_pos)
                    print(f"[ECONOMY RECOVERY] [{int(game_time)}s] ★ Expanding for growth ({gold_marker}, bases: {base_count}) ★")
        except (AttributeError, TypeError, ValueError) as e:
            # Expansion building failed
            pass

    async def _predict_and_expand(self) -> None:
        """
        ★ 미래 수입 예측 및 사전 확장 ★

        미네랄 패치 고갈 예측:
        - 현재 채취 속도와 남은 미네랄 양 비교
        - 고갈 예상 시 미리 확장
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.ready:
            return

        game_time = getattr(self.bot, "time", 0)

        try:
            for th in self.bot.townhalls.ready:
                # 해당 기지 근처 미네랄 체크
                minerals_near = self.bot.mineral_field.closer_than(10, th)

                if not minerals_near:
                    continue

                # 총 남은 미네랄 양
                total_remaining = sum(m.mineral_contents for m in minerals_near)

                # 일꾼 수 기반 채취 속도 추정 (일꾼당 ~40/분)
                workers_at_base = th.assigned_harvesters
                mining_rate = workers_at_base * 40  # 분당

                # 고갈 예상 시간 (분)
                if mining_rate > 0:
                    depletion_time = total_remaining / mining_rate
                else:
                    depletion_time = 999

                # 2분 내 고갈 예상 시 확장 (확장 건설에 1분 30초 소요)
                if depletion_time < 2.0 and total_remaining < 2000:
                    base_count = self.bot.townhalls.amount
                    pending = self.bot.already_pending(UnitTypeId.HATCHERY)

                    if pending == 0 and base_count < 5:
                        if int(game_time) % 30 == 0 and self.bot.iteration % 22 == 0:
                            print(f"[ECONOMY PREDICTION] [{int(game_time)}s] Base depleting in {depletion_time:.1f} min")
                            print(f"[ECONOMY PREDICTION]   Remaining minerals: {total_remaining}")
                            print(f"[ECONOMY PREDICTION]   Triggering pre-emptive expansion...")

                        await self._trigger_expansion_for_growth()
                        break  # 한 번에 하나만

        except (AttributeError, TypeError, ValueError) as e:
            # Growth expansion check failed
            pass

    def is_economy_recovery_mode(self) -> bool:
        """경제 회복 모드 여부"""
        return getattr(self, "_economy_recovery_mode", False)

    def get_target_drone_count(self) -> int:
        """목표 드론 수"""
        return getattr(self, "_target_drone_count", 66)

    async def _check_air_threat_response(self) -> None:
        """
        ★ 공중 위협 대응 시스템 (Automatic Anti-Air Defense) ★

        적 공중 유닛이 감지되면:
        1. 모든 기지에 포자 촉수(Spore Crawler) 1개씩 강제 건설
        2. 히드라리스크 덴 우선 건설
        """
        if not hasattr(self.bot, "enemy_units") or not self.bot.enemy_units:
            return

        # 적 공중 유닛 감지 (오버로드/감시군주 제외)
        air_threats = [u for u in self.bot.enemy_units if getattr(u, "is_flying", False) and u.type_id not in {UnitTypeId.OVERLORD, UnitTypeId.OVERSEER}]
        if not air_threats:
            return

        # 기지가 없으면 리턴
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.ready:
            return

        # 1. 모든 기지에 포자 촉수 건설 Check
        if self.bot.can_afford(UnitTypeId.SPORECRAWLER):
            for th in self.bot.townhalls.ready:
                # 기지 근처 10거리 내에 포자 촉수가 없으면 건설
                spores = self.bot.structures(UnitTypeId.SPORECRAWLER).closer_than(10, th)
                if not spores.exists and self.bot.already_pending(UnitTypeId.SPORECRAWLER) == 0:
                    # ★ 안전한 위치에서 건설 (적이 없는 곳) ★
                    enemies_near_base = self.bot.enemy_units.closer_than(10, th) if self.bot.enemy_units else []
                    if len(enemies_near_base) > 3:
                        continue  # 적이 너무 많으면 이 기지 건설 스킵 (일꾼 안전 우선)

                    workers = self.bot.workers.closer_than(20, th)
                    if workers:
                        # ★ 미네랄 라인 방향으로 건설 (안전한 위치) ★
                        mineral_fields = self.bot.mineral_field.closer_than(10, th)
                        if mineral_fields:
                            pos = th.position.towards(mineral_fields.center, 4)
                        else:
                            pos = th.position.towards(self.bot.game_info.map_center, 4)
                        worker = workers.closest_to(pos)
                        if worker:
                            self.bot.do(worker.build(UnitTypeId.SPORECRAWLER, pos))
                            print(f"[DEFENSE] ★ Anti-Air Detected! Building Spore Crawler at {th.position} ★")
                            return # 한 번에 하나씩

        # 2. 히드라리스크 덴 테크 올리기 (지상 대공 핵심)
        if hasattr(self.bot, "structures"):
            hydra_den = self.bot.structures(UnitTypeId.HYDRALISKDEN)
            if not hydra_den.exists and self.bot.already_pending(UnitTypeId.HYDRALISKDEN) == 0:
                if self.bot.structures(UnitTypeId.LAIR).ready.exists or self.bot.structures(UnitTypeId.HIVE).ready.exists:
                     if self.bot.can_afford(UnitTypeId.HYDRALISKDEN):
                        await self.bot.build(UnitTypeId.HYDRALISKDEN, near=self.bot.townhalls.first)
                        print(f"[DEFENSE] ★ Anti-Air Tech: Building Hydralisk Den! ★")

    async def _check_maynarding(self) -> None:
        """
        Check for hatcheries nearing completion (Maynarding).
        ★ OPTIMIZED: 80% 진행도에서 더 많은 일꾼 미리 보내기 ★
        If progress > 80%, transfer workers from saturated base.
        """
        if not hasattr(self.bot, "structures"):
            return

        # Find hatcheries under construction - ★ OPTIMIZED: 90% → 80% (더 빠른 준비) ★
        building_hatcheries = self.bot.structures(UnitTypeId.HATCHERY).not_ready.filter(
            lambda h: h.build_progress > 0.8  # ★ 0.9 → 0.8 ★
            and h.tag not in self.transferred_hatcheries
        )

        if not building_hatcheries.exists:
            return

        for target_hatch in building_hatcheries:
            # Find a source base (ready, has > 12 workers)
            ready_bases = self.bot.townhalls.ready.filter(
                lambda th: th.assigned_harvesters > 12
            )
            
            if not ready_bases.exists:
                continue

            # Closest source base
            source_base = ready_bases.closest_to(target_hatch)
            
            # ★ SAFE MAYNARDING: 적정 인원만 이동 + 안전 체크 ★
            workers = self.bot.workers.filter(
                lambda w: w.distance_to(source_base) < 10 and w.is_gathering
            )

            if workers.amount < 8:  # ★ 소스 기지에 최소 8명은 유지 ★
                continue

            # ★ 안전 체크: 목적지 근처 적 확인 ★
            enemies_near_target = self.bot.enemy_units.closer_than(15, target_hatch.position) if self.bot.enemy_units else []
            if len(enemies_near_target) > 0:
                continue  # 적이 있으면 이동 취소

            # ★ 적정 인원: 소스 기지 포화도 유지하면서 이동 (최대 6명) ★
            source_ideal = source_base.ideal_harvesters
            excess = max(0, workers.amount - source_ideal)
            transfer_count = min(excess, 6)  # ★ 16 → 6 (과도한 이동 방지) ★
            if transfer_count < 2:
                continue  # 이동할 일꾼이 2명 미만이면 스킵

            transfer_group = workers.take(transfer_count) if workers.amount >= transfer_count else workers

            # ★ 미네랄 gather 명령으로 이동 (도착 후 바로 채취) ★
            target_minerals = self.bot.mineral_field.closer_than(10, target_hatch.position)
            for worker in transfer_group:
                if target_minerals:
                    self.bot.do(worker.gather(target_minerals.closest_to(target_hatch.position)))
                else:
                    self.bot.do(worker.move(target_hatch.position))

            print(f"[ECONOMY] Maynarding: {len(transfer_group)} workers to new base (safe)")
            self.transferred_hatcheries.add(target_hatch.tag)

    # ========================================
    # Expansion Optimization & Telemetry (Phase 17)
    # ========================================

    def _check_first_expansion_timing(self):
        """1분 확장 타이밍 정밀 측정"""
        if not hasattr(self.bot, "townhalls") or self.bot.townhalls.amount < 2:
            return

        # 2번째 해처리가 건설 시작되었는지 확인
        hatcheries = self.bot.structures(UnitTypeId.HATCHERY)
        second_hatch = None
        for h in hatcheries:
            if h.position != self.bot.start_location:
                 second_hatch = h
                 break
        
        if second_hatch:
            # 건설 시작 시간 추정 (현재 시간 - 진행된 시간)
            # build_time = 71s (Standard speed)
            start_time = self.bot.time - (second_hatch.build_progress * 71)
            self.first_expansion_time = start_time
            self.first_expansion_reported = True
            
            # 로그 출력
            status = "SUCCESS" if start_time < 70 else "DELAYED"
            print(f"[ECONOMY_TELEMETRY] First Expansion Started at {start_time:.2f}s ({status})")

    async def _manage_expansion_blocking(self):
        """
        적 앞마당 확장 방해 (Expansion Blocking)
        0:50초에 드론 1기를 적 앞마당으로 보내서 건설을 방해합니다.
        """
        game_time = self.bot.time
        
        # 1. 종료 조건
        if game_time > self.expansion_block_start_time + self.expansion_block_duration:
             if self.expansion_block_active and self.expansion_block_worker_tag:
                 # 복귀
                 worker = self.bot.units.find_by_tag(self.expansion_block_worker_tag)
                 if worker:
                     self.bot.do(worker.gather(self.bot.mineral_field.closest_to(self.bot.start_location)))
                 self.expansion_block_active = False
                 self.expansion_block_worker_tag = None
             return

        # 2. 시작 조건 (0:50 ~ 1:00 사이)
        if game_time < self.expansion_block_start_time:
            return

        if not self.expansion_block_active:
             # 일꾼 선발
             if not hasattr(self.bot, "workers") or not self.bot.workers:
                 return
             
             candidates = self.bot.workers.filter(lambda w: w.is_carrying_minerals or w.is_gathering)
             if candidates:
                 worker = candidates.first
                 self.expansion_block_worker_tag = worker.tag
                 self.expansion_block_active = True
                 print(f"[ECONOMY] Sending Expansion Blocker Drone (Tag: {worker.tag})")
        
        # 3. 방해 실행
        if self.expansion_block_active and self.expansion_block_worker_tag:
             worker = self.bot.units.find_by_tag(self.expansion_block_worker_tag)
             if not worker:
                 self.expansion_block_active = False
                 return
             
             # 적 앞마당 찾기
             target_loc = None
             if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                 enemy_main = self.bot.enemy_start_locations[0]
                 if hasattr(self.bot, "expansion_locations_list"):
                     expansions = [loc for loc in self.bot.expansion_locations_list if loc != enemy_main]
                     if expansions:
                         target_loc = min(expansions, key=lambda p: p.distance_to(enemy_main))
             
             if target_loc:
                 if worker.distance_to(target_loc) > 5:
                     self.bot.do(worker.move(target_loc))
                 else:
                     nearby_enemies = self.bot.enemy_units.closer_than(5, worker)
                     if nearby_enemies:
                         self.bot.do(worker.attack(nearby_enemies.closest_to(worker)))
                     else:
                         # 패트롤
                         p1 = target_loc.offset((2, 2))
                         self.bot.do(worker.patrol(p1))

    # ========================================
    # ★★★ Phase 18: Gas Optimization ★★★
    # ========================================

    async def _adjust_gas_workers_dynamically(self):
        """
        ★ Phase 18: 생산 큐에 따른 동적 가스 일꾼 조정 ★

        생산 큐에 가스가 많이 필요한 유닛이 있으면 가스 일꾼 증가,
        가스가 넘치면 가스 일꾼 감소
        """
        if not self.dynamic_gas_workers_enabled:
            return

        if not hasattr(self.bot, "gas_buildings") or not hasattr(self.bot, "vespene"):
            return

        gas = self.bot.vespene
        minerals = self.bot.minerals

        # 1. 가스가 매우 부족하면 가스 일꾼 증가
        if gas < 100 and minerals > 500:
            await self._boost_gas_workers()

        # 2. 가스가 넘치고 미네랄이 부족하면 가스 일꾼 감소
        elif gas > 1500 and minerals < 300:
            await self._reduce_gas_workers()

    async def _boost_gas_workers(self):
        """가스 일꾼 증가 (미네랄 일꾼 → 가스 일꾼)"""
        if not hasattr(self.bot, "gas_buildings"):
            return

        extractors = self.bot.gas_buildings.ready

        for extractor in extractors:
            if extractor.assigned_harvesters < 3:
                # 근처 미네랄 일꾼을 가스로 이동
                workers = self.bot.workers.closer_than(15, extractor).filter(
                    lambda w: w.is_gathering and not w.is_carrying_vespene
                )

                if workers:
                    worker = workers.first
                    self.bot.do(worker.gather(extractor))
                    print(f"[ECONOMY] Boosting gas workers (Gas: {self.bot.vespene})")
                    return

    async def _reduce_gas_workers(self):
        """가스 일꾼 감소 (가스 일꾼 → 미네랄 일꾼)"""
        if not hasattr(self.bot, "gas_buildings"):
            return

        extractors = self.bot.gas_buildings.ready

        for extractor in extractors:
            if extractor.assigned_harvesters > 2:  # 최소 2명 유지
                # 가스 일꾼을 미네랄로 이동
                workers = self.bot.workers.filter(
                    lambda w: w.is_gathering and w.order_target == extractor.tag
                )

                if workers:
                    worker = workers.first
                    # 가장 가까운 미네랄 패치 찾기
                    if self.bot.townhalls.ready:
                        closest_th = self.bot.townhalls.ready.closest_to(worker)
                        minerals = self.bot.mineral_field.closer_than(10, closest_th)
                        if minerals:
                            self.bot.do(worker.gather(minerals.closest_to(worker)))
                            print(f"[ECONOMY] Reducing gas workers (Gas: {self.bot.vespene}, Min: {self.bot.minerals})")
                            return

    async def _prevent_gas_overflow(self):
        """
        ★ Phase 18: 가스 오버플로우 방지 ★

        가스가 3000+ 이상이면 가스 일꾼을 미네랄로 이동
        """
        if not hasattr(self.bot, "vespene") or not hasattr(self.bot, "gas_buildings"):
            return

        gas = self.bot.vespene

        if gas < self.gas_overflow_prevention_threshold:
            return

        # 가스가 넘침 - 가스 일꾼을 미네랄로 이동
        print(f"[ECONOMY] ★ GAS OVERFLOW: {gas} (moving gas workers to minerals) ★")

        extractors = self.bot.gas_buildings.ready

        workers_moved = 0
        max_workers_to_move = 6  # 최대 6명까지 이동

        for extractor in extractors:
            if workers_moved >= max_workers_to_move:
                break

            if extractor.assigned_harvesters > 0:
                # 가스 일꾼을 미네랄로 이동
                workers = self.bot.workers.filter(
                    lambda w: w.order_target == extractor.tag
                )

                for worker in workers:
                    if workers_moved >= max_workers_to_move:
                        break

                    # 가장 가까운 미네랄 패치 찾기
                    if self.bot.townhalls.ready:
                        closest_th = self.bot.townhalls.ready.closest_to(worker)
                        minerals = self.bot.mineral_field.closer_than(10, closest_th)
                        if minerals:
                            self.bot.do(worker.gather(minerals.closest_to(worker)))
                            workers_moved += 1

    def enable_gas_boost_mode(self, duration: float = 120):
        """
        ★ Phase 18: 가스 부스트 모드 활성화 ★

        빠른 테크가 필요할 때 (뮤탈, 히드라 등) 가스 채취를 우선합니다.

        Args:
            duration: 부스트 지속 시간 (기본: 120초 = 2분)
        """
        self.gas_boost_mode = True
        self.gas_boost_start_time = self.bot.time
        self.gas_boost_duration = duration

        print(f"[ECONOMY] ★ GAS BOOST MODE ACTIVATED (duration: {duration}s) ★")

    def disable_gas_boost_mode(self):
        """가스 부스트 모드 비활성화"""
        self.gas_boost_mode = False
        print(f"[ECONOMY] Gas boost mode deactivated")

    def get_gas_stats(self) -> dict:
        """★ Phase 18: 가스 통계 반환 ★"""
        if not hasattr(self.bot, "gas_buildings"):
            return {}

        extractors = self.bot.gas_buildings.ready
        total_gas_workers = sum(e.assigned_harvesters for e in extractors)

        return {
            "gas": self.bot.vespene,
            "extractors": len(extractors),
            "gas_workers": total_gas_workers,
            "gas_boost_mode": self.gas_boost_mode,
            "optimal_gas_timing": self.gas_timing_by_race.get(
                str(self.bot.enemy_race).split(".")[-1] if hasattr(self.bot, "enemy_race") else "Unknown",
                90
            ),
        }
