# -*- coding: utf-8 -*-
"""
Logic Optimizer - 전체 시스템 실행 최적화

47개 시스템의 실행을 동적으로 관리:
1. 게임 단계별 시스템 활성화/비활성화
2. 우선순위 기반 실행 순서
3. 적응형 실행 빈도 조정
4. 중복 작업 제거
"""

from typing import Dict, List, Set, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from utils.logger import get_logger


class GamePhase(Enum):
    """게임 단계"""
    OPENING = "opening"          # 0-3분: 빌드 오더
    EARLY = "early"              # 3-6분: 초반 공격/방어
    MID = "mid"                  # 6-12분: 확장 및 테크
    LATE = "late"                # 12분+: 후반전


class SystemPriority(Enum):
    """시스템 우선순위"""
    CRITICAL = 0    # 매 프레임 실행 (Defense, Combat)
    HIGH = 1        # 0.5초마다 (Economy, Production)
    MEDIUM = 2      # 1초마다 (Strategy, Intel)
    LOW = 3         # 2초마다 (Creep, Upgrades)
    MINIMAL = 4     # 5초마다 (Analytics, Stats)


@dataclass
class SystemConfig:
    """시스템 실행 설정"""
    name: str
    priority: SystemPriority
    enabled_phases: Set[GamePhase]
    interval_frames: int  # 실행 간격 (프레임 수)
    condition: Optional[Callable] = None  # 활성화 조건
    last_executed: int = 0


