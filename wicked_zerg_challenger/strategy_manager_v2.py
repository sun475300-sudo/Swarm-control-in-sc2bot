# -*- coding: utf-8 -*-
"""
Strategy Manager V2 - Enhanced Strategy Management System

New Features:
1. Win Condition Detection - Identify winning/losing conditions
2. Build Order Transition System - Smooth phase transitions
3. Strategy Scoring System - Evaluate strategy effectiveness
4. Resource Allocation Framework - Priority-based resource distribution
5. Multi-pronged Strategy Execution - Coordinate attack/expand/harass

Inherits from StrategyManager and extends functionality.
"""

from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from strategy_manager import StrategyManager, GamePhase, StrategyMode, EnemyRace
from utils.logger import get_logger

try:
    from config.unit_configs import StrategyConfig
except ImportError:
    StrategyConfig = None


class WinCondition(Enum):
    """승리/패배 조건"""
    UNKNOWN = "unknown"
    WINNING_ECONOMY = "winning_economy"      # 경제 우위
    WINNING_ARMY = "winning_army"            # 군사 우위
    WINNING_TECH = "winning_tech"            # 기술 우위
    LOSING_ECONOMY = "losing_economy"        # 경제 열세
    LOSING_ARMY = "losing_army"              # 군사 열세
    LOSING_TECH = "losing_tech"              # 기술 열세
    EVEN = "even"                            # 균형


class BuildOrderPhase(Enum):
    """빌드 오더 페이즈"""
    OPENING = "opening"          # 0-3분: 초반 개막
    TRANSITION = "transition"    # 3-6분: 중반 전환
    MIDGAME = "midgame"         # 6-10분: 중반 운영
    LATEGAME = "lategame"       # 10분+: 후반 확장


class StrategyPriority(Enum):
    """전략 우선순위"""
    CRITICAL = 5    # 즉시 실행 (생존 관련)
    HIGH = 4        # 높은 우선순위
    MEDIUM = 3      # 보통
    LOW = 2         # 낮음
    OPTIONAL = 1    # 선택적


