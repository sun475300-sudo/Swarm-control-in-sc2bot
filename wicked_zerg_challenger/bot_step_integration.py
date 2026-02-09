# -*- coding: utf-8 -*-
"""
Bot Step Integration - on_step 구현 통합 모듈

이 모듈은 WickedZergBotPro의 on_step 메서드를 구현하여
실제 게임 로직과 훈련 로직을 통합합니다.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

# Error Handler 통합
from error_handler import error_handler

# Build Order System (lazy import fallback)
try:
    from build_order_system import BuildOrderSystem
except ImportError:
    BuildOrderSystem = None

# Performance Profiler
try:
    from utils.performance_profiler import get_profiler
except ImportError:
    get_profiler = None


class LogicActivityTracker:
    """실시간 로직 활성화 추적기"""

    def __init__(self):
        self.active_logics: Dict[str, Dict] = {}
        self.last_report_time = 0
        self.report_interval = 10.0  # 10초마다 보고
        self.execution_counts: Dict[str, int] = {}
        self.execution_times: Dict[str, float] = {}

    def start_logic(self, name: str) -> float:
        """로직 시작 시간 기록"""
        start_time = time.time()
        self.active_logics[name] = {
            "start_time": start_time,
            "status": "running"
        }
        return start_time

    def end_logic(self, name: str, start_time: float, success: bool = True):
        """로직 종료 및 실행 시간 기록"""
        elapsed = time.time() - start_time
        if name in self.active_logics:
            self.active_logics[name]["status"] = "done" if success else "error"
            self.active_logics[name]["elapsed"] = elapsed

        # 통계 업데이트
        self.execution_counts[name] = self.execution_counts.get(name, 0) + 1
        self.execution_times[name] = self.execution_times.get(name, 0) + elapsed

    def get_activity_report(self, game_time: float) -> str:
        """활성화된 로직 보고서 생성"""
        current_time = time.time()
        if current_time - self.last_report_time < self.report_interval:
            return ""

        self.last_report_time = current_time

        lines = [f"\n[LOGIC ACTIVITY] 게임 시간: {int(game_time)}초"]
        lines.append("=" * 50)

        # 실행 횟수 및 시간 출력
        for name, count in sorted(self.execution_counts.items()):
            total_time = self.execution_times.get(name, 0)
            avg_time = (total_time / count * 1000) if count > 0 else 0
            lines.append(f"  {name}: {count}회 실행, 평균 {avg_time:.2f}ms")

        lines.append("=" * 50)

        # 카운터 리셋
        self.execution_counts.clear()
        self.execution_times.clear()

        return "\n".join(lines)

    def get_current_status(self) -> List[str]:
        """현재 활성화된 로직 목록 반환"""
        return [name for name, info in self.active_logics.items()
                if info.get("status") == "running"]

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:

    class BotAI:
        pass

    class UnitTypeId:
        DRONE = "DRONE"
        OVERLORD = "OVERLORD"
        ZERGLING = "ZERGLING"
        QUEEN = "QUEEN"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        MUTALISK = "MUTALISK"
        BANELING = "BANELING"
        RAVAGER = "RAVAGER"
        LURKER = "LURKER"
        CORRUPTOR = "CORRUPTOR"
        ULTRALISK = "ULTRALISK"
        BROODLORD = "BROODLORD"
        INFESTOR = "INFESTOR"
        VIPER = "VIPER"
        SPIRE = "SPIRE"
        GREATERSPIRE = "GREATERSPIRE"
        HIVE = "HIVE"
        LAIR = "LAIR"
        HATCHERY = "HATCHERY"
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        LARVA = "LARVA"

try:
    from .building_placement_helper import BuildingPlacementHelper
except ImportError:
    BuildingPlacementHelper = None


# Tech Coordinator (Conflict Resolution)
try:
    from tech_coordinator import TechCoordinator
except ImportError:
    TechCoordinator = None

# Worker Combat System (Early Rush Defense)
try:
    from worker_combat_system import WorkerCombatSystem
except ImportError:
    WorkerCombatSystem = None

# Strict Upgrade Priority System
try:
    from strict_upgrade_priority import StrictUpgradePriority
except ImportError:
    StrictUpgradePriority = None

# ★★★ PHASE 8/9 SYSTEMS ★★★

# Enhanced Scouting System
try:
    from scouting.enhanced_scout_system import EnhancedScoutSystem
except ImportError:
    EnhancedScoutSystem = None

# Harassment Coordinator
try:
    from combat.harassment_coordinator import HarassmentCoordinator
except ImportError:
    HarassmentCoordinator = None

# Queen Inject Optimizer
try:
    from economy.queen_inject_optimizer import QueenInjectOptimizer
except ImportError:
    QueenInjectOptimizer = None

# Queen Transfusion Manager
try:
    from economy.queen_transfusion_manager import QueenTransfusionManager
except ImportError:
    QueenTransfusionManager = None

# Resource Manager (Thread-safe reservations)
try:
    from core.resource_manager import ResourceManager
except ImportError:
    ResourceManager = None

# Spatial Query Optimizer (C++ optimized proximity)
try:
    from combat.spatial_query_optimizer import SpatialQueryOptimizer
except ImportError:
    SpatialQueryOptimizer = None

# Multi-Prong Attack Coordinator
try:
    from combat.multi_prong_coordinator import MultiProngCoordinator
except ImportError:
    MultiProngCoordinator = None

# Trade Efficiency Analyzer
try:
    from combat.trade_analyzer import TradeAnalyzer
except ImportError:
    TradeAnalyzer = None

# Late Game Composition Optimizer
try:
    from strategy.late_game_optimizer import LateGameOptimizer
except ImportError:
    LateGameOptimizer = None

# Overlord Vision Network
try:
    from overlord_vision_network import OverlordVisionNetwork
except ImportError:
    OverlordVisionNetwork = None

# Build Order Optimizer
try:
    from strategy.build_order_optimizer import BuildOrderOptimizer
except ImportError:
    BuildOrderOptimizer = None

# Adaptive Build Order AI
try:
    from strategy.adaptive_build_order import AdaptiveBuildOrder
except ImportError:
    AdaptiveBuildOrder = None

# Timing Attacks Library
try:
    from strategy.timing_attacks import TimingAttacks
except ImportError:
    TimingAttacks = None

# Advanced Creep Automation V2
try:
    from creep_automation_v2 import CreepAutomationV2
except ImportError:
    CreepAutomationV2 = None

# Proxy Hatchery Tactics
try:
    from strategy.proxy_hatchery import ProxyHatchery
except ImportError:
    ProxyHatchery = None

# 1-Min Multi Test
try:
    from tests.one_min_multi_test import OneMinMultiTest
except ImportError:
    OneMinMultiTest = None

# Unit Authority Manager
try:
    from unit_authority_manager import UnitAuthorityManager, AuthorityLevel
except ImportError:
    UnitAuthorityManager = None
    AuthorityLevel = None

# Advanced Scout System V2
try:
    from scouting.advanced_scout_system_v2 import AdvancedScoutSystemV2
except ImportError:
    AdvancedScoutSystemV2 = None

class BotStepIntegrator:
    """
    Bot의 on_step 메서드를 구현하는 통합 클래스

    기능:
    1. 매니저들 초기화 (lazy loading)
    2. 게임 로직 실행 (economy, production, combat 등)
    3. 훈련 모드: 보상 계산 및 RL 업데이트
    4. 최신 개선 사항 통합 (advanced_building_manager 등)
    5. 실시간 로직 활성화 보고
    """

    def __init__(self, bot):
        self.bot = bot
        self._managers_initialized = False
        self._logic_tracker = LogicActivityTracker()

        # 건물 배치 헬퍼
        if BuildingPlacementHelper:
            self.placement_helper = BuildingPlacementHelper(bot)
            self.bot.placement_helper = self.placement_helper # Attach globally
        else:
            self.placement_helper = None
            self.bot.placement_helper = None

        # NOTE: UnitAuthorityManager and AdvancedScoutV2 are initialized
        # in the Phase 10+ section below with proper None-safety checks.

        if TechCoordinator:
            self.bot.tech_coordinator = TechCoordinator(bot)
            print("[INIT] TechCoordinator initialized")
        else:
            self.bot.tech_coordinator = None

        # Worker Combat System (Early Rush Defense)
        if WorkerCombatSystem:
            self.bot.worker_combat = WorkerCombatSystem(bot)
            print("[INIT] WorkerCombatSystem initialized")
        else:
            self.bot.worker_combat = None

        # Strict Upgrade Priority System
        if StrictUpgradePriority:
            self.bot.upgrade_priority = StrictUpgradePriority(bot)
            print("[INIT] StrictUpgradePriority initialized")
        else:
            self.bot.upgrade_priority = None

        # ★★★ PHASE 8/9 SYSTEMS INITIALIZATION ★★★

        # Enhanced Scouting System
        # ★ Skip if AdvancedScoutSystemV2 is available (it supersedes EnhancedScout)
        if EnhancedScoutSystem and not AdvancedScoutSystemV2:
            self.bot.enhanced_scout = EnhancedScoutSystem(bot)
            print("[INIT] EnhancedScoutSystem initialized (Phase 9)")
        else:
            self.bot.enhanced_scout = None

        # Harassment Coordinator
        if HarassmentCoordinator:
            self.bot.harassment_coord = HarassmentCoordinator(bot)
            print("[INIT] HarassmentCoordinator initialized (Phase 9)")
        else:
            self.bot.harassment_coord = None

        # Queen Inject Optimizer
        if QueenInjectOptimizer:
            self.bot.queen_inject_opt = QueenInjectOptimizer(bot)
            print("[INIT] QueenInjectOptimizer initialized (Phase 8)")
        else:
            self.bot.queen_inject_opt = None

        # Queen Transfusion Manager
        if QueenTransfusionManager:
            self.bot.queen_transfusion = QueenTransfusionManager(bot)
            print("[INIT] QueenTransfusionManager initialized (Phase 21)")
        else:
            self.bot.queen_transfusion = None

        # Resource Manager (Thread-safe resource reservation)
        if ResourceManager:
            self.bot.resource_manager = ResourceManager(bot)
            print("[INIT] ResourceManager initialized (Phase 21 - Race condition fix)")
        else:
            self.bot.resource_manager = None

        # Spatial Query Optimizer (Performance optimization)
        if SpatialQueryOptimizer:
            self.bot.spatial_query = SpatialQueryOptimizer(bot)
            print("[INIT] SpatialQueryOptimizer initialized (Phase 21 - C++ optimization)")
        else:
            self.bot.spatial_query = None

        # Multi-Prong Attack Coordinator
        if MultiProngCoordinator:
            self.bot.multi_prong = MultiProngCoordinator(bot)
            print("[INIT] MultiProngCoordinator initialized (Phase 8)")
        else:
            self.bot.multi_prong = None

        # Trade Efficiency Analyzer
        if TradeAnalyzer:
            self.bot.trade_analyzer = TradeAnalyzer(bot)
            print("[INIT] TradeAnalyzer initialized (Phase 8)")
        else:
            self.bot.trade_analyzer = None

        # Late Game Composition Optimizer
        if LateGameOptimizer:
            self.bot.late_game_opt = LateGameOptimizer(bot)
            print("[INIT] LateGameOptimizer initialized (Phase 8)")
        else:
            self.bot.late_game_opt = None

        # Overlord Vision Network
        if OverlordVisionNetwork:
            self.bot.vision_network = OverlordVisionNetwork(bot)
            print("[INIT] OverlordVisionNetwork initialized (Phase 8)")
        else:
            self.bot.vision_network = None

        # Build Order Optimizer
        if BuildOrderOptimizer:
            self.bot.build_order_opt = BuildOrderOptimizer(bot)
            print("[INIT] BuildOrderOptimizer initialized (Phase 9)")
        else:
            self.bot.build_order_opt = None

        # Adaptive Build Order AI
        if AdaptiveBuildOrder:
            self.bot.adaptive_build = AdaptiveBuildOrder(bot)
            print("[INIT] AdaptiveBuildOrder initialized (Phase 8)")
        else:
            self.bot.adaptive_build = None

        # Timing Attacks Library
        if TimingAttacks:
            self.bot.timing_attacks = TimingAttacks(bot)
            print("[INIT] TimingAttacks initialized (Phase 8)")
        else:
            self.bot.timing_attacks = None

        # Advanced Creep Automation V2
        if CreepAutomationV2:
            self.bot.creep_v2 = CreepAutomationV2(bot)
            print("[INIT] CreepAutomationV2 initialized (Phase 8)")
        else:
            self.bot.creep_v2 = None

        # Proxy Hatchery Tactics
        if ProxyHatchery:
            self.bot.proxy_hatch = ProxyHatchery(bot)
            print("[INIT] ProxyHatchery initialized (Phase 8)")
        else:
            self.bot.proxy_hatch = None

        # 1-Min Multi Test
        if OneMinMultiTest:
            self.bot.multi_test = OneMinMultiTest(bot)
            print("[INIT] OneMinMultiTest initialized (Phase 9)")
        else:
            self.bot.multi_test = None

        # Unit Authority Manager
        if UnitAuthorityManager:
            self.bot.unit_authority = UnitAuthorityManager(bot)
            print("[INIT] ★ UnitAuthorityManager initialized ★")
        else:
            self.bot.unit_authority = None

        # Advanced Scout System V2 (개선판)
        if AdvancedScoutSystemV2:
            self.bot.advanced_scout_v2 = AdvancedScoutSystemV2(bot)
            print("[INIT] ★ AdvancedScoutSystemV2 initialized (Overseer + Changeling) ★")
        else:
            self.bot.advanced_scout_v2 = None

    async def initialize_managers(self):
        """
        매니저들 초기화 (lazy loading)
        NOTE: 메인 봇 클래스(WickedZergBotProImpl)에서 초기화가 수행되므로
        여기서는 추가적인 초기화 로직을 수행하지 않습니다.
        """
        self._managers_initialized = True
        return

    async def _update_blackboard_state(self, iteration: int):
        """
        ★★★ Blackboard 게임 상태 업데이트 ★★★

        모든 매니저가 Blackboard를 통해 게임 상태를 조회할 수 있도록
        매 프레임마다 최신 상태로 업데이트
        """
        blackboard = self.bot.blackboard
        if not blackboard:
            return

        # 1. 기본 게임 정보
        blackboard.update_game_info(self.bot)

        # 2. 자원 상태
        blackboard.update_resources(
            minerals=self.bot.minerals,
            vespene=self.bot.vespene,
            supply_used=self.bot.supply_used,
            supply_cap=self.bot.supply_cap
        )

        # 3. 기지 및 일꾼 카운트
        blackboard.bases_count = self.bot.townhalls.amount
        blackboard.worker_count = self.bot.workers.amount

        # 4. 주요 유닛 카운트 업데이트
        if UnitTypeId:
            key_units = [
                UnitTypeId.DRONE,
                UnitTypeId.OVERLORD,
                UnitTypeId.ZERGLING,
                UnitTypeId.QUEEN,
                UnitTypeId.ROACH,
                UnitTypeId.HYDRALISK,
                UnitTypeId.MUTALISK,
            ]

            for unit_type in key_units:
                current = self.bot.units(unit_type).amount
                pending = self.bot.already_pending(unit_type)
                blackboard.update_unit_count(unit_type, current, pending)

        # 5. 전략 정보
        if hasattr(self.bot, "enemy_race"):
            blackboard.enemy_race = str(self.bot.enemy_race)

        if hasattr(self.bot, "aggressive_strategies") and self.bot.aggressive_strategies:
            blackboard.current_strategy = self.bot.aggressive_strategies.active_strategy.value

        # 6. 빌드 오더 완료 여부
        if hasattr(self.bot, "build_order_system") and self.bot.build_order_system:
            if hasattr(self.bot.build_order_system, "is_finished"):
                blackboard.build_order_complete = self.bot.build_order_system.is_finished()
            elif hasattr(self.bot.build_order_system, "finished"):
                blackboard.build_order_complete = self.bot.build_order_system.finished
            else:
                # Fallback: 5분 이후면 완료로 간주
                blackboard.build_order_complete = self.bot.time > 300.0

    async def execute_game_logic(self, iteration: int):
        """게임 로직 실행"""

        # ★ SC2 매너 채팅: GL HF 선언 ★
        if not getattr(self.bot, "_glhf_sent", False):
            if self.bot.time < 10.0:
                await self.bot.chat_send("gl hf")
            self.bot._glhf_sent = True

        try:
            # 0. Performance Optimizer 프레임 시작
            if hasattr(self.bot, "performance_optimizer") and self.bot.performance_optimizer:
                self.bot.performance_optimizer.start_frame()

            # 0.005 ★★★ Logic Optimizer (시스템 활성화 관리) ★★★
            if hasattr(self.bot, "logic_optimizer") and self.bot.logic_optimizer:
                await self.bot.logic_optimizer.on_step(iteration)

            # 0.006 ★★★ Unit Authority Manager (유닛 제어 권한 관리) ★★★
            if hasattr(self.bot, "unit_authority") and self.bot.unit_authority:
                await self.bot.unit_authority.on_step(iteration)

            # 0.0065 ★★★ Early Defense System (초반 러시 방어) - USER ADDED ★★★
            if hasattr(self.bot, "early_defense") and self.bot.early_defense:
                start_time = self._logic_tracker.start_logic("EarlyDefense")
                try:
                    await self.bot.early_defense.execute(iteration)
                except Exception as e:
                    if error_handler.debug_mode: raise
                    print(f"[ERROR] EarlyDefense error: {e}")
                finally:
                    self._logic_tracker.end_logic("EarlyDefense", start_time)

            # 0.0066 ★★★ Idle Unit Manager - REMOVED EARLY CALL ★★★
            # ★ IdleUnits는 8.03에서만 실행 (다른 시스템이 유닛 할당 완료 후 실행해야 함)
            # ★ 이 위치에서 실행하면 견제/스카우트 유닛을 강제 복귀시키는 문제 발생

                # ★ 죽은 유닛의 권한 해제 (2초마다) ★
                if iteration % 44 == 0:
                    self._cleanup_dead_unit_authorities()

            # 0.007 ★★★ Map Memory System (맵 기억 - 적 건물 추적) ★★★
            if hasattr(self.bot, "map_memory") and self.bot.map_memory:
                await self.bot.map_memory.on_step(iteration)

            # 0.008 ★★★ Complete Destruction Trainer (모든 건물 파괴) ★★★
            if hasattr(self.bot, "complete_destruction") and self.bot.complete_destruction:
                await self.bot.complete_destruction.on_step(iteration)

            # 0.009 ★★★ Roach Tactics Trainer (바퀴 잠복 회복 전술) ★★★
            if hasattr(self.bot, "roach_tactics") and self.bot.roach_tactics:
                await self.bot.roach_tactics.on_step(iteration)

            # 0.010 ★★★ Zergling Harassment Trainer (저글링 괴롭힘 전술) ★★★
            if hasattr(self.bot, "zergling_harass") and self.bot.zergling_harass:
                await self.bot.zergling_harass.on_step(iteration)

            # 0.011 ★★★ Overseer Scout Trainer (감시군주 정찰) ★★★
            if hasattr(self.bot, "overseer_scout") and self.bot.overseer_scout:
                await self.bot.overseer_scout.on_step(iteration)

            # 0.012 ★★★ Air Threat Response Trainer (공중 위협 대응) ★★★
            if hasattr(self.bot, "air_threat_response") and self.bot.air_threat_response:
                await self.bot.air_threat_response.on_step(iteration)

            # 0.013 ★★★ Space Control Trainer (공간 확보) ★★★
            if hasattr(self.bot, "space_control") and self.bot.space_control:
                await self.bot.space_control.on_step(iteration)

            # 0.014 Comprehensive Unit Abilities (모든 유닛 스킬)
            if hasattr(self.bot, "unit_abilities") and self.bot.unit_abilities:
                await self.bot.unit_abilities.on_step(iteration)

            # 0.015 Roach Tunneling Tactics (바퀴 땅굴발톱 전술)
            if hasattr(self.bot, "roach_tunneling") and self.bot.roach_tunneling:
                await self.bot.roach_tunneling.on_step(iteration)

            # 0.016 Creep Expansion System (전 맵 점막 확장)
            if hasattr(self.bot, "creep_expansion") and self.bot.creep_expansion:
                await self.bot.creep_expansion.on_step(iteration)

            # 0.0165 ★ NEW: Creep Denial System (적 점막 제거) ★
            if hasattr(self.bot, "creep_denial") and self.bot.creep_denial:
                start_time = self._logic_tracker.start_logic("CreepDenial")
                try:
                    await self.bot.creep_denial.on_step(iteration)

                    # 주기적으로 보고서 출력 (1분마다)
                    if iteration % 1320 == 0:
                        report = self.bot.creep_denial.get_creep_denial_report()
                        print(report)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["CreepDenial"] = error_handler.error_counts.get("CreepDenial", 0) + 1
                        if error_handler.error_counts["CreepDenial"] <= error_handler.max_error_logs:
                            print(f"[ERROR] CreepDenial error: {e}")
                finally:
                    self._logic_tracker.end_logic("CreepDenial", start_time)

            # 0.017 Hive Tech Maximizer (군락 기술 극대화)
            if hasattr(self.bot, "hive_tech") and self.bot.hive_tech:
                await self.bot.hive_tech.on_step(iteration)

            # 0.01 ★★★ Blackboard 상태 업데이트 (최우선) ★★★
            if hasattr(self.bot, "blackboard") and self.bot.blackboard:
                await self._update_blackboard_state(iteration)

            # 0.02 ★★★ Spatial Optimizer & Data Cache (최우선 최적화) ★★★
            # 다른 모든 시스템보다 먼저 실행하여 캐시 준비 (항상 실행)
            if hasattr(self.bot, "spatial_optimizer") and self.bot.spatial_optimizer:
                try:
                    await self.bot.spatial_optimizer.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise

            if hasattr(self.bot, "data_cache") and self.bot.data_cache:
                try:
                    await self.bot.data_cache.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise

            # ★★★ Base Destruction Coordinator (모든 적 기지 파괴) ★★★
            if hasattr(self.bot, "base_destruction") and self.bot.base_destruction:
                try:
                    await self.bot.base_destruction.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise

            # ★★★ Runtime Self-Healing (실행 중 자동 복구) ★★★
            if hasattr(self.bot, "self_healing") and self.bot.self_healing:
                try:
                    await self.bot.self_healing.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise

            # ★★★ Personality Module (채팅/성격) ★★★
            if hasattr(self.bot, "personality") and self.bot.personality:
                try:
                    await self.bot.personality.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise

            # ★★★ Battle Preparation System (교전 대비) ★★★
            if hasattr(self.bot, "battle_prep") and self.bot.battle_prep:
                try:
                    await self.bot.battle_prep.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise

            # ★★★ Destructible Awareness System (파괴 가능 구조물) ★★★
            if hasattr(self.bot, "destructible_aware") and self.bot.destructible_aware:
                try:
                    # 게임 시작 시 한 번만 실행
                    if iteration == 1:
                        await self.bot.destructible_aware.on_start()

                    await self.bot.destructible_aware.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise

            # ★★★ Nydus Network Trainer (땅굴망 학습) ★★★
            if hasattr(self.bot, "nydus_trainer") and self.bot.nydus_trainer:
                try:
                    await self.bot.nydus_trainer.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise

            # ★★★ Overlord Safety Manager (대군주 안전) ★★★
            if hasattr(self.bot, "overlord_safety") and self.bot.overlord_safety:
                try:
                    await self.bot.overlord_safety.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise

            # 0.03 ★★★ Build Order System (빌드 오더 - 최최우선) ★★★
            if self.bot.time < 300.0:  # 5분 이내 (Roach Rush 지원)
                if not hasattr(self.bot, "build_order_system"):
                    if BuildOrderSystem is not None:
                        try:
                            self.bot.build_order_system = BuildOrderSystem(self.bot)
                            print("[BUILD_ORDER] 빌드 오더 시스템 활성화!")

                            # ★ RL Agent에게 오프닝 빌드 조언 구하기 (게임 시작 시 1회) ★
                            if self.bot.train_mode and hasattr(self.bot, "rl_agent") and self.bot.rl_agent:
                                # 초기 상태로 제안 받기 (0 벡터라도 무관 - 초기 성향)
                                # 간단히 action_labels[0] 등을 쓰는 대신, 랜덤 또는 epsilon 탐험 이용
                                # 여기서는 RL Agent의 get_action을 호출하여 초기 전략 결정
                                try:
                                    import numpy as np
                                    dummy_state = np.zeros(15) # 초기화 전이라 0
                                    _, action_label, _ = self.bot.rl_agent.get_action(dummy_state, training=True)

                                    from build_order_system import BuildOrderType
                                    new_build = None

                                    if action_label == "ECONOMY":
                                        new_build = BuildOrderType.ECONOMY_15HATCH
                                    elif action_label == "AGGRESSIVE":
                                        # 50% 확률로 10pool 또는 Roach Rush
                                        if np.random.random() < 0.5:
                                            new_build = BuildOrderType.AGGRESSIVE_10POOL
                                        else:
                                            new_build = BuildOrderType.ROACH_RUSH
                                    elif action_label == "DEFENSIVE":
                                        new_build = BuildOrderType.SAFE_14POOL # or LURKER??
                                    elif action_label == "TECH":
                                        if np.random.random() < 0.5:
                                            new_build = BuildOrderType.MUTALISK_RUSH
                                        else:
                                            new_build = BuildOrderType.HYDRA_TIMING
                                    elif action_label == "ALL_IN":
                                        new_build = BuildOrderType.STANDARD_12POOL # or Baneling Bust logic

                                    if new_build:
                                        self.bot.build_order_system.current_build_order = new_build
                                        self.bot.build_order_system._setup_build_order() # 재설정
                                        print(f"[RL_OPENING] RLAgent initialized build: {new_build.value} (Action: {action_label})")

                                except Exception as e:
                                    print(f"[WARNING] Failed to set RL opening: {e}")

                        except Exception as e:
                            if error_handler.debug_mode:
                                raise
                            else:
                                error_handler.error_counts["BuildOrderInit"] += 1
                                if error_handler.error_counts["BuildOrderInit"] <= error_handler.max_error_logs:
                                    print(f"[ERROR] Build Order initialization error: {e}")
                            self.bot.build_order_system = None
                    else:
                        # BuildOrderSystem not available
                        self.bot.build_order_system = None

                if hasattr(self.bot, "build_order_system") and self.bot.build_order_system:
                    start_time = self._logic_tracker.start_logic("BuildOrder")
                    try:
                        await self.bot.build_order_system.execute(iteration)
                        # 주기적으로 진행도 출력
                        if iteration % 150 == 0:
                            progress = self.bot.build_order_system.get_progress()
                            print(f"[BUILD_ORDER] {progress}")
                    except Exception as e:
                        if error_handler.debug_mode:
                            raise
                        else:
                            error_handler.error_counts["BuildOrder"] += 1
                            if error_handler.error_counts["BuildOrder"] <= error_handler.max_error_logs:
                                print(f"[ERROR] Build Order error: {e}")
                    finally:
                        self._logic_tracker.end_logic("BuildOrder", start_time)

            # 0.05 ★★★ DefenseCoordinator (통합 방어 시스템 - 최우선) ★★★
            if hasattr(self.bot, "defense_coordinator") and self.bot.defense_coordinator:
                start_time = self._logic_tracker.start_logic("DefenseCoordinator")
                try:
                    await self.bot.defense_coordinator.execute(iteration)
                    # 주기적으로 상태 출력
                    if iteration % 100 == 0:
                        status = self.bot.defense_coordinator.get_status()
                        threat = self.bot.blackboard.threat.level.name if self.bot.blackboard else "UNKNOWN"
                        print(f"[DEFENSE] Threat: {threat}, Status: {status}")
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["DefenseCoordinator"] += 1
                        if error_handler.error_counts["DefenseCoordinator"] <= error_handler.max_error_logs:
                            print(f"[ERROR] DefenseCoordinator error: {e}")
                finally:
                    self._logic_tracker.end_logic("DefenseCoordinator", start_time)

            # 0.048 ★★★ EarlyDefenseSystem (0-3분 러시 전용 방어) ★★★
            if self.bot.time < 180 and hasattr(self.bot, "early_defense") and self.bot.early_defense:
                start_time = self._logic_tracker.start_logic("EarlyDefense")
                try:
                    await self.bot.early_defense.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["EarlyDefense"] = error_handler.error_counts.get("EarlyDefense", 0) + 1
                        if error_handler.error_counts["EarlyDefense"] <= error_handler.max_error_logs:
                            print(f"[ERROR] EarlyDefense error: {e}")
                finally:
                    self._logic_tracker.end_logic("EarlyDefense", start_time)

            # 0.051 ★★★ Worker Combat System (Early Rush Defense) ★★★
            if hasattr(self.bot, "worker_combat") and self.bot.worker_combat:
                start_time = self._logic_tracker.start_logic("WorkerCombat")
                try:
                    await self.bot.worker_combat.on_step()
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["WorkerCombat"] = error_handler.error_counts.get("WorkerCombat", 0) + 1
                        if error_handler.error_counts["WorkerCombat"] <= error_handler.max_error_logs:
                            print(f"[ERROR] WorkerCombat error: {e}")
                finally:
                    self._logic_tracker.end_logic("WorkerCombat", start_time)

            # 0.052 ★★★ Strict Upgrade Priority (업그레이드 우선순위) ★★★
            if hasattr(self.bot, "upgrade_priority") and self.bot.upgrade_priority:
                start_time = self._logic_tracker.start_logic("UpgradePriority")
                try:
                    await self.bot.upgrade_priority.on_step()
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["UpgradePriority"] = error_handler.error_counts.get("UpgradePriority", 0) + 1
                        if error_handler.error_counts["UpgradePriority"] <= error_handler.max_error_logs:
                            print(f"[ERROR] UpgradePriority error: {e}")
                finally:
                    self._logic_tracker.end_logic("UpgradePriority", start_time)

            # 0.055 ★★★ RL Tech Adapter (적 테크 기반 적응) ★★★
            if hasattr(self.bot, "rl_tech_adapter") and self.bot.rl_tech_adapter:
                start_time = self._logic_tracker.start_logic("RLTechAdapter")
                try:
                    await self.bot.rl_tech_adapter.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["RLTechAdapter"] += 1
                        if error_handler.error_counts["RLTechAdapter"] <= error_handler.max_error_logs:
                            print(f"[ERROR] RLTechAdapter error: {e}")
                finally:
                    self._logic_tracker.end_logic("RLTechAdapter", start_time)

            # 0.057 ★★★ Micro Focus Mode (전투 우선순위 동적 할당) ★★★
            micro_interval = 8  # 기본 간격
            if hasattr(self.bot, "micro_focus") and self.bot.micro_focus:
                start_time = self._logic_tracker.start_logic("MicroFocusMode")
                try:
                    micro_interval = self.bot.micro_focus.update(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["MicroFocusMode"] += 1
                        if error_handler.error_counts["MicroFocusMode"] <= error_handler.max_error_logs:
                            print(f"[ERROR] MicroFocusMode error: {e}")
                finally:
                    self._logic_tracker.end_logic("MicroFocusMode", start_time)

            # 0.058 ★★★ Dynamic Resource Balancer (자원 불균형 조정) ★★★
            if hasattr(self.bot, "resource_balancer") and self.bot.resource_balancer:
                start_time = self._logic_tracker.start_logic("ResourceBalancer")
                try:
                    ratio_adjustments = self.bot.resource_balancer.update(iteration)

                    # ★ OPTIMIZED: Store in bot for all systems to use
                    self.bot.current_gas_ratio = ratio_adjustments.get("gas_unit_ratio", 0.50)
                    self.bot.resource_state = ratio_adjustments.get("state", "BALANCED")
                    self.bot.mineral_excess = ratio_adjustments.get("mineral_excess", False)
                    self.bot.gas_shortage = ratio_adjustments.get("gas_shortage", False)

                    # UnitFactory에 조정된 비율 전달
                    if hasattr(self.bot, "unit_factory") and self.bot.unit_factory:
                        self.bot.unit_factory.gas_unit_ratio_target = self.bot.current_gas_ratio
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["ResourceBalancer"] += 1
                        if error_handler.error_counts["ResourceBalancer"] <= error_handler.max_error_logs:
                            print(f"[ERROR] ResourceBalancer error: {e}")
                finally:
                    self._logic_tracker.end_logic("ResourceBalancer", start_time)

            # 0.059 ★★★ Smart Resource Balancer (실시간 일꾼 재배치) ★★★
            if hasattr(self.bot, "smart_balancer") and self.bot.smart_balancer:
                start_time = self._logic_tracker.start_logic("SmartBalancer")
                try:
                    await self.bot.smart_balancer.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["SmartBalancer"] += 1
                        if error_handler.error_counts["SmartBalancer"] <= error_handler.max_error_logs:
                            print(f"[ERROR] SmartBalancer error: {e}")
                finally:
                    self._logic_tracker.end_logic("SmartBalancer", start_time)

            # 0.059 ★★★ INSTANT Air Threat Response (치명적 공중 유닛 즉시 대응) ★★★
            if iteration % 11 == 0:  # 매 0.5초마다 체크 (빠른 반응)
                try:
                    from sc2.ids.unit_typeid import UnitTypeId
                    enemy_units = getattr(self.bot, "enemy_units", None)
                    enemy_structures = getattr(self.bot, "enemy_structures", None)

                    if enemy_units and enemy_structures:
                        # Carrier 감지 → 즉시 Corruptor 생산
                        if enemy_units(UnitTypeId.CARRIER).exists:
                            if self.bot.can_afford(UnitTypeId.CORRUPTOR) and self.bot.larva.exists:
                                larva = self.bot.larva.first
                                self.bot.do(larva.train(UnitTypeId.CORRUPTOR))
                                print(f"[INSTANT_AIR] Carrier detected! Building Corruptor")

                        # Stargate 감지 → Hydralisk Den 건설 준비
                        elif enemy_structures(UnitTypeId.STARGATE).exists:
                            hydra_den = self.bot.structures(UnitTypeId.HYDRALISKDEN)
                            if not hydra_den.exists and not self.bot.already_pending(UnitTypeId.HYDRALISKDEN):
                                if self.bot.can_afford(UnitTypeId.HYDRALISKDEN):
                                    lair_or_hive = self.bot.structures.of_type([UnitTypeId.LAIR, UnitTypeId.HIVE])
                                    if lair_or_hive.ready.exists:
                                        await self.bot.build(UnitTypeId.HYDRALISKDEN, near=lair_or_hive.ready.first)
                                        print(f"[INSTANT_AIR] Stargate detected! Building Hydralisk Den")

                        # Battlecruiser 감지 → 즉시 Corruptor 대량 생산
                        elif enemy_units(UnitTypeId.BATTLECRUISER).exists:
                            corruptor_count = self.bot.units(UnitTypeId.CORRUPTOR).amount
                            if corruptor_count < 12 and self.bot.can_afford(UnitTypeId.CORRUPTOR):
                                for larva in self.bot.larva[:3]:  # 최대 3마리 동시 생산
                                    self.bot.do(larva.train(UnitTypeId.CORRUPTOR))
                                print(f"[INSTANT_AIR] Battlecruiser detected! Mass Corruptor production")
                except Exception as e:
                    # Silent fail - 즉각 대응이므로 에러가 critical하지 않음
                    pass

            # 0.060 ★★★ Dynamic Counter System (적 유닛 즉시 카운터) ★★★
            if hasattr(self.bot, "dynamic_counter") and self.bot.dynamic_counter:
                start_time = self._logic_tracker.start_logic("DynamicCounter")
                try:
                    await self.bot.dynamic_counter.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["DynamicCounter"] += 1
                        if error_handler.error_counts["DynamicCounter"] <= error_handler.max_error_logs:
                            print(f"[ERROR] DynamicCounter error: {e}")
                finally:
                    self._logic_tracker.end_logic("DynamicCounter", start_time)

            # 0.061 ★★★ Creep Highway Manager (기지 간 연결) ★★★
            if hasattr(self.bot, "creep_highway") and self.bot.creep_highway:
                start_time = self._logic_tracker.start_logic("CreepHighway")
                try:
                    await self.bot.creep_highway.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["CreepHighway"] += 1
                        if error_handler.error_counts["CreepHighway"] <= error_handler.max_error_logs:
                            print(f"[ERROR] CreepHighway error: {e}")
                finally:
                    self._logic_tracker.end_logic("CreepHighway", start_time)

            # 0.062 ★★★ SpellCaster Automation (마법 유닛 자동화) ★★★
            if hasattr(self.bot, "spellcaster") and self.bot.spellcaster:
                start_time = self._logic_tracker.start_logic("SpellCaster")
                try:
                    await self.bot.spellcaster.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["SpellCaster"] += 1
                        if error_handler.error_counts["SpellCaster"] <= error_handler.max_error_logs:
                            print(f"[ERROR] SpellCaster error: {e}")
                finally:
                    self._logic_tracker.end_logic("SpellCaster", start_time)

            # DEPRECATED: ActiveScoutingSystem replaced by AdvancedScoutingSystemV2
            # 0.063 ★★★ Active Scouting System (능동형 정찰) ★★★
            # if hasattr(self.bot, "active_scout") and self.bot.active_scout:
            #     start_time = self._logic_tracker.start_logic("ActiveScout")
            #     try:
            #         await self.bot.active_scout.on_step(iteration)
            #     except Exception as e:
            #         if error_handler.debug_mode:
            #             raise
            #         else:
            #             error_handler.error_counts["ActiveScout"] += 1
            #             if error_handler.error_counts["ActiveScout"] <= error_handler.max_error_logs:
            #                 print(f"[ERROR] ActiveScout error: {e}")
            #     finally:
            #         self._logic_tracker.end_logic("ActiveScout", start_time)

            # 0.064 ★★★ Upgrade Coordination System (업그레이드 타이밍) ★★★
            if hasattr(self.bot, "upgrade_coord") and self.bot.upgrade_coord:
                start_time = self._logic_tracker.start_logic("UpgradeCoord")
                try:
                    await self.bot.upgrade_coord.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["UpgradeCoord"] += 1
                        if error_handler.error_counts["UpgradeCoord"] <= error_handler.max_error_logs:
                            print(f"[ERROR] UpgradeCoord error: {e}")
                finally:
                    self._logic_tracker.end_logic("UpgradeCoord", start_time)

            # 0.06 ★★★ Early Scout System (초반 정찰) ★★★
            if self.bot.time < 300.0:  # 5분 이내
                if not hasattr(self.bot, "early_scout"):
                    try:
                        from early_scout_system import EarlyScoutSystem
                        self.bot.early_scout = EarlyScoutSystem(self.bot)
                        print("[EARLY_SCOUT] 초반 정찰 시스템 활성화!")
                    except ImportError as e:
                        print(f"[WARNING] Early scout system not available: {e}")
                        self.bot.early_scout = None

                if hasattr(self.bot, "early_scout") and self.bot.early_scout:
                    start_time = self._logic_tracker.start_logic("EarlyScout")
                    try:
                        await self.bot.early_scout.execute(iteration)
                        # 주기적으로 상태 출력
                        if iteration % 150 == 0:
                            status = self.bot.early_scout.get_scout_status()
                            print(f"[EARLY_SCOUT] {status}")
                    except Exception as e:
                        if error_handler.debug_mode:
                            raise
                        else:
                            error_handler.error_counts["EarlyScout"] += 1
                            if error_handler.error_counts["EarlyScout"] <= error_handler.max_error_logs:
                                print(f"[ERROR] Early Scout error: {e}")
                    finally:
                        self._logic_tracker.end_logic("EarlyScout", start_time)

            # 0.061 ★★★ Advanced Scouting System V2 (개선판 - Overseer + Changeling) ★★★
            if hasattr(self.bot, "advanced_scout_v2") and self.bot.advanced_scout_v2:
                start_time = self._logic_tracker.start_logic("AdvancedScoutV2")
                try:
                    await self.bot.advanced_scout_v2.on_step(iteration)
                    # 주기적으로 정찰 리포트 출력
                    if iteration % 660 == 0:  # ~30초마다
                        report = self.bot.advanced_scout_v2.get_scout_report()
                        print(f"[ADVANCED_SCOUT_V2] Ling:{report['zergling_patrol_count']}, "
                              f"Overlord:{report['overlord_scout_count']}, "
                              f"Overseer:{report['overseer_count']}, "
                              f"Changeling:{report['changeling_count']}, "
                              f"Interval:{report['current_interval']:.0f}s, "
                              f"InfoAge:{report['enemy_info_age']:.0f}s")
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["AdvancedScoutV2"] = error_handler.error_counts.get("AdvancedScoutV2", 0) + 1
                        if error_handler.error_counts["AdvancedScoutV2"] <= error_handler.max_error_logs:
                            print(f"[ERROR] AdvancedScoutV2 error: {e}")
                finally:
                    self._logic_tracker.end_logic("AdvancedScoutV2", start_time)

            # 0.062 ★★★ Build Order Optimizer (Phase 9 - 빌드 최적화) ★★★
            if hasattr(self.bot, "build_order_opt") and self.bot.build_order_opt:
                start_time = self._logic_tracker.start_logic("BuildOrderOpt")
                try:
                    await self.bot.build_order_opt.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["BuildOrderOpt"] = error_handler.error_counts.get("BuildOrderOpt", 0) + 1
                        if error_handler.error_counts["BuildOrderOpt"] <= error_handler.max_error_logs:
                            print(f"[ERROR] BuildOrderOpt error: {e}")
                finally:
                    self._logic_tracker.end_logic("BuildOrderOpt", start_time)

            # 0.063 ★★★ 1-Min Multi Test (Phase 9 - 타이밍 검증) ★★★
            if hasattr(self.bot, "multi_test") and self.bot.multi_test:
                start_time = self._logic_tracker.start_logic("MultiTest")
                try:
                    await self.bot.multi_test.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["MultiTest"] = error_handler.error_counts.get("MultiTest", 0) + 1
                        if error_handler.error_counts["MultiTest"] <= error_handler.max_error_logs:
                            print(f"[ERROR] MultiTest error: {e}")
                finally:
                    self._logic_tracker.end_logic("MultiTest", start_time)

            # 0.1 Strategy Manager 업데이트 (종족별 전략 + Emergency Mode)
            if hasattr(self.bot, "strategy_manager") and self.bot.strategy_manager:
                start_time = self._logic_tracker.start_logic("Strategy")
                try:
                    # Debug: 매니저 호출 확인
                    if iteration == 1 or iteration % 500 == 0:
                        print(f"[DEBUG] Calling strategy_manager.update() at iteration {iteration}")
                    self.bot.strategy_manager.update()

                    # Phase 18: Smart Surrender Check
                    if hasattr(self.bot.strategy_manager, "check_surrender"):
                        if self.bot.strategy_manager.check_surrender(self.bot.time):
                             print("[SURRENDER] StrategyManager requested surrender.")
                             await self.bot.chat_send("gg")
                             await self.bot.client.leave()
                             return
                             
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["StrategyManager"] += 1
                        if error_handler.error_counts["StrategyManager"] <= error_handler.max_error_logs:
                            print(f"[ERROR] Strategy Manager error: {e}")
                finally:
                    self._logic_tracker.end_logic("Strategy", start_time)
            else:
                if iteration == 1:
                    print(f"[WARNING] strategy_manager not found! hasattr={hasattr(self.bot, 'strategy_manager')}, value={getattr(self.bot, 'strategy_manager', None)}")

            # 0.15 ★ Defeat Detection (패배 직감 시스템) ★
            if hasattr(self.bot, "defeat_detection") and self.bot.defeat_detection:
                start_time = self._logic_tracker.start_logic("DefeatDetection")
                try:
                    defeat_status = await self.bot.defeat_detection.on_step(iteration)

                    # ★★★ 패배 불가피 시 게임 포기 (훈련 효율 향상) ★★★
                    if defeat_status.get("should_surrender", False):
                        game_time = getattr(self.bot, "time", 0)
                        reason = defeat_status.get("defeat_reason", "알 수 없음")
                        print(f"\n[SURRENDER] ★★★ 게임 포기! ★★★")
                        print(f"  - 게임 시간: {int(game_time)}초")
                        print(f"  - 이유: {reason}")
                        print(f"  - 다음 게임으로 이동...\n")

                        # ★ SC2 매너 채팅: GG 선언 ★
                        await self.bot.chat_send("gg")
                        await asyncio.sleep(1.0) # 채팅 전송 대기

                        # SC2 게임 종료
                        try:
                            await self.bot.client.leave()
                        except Exception as leave_error:
                            print(f"[ERROR] 게임 종료 실패: {leave_error}")

                        return  # on_step 즉시 종료

                    # 패배 직전이면 마지막 방어 시도
                    if defeat_status.get("last_stand_required", False):
                        if iteration % 200 == 0:  # 주기적으로 출력
                            print(f"[DEFEAT DETECTION] ★ 패배 직전! 마지막 방어 시도! ★")
                            print(f"  - 패배 수준: {self.bot.defeat_detection.get_defeat_level_name()}")
                            print(f"  - 이유: {defeat_status.get('defeat_reason', '알 수 없음')}")

                        # Combat Manager에게 마지막 방어 위치 전달
                        if hasattr(self.bot, "combat") and self.bot.combat:
                            last_stand_pos = defeat_status.get("last_stand_position")
                            if last_stand_pos and hasattr(self.bot.combat, "_defense_rally_point"):
                                self.bot.combat._defense_rally_point = last_stand_pos
                                self.bot.combat._base_defense_active = True

                    # 패배 불가피하면 항복 고려 (훈련 모드에서는 빠른 게임 종료)
                    elif defeat_status.get("should_surrender", False):
                        if iteration % 200 == 0:
                            print(f"[DEFEAT DETECTION] 패배 불가피 - {defeat_status.get('defeat_reason', '알 수 없음')}")

                    # 위기 상황이면 경고
                    elif defeat_status.get("defeat_level", 0) >= 2:  # CRITICAL
                        if iteration % 300 == 0:
                            print(f"[DEFEAT DETECTION] 위기 상황! - {defeat_status.get('defeat_reason', '알 수 없음')}")

                except Exception as e:
                    if iteration % 200 == 0:
                        print(f"[WARNING] Defeat Detection error: {e}")
                finally:
                    self._logic_tracker.end_logic("DefeatDetection", start_time)

            # ★ NEW: Chat Manager - 상대방 항복/채팅 감지 (10프레임마다) ★
            if iteration % 10 == 0:
                await self._handle_chat_interaction()

            # 1. Intel (정보 수집)
            await self._safe_manager_step(self.bot.intel, iteration, "Intel")

            # 1.5 ★★★ Opponent Modeling (Phase 15 - 적 학습 및 전략 예측) ★★★
            if hasattr(self.bot, "opponent_modeling") and self.bot.opponent_modeling:
                start_time = self._logic_tracker.start_logic("OpponentModeling")
                try:
                    # Update opponent modeling with current game state
                    await self.bot.opponent_modeling.on_step(iteration)

                    # Log strategy prediction every 30 seconds
                    if iteration % 660 == 0:  # ~30 seconds at 22 FPS
                        predicted_strategy, confidence = self.bot.opponent_modeling.get_predicted_strategy()
                        if predicted_strategy and confidence > 0.3:
                            print(f"[OPPONENT_MODELING] Strategy: {predicted_strategy} ({confidence:.1%} confidence)")
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["OpponentModeling"] = error_handler.error_counts.get("OpponentModeling", 0) + 1
                        if error_handler.error_counts["OpponentModeling"] <= error_handler.max_error_logs:
                            print(f"[ERROR] OpponentModeling error: {e}")
                finally:
                    self._logic_tracker.end_logic("OpponentModeling", start_time)

            # 2. Scouting (정찰) - DEPRECATED: Use AdvancedScoutingSystemV2 instead
            # await self._safe_manager_step(self.bot.scout, iteration, "Scouting")

            # 2.2. Creep Manager (점막 계획)
            # ★ Skip if CreepAutomationV2 is active (avoid duplicate creep commands)
            if not (hasattr(self.bot, "creep_v2") and self.bot.creep_v2):
                await self._safe_manager_step(
                    getattr(self.bot, "creep_manager", None),
                    iteration,
                    "Creep manager",
                )

            # 2.5 Tech Coordinator (테크 건물 건설 조정) ★
            # Production 전에 테크 건설 요청을 처리
            if self.bot.tech_coordinator:
                start_time = self._logic_tracker.start_logic("TechCoordinator")
                try:
                    await self.bot.tech_coordinator.update()
                except Exception as e:
                    print(f"[ERROR] TechCoordinator error: {e}")
                finally:
                    self._logic_tracker.end_logic("TechCoordinator", start_time)

            # 2.9 Unit Authority Manager (Phase 10)
            if hasattr(self.bot, "unit_authority"):
                await self.bot.unit_authority.on_step(iteration)

            # 3. ProductionController (통합 생산 관리 - Dynamic Authority) ★★★
            # Blackboard 생산 큐를 우선순위에 따라 처리
            if hasattr(self.bot, "production_controller") and self.bot.production_controller:
                start_time = self._logic_tracker.start_logic("ProductionController")
                try:
                    await self.bot.production_controller.execute(iteration)

                    # 주기적으로 통계 출력
                    if iteration % 200 == 0:
                        stats = self.bot.production_controller.get_production_stats()
                        print(f"[PRODUCTION] Authority: {stats['authority_mode']}, Queue: {stats['queue_size']}")
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["ProductionController"] += 1
                        if error_handler.error_counts["ProductionController"] <= error_handler.max_error_logs:
                            print(f"[ERROR] ProductionController error: {e}")
                finally:
                    self._logic_tracker.end_logic("ProductionController", start_time)

            # 3.5 Unit Factory (기존 시스템 - ProductionController와 협력)
            # TODO: 점진적으로 ProductionController로 이관
            if hasattr(self.bot, "unit_factory") and self.bot.unit_factory:
                start_time = self._logic_tracker.start_logic("UnitFactory")
                try:
                    # UnitFactory는 이제 Blackboard에 생산 요청만 등록
                    # 실제 생산은 ProductionController가 처리
                    await self.bot.unit_factory.on_step(iteration)
                except Exception as e:
                    if iteration % 200 == 0:
                        print(f"[WARNING] Unit factory error: {e}")
                finally:
                    self._logic_tracker.end_logic("UnitFactory", start_time)

            # 3.6 Economy Manager - Overlord Priority (Army -> Overlord -> Strategy)
            # 대군주 생산을 전략/드론보다 우선순위에 둠
            if hasattr(self.bot, "economy") and self.bot.economy:
                # _train_overlord_if_needed 메서드 직접 호출
                train_ov_method = getattr(self.bot.economy, "_train_overlord_if_needed", None)
                if train_ov_method:
                     await train_ov_method()

            # 4. Production (생산)
            if self.bot.production:
                start_time = self._logic_tracker.start_logic("Production")
                success = True
                try:
                    # ProductionResilience의 메서드 호출
                    if hasattr(self.bot.production, "fix_production_bottleneck"):
                        await self.bot.production.fix_production_bottleneck()
                except Exception as e:
                    success = False
                    print(f"[WARNING] Production error: {e}")
                finally:
                    self._logic_tracker.end_logic("Production", start_time, success)

            # 4.2 Aggressive Strategies (초반 공격 전략) - ★ MOVED AFTER PRODUCTION ★
            # Production과 UnitFactory 이후 실행하여 애벌레 경쟁 최소화
            if iteration % 4 == 0:  # 4프레임마다 실행
                await self._safe_manager_step(
                    getattr(self.bot, "aggressive_strategies", None),
                    iteration,
                    "Aggressive Strategies",
                    method_name="execute",
                )

            # 4.95 ★ OPTIMIZED: Advanced Worker Optimizer BEFORE Economy ★
            # Worker optimization runs FIRST so economy can use saturation data
            if hasattr(self.bot, "worker_optimizer") and self.bot.worker_optimizer:
                start_time = self._logic_tracker.start_logic("WorkerOptimizer")
                try:
                    await self.bot.worker_optimizer.on_step(iteration)

                    # 주기적으로 효율성 보고서 출력 (1분마다)
                    if iteration % 1320 == 0:
                        report = self.bot.worker_optimizer.get_efficiency_report()
                        print(report)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["WorkerOptimizer"] = error_handler.error_counts.get("WorkerOptimizer", 0) + 1
                        if error_handler.error_counts["WorkerOptimizer"] <= error_handler.max_error_logs:
                            print(f"[ERROR] WorkerOptimizer error: {e}")
                finally:
                    self._logic_tracker.end_logic("WorkerOptimizer", start_time)

            # 5. Economy (경제) - ★ MOVED AFTER ARMY PRODUCTION & WORKER OPT ★
            # Worker optimizer가 먼저 실행되어 최적 saturation 계산
            # 전투 병력 생산 후 남은 애벌레로 드론 생산
            await self._safe_manager_step(self.bot.economy, iteration, "Economy")

            # ★ Phase 21: 확장 타이밍 모니터링 (50초마다) ★
            if iteration % 1100 == 0:  # Every 50 seconds
                self._check_expansion_status()

            # 5.1 ★★★ Queen Inject Optimizer (Phase 8 - 완벽한 Inject) ★★★
            if hasattr(self.bot, "queen_inject_opt") and self.bot.queen_inject_opt:
                start_time = self._logic_tracker.start_logic("QueenInjectOpt")
                try:
                    await self.bot.queen_inject_opt.on_step(iteration)
                    # 주기적으로 효율성 출력
                    if iteration % 1320 == 0:  # ~1분마다
                        stats = self.bot.queen_inject_opt.get_inject_stats()
                        print(f"[QUEEN_INJECT] Efficiency: {stats['inject_efficiency']*100:.1f}%, "
                              f"Total: {stats['total_injects']}, "
                              f"Queens: {stats['queens_assigned']}")
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["QueenInjectOpt"] = error_handler.error_counts.get("QueenInjectOpt", 0) + 1
                        if error_handler.error_counts["QueenInjectOpt"] <= error_handler.max_error_logs:
                            print(f"[ERROR] QueenInjectOpt error: {e}")
                finally:
                    self._logic_tracker.end_logic("QueenInjectOpt", start_time)

            # 5.2 ★★★ Queen Transfusion Manager (Phase 21 - Smart Healing) ★★★
            if hasattr(self.bot, "queen_transfusion") and self.bot.queen_transfusion:
                start_time = self._logic_tracker.start_logic("QueenTransfusion")
                try:
                    # Get available queens (defense/flexible role queens with energy)
                    from sc2.ids.unit_typeid import UnitTypeId
                    queens = self.bot.units(UnitTypeId.QUEEN)

                    # Get damaged friendly units (biological only)
                    damaged_units = self.bot.units.filter(
                        lambda u: u.is_biological and u.health_percentage < 0.6
                    )

                    if queens and damaged_units:
                        await self.bot.queen_transfusion.execute_transfusions(
                            queens, damaged_units, iteration
                        )

                    # Log statistics periodically
                    self.bot.queen_transfusion.log_statistics(iteration)

                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["QueenTransfusion"] = error_handler.error_counts.get("QueenTransfusion", 0) + 1
                        if error_handler.error_counts["QueenTransfusion"] <= error_handler.max_error_logs:
                            print(f"[ERROR] QueenTransfusion error: {e}")
                finally:
                    self._logic_tracker.end_logic("QueenTransfusion", start_time)

            # 5.3 ★★★ Resource Manager (Phase 21 - Race Condition Prevention) ★★★
            if hasattr(self.bot, "resource_manager") and self.bot.resource_manager:
                try:
                    # Log statistics periodically
                    self.bot.resource_manager.log_statistics(iteration)

                    # Clear stale reservations (safety mechanism)
                    if iteration % 220 == 0:  # Every 10 seconds
                        await self.bot.resource_manager.clear_stale_reservations(iteration)

                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["ResourceManager"] = error_handler.error_counts.get("ResourceManager", 0) + 1
                        if error_handler.error_counts["ResourceManager"] <= error_handler.max_error_logs:
                            print(f"[ERROR] ResourceManager error: {e}")

            # 5.4 ★★★ Spatial Query Optimizer (Phase 21 - Performance) ★★★
            if hasattr(self.bot, "spatial_query") and self.bot.spatial_query:
                try:
                    # Clear cache at start of frame
                    self.bot.spatial_query.clear_cache_if_needed(iteration)

                    # Log statistics periodically
                    self.bot.spatial_query.log_statistics(iteration)

                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["SpatialQuery"] = error_handler.error_counts.get("SpatialQuery", 0) + 1
                        if error_handler.error_counts["SpatialQuery"] <= error_handler.max_error_logs:
                            print(f"[ERROR] SpatialQuery error: {e}")

            # 5.5 ★★★ Overlord Vision Network (Phase 8 - 시야 네트워크) ★★★
            if hasattr(self.bot, "vision_network") and self.bot.vision_network:
                start_time = self._logic_tracker.start_logic("VisionNetwork")
                try:
                    await self.bot.vision_network.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["VisionNetwork"] = error_handler.error_counts.get("VisionNetwork", 0) + 1
                        if error_handler.error_counts["VisionNetwork"] <= error_handler.max_error_logs:
                            print(f"[ERROR] VisionNetwork error: {e}")
                finally:
                    self._logic_tracker.end_logic("VisionNetwork", start_time)

            # 5.3 ★★★ Advanced Creep Automation V2 (Phase 8 - 고급 크립) ★★★
            if hasattr(self.bot, "creep_v2") and self.bot.creep_v2:
                start_time = self._logic_tracker.start_logic("CreepV2")
                try:
                    await self.bot.creep_v2.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["CreepV2"] = error_handler.error_counts.get("CreepV2", 0) + 1
                        if error_handler.error_counts["CreepV2"] <= error_handler.max_error_logs:
                            print(f"[ERROR] CreepV2 error: {e}")
                finally:
                    self._logic_tracker.end_logic("CreepV2", start_time)

            # 4.5. Evolution Upgrades (공방 업그레이드)
            await self._safe_manager_step(
                getattr(self.bot, "upgrade_manager", None),
                iteration,
                "Upgrade manager",
            )

            # 4.6 ★ NEW: Upgrade Resource Planner (업그레이드 자원 계획) ★
            if hasattr(self.bot, "upgrade_planner") and self.bot.upgrade_planner:
                start_time = self._logic_tracker.start_logic("UpgradePlanner")
                try:
                    await self.bot.upgrade_planner.on_step(iteration)

                    # 주기적으로 보고서 출력 (30초마다)
                    if iteration % 660 == 0:
                        report = self.bot.upgrade_planner.get_upgrade_progress_report()
                        print(report)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["UpgradePlanner"] = error_handler.error_counts.get("UpgradePlanner", 0) + 1
                        if error_handler.error_counts["UpgradePlanner"] <= error_handler.max_error_logs:
                            print(f"[ERROR] UpgradePlanner error: {e}")
                finally:
                    self._logic_tracker.end_logic("UpgradePlanner", start_time)

            # 5. Advanced Building Manager (최신 개선 사항)
            if hasattr(self.bot, "advanced_building_manager"):
                start_time = self._logic_tracker.start_logic("AdvancedBuilding")
                success = True
                try:
                    # 자원 적체 시 처리
                    if iteration % 22 == 0:  # 매 1초마다
                        surplus_results = (
                            await self.bot.advanced_building_manager.handle_resource_surplus()
                        )
                        if surplus_results and iteration % 100 == 0:
                            print(f"[RESOURCE SURPLUS] Handled: {surplus_results}")

                    # 방어 건물 최적 위치에 건설 - ★ 3베이스 이후에만! ★
                    if iteration % 44 == 0:  # 매 2초마다
                        # ★ CRITICAL: 초반 확장 우선! 3분 이후 + 3베이스 이후에만 방어 건물 건설 ★
                        game_time = getattr(self.bot, "time", 0)
                        base_count = self.bot.townhalls.amount if hasattr(self.bot, "townhalls") else 1
                        if game_time >= 180 and base_count >= 3:
                            await self.bot.advanced_building_manager.build_defense_buildings_optimally()
                except Exception as e:
                    success = False
                    if iteration % 200 == 0:
                        print(f"[WARNING] Advanced Building Manager error: {e}")
                finally:
                    self._logic_tracker.end_logic("AdvancedBuilding", start_time, success)

            # 6. Aggressive Tech Builder (최신 개선 사항)
            if hasattr(self.bot, "aggressive_tech_builder"):
                start_time = self._logic_tracker.start_logic("AggressiveTech")
                success = True
                try:
                    # 자원이 넘칠 때 테크 건설
                    if iteration % 22 == 0:  # 매 1초마다
                        has_excess, _, _ = (
                            self.bot.aggressive_tech_builder.has_excess_resources()
                        )
                        if has_excess:
                            recommendations = (
                                await self.bot.aggressive_tech_builder.recommend_tech_builds()
                            )
                            for tech_type, base_supply, priority in recommendations:
                                await self.bot.aggressive_tech_builder.build_tech_aggressively(
                                    tech_type,
                                    lambda: self._build_tech(tech_type),
                                    base_supply,
                                    priority,
                                )
                except Exception as e:
                    success = False
                    if iteration % 200 == 0:
                        print(f"[WARNING] Aggressive Tech Builder error: {e}")
                finally:
                    self._logic_tracker.end_logic("AggressiveTech", start_time, success)

            # 6.5. 긴급 방어 로직 (Strategy Manager 연동)
            await self._handle_emergency_defense(iteration)

            # 7. Queen Manager (여왕 관리)
            await self._safe_manager_step(self.bot.queen_manager, iteration, "Queen Manager")

            # 8. Combat (전투) - 단일 호출 (방어 모드 자동 감지)
            await self._safe_manager_step(self.bot.combat, iteration, "Combat")

            # 8.03 ★ NEW: Idle Unit Manager (유휴 유닛 괴롭힘) ★
            if hasattr(self.bot, "idle_units") and self.bot.idle_units:
                start_time = self._logic_tracker.start_logic("IdleUnits")
                try:
                    await self.bot.idle_units.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["IdleUnits"] = error_handler.error_counts.get("IdleUnits", 0) + 1
                        if error_handler.error_counts["IdleUnits"] <= error_handler.max_error_logs:
                            print(f"[ERROR] IdleUnits error: {e}")
                finally:
                    self._logic_tracker.end_logic("IdleUnits", start_time)

            # 8.05 ★ NEW: Combat Phase Controller (전투 단계별 컨트롤) ★
            if hasattr(self.bot, "combat_phase") and self.bot.combat_phase:
                start_time = self._logic_tracker.start_logic("CombatPhase")
                try:
                    await self.bot.combat_phase.on_step(iteration)

                    # 주기적으로 전투 보고서 출력 (30초마다)
                    if iteration % 660 == 0:
                        report = self.bot.combat_phase.get_combat_report()
                        print(report)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["CombatPhase"] = error_handler.error_counts.get("CombatPhase", 0) + 1
                        if error_handler.error_counts["CombatPhase"] <= error_handler.max_error_logs:
                            print(f"[ERROR] CombatPhase error: {e}")
                finally:
                    self._logic_tracker.end_logic("CombatPhase", start_time)

            # 8.1 ★★★ Harassment Coordinator (Phase 9 - 견제 시스템) ★★★
            if hasattr(self.bot, "harassment_coord") and self.bot.harassment_coord:
                start_time = self._logic_tracker.start_logic("HarassmentCoord")
                try:
                    await self.bot.harassment_coord.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["HarassmentCoord"] = error_handler.error_counts.get("HarassmentCoord", 0) + 1
                        if error_handler.error_counts["HarassmentCoord"] <= error_handler.max_error_logs:
                            print(f"[ERROR] HarassmentCoord error: {e}")
                finally:
                    self._logic_tracker.end_logic("HarassmentCoord", start_time)

            # 8.2 ★★★ Multi-Prong Attack (Phase 8 - 다방향 공격) ★★★
            if hasattr(self.bot, "multi_prong") and self.bot.multi_prong:
                start_time = self._logic_tracker.start_logic("MultiProng")
                try:
                    await self.bot.multi_prong.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["MultiProng"] = error_handler.error_counts.get("MultiProng", 0) + 1
                        if error_handler.error_counts["MultiProng"] <= error_handler.max_error_logs:
                            print(f"[ERROR] MultiProng error: {e}")
                finally:
                    self._logic_tracker.end_logic("MultiProng", start_time)

            # 8.3 ★★★ Trade Efficiency Analyzer (Phase 8 - 교환 효율) ★★★
            if hasattr(self.bot, "trade_analyzer") and self.bot.trade_analyzer:
                start_time = self._logic_tracker.start_logic("TradeAnalyzer")
                try:
                    await self.bot.trade_analyzer.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["TradeAnalyzer"] = error_handler.error_counts.get("TradeAnalyzer", 0) + 1
                        if error_handler.error_counts["TradeAnalyzer"] <= error_handler.max_error_logs:
                            print(f"[ERROR] TradeAnalyzer error: {e}")
                finally:
                    self._logic_tracker.end_logic("TradeAnalyzer", start_time)

            # 9. Spell Units (Infestor/Viper)
            await self._safe_manager_step(
                getattr(self.bot, "spell_manager", None),
                iteration,
                "Spell manager",
                method_name="update",
            )

            # ★ NEW: Unit Morph Manager (Baneling/Ravager/Lurker/Broodlord) ★
            await self._safe_manager_step(
                getattr(self.bot, "morph_manager", None),
                iteration,
                "Morph manager",
            )

            # ★ NEW: Protoss Counter System (DT/Oracle/Disruptor/Immortal/Prism) ★
            await self._safe_manager_step(
                getattr(self.bot, "protoss_counter", None),
                iteration,
                "Protoss counter",
            )

            # ★ NEW: Multi-Base Defense System (모든 확장 기지 방어) ★
            await self._safe_manager_step(
                getattr(self.bot, "multi_base_defense", None),
                iteration,
                "Multi-base defense",
            )

            # 10. Micro Control (마이크로 컨트롤)
            # ★ NEW: Focus Mode Trigger ★
            if hasattr(self.bot, "micro") and self.bot.micro:
                is_focused = False
                # 1. 인텔 매니저 확인 (공격 받는 중)
                if hasattr(self.bot, "intel") and self.bot.intel and self.bot.intel.is_under_attack():
                    is_focused = True
                
                # 2. 공격 중인지 확인 (CombatManager 상태)
                if not is_focused and hasattr(self.bot, "combat") and hasattr(self.bot.combat, "is_engaging"):
                     if self.bot.combat.is_engaging: # 전투 중
                         is_focused = True

                # Focus Mode 설정
                if hasattr(self.bot.micro, "set_focus_mode"):
                    self.bot.micro.set_focus_mode(is_focused)

            # ★ MicroV3가 활성이면 Boids Micro 스킵 (명령 덮어쓰기 방지) ★
            if not (hasattr(self.bot, "micro_v3") and self.bot.micro_v3):
                await self._safe_manager_step(self.bot.micro, iteration, "Micro")

            # 10.1 ★★★ Advanced Micro Controller V3 (Phase 15 - 고급 마이크로) ★★★
            if hasattr(self.bot, "micro_v3") and self.bot.micro_v3:
                start_time = self._logic_tracker.start_logic("MicroV3")
                try:
                    await self.bot.micro_v3.on_step(iteration)

                    # Log micro status every 60 seconds
                    if iteration % 1320 == 0:  # ~60 seconds at 22 FPS
                        status = self.bot.micro_v3.get_status()
                        print(f"[MICRO_V3] Ravagers: {len(status.get('ravager_cooldowns', {}))}, "
                              f"Lurkers burrowed: {len(status.get('lurker_burrowed', {}))}, "
                              f"Focus fire: {len(status.get('focus_fire_assignments', {}))} assignments")
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["MicroV3"] = error_handler.error_counts.get("MicroV3", 0) + 1
                        if error_handler.error_counts["MicroV3"] <= error_handler.max_error_logs:
                            print(f"[ERROR] MicroV3 error: {e}")
                finally:
                    self._logic_tracker.end_logic("MicroV3", start_time)

            # 10.5 Advanced Scouting V2 (Phase 10)
            # ★ REMOVED: 0.061에서 이미 실행됨 (중복 호출 방지) ★
            # if hasattr(self.bot, "advanced_scout_v2"):
            #     await self._safe_manager_step(self.bot.advanced_scout_v2, iteration, "AdvancedScoutV2")

            # 11. Rogue Tactics (이병렬 선수 전술 - 맹독충 드랍 등)
            if iteration % 8 == 0:  # 8프레임마다 실행
                await self._safe_manager_step(
                    getattr(self.bot, "rogue_tactics", None),
                    iteration,
                    "Rogue Tactics",
                    method_name="update",
                )

            # 12. Hierarchical RL System (계층적 강화학습 - 전략 결정)
            if iteration % 22 == 0:  # 매 1초마다 전략 결정
                await self._safe_hierarchical_rl_step(iteration)

            # 12.1 ★★★ Late Game Composition Optimizer (Phase 8 - 후반 조합) ★★★
            if hasattr(self.bot, "late_game_opt") and self.bot.late_game_opt:
                start_time = self._logic_tracker.start_logic("LateGameOpt")
                try:
                    await self.bot.late_game_opt.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["LateGameOpt"] = error_handler.error_counts.get("LateGameOpt", 0) + 1
                        if error_handler.error_counts["LateGameOpt"] <= error_handler.max_error_logs:
                            print(f"[ERROR] LateGameOpt error: {e}")
                finally:
                    self._logic_tracker.end_logic("LateGameOpt", start_time)

            # 12.2 ★★★ Adaptive Build Order AI (Phase 8 - 적응형 빌드) ★★★
            if hasattr(self.bot, "adaptive_build") and self.bot.adaptive_build:
                start_time = self._logic_tracker.start_logic("AdaptiveBuild")
                try:
                    await self.bot.adaptive_build.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["AdaptiveBuild"] = error_handler.error_counts.get("AdaptiveBuild", 0) + 1
                        if error_handler.error_counts["AdaptiveBuild"] <= error_handler.max_error_logs:
                            print(f"[ERROR] AdaptiveBuild error: {e}")
                finally:
                    self._logic_tracker.end_logic("AdaptiveBuild", start_time)

            # 12.3 ★★★ Timing Attacks Library (Phase 8 - 타이밍 공격) ★★★
            if hasattr(self.bot, "timing_attacks") and self.bot.timing_attacks:
                start_time = self._logic_tracker.start_logic("TimingAttacks")
                try:
                    await self.bot.timing_attacks.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["TimingAttacks"] = error_handler.error_counts.get("TimingAttacks", 0) + 1
                        if error_handler.error_counts["TimingAttacks"] <= error_handler.max_error_logs:
                            print(f"[ERROR] TimingAttacks error: {e}")
                finally:
                    self._logic_tracker.end_logic("TimingAttacks", start_time)

            # 12.4 ★★★ Proxy Hatchery Tactics (Phase 8 - 프록시 전술) ★★★
            if hasattr(self.bot, "proxy_hatch") and self.bot.proxy_hatch:
                start_time = self._logic_tracker.start_logic("ProxyHatch")
                try:
                    await self.bot.proxy_hatch.on_step(iteration)
                except Exception as e:
                    if error_handler.debug_mode:
                        raise
                    else:
                        error_handler.error_counts["ProxyHatch"] = error_handler.error_counts.get("ProxyHatch", 0) + 1
                        if error_handler.error_counts["ProxyHatch"] <= error_handler.max_error_logs:
                            print(f"[ERROR] ProxyHatch error: {e}")
                finally:
                    self._logic_tracker.end_logic("ProxyHatch", start_time)

            # 13. Transformer Decision (트랜스포머 의사결정 - 고급 패턴 인식)
            if iteration % 44 == 0:  # 매 2초마다
                await self._safe_transformer_step(iteration)

            # NOTE: Scouting과 Creep Manager는 이미 위에서 실행됨 (Line 303, 306)
            # 중복 실행 방지를 위해 제거됨 (2026-01-25)

            # 14. 실시간 로직 활성화 보고
            game_time = getattr(self.bot, "time", 0)
            report = self._logic_tracker.get_activity_report(game_time)
            if report:
                print(report)

            # 15. ★ 화면 디버그 정보 표시 ★
            if iteration % 4 == 0:  # 4프레임마다 갱신
                await self.draw_debug_info()

        except Exception as e:
            if error_handler.debug_mode:
                print(f"\n[ERROR] Game logic execution error in DEBUG_MODE")
                raise
            else:
                error_handler.error_counts["GameLogic"] += 1
                if error_handler.error_counts["GameLogic"] <= error_handler.max_error_logs:
                    print(f"[ERROR] Game logic execution error: {e}")
        finally:
            # Performance Optimizer 프레임 종료
            if hasattr(self.bot, "performance_optimizer") and self.bot.performance_optimizer:
                try:
                    self.bot.performance_optimizer.end_frame()
                except (AttributeError, TypeError, RuntimeError) as e:
                    # Silently ignore end_frame errors - performance tracking is non-critical
                    pass

    def _cleanup_dead_unit_authorities(self):
        """죽은 유닛의 권한 자동 해제"""
        if not hasattr(self.bot, "unit_authority"):
            return

        try:
            # 각 시스템별로 죽은 유닛 권한 해제
            system_names = [
                "scouting", "harassment_coord", "multi_prong_coord",
                "combat_manager", "spell_unit_manager", "economy_manager"
            ]

            for system_name in system_names:
                system = getattr(self.bot, system_name, None)
                if not system:
                    continue

                # 시스템이 unit_tags 또는 active_scouts 속성을 가지고 있으면
                if hasattr(system, "unit_tags"):
                    for unit_tag in list(system.unit_tags):
                        unit = self.bot.units.find_by_tag(unit_tag)
                        if not unit:  # 유닛이 죽었음
                            self.bot.unit_authority.release_unit(unit_tag, system_name)
                            system.unit_tags.discard(unit_tag)

                # AdvancedScoutingV2의 active_scouts 처리
                if hasattr(system, "active_scouts"):
                    for unit_tag in list(system.active_scouts.keys()):
                        unit = self.bot.units.find_by_tag(unit_tag)
                        if not unit:  # 유닛이 죽었음
                            self.bot.unit_authority.release_unit(unit_tag, system_name)
                            del system.active_scouts[unit_tag]

        except Exception as e:
            # Silent fail - 권한 해제는 critical하지 않음
            pass

    async def draw_debug_info(self):
        """화면 좌측 상단에 봇 상태 디버그 정보 표시"""
        try:
            b = self.bot
            client = getattr(b, "client", None)
            if not client or not hasattr(client, "debug_text_screen"):
                return

            # 1. 기본 정보 (자원, 인구, 기지)
            minerals = int(b.minerals)
            gas = int(b.vespene)
            supply = f"{int(b.supply_used)}/{int(b.supply_cap)}"
            bases = b.townhalls.amount if hasattr(b, "townhalls") else 0
            workers = b.workers.amount if hasattr(b, "workers") else 0

            # 2. 전략 상태
            strategy_mode = "DEFAULT"
            if hasattr(b, "strategy_manager") and b.strategy_manager:
                strategy_mode = str(b.strategy_manager.current_mode).split('.')[-1]
                if hasattr(b, "strategy_manager") and getattr(b.strategy_manager, "emergency_spine_requested", False):
                    strategy_mode += " (EMERGENCY)"

            # 3. 확장 상태 (ProductionResilience)
            expand_status = "Unknown"
            if hasattr(b, "production") and b.production and hasattr(b.production, "_can_expand_safely"):
                 try:
                     can_expand, reason = b.production._can_expand_safely()
                     if can_expand:
                         expand_status = "Ready"
                     else:
                         expand_status = f"Blocked ({reason})"
                 except (AttributeError, TypeError, ValueError) as e:
                     # Expansion check failed, use default status
                     expand_status = "Unknown"
                     if iteration % 1000 == 0:  # Log occasionally
                         print(f"[DEBUG] Expansion check error: {e}")

            # 4. 텍스트 표시
            debug_text = f"""
            [WickedZergBot Pro]
            Time: {int(b.time // 60)}:{int(b.time % 60):02d}
            Strategy: {strategy_mode}

            Resources: M {minerals} / G {gas}
            Supply: {supply}
            Eco: {bases} Bases / {workers} Drones

            Expansion: {expand_status}
            """

            # 화면 좌측 상단 (0.01, 0.01)에 표시
            client.debug_text_screen(debug_text, pos=(0.01, 0.01), size=12, color=(0, 255, 0))

            # 패배 직감 상태가 있다면 표시
            if hasattr(b, "defeat_detection") and b.defeat_detection:
                status = b.defeat_detection._get_current_status()
                level = status.get("defeat_level", 0)
                if level > 0:
                    defeat_text = f"Danger Level: {level} ({status.get('defeat_reason', '')})"
                    client.debug_text_screen(defeat_text, pos=(0.01, 0.2), size=12, color=(255, 0, 0))

            # debug_send 메서드가 있는 경우에만 호출
            if hasattr(client, "debug_send"):
                await client.debug_send()
        except (AttributeError, TypeError, RuntimeError) as e:
            # 디버그 정보 표시 실패는 조용히 무시 (debug display is non-critical)
            pass

    async def _safe_manager_step(
        self, manager, iteration: int, label: str, method_name: str = "on_step"
    ) -> None:
        """
        안전한 매니저 실행 (error_handler + Logic Optimizer 통합)

        1. Logic Optimizer로 실행 여부 결정
        2. error_handler가 DEBUG_MODE에 따라 자동으로 처리:
           - DEBUG_MODE=True: 즉시 크래시 (개발)
           - DEBUG_MODE=False: 로그 후 계속 (프로덕션)
        """
        if not manager:
            return

        # ★★★ Logic Optimizer: 실행 여부 결정 ★★★
        if hasattr(self.bot, "logic_optimizer") and self.bot.logic_optimizer:
            if not self.bot.logic_optimizer.should_execute_system(label, iteration):
                return  # 이번 프레임은 스킵

        method = getattr(manager, method_name, None)
        if not method:
            return

        start_time = self._logic_tracker.start_logic(label)
        success = True

        try:
            await method(iteration)
        except Exception as e:
            success = False
            if error_handler.debug_mode:
                # DEBUG_MODE: 즉시 크래시
                print(f"\n[ERROR] {label} failed in DEBUG_MODE - crashing for debugging")
                print(f"[ERROR] Exception: {e}")
                raise
            else:
                # 프로덕션 모드: 로그 후 계속
                error_handler.error_counts[label] += 1
                if error_handler.error_counts[label] <= error_handler.max_error_logs:
                    print(f"[ERROR] {label} error: {e}")
                    if error_handler.error_counts[label] == error_handler.max_error_logs:
                        print(f"[ERROR] {label}: Suppressing further error logs")
        finally:
            self._logic_tracker.end_logic(label, start_time, success)

    async def _safe_hierarchical_rl_step(self, iteration: int) -> None:
        """계층적 강화학습 시스템 실행 (RL Agent 연동 완료)"""
        if not hasattr(self.bot, "hierarchical_rl") or self.bot.hierarchical_rl is None:
            return

        start_time = self._logic_tracker.start_logic("HierarchicalRL")
        success = True
        try:
            override_strategy = None
            rl_decision_used = False

            # ★★★ RLAgent 최우선: 게임 상태와 선택된 전략을 기록 ★★★
            if hasattr(self.bot, "rl_agent") and self.bot.rl_agent:
                try:
                    import numpy as np

                    # === 1. Feature Engineering (15차원 상태 벡터) ===
                    # ★ 모든 필드가 실제 게임 정보로 채워짐 (0.0 없음) ★

                    # 적 기지 수
                    enemy_bases = 0
                    if hasattr(self.bot, "enemy_structures"):
                        # Count all enemy townhall types (Hatchery/CC/Nexus etc)
                        from sc2.ids.unit_typeid import UnitTypeId
                        townhall_types = {
                            UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE,
                            UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS,
                            UnitTypeId.NEXUS
                        }
                        enemy_bases = sum(1 for s in self.bot.enemy_structures if s.type_id in townhall_types)

                    # 업그레이드 수
                    upgrade_count = 0
                    if hasattr(self.bot, "state") and self.bot.state.upgrades:
                        upgrade_count = len(self.bot.state.upgrades)

                    # 라바 수
                    larva_count = 0
                    if hasattr(self.bot, "larva"):
                        larva_count = len(self.bot.larva)

                    # 군대 체력 합계 (전투력 지표)
                    our_army_hp = 0
                    if hasattr(self.bot, "units"):
                        combat_units = self.bot.units.filter(lambda u: u.type_id not in [UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.LARVA, UnitTypeId.EGG])
                        our_army_hp = sum(u.health for u in combat_units)

                    enemy_army_hp = 0
                    if hasattr(self.bot, "enemy_units"):
                        enemy_army_hp = sum(u.health for u in self.bot.enemy_units)

                    # 맵 장악력 (HierarchicalRL 메서드 재사용)
                    map_control = 0.5
                    if hasattr(self.bot.hierarchical_rl, "_calculate_map_control"):
                        map_control = self.bot.hierarchical_rl._calculate_map_control(self.bot)

                    game_state = np.array([
                        getattr(self.bot, "minerals", 0) / 2000.0,
                        getattr(self.bot, "vespene", 0) / 1000.0,
                        getattr(self.bot, "supply_used", 0) / 200.0,
                        getattr(self.bot, "supply_cap", 0) / 200.0,
                        len(getattr(self.bot, "workers", [])) / 100.0,
                        len(getattr(self.bot, "units", [])) / 100.0,
                        len(getattr(self.bot, "enemy_units", [])) / 100.0,
                        len(getattr(self.bot, "townhalls", [])) / 10.0,
                        getattr(self.bot, "time", 0) / 1000.0,
                        # ★ COMPLETE: Filled Features (6 dims) - NO MORE 0.0! ★
                        enemy_bases / 5.0,        # 적 기지 수
                        upgrade_count / 10.0,     # 업그레이드 진척도
                        larva_count / 20.0,       # 라바 가용량
                        map_control,              # 맵 장악력 (0~1)
                        our_army_hp / 5000.0,     # 아군 전투력
                        enemy_army_hp / 5000.0    # 적군 전투력
                    ], dtype=np.float32)

                    # ★ 상태 벡터 로깅 (30초마다) - 실제 값 확인 ★
                    if iteration % 660 == 0:  # 30초
                        print(f"[RL_STATE] 게임 상태 벡터 (15차원):")
                        print(f"  미네랄: {game_state[0]:.3f}, 가스: {game_state[1]:.3f}")
                        print(f"  서플라이: {game_state[2]:.3f}/{game_state[3]:.3f}")
                        print(f"  일꾼: {game_state[4]:.3f}, 유닛: {game_state[5]:.3f}, 적 유닛: {game_state[6]:.3f}")
                        print(f"  기지: {game_state[7]:.3f}, 시간: {game_state[8]:.3f}")
                        print(f"  적 기지: {game_state[9]:.3f}, 업그레이드: {game_state[10]:.3f}, 라바: {game_state[11]:.3f}")
                        print(f"  맵 장악: {game_state[12]:.3f}, 아군 HP: {game_state[13]:.3f}, 적군 HP: {game_state[14]:.3f}")

                    # ★★★ CRITICAL: RLAgent에게 행동 결정 요청 (최우선) ★★★
                    # 학습 모드 = train_mode, 추론 모드 = not train_mode
                    training = getattr(self.bot, 'train_mode', True)
                    action_idx, action_label, prob = self.bot.rl_agent.get_action(game_state, training=training)

                    # ★ Time-based Control Handoff (시간 기반 제어권 전환) ★
                    # 초반 5분(300초): Rule-based decision 우선 (기본 전략 학습)
                    # 5분 이후: RLAgent 결정 우선 (학습된 전략 활용)
                    if self.bot.time < 300.0:
                        override_strategy = None  # Rule-based decision 사용
                        rl_decision_used = False
                        if iteration % 220 == 0:
                            print(f"[RL_DECISION] ⏰ Early game: Rule-based (RLAgent training: ε={self.bot.rl_agent.epsilon:.3f})")
                    else:
                        # ★ RLAgent의 결정을 무조건 따름 ★
                        override_strategy = action_label
                        rl_decision_used = True
                        # ★ 결정 로깅 (10초마다) ★
                        if iteration % 220 == 0:
                            mode = "TRAINING" if training else "INFERENCE"
                            print(f"[RL_DECISION] ★ RLAgent 결정 ({mode}): {action_label} (확률: {prob:.3f}, ε={self.bot.rl_agent.epsilon:.3f}) ★")

                except Exception as e:
                    if error_handler.debug_mode:
                        print(f"[ERROR] RLAgent error in DEBUG_MODE: {e}")
                        raise
                    else:
                        error_handler.error_counts["RLAgent"] += 1
                        if error_handler.error_counts["RLAgent"] <= error_handler.max_error_logs:
                            print(f"[ERROR] RLAgent error: {e}")

            # ★★★ HierarchicalRL 실행 (RL Override 강제 적용) ★★★
            # 이제 순수하게 전략적 결정만 반환함
            result = self.bot.hierarchical_rl.step(self.bot, override_strategy=override_strategy)

            # 전략 모드 적용 (StrategyManager에게 전달)
            if result and "strategy_mode" in result:
                new_mode = result["strategy_mode"]
                current_mode_str = "Unknown"
                
                # StrategyManager에 모드 적용
                if hasattr(self.bot, "strategy_manager") and self.bot.strategy_manager:
                    # StrategyMode Enum 변환 시도
                    from strategy_manager import StrategyMode
                    try:
                        # 문자열(예: "ALL_IN")을 Enum으로 변환
                        mode_enum = StrategyMode[new_mode]
                        
                        # 모드가 변경될 때만 로그 출력 및 적용
                        if self.bot.strategy_manager.current_mode != mode_enum:
                            self.bot.strategy_manager.current_mode = mode_enum
                            if iteration % 100 == 0:
                                print(f"[COMMANDER] ★ 전략 변경: {new_mode} (Auth: {result.get('author', 'Unknown')})")
                    except KeyError:
                        pass # 유효하지 않은 모드 문자열이면 무시
                
                self.bot._current_strategy = new_mode

                # ★ 결정 로깅 (10초마다) ★
                if iteration % 220 == 0:  # 10초마다
                    if rl_decision_used:
                        print(f"[STRATEGY] ★★★ RLAgent 결정 적용: {new_mode} ★★★")
                    else:
                        print(f"[STRATEGY] 규칙 기반 결정: {new_mode} (RLAgent 없음)")

                # ★ 불일치 경고 (RL이 있는데 사용 안 됨) ★
                if hasattr(self.bot, "rl_agent") and self.bot.rl_agent and not rl_decision_used:
                    if iteration % 220 == 0:
                        print(f"[WARNING] ★ RLAgent가 있지만 결정이 사용되지 않음! ★")
                    
        except Exception as e:
            success = False
            if iteration % 200 == 0:
                print(f"[WARNING] Hierarchical RL error: {e}")
        finally:
            self._logic_tracker.end_logic("HierarchicalRL", start_time, success)

    async def _safe_transformer_step(self, iteration: int) -> None:
        """트랜스포머 의사결정 모델 실행"""
        if not hasattr(self.bot, "transformer_model") or self.bot.transformer_model is None:
            return

        start_time = self._logic_tracker.start_logic("Transformer")
        success = True
        try:
            # 게임 상태를 시퀀스로 변환하여 트랜스포머에 입력
            game_state = self._extract_game_state_sequence()
            if game_state:
                prediction = self.bot.transformer_model.predict(game_state)

                # 예측 결과 저장
                if prediction:
                    self.bot._transformer_prediction = prediction
        except Exception as e:
            success = False
            if iteration % 200 == 0:
                print(f"[WARNING] Transformer model error: {e}")
        finally:
            self._logic_tracker.end_logic("Transformer", start_time, success)

    def _extract_game_state_sequence(self) -> list:
        """게임 상태를 시퀀스로 추출 (트랜스포머 입력용)"""
        try:
            sequence = []

            # 자원 상태
            sequence.append(getattr(self.bot, "minerals", 0) / 1000.0)
            sequence.append(getattr(self.bot, "vespene", 0) / 1000.0)

            # 서플라이 상태
            sequence.append(getattr(self.bot, "supply_used", 0) / 200.0)
            sequence.append(getattr(self.bot, "supply_cap", 0) / 200.0)

            # 유닛 수
            if hasattr(self.bot, "units"):
                sequence.append(len(self.bot.units) / 100.0)
            else:
                sequence.append(0.0)

            # 적 유닛 수
            if hasattr(self.bot, "enemy_units"):
                sequence.append(len(self.bot.enemy_units) / 100.0)
            else:
                sequence.append(0.0)

            # 게임 시간
            sequence.append(getattr(self.bot, "time", 0) / 1000.0)

            # 기지 수
            if hasattr(self.bot, "townhalls"):
                sequence.append(len(self.bot.townhalls) / 10.0)
            else:
                sequence.append(0.0)

            return sequence
        except (AttributeError, TypeError, ValueError, KeyError) as e:
            # Return empty sequence if state observation fails
            return []

    def _is_defense_mode(self) -> bool:
        """방어 모드 여부 확인"""
        # Strategy Manager 확인
        if hasattr(self.bot, "strategy_manager") and self.bot.strategy_manager:
            from strategy_manager import StrategyMode
            if self.bot.strategy_manager.current_mode in [StrategyMode.EMERGENCY, StrategyMode.DEFENSIVE]:
                return True

        # Intel Manager 확인
        if hasattr(self.bot, "intel") and self.bot.intel:
            if hasattr(self.bot.intel, "is_major_attack") and self.bot.intel.is_major_attack():
                return True
            if hasattr(self.bot.intel, "is_under_attack") and self.bot.intel.is_under_attack():
                return True

        return False

    async def _handle_emergency_defense(self, iteration: int) -> None:
        """
        긴급 방어 로직 처리

        Strategy Manager가 Emergency/Defense 모드일 때:
        1. 긴급 스파인 크롤러 건설
        2. 긴급 스포어 크롤러 건설
        3. 방어 유닛 우선 생산 신호

        패배 직감 시스템 연동:
        - 패배 직전: 스파인 크롤러 최대 6개까지 긴급 건설
        - 위기 상황: 스파인 크롤러 4개까지 건설
        - 일반: 스파인 크롤러 3개까지 건설
        """
        if iteration % 22 != 0:  # 1초마다 확인
            return

        # Strategy Manager 확인
        strategy = getattr(self.bot, "strategy_manager", None)
        if not strategy:
            return

        game_time = getattr(self.bot, "time", 0)

        # ★ 패배 직감 시스템 연동 ★
        defeat_level = 0
        last_stand_mode = False
        if hasattr(self.bot, "defeat_detection") and self.bot.defeat_detection:
            defeat_status = self.bot.defeat_detection._get_current_status()
            defeat_level = defeat_status.get("defeat_level", 0)
            last_stand_mode = defeat_status.get("last_stand_required", False)

        try:
            # ★ 패배 직전: 스파인 크롤러 최대 6개 ★
            if last_stand_mode or defeat_level >= 3:
                max_spines = 6
                force_build = True
            # ★ 위기 상황: 스파인 크롤러 4개 ★
            elif defeat_level >= 2:
                max_spines = 4
                force_build = True
            # ★ 일반: 스파인 크롤러 3개 ★
            else:
                max_spines = 3
                force_build = False

            # 긴급 스파인 크롤러 건설
            if getattr(strategy, "emergency_spine_requested", False) or force_build:
                if hasattr(self.bot, "structures") and hasattr(self.bot, "townhalls"):
                    from sc2.ids.unit_typeid import UnitTypeId

                    # 스파인 크롤러 현재 수 확인
                    spines = self.bot.structures(UnitTypeId.SPINECRAWLER)
                    spine_count = spines.amount if hasattr(spines, 'amount') else 0
                    pending = self.bot.already_pending(UnitTypeId.SPINECRAWLER)

                    # 스포닝 풀 필요
                    pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
                    if pools.exists and spine_count + pending < max_spines and self.bot.can_afford(UnitTypeId.SPINECRAWLER):
                        if self.bot.townhalls.exists:
                            main_base = self.bot.townhalls.first
                            defense_pos = main_base.position.towards(self.bot.game_info.map_center, 7)
                            await self.bot.build(UnitTypeId.SPINECRAWLER, near=defense_pos)

                            if last_stand_mode:
                                print(f"[LAST STAND] [{int(game_time)}s] ★ 긴급 스파인 크롤러 건설! ({spine_count + pending + 1}/{max_spines}) ★")
                            else:
                                print(f"[EMERGENCY] [{int(game_time)}s] Building emergency Spine Crawler ({spine_count + pending + 1}/{max_spines})")

                            if hasattr(strategy, "emergency_spine_requested"):
                                strategy.emergency_spine_requested = False

            # 긴급 스포어 크롤러 건설 (대공)
            if getattr(strategy, "emergency_spore_requested", False):
                if hasattr(self.bot, "structures") and hasattr(self.bot, "townhalls"):
                    from sc2.ids.unit_typeid import UnitTypeId

                    spores = self.bot.structures(UnitTypeId.SPORECRAWLER)
                    spore_count = spores.amount if hasattr(spores, 'amount') else 0
                    pending = self.bot.already_pending(UnitTypeId.SPORECRAWLER)

                    pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
                    if pools.exists and spore_count + pending < 2 and self.bot.can_afford(UnitTypeId.SPORECRAWLER):
                        if self.bot.townhalls.exists:
                            main_base = self.bot.townhalls.first
                            await self.bot.build(UnitTypeId.SPORECRAWLER, near=main_base.position)
                            print(f"[EMERGENCY] [{int(game_time)}s] Building emergency Spore Crawler!")
                            strategy.emergency_spore_requested = False

            # === 공중 위협 대응: 히드라리스크 굴 건설 ===
            if hasattr(strategy, "is_air_threat_detected") and strategy.is_air_threat_detected():
                await self._build_anti_air_tech(iteration, game_time)

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Emergency defense error: {e}")

    async def _build_anti_air_tech(self, iteration: int, game_time: float) -> None:
        """
        공중 위협 대응 테크 건설 (강화 버전)

        우선순위:
        1. 스포어 크롤러 (모든 기지에 최소 1개, 위협시 2개)
        2. 레어 진화 (히드라 굴 전제 조건)
        3. 히드라리스크 굴 건설
        4. 퀸 추가 생산 요청
        """
        if not hasattr(self.bot, "structures"):
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId

            # === 0. 공중 위협 레벨 계산 ===
            air_threat_level = self._calculate_air_threat_level()

            # === 1. 스포어 크롤러 긴급 건설 (최우선) ===
            spore_target = 2 if air_threat_level >= 2 else 1  # 위협 높으면 기지당 2개

            # 성능 최적화: 루프 외부에서 한 번만 쿼리
            all_spores = self.bot.structures(UnitTypeId.SPORECRAWLER)
            pending_spores = self.bot.already_pending(UnitTypeId.SPORECRAWLER)
            pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready

            for th in self.bot.townhalls:
                # 캐싱된 spore 구조물에서 가까운 것만 필터링
                nearby_spores = all_spores.closer_than(15, th)
                spore_count = nearby_spores.amount if hasattr(nearby_spores, 'amount') else 0

                if spore_count + pending_spores < spore_target and self.bot.can_afford(UnitTypeId.SPORECRAWLER):
                    # 스포닝 풀 확인 (캐싱된 결과 사용)
                    if pools.exists:
                        # 미네랄 라인 근처에 배치 (일꾼 보호)
                        minerals = self.bot.mineral_field.closer_than(10, th)
                        if minerals:
                            mineral_center = minerals.center
                            defense_pos = th.position.towards(mineral_center, 4)
                        else:
                            defense_pos = th.position

                        await self.bot.build(UnitTypeId.SPORECRAWLER, near=defense_pos)
                        print(f"[ANTI-AIR] [{int(game_time)}s] ★ Building Spore Crawler (threat level: {air_threat_level}) ★")
                        return

            # === 2. 레어 진화 확인 (히드라 굴 전제 조건) ===
            lair = self.bot.structures(UnitTypeId.LAIR)
            hive = self.bot.structures(UnitTypeId.HIVE)
            has_lair_or_higher = lair.ready.exists or hive.ready.exists
            lair_pending = self.bot.already_pending(UnitTypeId.LAIR) > 0

            if not has_lair_or_higher and not lair_pending:
                # 해처리에서 레어 진화 시작
                hatcheries = self.bot.structures(UnitTypeId.HATCHERY).ready
                pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
                if hatcheries.exists and pools.exists and self.bot.can_afford(UnitTypeId.LAIR):
                    # idle 해처리 찾기
                    for hatch in hatcheries:
                        if hasattr(hatch, "is_idle") and hatch.is_idle:
                            self.bot.do(hatch(UnitTypeId.LAIR))
                            print(f"[ANTI-AIR] [{int(game_time)}s] ★ Upgrading to Lair for Hydralisk Den ★")
                            return

            # === 3. 히드라리스크 굴 건설 ===
            hydra_dens = self.bot.structures(UnitTypeId.HYDRALISKDEN)
            hydra_pending = self.bot.already_pending(UnitTypeId.HYDRALISKDEN)

            if not hydra_dens.exists and hydra_pending == 0:
                if has_lair_or_higher and self.bot.can_afford(UnitTypeId.HYDRALISKDEN):
                    if self.bot.townhalls.exists:
                        # 점막 체크 헬퍼 사용
                        if self.placement_helper:
                            success = await self.placement_helper.build_structure_safely(
                                UnitTypeId.HYDRALISKDEN,
                                self.bot.townhalls.first.position,
                                max_distance=15.0
                            )
                            if success:
                                print(f"[ANTI-AIR] [{int(game_time)}s] ★★ Building Hydralisk Den for anti-air! ★★")
                                return
                        else:
                            # 폴백: 기존 방식
                            await self.bot.build(UnitTypeId.HYDRALISKDEN, near=self.bot.townhalls.first.position)
                            print(f"[ANTI-AIR] [{int(game_time)}s] ★★ Building Hydralisk Den for anti-air! ★★")
                            return

            # === 4. 히드라 우선 생산 플래그 설정 ===
            if hydra_dens.ready.exists:
                # Unit Factory에 히드라 우선 생산 신호
                if hasattr(self.bot, "unit_factory"):
                    self.bot.unit_factory._force_hydra = True

            # === 5. 퀸 추가 생산 요청 (대공 유닛) ===
            if air_threat_level >= 2:
                if hasattr(self.bot, "queen_manager"):
                    # 퀸 보너스 증가
                    self.bot.queen_manager.creep_queen_bonus = 4  # 3 → 4

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Anti-air tech build error: {e}")

    def _calculate_air_threat_level(self) -> int:
        """
        공중 위협 레벨 계산

        Returns:
            0: 없음
            1: 낮음 (1-2 공중 유닛)
            2: 중간 (3-5 공중 유닛 또는 캐리어/무리군주)
            3: 높음 (6+ 공중 유닛 또는 다수 고위협 유닛)
        """
        if not hasattr(self.bot, "enemy_units"):
            return 0

        air_count = 0
        high_threat_air_count = 0

        high_threat_air = {"CARRIER", "TEMPEST", "MOTHERSHIP", "BATTLECRUISER", "BROODLORD", "VOIDRAY"}

        for enemy in self.bot.enemy_units:
            try:
                if getattr(enemy, "is_flying", False):
                    air_count += 1
                    enemy_type = getattr(enemy.type_id, "name", "").upper()
                    if enemy_type in high_threat_air:
                        high_threat_air_count += 1
            except (AttributeError, TypeError) as e:
                # Skip enemy unit if attributes unavailable
                continue

        # 위협 레벨 결정
        if air_count == 0:
            return 0
        elif high_threat_air_count >= 1 or air_count >= 6:
            return 3
        elif air_count >= 3:
            return 2
        else:
            return 1

    async def _build_tech(self, tech_type):
        """테크 건물 건설 헬퍼 함수"""
        if not hasattr(self.bot, "townhalls"):
            return False
        if not self.bot.townhalls.exists:
            return False

        main_base = self.bot.townhalls.first
        map_center = None
        if hasattr(self.bot, "game_info"):
            map_center = getattr(self.bot.game_info, "map_center", None)
        if map_center is None:
            map_center = main_base.position
        try:
            return await self.bot.build(
                tech_type,
                near=main_base.position.towards(map_center, 5),
            )
        except (AttributeError, TypeError, ValueError) as e:
            # Building placement failed - return False to retry later
            return False

    @error_handler.safe_coroutine(log_key="TrainingLogic", default_return=None)
    async def execute_training_logic(self, iteration: int):
        """훈련 로직 실행 (train_mode=True일 때만)"""
        if not self.bot.train_mode:
            return

        # 보상 시스템 계산
        if hasattr(self.bot, "_reward_system"):
            step_reward = self.bot._reward_system.calculate_step_reward(
                self.bot
            )

            # RL 에이전트 업데이트
            if hasattr(self.bot, "rl_agent") and self.bot.rl_agent:
                self.bot.rl_agent.update_reward(step_reward)

            # 주기적으로 보상 로그 출력
            if iteration % 500 == 0:
                print(f"[TRAINING] Step reward: {step_reward:.3f}")

    async def on_step(self, iteration: int):
        """
        통합 on_step 메서드

        이 메서드는 WickedZergBotPro의 on_step에서 호출됩니다.
        """
        # ★ PERFORMANCE PROFILING: Start frame timing
        profiler = get_profiler(self.bot.logger) if get_profiler else None
        if profiler:
            profiler.start_frame()

        try:
            # 1. 매니저들 초기화 (첫 호출 시)
            await self.initialize_managers()

            # 2. 게임 로직 실행
            await self.execute_game_logic(iteration)

            # 3. 훈련 로직 실행 (train_mode=True일 때만)
            await self.execute_training_logic(iteration)

        except Exception as e:
            if iteration % 100 == 0:
                print(f"[ERROR] on_step execution error: {e}")
                import traceback

                traceback.print_exc()
        finally:
            # ★ PERFORMANCE PROFILING: End frame timing
            if profiler:
                profiler.end_frame()

                # Print performance report every 5 minutes
                if iteration % 6600 == 0:  # ~5 minutes at 22 FPS
                    profiler.print_report()


    async def _handle_chat_interaction(self):
        """
        상대방 채팅 메시지 처리
        - "gg", "surrender" 등 항복 메시지 감지 시 응답
        """
        if not hasattr(self.bot, "state") or not hasattr(self.bot.state, "chat"):
            return

        for chat in self.bot.state.chat:
            # 내 메시지는 무시
            if chat.player_id == self.bot.player_id:
                continue
            
            message = chat.message.lower().strip()
            
            # 항복/GG 메시지 패턴
            surrender_patterns = ["gg", "good game", "surrender", "i quit", "gewonnen", "g.g"]
            
            if any(pattern in message for pattern in surrender_patterns):
                # 이미 응답했는지 확인 (플래그 사용)
                if not getattr(self.bot, "_gg_replied", False):
                    print(f"[CHAT] Opponent surrendered: {chat.message}")
                    await self.bot.chat_send("gg wp")
                    self.bot._gg_replied = True
                    
                    # 훈련 보상에 승리 보너스 추가 가능성 (여기서는 로깅만)
                    print("[CHAT] Detected opponent surrender! Victory imminent.")

def create_on_step_implementation(bot):
    """
    on_step 구현을 생성하는 팩토리 함수

    Usage:
        integrator = create_on_step_implementation(self)
        async def on_step(self, iteration: int):
            await integrator.on_step(iteration)
    """
    return BotStepIntegrator(bot)