class LogicOptimizer:
    """
    전체 시스템 실행 최적화

    47개 시스템을 효율적으로 관리하여 성능 향상
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("LogicOptimizer")

        # 시스템 설정
        self.systems: Dict[str, SystemConfig] = {}
        self._initialize_system_configs()

        # 성능 추적
        self.total_systems = 0
        self.active_systems = 0
        self.disabled_systems = 0

        # 최적화 통계
        self.frames_saved = 0
        self.cpu_time_saved = 0.0

    def _initialize_system_configs(self):
        """시스템 설정 초기화"""

        # === CRITICAL: 매 프레임 (전투/방어) ===
        self._register_system("DefenseCoordinator", SystemPriority.CRITICAL,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=1)

        self._register_system("Combat", SystemPriority.CRITICAL,
                             {GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=1)

        self._register_system("Micro", SystemPriority.CRITICAL,
                             {GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=1,
                             condition=lambda: self._has_army())

        self._register_system("BattlePrep", SystemPriority.CRITICAL,
                             {GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=2,
                             condition=lambda: self._is_combat_active())

        # === HIGH: 0.5초마다 (경제/생산) ===
        self._register_system("Economy", SystemPriority.HIGH,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=11)  # ~0.5초

        self._register_system("ProductionController", SystemPriority.HIGH,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=11)

        self._register_system("UnitFactory", SystemPriority.HIGH,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=11)

        self._register_system("SmartBalancer", SystemPriority.HIGH,
                             {GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=22,  # 1초
                             condition=lambda: self.bot.vespene > 500 or self.bot.minerals > 1000)

        # === MEDIUM: 1초마다 (전략/정보) ===
        self._register_system("Strategy", SystemPriority.MEDIUM,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=22)

        self._register_system("Intel", SystemPriority.MEDIUM,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=22)

        self._register_system("HierarchicalRL", SystemPriority.MEDIUM,
                             {GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=22)

        self._register_system("DynamicCounter", SystemPriority.MEDIUM,
                             {GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=22,
                             condition=lambda: self._has_enemy_threats())

        self._register_system("BaseDestruction", SystemPriority.MEDIUM,
                             {GamePhase.MID, GamePhase.LATE},
                             interval=22,
                             condition=lambda: self._can_attack())

        # === LOW: 2초마다 (점막/업그레이드) ===
        self._register_system("Creep", SystemPriority.LOW,
                             {GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=44)

        self._register_system("CreepHighway", SystemPriority.LOW,
                             {GamePhase.MID, GamePhase.LATE},
                             interval=44,
                             condition=lambda: self.bot.townhalls.amount >= 2)

        self._register_system("UpgradeCoord", SystemPriority.LOW,
                             {GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=44)

        self._register_system("QueenManager", SystemPriority.LOW,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=44)

        # === MINIMAL: 5초마다 (분석/통계) ===
        self._register_system("Scouting", SystemPriority.MINIMAL,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=110)

        self._register_system("ActiveScout", SystemPriority.MINIMAL,
                             {GamePhase.EARLY, GamePhase.MID},
                             interval=110,
                             condition=lambda: self.bot.time < 600)  # 10분까지만

        self._register_system("DestructibleAware", SystemPriority.MINIMAL,
                             {GamePhase.EARLY, GamePhase.MID},
                             interval=220,
                             condition=lambda: self.bot.time < 480)  # 8분까지만

        # === 특수: 빌드 오더 (5분까지만) ===
        self._register_system("BuildOrder", SystemPriority.CRITICAL,
                             {GamePhase.OPENING},
                             interval=1,
                             condition=lambda: self.bot.time < 300)

        # === 특수: Nydus Network (4분 이후) ===
        self._register_system("NydusTrainer", SystemPriority.MEDIUM,
                             {GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=110,
                             condition=lambda: self.bot.time > 240 and self._has_nydus_network())

        # === 특수: 공격 전략 ===
        self._register_system("AggressiveStrategies", SystemPriority.HIGH,
                             {GamePhase.OPENING, GamePhase.EARLY},
                             interval=4,
                             condition=lambda: self.bot.time < 360)  # 6분까지만

        # === 최적화 시스템 (항상 실행) ===
        self._register_system("SpatialOptimizer", SystemPriority.CRITICAL,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=1)

        self._register_system("DataCache", SystemPriority.CRITICAL,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=1)

        self._register_system("MapMemory", SystemPriority.CRITICAL,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=1)  # 매 프레임 (적 건물 발견 중요)

        self._register_system("SelfHealing", SystemPriority.HIGH,
                             {GamePhase.OPENING, GamePhase.EARLY, GamePhase.MID, GamePhase.LATE},
                             interval=110)  # 5초

        self.total_systems = len(self.systems)
        self.logger.info(f"[INIT] Registered {self.total_systems} systems")

    def _register_system(self, name: str, priority: SystemPriority,
                        enabled_phases: Set[GamePhase], interval: int,
                        condition: Optional[Callable] = None):
        """시스템 등록"""
        self.systems[name] = SystemConfig(
            name=name,
            priority=priority,
            enabled_phases=enabled_phases,
            interval_frames=interval,
            condition=condition
        )

    def should_execute_system(self, system_name: str, iteration: int) -> bool:
        """
        시스템 실행 여부 결정

        조건:
        1. 시스템이 등록되어 있는가?
        2. 현재 게임 단계에서 활성화되어 있는가?
        3. 실행 간격이 지났는가?
        4. 추가 조건을 만족하는가?
        """
        if system_name not in self.systems:
            return True  # 등록되지 않은 시스템은 기본 실행

        config = self.systems[system_name]

        # 1. 게임 단계 확인
        current_phase = self._get_current_phase()
        if current_phase not in config.enabled_phases:
            return False

        # 2. 실행 간격 확인
        if iteration - config.last_executed < config.interval_frames:
            return False

        # 3. 추가 조건 확인
        if config.condition is not None:
            try:
                if not config.condition():
                    return False
            except Exception:
                pass  # 조건 체크 실패 시 실행

        # 실행 기록
        config.last_executed = iteration
        return True

    def _get_current_phase(self) -> GamePhase:
        """현재 게임 단계 반환"""
        game_time = self.bot.time

        if game_time < 180:
            return GamePhase.OPENING
        elif game_time < 360:
            return GamePhase.EARLY
        elif game_time < 720:
            return GamePhase.MID
        else:
            return GamePhase.LATE

    def _has_army(self) -> bool:
        """군대가 있는지 확인"""
        try:
            from sc2.ids.unit_typeid import UnitTypeId
            army = self.bot.units.filter(
                lambda u: u.type_id not in {
                    UnitTypeId.DRONE, UnitTypeId.OVERLORD,
                    UnitTypeId.LARVA, UnitTypeId.EGG
                }
            )
            return army.amount > 5
        except Exception:
            return True

    def _is_combat_active(self) -> bool:
        """전투 중인지 확인"""
        try:
            # Intel Manager 확인
            if hasattr(self.bot, "intel") and self.bot.intel:
                if hasattr(self.bot.intel, "is_under_attack"):
                    if self.bot.intel.is_under_attack():
                        return True

            # 적 유닛 근처 확인
            if self.bot.enemy_units:
                if self.bot.townhalls.exists:
                    main_base = self.bot.townhalls.first
                    nearby_enemies = self.bot.enemy_units.closer_than(20, main_base)
                    return nearby_enemies.amount > 0

            return False
        except Exception:
            return False

    def _has_enemy_threats(self) -> bool:
        """적 위협이 있는지 확인"""
        try:
            if not self.bot.enemy_units:
                return False

            # 고위협 유닛 확인
            from sc2.ids.unit_typeid import UnitTypeId
            threats = {
                UnitTypeId.BATTLECRUISER, UnitTypeId.CARRIER, UnitTypeId.TEMPEST,
                UnitTypeId.SIEGETANK, UnitTypeId.COLOSSUS, UnitTypeId.IMMORTAL,
                UnitTypeId.ULTRALISK, UnitTypeId.THOR
            }

            for enemy in self.bot.enemy_units:
                if enemy.type_id in threats:
                    return True

            return False
        except Exception:
            return False

    def _can_attack(self) -> bool:
        """공격 가능한지 확인"""
        try:
            # 군대가 충분한지
            if not self._has_army():
                return False

            # 기지가 안정적인지
            if self.bot.townhalls.amount < 2:
                return False

            # 자원이 충분한지
            if self.bot.supply_used < 100:
                return False

            return True
        except Exception:
            return False

    def _has_nydus_network(self) -> bool:
        """Nydus Network가 있는지 확인"""
        try:
            from sc2.ids.unit_typeid import UnitTypeId
            networks = self.bot.structures(UnitTypeId.NYDUSNETWORK).ready
            return networks.exists
        except Exception:
            return False

    def get_optimization_stats(self, iteration: int) -> Dict:
        """최적화 통계 반환"""
        current_phase = self._get_current_phase()

        # 현재 활성화된 시스템 수
        active = 0
        disabled = 0

        for config in self.systems.values():
            if current_phase in config.enabled_phases:
                # 조건 체크
                if config.condition is None:
                    active += 1
                else:
                    try:
                        if config.condition():
                            active += 1
                        else:
                            disabled += 1
                    except Exception:
                        active += 1
            else:
                disabled += 1

        self.active_systems = active
        self.disabled_systems = disabled

        # CPU 절약 추정
        cpu_saved_percent = (disabled / self.total_systems * 100) if self.total_systems > 0 else 0

        return {
            "current_phase": current_phase.value,
            "total_systems": self.total_systems,
            "active_systems": active,
            "disabled_systems": disabled,
            "cpu_saved_percent": f"{cpu_saved_percent:.1f}%",
            "iteration": iteration
        }

    def print_optimization_report(self, iteration: int):
        """최적화 보고서 출력"""
        stats = self.get_optimization_stats(iteration)

        self.logger.info(
            f"[OPTIMIZATION] [{int(self.bot.time)}s] Phase: {stats['current_phase']}, "
            f"Active: {stats['active_systems']}/{stats['total_systems']}, "
            f"CPU Saved: {stats['cpu_saved_percent']}"
        )

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        # 20초마다 보고서 출력
        if iteration % 440 == 0:
            self.print_optimization_report(iteration)