class StrategyManagerV2(StrategyManager):
    """
    Enhanced Strategy Manager with advanced decision-making

    Key Features:
    - Win condition analysis
    - Build order transitions
    - Strategy effectiveness scoring
    - Resource allocation priorities
    - Multi-strategy coordination
    """

    def __init__(self, bot, blackboard=None):
        """Initialize Strategy Manager V2"""
        super().__init__(bot, blackboard)
        self.logger = get_logger("StrategyManagerV2")

        # Load configuration
        self.config = StrategyConfig() if StrategyConfig else None

        # Win condition tracking
        self.current_win_condition = WinCondition.UNKNOWN
        self.win_condition_history: List[WinCondition] = []
        self.win_condition_update_interval = self.config.WIN_CONDITION_UPDATE_INTERVAL if self.config else 5.0
        self.last_win_condition_check = 0.0

        # Smart Surrender (Phase 18)
        self.surrender_trigger_time = 0
        self.surrender_threshold = 30 # seconds of strong losing


        # Build order system
        self.current_build_phase = BuildOrderPhase.OPENING
        self.build_transition_complete = False
        self.planned_expansions = []
        self.expansion_targets: List[Tuple[float, Any]] = []  # (timing, location)

        # Strategy scoring
        self.strategy_scores: Dict[str, float] = {}
        self.active_strategies: List[Dict[str, Any]] = []

        # Resource allocation (설정값 사용)
        if self.config:
            self.resource_priorities: Dict[str, float] = {
                "economy": self.config.DEFAULT_PRIORITY_ECONOMY,
                "army": self.config.DEFAULT_PRIORITY_ARMY,
                "tech": self.config.DEFAULT_PRIORITY_TECH,
                "defense": self.config.DEFAULT_PRIORITY_DEFENSE
            }
        else:
            self.resource_priorities: Dict[str, float] = {
                "economy": 0.4,
                "army": 0.4,
                "tech": 0.1,
                "defense": 0.1
            }

        # Multi-strategy execution
        self.strategy_queue: List[Dict[str, Any]] = []
        self.concurrent_strategy_limit = self.config.CONCURRENT_STRATEGY_LIMIT if self.config else 3

        # Adaptive Composition (Phase 18)
        self.target_unit_ratios: Dict[str, float] = {}
        self.last_composition_update = 0


        self.logger.info("[STRATEGY_V2] Initialized with enhanced decision-making")

    def update(self) -> None:
        """Enhanced update with V2 features"""
        # Call parent update first
        super().update()

        game_time = getattr(self.bot, "time", 0.0)

        # V2 features
        self._update_win_condition(game_time)
        self._update_build_phase(game_time)
        self._evaluate_strategy_effectiveness()
        self._adjust_resource_priorities()
        self._execute_multi_strategy()
        
        # Phase 18: Adaptive Composition
        self._update_unit_composition(game_time)

        # Phase 18: Smart Surrender
        # await self._check_smart_surrender(game_time) # Async call needs await


        if self.blackboard:
            self.blackboard.set("win_condition", self.current_win_condition.name)
            self.blackboard.set("build_phase", self.current_build_phase.name)
            self.blackboard.set("resource_priorities", self.resource_priorities)
            self.blackboard.set("active_strategies", len(self.active_strategies))

        # Phase 18: Smart Surrender
        self._check_smart_surrender(game_time)

    # ========== WIN CONDITION DETECTION ==========

    def _update_win_condition(self, game_time: float) -> None:
        """
        Analyze game state to determine win condition

        Factors:
        - Worker count vs enemy
        - Base count vs enemy
        - Army supply vs enemy
        - Tech progress vs enemy
        - Map control
        """
        if game_time - self.last_win_condition_check < self.win_condition_update_interval:
            return

        self.last_win_condition_check = game_time

        # Calculate metrics
        economy_score = self._calculate_economy_score()
        army_score = self._calculate_army_score()
        tech_score = self._calculate_tech_score()

        # Determine overall condition (설정값 사용)
        total_score = economy_score + army_score + tech_score

        previous_condition = self.current_win_condition

        if self.config:
            strong_win = self.config.STRONG_WINNING_SCORE
            strong_lose = self.config.STRONG_LOSING_SCORE
            cat_threshold = self.config.SCORE_CATEGORY_THRESHOLD
        else:
            strong_win = 6
            strong_lose = -6
            cat_threshold = 2

        if total_score >= strong_win:  # Strong winning
            if economy_score >= cat_threshold:
                self.current_win_condition = WinCondition.WINNING_ECONOMY
            elif army_score >= cat_threshold:
                self.current_win_condition = WinCondition.WINNING_ARMY
            else:
                self.current_win_condition = WinCondition.WINNING_TECH
        elif total_score <= strong_lose:  # Strong losing
            if economy_score <= -cat_threshold:
                self.current_win_condition = WinCondition.LOSING_ECONOMY
            elif army_score <= -cat_threshold:
                self.current_win_condition = WinCondition.LOSING_ARMY
            else:
                self.current_win_condition = WinCondition.LOSING_TECH
        else:
            self.current_win_condition = WinCondition.EVEN

        # Track history (설정값 사용)
        if self.current_win_condition != previous_condition:
            self.win_condition_history.append(self.current_win_condition)
            history_size = self.config.WIN_CONDITION_HISTORY_SIZE if self.config else 20
            if len(self.win_condition_history) > history_size:
                self.win_condition_history.pop(0)

            self.logger.info(f"[{int(game_time)}s] Win Condition: {self.current_win_condition.name} "
                           f"(Economy: {economy_score:+.1f}, Army: {army_score:+.1f}, Tech: {tech_score:+.1f})")

    def _calculate_economy_score(self) -> float:
        """
        Calculate economy advantage/disadvantage

        Returns:
            Score: +3 (strong advantage) to -3 (strong disadvantage)
        """
        score = 0.0

        # Worker count comparison (설정값 사용)
        our_workers = self._count_workers()
        enemy_workers = self._estimate_enemy_workers()

        if enemy_workers > 0:
            worker_ratio = our_workers / enemy_workers
            if self.config:
                if worker_ratio >= self.config.ECONOMY_WORKER_RATIO_STRONG:
                    score += self.config.ECONOMY_SCORE_STRONG
                elif worker_ratio >= self.config.ECONOMY_WORKER_RATIO_GOOD:
                    score += self.config.ECONOMY_SCORE_GOOD
                elif worker_ratio <= self.config.ECONOMY_WORKER_RATIO_WEAK:
                    score += self.config.ECONOMY_SCORE_WEAK
                elif worker_ratio <= self.config.ECONOMY_WORKER_RATIO_BAD:
                    score += self.config.ECONOMY_SCORE_BAD
            else:
                if worker_ratio >= 1.5:
                    score += 2.0
                elif worker_ratio >= 1.2:
                    score += 1.0
                elif worker_ratio <= 0.7:
                    score -= 2.0
                elif worker_ratio <= 0.8:
                    score -= 1.0

        # Base count comparison (설정값 사용)
        our_bases = self._count_bases()
        enemy_bases = self._estimate_enemy_bases()

        if enemy_bases > 0:
            base_ratio = our_bases / enemy_bases
            if self.config:
                if base_ratio >= self.config.ECONOMY_BASE_RATIO_GOOD:
                    score += self.config.ECONOMY_SCORE_GOOD
                elif base_ratio <= self.config.ECONOMY_BASE_RATIO_BAD:
                    score += self.config.ECONOMY_SCORE_BAD
            else:
                if base_ratio >= 1.5:
                    score += 1.0
                elif base_ratio <= 0.7:
                    score -= 1.0

        return score

    def _calculate_army_score(self) -> float:
        """
        Calculate army advantage/disadvantage

        Returns:
            Score: +3 to -3
        """
        score = 0.0

        # Army supply comparison (설정값 사용)
        our_army_supply = getattr(self.bot, "supply_army", 0)
        enemy_army_supply = self._estimate_enemy_army_supply()

        if enemy_army_supply > 0:
            army_ratio = our_army_supply / enemy_army_supply
            if self.config:
                if army_ratio >= self.config.ARMY_RATIO_OVERWHELMING:
                    score += self.config.ARMY_SCORE_OVERWHELMING
                elif army_ratio >= self.config.ARMY_RATIO_STRONG:
                    score += self.config.ARMY_SCORE_STRONG
                elif army_ratio >= self.config.ARMY_RATIO_GOOD:
                    score += self.config.ARMY_SCORE_GOOD
                elif army_ratio <= self.config.ARMY_RATIO_WEAK:
                    score += self.config.ARMY_SCORE_WEAK
                elif army_ratio <= self.config.ARMY_RATIO_BAD:
                    score += self.config.ARMY_SCORE_BAD
                elif army_ratio <= self.config.ARMY_RATIO_POOR:
                    score += self.config.ARMY_SCORE_POOR
            else:
                if army_ratio >= 2.0:
                    score += 3.0
                elif army_ratio >= 1.5:
                    score += 2.0
                elif army_ratio >= 1.2:
                    score += 1.0
                elif army_ratio <= 0.5:
                    score -= 3.0
                elif army_ratio <= 0.7:
                    score -= 2.0
                elif army_ratio <= 0.8:
                    score -= 1.0

        return score

    def _calculate_tech_score(self) -> float:
        """
        Calculate tech advantage/disadvantage

        Returns:
            Score: +2 to -2
        """
        score = 0.0

        # Count tech buildings (설정값 사용)
        our_tech = self._count_tech_structures()
        enemy_tech = self._estimate_enemy_tech()

        if self.config:
            if our_tech >= enemy_tech + self.config.TECH_DIFF_STRONG:
                score += self.config.TECH_SCORE_STRONG
            elif our_tech >= enemy_tech + self.config.TECH_DIFF_GOOD:
                score += self.config.TECH_SCORE_GOOD
            elif our_tech <= enemy_tech + self.config.TECH_DIFF_BAD:
                score += self.config.TECH_SCORE_BAD
            elif our_tech <= enemy_tech + self.config.TECH_DIFF_POOR:
                score += self.config.TECH_SCORE_POOR
        else:
            if our_tech >= enemy_tech + 2:
                score += 2.0
            elif our_tech >= enemy_tech + 1:
                score += 1.0
            elif our_tech <= enemy_tech - 2:
                score -= 2.0
            elif our_tech <= enemy_tech - 1:
                score -= 1.0

        return score

    def _count_workers(self) -> int:
        """Count our workers"""
        if not hasattr(self.bot, "units"):
            return 0
        try:
            from sc2.ids.unit_typeid import UnitTypeId
            return self.bot.units(UnitTypeId.DRONE).amount
        except (ImportError, AttributeError) as e:
            self.logger.debug(f"Failed to count workers: {e}")
            return 0

    def _estimate_enemy_workers(self) -> int:
        """Estimate enemy worker count (설정값 사용)"""
        default_workers = self.config.DEFAULT_ENEMY_WORKERS if self.config else 16
        if not hasattr(self.bot, "enemy_units"):
            return default_workers

        worker_types = {"SCV", "PROBE", "DRONE", "MULE"}
        count = 0
        for unit in self.bot.enemy_units:
            try:
                if unit.type_id.name.upper() in worker_types:
                    count += 1
            except AttributeError:
                continue

        # If we haven't scouted workers, estimate based on bases (설정값 사용)
        if count == 0:
            enemy_bases = self._estimate_enemy_bases()
            workers_per_base = self.config.DEFAULT_ENEMY_WORKERS if self.config else 16
            count = enemy_bases * workers_per_base

        min_workers = self.config.MIN_ENEMY_WORKERS if self.config else 16
        return max(count, min_workers)

    def _count_bases(self) -> int:
        """Count our bases"""
        if not hasattr(self.bot, "townhalls"):
            return 0
        return self.bot.townhalls.amount

    def _estimate_enemy_bases(self) -> int:
        """Estimate enemy base count (설정값 사용)"""
        default_bases = self.config.DEFAULT_ENEMY_BASES if self.config else 1
        if not hasattr(self.bot, "enemy_structures"):
            return default_bases

        base_types = {
            "COMMANDCENTER", "ORBITALCOMMAND", "PLANETARYFORTRESS",
            "NEXUS", "HATCHERY", "LAIR", "HIVE"
        }

        count = 0
        for structure in self.bot.enemy_structures:
            try:
                if structure.type_id.name.upper() in base_types:
                    count += 1
            except AttributeError:
                continue

        min_bases = self.config.MIN_ENEMY_BASES if self.config else 1
        return max(count, min_bases)

    def _estimate_enemy_army_supply(self) -> int:
        """Estimate enemy army supply (설정값 사용)"""
        default_supply = self.config.DEFAULT_ENEMY_SUPPLY if self.config else 10
        if not hasattr(self.bot, "enemy_units"):
            return default_supply

        supply = 0
        supply_costs = self.config.UNIT_SUPPLY_COSTS if self.config else {
            "MARINE": 1, "MARAUDER": 2, "SIEGETANK": 3, "THOR": 6,
            "ZEALOT": 2, "STALKER": 2, "IMMORTAL": 4, "COLOSSUS": 6,
            "ZERGLING": 0.5, "ROACH": 2, "HYDRALISK": 2, "ULTRALISK": 6,
            "DEFAULT": 2
        }

        for unit in self.bot.enemy_units:
            try:
                if unit.can_attack:
                    unit_name = unit.type_id.name.upper()
                    supply += supply_costs.get(unit_name, supply_costs.get("DEFAULT", 2))
            except AttributeError:
                continue

        min_supply = self.config.MIN_ENEMY_SUPPLY if self.config else 10
        return max(supply, min_supply)

    def _count_tech_structures(self) -> int:
        """Count our tech buildings"""
        if not hasattr(self.bot, "structures"):
            return 0

        try:
            from sc2.ids.unit_typeid import UnitTypeId
            tech_buildings = [
                UnitTypeId.LAIR, UnitTypeId.HIVE,
                UnitTypeId.SPAWNINGPOOL, UnitTypeId.ROACHWARREN,
                UnitTypeId.HYDRALISKDEN, UnitTypeId.SPIRE,
                UnitTypeId.GREATERSPIRE, UnitTypeId.INFESTATIONPIT,
                UnitTypeId.ULTRALISKCAVERN, UnitTypeId.LURKERDENMP
            ]
            count = 0
            for building_type in tech_buildings:
                count += self.bot.structures(building_type).amount
            return count
        except (ImportError, AttributeError) as e:
            self.logger.debug(f"Failed to count tech structures: {e}")
            return 0

    def _estimate_enemy_tech(self) -> int:
        """Estimate enemy tech level (설정값 사용)"""
        default_tech = self.config.DEFAULT_ENEMY_TECH if self.config else 1
        if not hasattr(self.bot, "enemy_structures"):
            return default_tech

        # Count known enemy tech structures
        tech_count = 0
        for structure in self.bot.enemy_structures:
            try:
                name = structure.type_id.name.upper()
                # Tech buildings
                if any(tech in name for tech in [
                    "BARRACKS", "FACTORY", "STARPORT",
                    "GATEWAY", "ROBOTICSFACILITY", "STARGATE",
                    "SPAWNINGPOOL", "ROACHWARREN", "HYDRALISKDEN", "SPIRE"
                ]):
                    tech_count += 1
            except AttributeError:
                continue

        min_tech = self.config.MIN_ENEMY_TECH if self.config else 1
        return max(tech_count, min_tech)

    # ========== BUILD ORDER TRANSITION SYSTEM ==========

    def _update_build_phase(self, game_time: float) -> None:
        """
        Update build order phase based on game time and conditions

        Phases:
        - Opening (0-3min): Early economy, basic army
        - Transition (3-6min): Tech up, prepare for timing
        - Midgame (6-10min): Multi-base economy, army production
        - Lategame (10min+): Max out, endgame units
        """
        previous_phase = self.current_build_phase

        # 페이즈 시간 (설정값 사용)
        if self.config:
            opening_time = self.config.OPENING_PHASE_TIME
            transition_time = self.config.TRANSITION_PHASE_TIME
            midgame_time = self.config.MIDGAME_PHASE_TIME
        else:
            opening_time = 180
            transition_time = 360
            midgame_time = 600

        if game_time < opening_time:
            self.current_build_phase = BuildOrderPhase.OPENING
        elif game_time < transition_time:
            self.current_build_phase = BuildOrderPhase.TRANSITION
        elif game_time < midgame_time:
            self.current_build_phase = BuildOrderPhase.MIDGAME
        else:
            self.current_build_phase = BuildOrderPhase.LATEGAME

        # Trigger transition logic on phase change
        if self.current_build_phase != previous_phase:
            self._execute_build_transition(previous_phase, self.current_build_phase)

    def _execute_build_transition(self, from_phase: BuildOrderPhase, to_phase: BuildOrderPhase) -> None:
        """
        Execute build order transition actions

        Args:
            from_phase: Previous build phase
            to_phase: New build phase
        """
        game_time = getattr(self.bot, "time", 0.0)
        self.logger.info(f"[{int(game_time)}s] BUILD TRANSITION: {from_phase.name} → {to_phase.name}")

        if to_phase == BuildOrderPhase.TRANSITION:
            self._transition_to_midgame()
        elif to_phase == BuildOrderPhase.MIDGAME:
            self._transition_to_aggressive()
        elif to_phase == BuildOrderPhase.LATEGAME:
            self._transition_to_maxout()

    def _transition_to_midgame(self) -> None:
        """Transition actions for mid-game (3-6 min)"""
        self.logger.info("[BUILD] Transitioning to mid-game: Lair + Warren/Den")

        # Priority: Lair, Roach Warren or Hydra Den
        # Economy manager handles actual construction

    def _transition_to_aggressive(self) -> None:
        """Transition to aggressive mid-game (6-10 min) (설정값 사용)"""
        self.logger.info("[BUILD] Transitioning to aggressive: Multi-base + Army production")

        # Plan 3rd base (설정값 사용)
        expansion_time = self.config.TRANSITION_EXPANSION_TIME if self.config else 380
        self._plan_expansion(target_time=expansion_time)

    def _transition_to_maxout(self) -> None:
        """Transition to late-game maxout (10+ min) (설정값 사용)"""
        self.logger.info("[BUILD] Transitioning to late-game: Max out army")

        # Plan 4th+ bases (설정값 사용)
        expansion_time = self.config.LATEGAME_EXPANSION_TIME if self.config else 650
        self._plan_expansion(target_time=expansion_time)

    def _plan_expansion(self, target_time: float) -> None:
        """
        Plan expansion at target time

        Args:
            target_time: Desired expansion timing (seconds)
        """
        self.planned_expansions.append(target_time)
        self.logger.info(f"[BUILD] Expansion planned at {int(target_time)}s")

    # ========== STRATEGY SCORING SYSTEM ==========

    def _evaluate_strategy_effectiveness(self) -> None:
        """
        Evaluate effectiveness of current strategies

        Scoring factors:
        - Resource efficiency
        - Army trades
        - Map control
        - Economic damage to enemy
        """
        game_time = getattr(self.bot, "time", 0.0)

        # Score each active strategy
        for strategy in self.active_strategies:
            strategy_name = strategy.get("name", "unknown")
            score = self._calculate_strategy_score(strategy)
            self.strategy_scores[strategy_name] = score

        # Log periodically (설정값 사용)
        status_interval = self.config.STATUS_PRINT_INTERVAL if self.config else 60
        if int(game_time) % status_interval == 0 and self.bot.iteration % 22 == 0:
            if self.strategy_scores:
                self.logger.info(f"[STRATEGY_SCORES] {self.strategy_scores}")

    def _calculate_strategy_score(self, strategy: Dict[str, Any]) -> float:
        """
        ★ Phase 21.1: 실제 전략 효과 계산 ★

        Calculate effectiveness score for a strategy based on:
        - Kill/Death ratio (교환비)
        - Resource efficiency (자원 효율)
        - Territory control (영토 확보)
        - Enemy production disruption (생산 방해)

        Returns:
            Score: 0.0 (ineffective) to 1.0 (highly effective)
        """
        score = 0.5  # Baseline (neutral)

        # 1. 교환비 계산 (Kill/Death Ratio)
        kill_death_score = self._calculate_kill_death_score()

        # 2. 자원 효율 계산 (Resource Trade Efficiency)
        resource_efficiency_score = self._calculate_resource_efficiency()

        # 3. 영토 확보 계산 (Territory Control)
        territory_score = self._calculate_territory_score()

        # 4. 적 생산 방해 (Enemy Production Disruption)
        disruption_score = self._calculate_disruption_score()

        # 가중 평균 (각 요소에 가중치 적용)
        weights = {
            "kill_death": 0.35,      # 35% - 교환비가 가장 중요
            "resource": 0.25,        # 25% - 자원 효율
            "territory": 0.20,       # 20% - 영토 확보
            "disruption": 0.20       # 20% - 생산 방해
        }

        score = (
            kill_death_score * weights["kill_death"] +
            resource_efficiency_score * weights["resource"] +
            territory_score * weights["territory"] +
            disruption_score * weights["disruption"]
        )

        # 0.0 ~ 1.0 범위로 제한
        return max(0.0, min(1.0, score))

    def _calculate_kill_death_score(self) -> float:
        """
        교환비 점수 계산 (Units Killed vs Lost)

        Returns:
            0.0 (terrible trades) to 1.0 (excellent trades)
        """
        # Blackboard에서 통계 가져오기
        if not self.blackboard:
            return 0.5

        units_killed = getattr(self.blackboard, "units_killed", 0)
        units_lost = getattr(self.blackboard, "units_lost", 0)

        # 아직 전투가 없으면 중립
        if units_killed == 0 and units_lost == 0:
            return 0.5

        # 손실 없이 킬만 있으면 완벽
        if units_lost == 0:
            return 1.0

        # Kill/Death ratio 계산
        kd_ratio = units_killed / max(units_lost, 1)

        # 비율을 0~1 점수로 변환
        # 1:1 = 0.5, 2:1 = 0.75, 3:1 = 0.875, 4:1+ = 1.0
        # 1:2 = 0.25, 1:3 = 0.125
        if kd_ratio >= 4.0:
            return 1.0
        elif kd_ratio >= 2.0:
            return 0.5 + (kd_ratio - 2.0) / 4.0  # 0.5 ~ 1.0
        elif kd_ratio >= 1.0:
            return 0.5 + (kd_ratio - 1.0) / 2.0  # 0.5 ~ 0.75
        else:  # kd_ratio < 1.0
            return kd_ratio * 0.5  # 0.0 ~ 0.5

    def _calculate_resource_efficiency(self) -> float:
        """
        자원 효율 점수 (Resources Traded)

        Returns:
            0.0 (poor efficiency) to 1.0 (excellent efficiency)
        """
        if not self.blackboard:
            return 0.5

        resources_killed = getattr(self.blackboard, "resources_killed", 0)
        resources_lost = getattr(self.blackboard, "resources_lost", 0)

        # 전투 없으면 중립
        if resources_killed == 0 and resources_lost == 0:
            return 0.5

        # 손실 없이 적 자원만 파괴
        if resources_lost == 0:
            return 1.0

        # 자원 교환비
        resource_ratio = resources_killed / max(resources_lost, 1)

        # 1:1 = 0.5, 2:1 = 0.75, 3:1+ = 1.0
        if resource_ratio >= 3.0:
            return 1.0
        elif resource_ratio >= 1.0:
            return 0.5 + (resource_ratio - 1.0) / 4.0
        else:
            return resource_ratio * 0.5

    def _calculate_territory_score(self) -> float:
        """
        영토 확보 점수 (Bases Gained vs Lost)

        Returns:
            0.0 (losing ground) to 1.0 (gaining ground)
        """
        # 현재 기지 수
        our_bases = len(getattr(self.bot, "townhalls", []))

        # 적 기지 수 추정
        if self.blackboard:
            enemy_bases = getattr(self.blackboard, "enemy_base_count", 1)
        else:
            enemy_bases = 1

        # 기지 비율
        base_ratio = our_bases / max(enemy_bases, 1)

        # 1:1 = 0.5, 2:1 = 0.75, 3:1 = 1.0
        if base_ratio >= 2.5:
            return 1.0
        elif base_ratio >= 1.0:
            return 0.5 + (base_ratio - 1.0) / 3.0
        else:
            return base_ratio * 0.5

    def _calculate_disruption_score(self) -> float:
        """
        적 생산 방해 점수 (Enemy Production Disrupted)

        Returns:
            0.0 (no disruption) to 1.0 (heavy disruption)
        """
        if not self.blackboard:
            return 0.5

        # 적 건물 파괴 수
        enemy_structures_destroyed = getattr(self.blackboard, "enemy_structures_destroyed", 0)

        # 적 일꾼 킬 수
        enemy_workers_killed = getattr(self.blackboard, "enemy_workers_killed", 0)

        # 점수 계산 (건물 1개 = 2점, 일꾼 1명 = 0.5점)
        disruption_points = enemy_structures_destroyed * 2.0 + enemy_workers_killed * 0.5

        # 10점 이상이면 완벽한 방해
        if disruption_points >= 10:
            return 1.0
        elif disruption_points > 0:
            return min(1.0, disruption_points / 10.0)
        else:
            return 0.0

    # ========== RESOURCE ALLOCATION ==========

    def _adjust_resource_priorities(self) -> None:
        """
        Dynamically adjust resource allocation based on game state

        Factors:
        - Win condition
        - Game phase
        - Enemy pressure
        """
        # Reset to defaults (설정값 사용)
        if self.config:
            self.resource_priorities = {
                "economy": self.config.DEFAULT_PRIORITY_ECONOMY,
                "army": self.config.DEFAULT_PRIORITY_ARMY,
                "tech": self.config.DEFAULT_PRIORITY_TECH,
                "defense": self.config.DEFAULT_PRIORITY_DEFENSE
            }
        else:
            self.resource_priorities = {
                "economy": 0.4,
                "army": 0.4,
                "tech": 0.1,
                "defense": 0.1
            }

        # Adjust based on win condition (설정값 사용)
        if self.current_win_condition == WinCondition.LOSING_ARMY:
            # Need more army immediately
            if self.config:
                self.resource_priorities["army"] = self.config.LOSING_ARMY_PRIORITY_ARMY
                self.resource_priorities["economy"] = self.config.LOSING_ARMY_PRIORITY_ECONOMY
                self.resource_priorities["defense"] = self.config.LOSING_ARMY_PRIORITY_DEFENSE
            else:
                self.resource_priorities["army"] = 0.6
                self.resource_priorities["economy"] = 0.2
                self.resource_priorities["defense"] = 0.2

        elif self.current_win_condition == WinCondition.LOSING_ECONOMY:
            # Need more workers/bases
            if self.config:
                self.resource_priorities["economy"] = self.config.WINNING_ECONOMY_PRIORITY_ECONOMY
                self.resource_priorities["army"] = self.config.WINNING_ECONOMY_PRIORITY_ARMY
                self.resource_priorities["defense"] = self.config.WINNING_ECONOMY_PRIORITY_DEFENSE
            else:
                self.resource_priorities["economy"] = 0.6
                self.resource_priorities["army"] = 0.2
                self.resource_priorities["defense"] = 0.2

        elif self.current_win_condition in [WinCondition.WINNING_ARMY, WinCondition.WINNING_ECONOMY]:
            # Push advantage
            if self.config:
                self.resource_priorities["army"] = self.config.WINNING_ARMY_PRIORITY_ARMY
                self.resource_priorities["economy"] = self.config.WINNING_ARMY_PRIORITY_ECONOMY
                self.resource_priorities["tech"] = self.config.WINNING_ARMY_PRIORITY_TECH
            else:
                self.resource_priorities["army"] = 0.6
                self.resource_priorities["economy"] = 0.2
                self.resource_priorities["tech"] = 0.2

        # Adjust for emergency mode (설정값 사용)
        if self.emergency_active:
            if self.config:
                self.resource_priorities["army"] = self.config.LOSING_EMERGENCY_PRIORITY_ARMY
                self.resource_priorities["defense"] = self.config.LOSING_EMERGENCY_PRIORITY_DEFENSE
                self.resource_priorities["economy"] = self.config.LOSING_EMERGENCY_PRIORITY_ECONOMY
                self.resource_priorities["tech"] = self.config.LOSING_EMERGENCY_PRIORITY_TECH
            else:
                self.resource_priorities["army"] = 0.7
                self.resource_priorities["defense"] = 0.3
                self.resource_priorities["economy"] = 0.0
                self.resource_priorities["tech"] = 0.0

    def get_resource_priority(self, category: str) -> float:
        """
        Get resource allocation priority for category

        Args:
            category: "economy", "army", "tech", or "defense"

        Returns:
            Priority weight (0.0 to 1.0)
        """
        return self.resource_priorities.get(category, 0.25)

    # ========== MULTI-STRATEGY EXECUTION ==========

    def _execute_multi_strategy(self) -> None:
        """
        Execute multiple concurrent strategies

        Strategies:
        1. Main army attack/defense
        2. Expansion timing
        3. Harassment (Mutalisk/Zergling)
        4. Tech progression
        """
        game_time = getattr(self.bot, "time", 0.0)

        # Clean up completed strategies
        self.active_strategies = [s for s in self.active_strategies if not s.get("complete", False)]

        # Add new strategies based on conditions
        if len(self.active_strategies) < self.concurrent_strategy_limit:
            self._queue_pending_strategies(game_time)

    def _queue_pending_strategies(self, game_time: float) -> None:
        """Queue new strategies based on game state"""
        # Example: Queue expansion if we have resources and map control
        if self._should_expand(game_time):
            self._add_strategy({
                "name": "expansion",
                "priority": StrategyPriority.HIGH,
                "start_time": game_time,
                "complete": False
            })

        # Example: Queue harassment if we have mutalisks
        if self._should_harass(game_time):
            self._add_strategy({
                "name": "harassment",
                "priority": StrategyPriority.MEDIUM,
                "start_time": game_time,
                "complete": False
            })

    def _should_expand(self, game_time: float) -> bool:
        """Check if we should expand now (설정값 사용)"""
        # Check if expansion is in plan
        timing_window = self.config.EXPANSION_TIMING_WINDOW if self.config else 10
        for planned_time in self.planned_expansions:
            if abs(game_time - planned_time) < timing_window:
                return True
        return False

    def _should_harass(self, game_time: float) -> bool:
        """Check if we should harass"""
        # Harass in mid-game if we have units
        if self.current_build_phase in [BuildOrderPhase.TRANSITION, BuildOrderPhase.MIDGAME]:
            # Check for harassment units (handled by harassment coordinator)
            return False  # Delegate to harassment_coordinator
        return False

    def _add_strategy(self, strategy: Dict[str, Any]) -> None:
        """Add strategy to active list"""
        # Check if already active
        strategy_name = strategy.get("name", "")
        if any(s.get("name") == strategy_name for s in self.active_strategies):
            return

        self.active_strategies.append(strategy)
        self.logger.info(f"[STRATEGY] Added: {strategy_name} (Priority: {strategy.get('priority', 'N/A')})")

    # ========== ADAPTIVE COMPOSITION (Phase 18) ==========

    def _update_unit_composition(self, game_time: float) -> None:
        """Update target unit composition based on enemy tech"""
        if game_time - self.last_composition_update < 5:
            return
            
        self.last_composition_update = game_time
        self.target_unit_ratios = self._calculate_desired_composition()

    def _calculate_desired_composition(self) -> Dict[str, float]:
        """
        Calculate ideal Zerg unit composition based on enemy army
        
        Returns:
            Dictionary of {unit_type_name: ratio}
        """
        ratios = {
            "roach": 0.0, "ravager": 0.0, "hydra": 0.0,
            "lingu": 0.0, "baneling": 0.0, "mutalisk": 0.0,
            "corruptor": 0.0, "infestor": 0.0, "viper": 0.0,
            "ultralisk": 0.0, "lurker": 0.0
        }
        
        # Default composition based on race if no enemies seen
        if not hasattr(self.bot, "enemy_units") or not self.bot.enemy_units:
             return self._get_default_composition_by_race()

        enemy_units = self.bot.enemy_units
        total_enemy_supply = sum(u.radius for u in enemy_units) # Rough proxy for supply
        if total_enemy_supply == 0:
            return self._get_default_composition_by_race()

        # Count enemy composition tags
        counts = {
            "air_capital": 0, # Carrier, BC, Tempest
            "air_fighter": 0, # Viking, Phoenix, VoidRay, Mutalisk
            "ground_mech": 0, # Tank, Thor, Colossus, Immortal
            "ground_bio": 0,  # Marine, Zealot, Zergling
            "massive": 0      # Ultralisk, Archon
        }

        for u in enemy_units:
            name = u.type_id.name.upper()
            if name in ["CARRIER", "BATTLECRUISER", "TEMPEST", "BROODLORD", "MOTHERSHIP"]:
                counts["air_capital"] += 1
            elif name in ["VIKINGFIGHTER", "PHOENIX", "VOIDRAY", "MUTALISK", "CORRUPTOR", "LIBERATOR", "BANSHEE"]:
                counts["air_fighter"] += 1
            elif name in ["SIEGETANK", "SIEGETANKSIEGED", "THOR", "COLOSSUS", "IMMORTAL", "STALKER", "DRAGOON"]:
                counts["ground_mech"] += 1
            elif name in ["MARINE", "MARAUDER", "ZEALOT", "ADEPT", "ZERGLING", "ROACH", "HYDRALISK"]:
                counts["ground_bio"] += 1
            elif name in ["ULTRALISK", "ARCHON"]:
                counts["massive"] += 1
        
        # ★ Phase 21.2: 향상된 유닛 조합 로직 ★
        # Logic Tree for Composition (우선순위 기반)

        # 1. Anti-Air Capital Ships (Carrier, BC, Tempest)
        if counts["air_capital"] >= 3:
            # 대규모 공중 자본함 위협 (3+ 유닛)
            ratios["corruptor"] = 0.55  # 주력 대응
            ratios["viper"] = 0.15      # Abduct 중요
            ratios["hydra"] = 0.20      # 지상 방어
            ratios["queen"] = 0.10      # Transfusion 지원
        elif counts["air_capital"] >= 1:
            # 소규모 공중 자본함 (1-2 유닛)
            ratios["corruptor"] = 0.40
            ratios["hydra"] = 0.30
            ratios["viper"] = 0.10
            ratios["zergling"] = 0.20  # Mineral dump
            
        # 2. Anti-Ground Mech (Ravager/Viper/Lurker)
        elif counts["ground_mech"] >= 5:
            ratios["ravager"] = 0.30
            ratios["roach"] = 0.20
            ratios["viper"] = 0.10
            ratios["zergling"] = 0.20
            ratios["hydra"] = 0.20
            
        # 3. Anti-Bio (Baneling/Roach/Lurker)
        elif counts["ground_bio"] >= 10:
            ratios["roach"] = 0.40
            ratios["ravager"] = 0.10
            ratios["baneling"] = 0.20
            ratios["hydra"] = 0.20
            ratios["infestor"] = 0.10 # Fungal
            
        # 4. Default Balanced
        else:
            return self._get_default_composition_by_race()
            
        return ratios

    def _get_default_composition_by_race(self) -> Dict[str, float]:
        """Default compositions per matchup"""
        if not hasattr(self.bot, "enemy_race"):
            return {"roach": 0.5, "hydra": 0.3, "ravager": 0.2}
            
        race = self.bot.enemy_race
        if race == self.bot.Race.Terran:
            # Roach/Ravager/Ling
            return {"roach": 0.4, "ravager": 0.2, "hydra": 0.2, "zergling": 0.2}
        elif race == self.bot.Race.Protoss:
            # Roach/Hydra/Lurker
            return {"roach": 0.4, "hydra": 0.4, "lurker": 0.1, "viper": 0.1}
        elif race == self.bot.Race.Zerg:
            # Roach/Ravager
            return {"roach": 0.6, "ravager": 0.3, "hydra": 0.1}
        else:
            return {"roach": 0.5, "hydra": 0.3, "ravager": 0.2}

    def get_unit_ratios(self) -> Dict[str, float]:
        """Public API for UnitFactory"""
        return self.target_unit_ratios

    # ========== SMART SURRENDER (Phase 18/17) ==========
    
    def _check_smart_surrender(self, game_time: float) -> bool:
        """Surrender if game is hopeless to save training time"""
        # Only surrender after 4 minutes (was 5)
        if game_time < 240:
             return False
             
        # Conditions for hopeless state:
        # 1. Strong Losing Economy AND Strong Losing Army
        is_hopeless = (
            self.current_win_condition in [WinCondition.LOSING_ECONOMY, WinCondition.LOSING_ARMY] 
            and self._calculate_economy_score() <= -3.0 # Very bad eco
            and self._calculate_army_score() <= -3.0    # Very bad army
        )
        
        if is_hopeless:
             if self.surrender_trigger_time == 0:
                 self.surrender_trigger_time = game_time
                 
             # If hopeless for 30 seconds
             duration = game_time - self.surrender_trigger_time
             if duration > self.surrender_threshold:
                 self.logger.warning(f"[SURRENDER] Game is hopeless for {int(duration)}s. Surrendering to speed up training.")
                 
                 # Force async leave
                 import asyncio
                 try:
                    asyncio.create_task(self.bot.client.leave())
                 except Exception as e:
                    self.logger.error(f"Failed to trigger leave: {e}")
                 
                 return True
        else:
             self.surrender_trigger_time = 0
             
        return False


    # ========== PUBLIC API ==========

    def get_win_condition(self) -> WinCondition:
        """Get current win condition"""
        return self.current_win_condition

    def get_build_phase(self) -> BuildOrderPhase:
        """Get current build order phase"""
        return self.current_build_phase

    def should_prioritize_economy(self) -> bool:
        """Check if economy should be prioritized (설정값 사용)"""
        threshold = self.config.SHOULD_EXPAND_THRESHOLD if self.config else 0.4
        return self.get_resource_priority("economy") >= threshold

    def should_prioritize_army(self) -> bool:
        """Check if army should be prioritized (설정값 사용)"""
        threshold = self.config.SHOULD_BUILD_ARMY_THRESHOLD if self.config else 0.5
        return self.get_resource_priority("army") >= threshold

    def get_status_report_v2(self) -> Dict[str, Any]:
        """
        Enhanced status report with V2 data

        Returns:
            Comprehensive status dictionary
        """
        base_report = super().get_status_report()

        v2_report = {
            **base_report,
            "win_condition": self.current_win_condition.name,
            "build_phase": self.current_build_phase.name,
            "resource_priorities": self.resource_priorities,
            "active_strategies": [s.get("name") for s in self.active_strategies],
            "strategy_scores": self.strategy_scores,
        }

        return v2_report
