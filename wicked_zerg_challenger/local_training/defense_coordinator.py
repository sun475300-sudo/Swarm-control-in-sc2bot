from typing import Optional, List, Tuple
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.units import Units
from utils.logger import get_logger

class DefenseCoordinator:
    """
    Centralized Defense Coordinator.
    Consolidates defense logic from StrategyManager, ProductionResilience, etc.
    Responsible for:
    1. Threat Assessment (Aggregating info)
    2. Emergency Production (Early game defense)
    3. Defense Structure Placement requests
    4. Rally Point Management
    """
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("DefenseCoordinator")
        self.last_threat_update = 0
        self.threat_level = "SAFE"
        
        # Early Defense State
        self.early_defense_active = True
        self.last_defense_check = 0
        self._last_defense_build_time = 0
        
        # Initialize BuildingPlacementHelper
        try:
            from building_placement_helper import BuildingPlacementHelper
            self.placement_helper = BuildingPlacementHelper(bot)
        except ImportError:
            self.placement_helper = None
            
    async def execute(self, iteration: int):
        """Main execution method called every step"""
        # 1. Threat Assessment
        self._assess_threats()
        
        # 2. Early Game Defense (replaces ProductionResilience._ensure_early_defense)
        # Run every 4 steps to save CPU, but check often for reaction speed
        if self.early_defense_active:
             if iteration % 4 == 0:
                await self._ensure_early_defense()
        
        # 3. Structure Defense (Spines/Spores)
        if iteration % 22 == 0: # Every ~1 sec
             await self._build_early_defense()

    def get_status(self) -> str:
        return f"Threat: {self.threat_level}"

    def _assess_threats(self):
        """Assess current threat level using StrategyManager and Intel"""
        # Sync with StrategyManager if available
        if hasattr(self.bot, "strategy_manager") and self.bot.strategy_manager:
            if self.bot.strategy_manager.emergency_active:
                 self.threat_level = "EMERGENCY"
            elif self.bot.strategy_manager.current_mode == "defensive": # StrategyMode.DEFENSIVE
                 self.threat_level = "HIGH"
            else:
                 self.threat_level = "SAFE"
        
        # TODO: Add more independent threat assessment here

    async def _ensure_early_defense(self) -> None:
        """
        3분 전 방어 유닛 빌드 최적화 (Consolidated from ProductionResilience)
        
        목표:
        - 2:00 (120초): 스포닝 풀 완료
        - 2:30 (150초): 최소 6저글링 + 퀸 생산 시작
        - 3:00 (180초): 최소 8저글링 + 퀸 1기 완료
        """
        b = self.bot
        game_time = getattr(b, "time", 0.0)

        # 게임 시간 180초(3분) 이후는 이 로직 스킵 (Early Defense 종료)
        if game_time > 180:
            self.early_defense_active = False
            return

        try:
            # === 스포닝 풀 확인 ===
            spawning_pool_exists = b.structures(UnitTypeId.SPAWNINGPOOL).exists
            spawning_pool_ready = b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists
            spawning_pool_pending = b.already_pending(UnitTypeId.SPAWNINGPOOL) > 0

            # 100초(1:40) 이후 스포닝 풀이 없으면 긴급 건설
            if game_time >= 100 and not spawning_pool_exists and not spawning_pool_pending:
                if b.can_afford(UnitTypeId.SPAWNINGPOOL) and b.townhalls.exists:
                    try:
                        main_base = b.townhalls.first
                        await b.build(
                            UnitTypeId.SPAWNINGPOOL,
                            near=main_base.position.towards(b.game_info.map_center, 5),
                        )
                        self.logger.info(f"[EARLY_DEFENSE] [{int(game_time)}s] Emergency Spawning Pool build")
                        return
                    except Exception:
                        pass

            # 스포닝 풀이 완료되지 않았으면 대기
            if not spawning_pool_ready:
                return

            # === 퀸 생산 확인 (방어 + 인젝트 핵심) ===
            queens = b.units(UnitTypeId.QUEEN) if hasattr(b, "units") else []
            queen_count = queens.amount if hasattr(queens, "amount") else 0
            queen_pending = b.already_pending(UnitTypeId.QUEEN)

            # 120초(2분) 이후 퀸이 없으면 긴급 생산
            if game_time >= 120 and queen_count == 0 and queen_pending == 0:
                if b.townhalls.ready.exists and b.can_afford(UnitTypeId.QUEEN):
                    try:
                        for hatchery in b.townhalls.ready:
                            if not hatchery.is_idle:
                                continue
                            b.do(hatchery.train(UnitTypeId.QUEEN))
                            self.logger.info(f"[EARLY_DEFENSE] [{int(game_time)}s] Emergency Queen production")
                            break
                    except Exception:
                        pass

            # === 저글링 생산 (최소 방어 병력) ===
            zerglings = b.units(UnitTypeId.ZERGLING) if hasattr(b, "units") else []
            zergling_count = zerglings.amount if hasattr(zerglings, "amount") else 0
            zergling_pending = b.already_pending(UnitTypeId.ZERGLING)

            # ★ 개선: 적 위협 감지 (기지 근처 적 유닛)
            enemy_threat_detected = False
            if hasattr(b, "enemy_units") and hasattr(b, "townhalls"):
                for th in b.townhalls:
                    nearby_enemies = [e for e in b.enemy_units if e.distance_to(th.position) < 40]
                    if nearby_enemies:
                        enemy_threat_detected = True
                        break

            # ★ 수정: 조건 완화 (4기/6기) 및 적 위협 또는 시간 조건
            min_zerglings_150s = 4  # ★ 6 -> 4 (조건 완화)
            min_zerglings_180s = 6  # ★ 8 -> 6 (조건 완화)

            target_zerglings = min_zerglings_150s if game_time < 180 else min_zerglings_180s

            # ★ 개선: 적 위협이 있거나 3분(180초) 이후에만 긴급 생산
            should_emergency_produce = (
                game_time >= 150 and
                (zergling_count + zergling_pending) < target_zerglings and
                (enemy_threat_detected or game_time >= 180)
            )

            if should_emergency_produce:
                larvae = b.units(UnitTypeId.LARVA) if hasattr(b, "units") else []
                if larvae.exists and b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
                    larvae_list = list(larvae.ready) if hasattr(larvae, 'ready') else list(larvae)
                    zerglings_to_produce = min(4, target_zerglings - zergling_count - zergling_pending)

                    for larva in larvae_list[:zerglings_to_produce]:
                        if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
                            b.do(larva.train(UnitTypeId.ZERGLING))
                    
                    if zerglings_to_produce > 0:
                        self.logger.info(f"[EARLY_DEFENSE] [{int(game_time)}s] Emergency Zergling production: {zergling_count} -> {target_zerglings}")

            # Overlord logic removed (Handled by ProductionController)

        except Exception as e:
            self.logger.error(f"[DEFENSE_ERROR] _ensure_early_defense error: {e}")

    async def _build_early_defense(self) -> None:
        """
        Build defense structures proactively or reactively.
        Respects StrategyManager requests.
        """
        b = self.bot
        game_time = getattr(b, "time", 0)

        # Need Spawning Pool for defense structures
        if not b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            return

        spine_crawlers = b.structures(UnitTypeId.SPINECRAWLER)
        spine_count = spine_crawlers.amount if hasattr(spine_crawlers, 'amount') else len(list(spine_crawlers))
        pending_spines = b.already_pending(UnitTypeId.SPINECRAWLER)

        spore_crawlers = b.structures(UnitTypeId.SPORECRAWLER)
        spore_count = spore_crawlers.amount if hasattr(spore_crawlers, 'amount') else 0
        pending_spores = b.already_pending(UnitTypeId.SPORECRAWLER)

        # Defense cooldown to prevent spam (except for emergency requests)
        if game_time - self._last_defense_build_time < 15:
            # Emergency requests bypass cooldown
            pass 
        elif game_time - self._last_defense_build_time < 5: # Minimum 5s even for emergency
            return

        # === 1. Check StrategyManager Requests ===
        strategy_manager = getattr(b, "strategy_manager", None)
        requested_spine = False
        requested_spore = False
        
        if strategy_manager:
            requested_spine = getattr(strategy_manager, "emergency_spine_requested", False)
            requested_spore = getattr(strategy_manager, "emergency_spore_requested", False)
        
        # === 2. Detect Rush Locally (Backup) ===
        local_rush = self._detect_early_rush_logic()
        
        # === 3. Build Decision ===
        
        # Spine Crawler (Ground Defense)
        if (requested_spine or local_rush) and spine_count < 2:
             if b.can_afford(UnitTypeId.SPINECRAWLER) and b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    defense_pos = main_base.position.towards(b.game_info.map_center, 6)
                    # Don't block mineral line
                    
                    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    self.logger.info(f"[EMERGENCY DEFENSE] [{int(game_time)}s] SPINE REQUESTED (Strat: {requested_spine}, Local: {local_rush})")
                    return
                except Exception:
                    pass

        # ★★★ IMPROVED: Spore Crawler (Air Defense) - 공중 위협 시 최대 3개까지 건설 ★★★
        if requested_spore and spore_count + pending_spores < 3:  # 긴급 시 3개까지 증가 (기존: 1개)
             if b.can_afford(UnitTypeId.SPORECRAWLER) and b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    # 다양한 위치에 분산 배치
                    offset = spore_count * 5  # 각 스포어를 5칸씩 떨어뜨림
                    await b.build(UnitTypeId.SPORECRAWLER, near=main_base.position.towards(b.game_info.map_center, 4 + offset))
                    self._last_defense_build_time = game_time
                    self.logger.info(f"[EMERGENCY DEFENSE] [{int(game_time)}s] SPORE #{spore_count + 1} REQUESTED (Air threat)")
                    return
                except Exception:
                    pass

        # === 4. Proactive Timeline (Standard Play) ===
        if game_time - self._last_defense_build_time < 15: # Respect cooldown for scheduled builds
            return

        # 2:00+ : First Spine Crawler
        if game_time >= 120 and spine_count + pending_spines < 1:
            if b.can_afford(UnitTypeId.SPINECRAWLER) and b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    defense_pos = main_base.position.towards(b.game_info.map_center, 7)
                    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    self.logger.info(f"[DEFENSE] [{int(game_time)}s] Building Spine Crawler #1")
                    return
                except Exception:
                    pass

        # 3:00+ : Second Spine Crawler
        if game_time >= 180 and spine_count + pending_spines < 2:
            if b.can_afford(UnitTypeId.SPINECRAWLER) and b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    defense_pos = main_base.position.towards(b.game_info.map_center, 9)
                    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    self.logger.info(f"[DEFENSE] [{int(game_time)}s] Building Spine Crawler #2")
                    return
                except Exception:
                    pass

        # ★★★ OPTIMIZED: 3:00 Spore Crawler (자원 예약 강화) ★★★
        if game_time >= 180 and spore_count + pending_spores < 1:  # 정확히 3:00
            # ★ 자원이 80이상이면 즉시 건설 (75 cost + 5 buffer) ★
            if b.minerals >= 80 and b.townhalls.exists:
                # Spawning Pool 체크
                pools = b.structures(UnitTypeId.SPAWNINGPOOL).ready
                if not pools.exists:
                    if game_time < 185:  # 3:05까지만 대기 로그
                        self.logger.info(f"[DEFENSE] [{int(game_time)}s] ⏳ Spore 대기: Spawning Pool 미완료")
                    return

                try:
                    main_base = b.townhalls.first
                    await b.build(UnitTypeId.SPORECRAWLER, near=main_base.position.towards(b.game_info.map_center, 4))
                    self._last_defense_build_time = game_time
                    self.logger.info(f"[DEFENSE] [{int(game_time)}s] ★★★ Spore Crawler #1 건설! (목표: 3:00) ★★★")
                    return
                except Exception as e:
                    self.logger.warning(f"[DEFENSE] Spore build failed: {e}")
            elif game_time < 185:  # 3:05까지만 대기 로그
                self.logger.info(f"[DEFENSE] [{int(game_time)}s] ⏳ Spore 자원 대기: {b.minerals}m (필요: 75m)")

        # 4:00+ : Third Spine Crawler
        if game_time >= 240 and spine_count + pending_spines < 3:
            if b.can_afford(UnitTypeId.SPINECRAWLER) and b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    defense_pos = main_base.position.towards(b.game_info.map_center, 11)
                    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    self.logger.info(f"[DEFENSE] [{int(game_time)}s] Building Spine Crawler #3")
                    return
                except Exception:
                    pass

        # === 확장 기지 방어 (5분 이후) ===
        if game_time >= 300:
            await self._build_expansion_defense(game_time)

    def _detect_early_rush_logic(self) -> bool:
        """초반 러쉬 감지 (Local Logic)"""
        b = self.bot
        game_time = getattr(b, "time", 0)
        if game_time > 180:
            return False

        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return False

        rush_units = {'ZERGLING', 'MARINE', 'ZEALOT', 'REAPER', 'ADEPT', 'ROACH'}

        for enemy in enemy_units:
            enemy_type = getattr(enemy.type_id, "name", "").upper()
            if enemy_type in rush_units:
                for th in b.townhalls:
                    if enemy.distance_to(th.position) < 30: # 30으로 완화
                        return True
        return False

    async def _build_expansion_defense(self, game_time: float) -> None:
        """확장 기지에 방어 건물 건설"""
        b = self.bot
        townhalls = b.townhalls.ready
        if townhalls.amount <= 1:
            return

        for th in townhalls:
            if th == b.townhalls.first:
                continue

            nearby_spines = b.structures(UnitTypeId.SPINECRAWLER).closer_than(15, th)
            nearby_spores = b.structures(UnitTypeId.SPORECRAWLER).closer_than(15, th)

            spine_count = nearby_spines.amount if hasattr(nearby_spines, 'amount') else 0
            spore_count = nearby_spores.amount if hasattr(nearby_spores, 'amount') else 0

            if spine_count < 1 and b.can_afford(UnitTypeId.SPINECRAWLER):
                try:
                    defense_pos = th.position.towards(b.game_info.map_center, 6)
                    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    self.logger.info(f"[DEFENSE] [{int(game_time)}s] Building Spine at expansion")
                    return
                except Exception:
                    pass

            # ★★★ IMPROVED: 확장 기지 스포어 크롤러 증가 (1개 → 2개) ★★★
            if spore_count < 2 and b.can_afford(UnitTypeId.SPORECRAWLER):  # 확장당 2개로 증가
                try:
                    offset = spore_count * 6  # 스포어 간격 조정
                    await b.build(UnitTypeId.SPORECRAWLER, near=th.position.towards(b.game_info.map_center, 3 + offset))
                    self._last_defense_build_time = game_time
                    self.logger.info(f"[DEFENSE] [{int(game_time)}s] Building Spore #{spore_count + 1} at expansion")
                    return
                except Exception:
                    pass
