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

        # Win condition tracking
        self.current_win_condition = WinCondition.UNKNOWN
        self.win_condition_history: List[WinCondition] = []
        self.win_condition_update_interval = 5.0  # Update every 5 seconds
        self.last_win_condition_check = 0.0

        # Build order system
        self.current_build_phase = BuildOrderPhase.OPENING
        self.build_transition_complete = False
        self.planned_expansions = []
        self.expansion_targets: List[Tuple[float, Any]] = []  # (timing, location)

        # Strategy scoring
        self.strategy_scores: Dict[str, float] = {}
        self.active_strategies: List[Dict[str, Any]] = []

        # Resource allocation
        self.resource_priorities: Dict[str, float] = {
            "economy": 0.4,    # 40% to economy (drones/expansions)
            "army": 0.4,       # 40% to army
            "tech": 0.1,       # 10% to tech
            "defense": 0.1     # 10% to defense
        }

        # Multi-strategy execution
        self.strategy_queue: List[Dict[str, Any]] = []
        self.concurrent_strategy_limit = 3

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

        # Update blackboard with V2 data
        if self.blackboard:
            self.blackboard.set("win_condition", self.current_win_condition.name)
            self.blackboard.set("build_phase", self.current_build_phase.name)
            self.blackboard.set("resource_priorities", self.resource_priorities)
            self.blackboard.set("active_strategies", len(self.active_strategies))

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

        # Determine overall condition
        total_score = economy_score + army_score + tech_score

        previous_condition = self.current_win_condition

        if total_score >= 6:  # Strong winning
            if economy_score >= 2:
                self.current_win_condition = WinCondition.WINNING_ECONOMY
            elif army_score >= 2:
                self.current_win_condition = WinCondition.WINNING_ARMY
            else:
                self.current_win_condition = WinCondition.WINNING_TECH
        elif total_score <= -6:  # Strong losing
            if economy_score <= -2:
                self.current_win_condition = WinCondition.LOSING_ECONOMY
            elif army_score <= -2:
                self.current_win_condition = WinCondition.LOSING_ARMY
            else:
                self.current_win_condition = WinCondition.LOSING_TECH
        else:
            self.current_win_condition = WinCondition.EVEN

        # Track history
        if self.current_win_condition != previous_condition:
            self.win_condition_history.append(self.current_win_condition)
            if len(self.win_condition_history) > 20:  # Keep last 20
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

        # Worker count comparison
        our_workers = self._count_workers()
        enemy_workers = self._estimate_enemy_workers()

        if enemy_workers > 0:
            worker_ratio = our_workers / enemy_workers
            if worker_ratio >= 1.5:
                score += 2.0
            elif worker_ratio >= 1.2:
                score += 1.0
            elif worker_ratio <= 0.7:
                score -= 2.0
            elif worker_ratio <= 0.8:
                score -= 1.0

        # Base count comparison
        our_bases = self._count_bases()
        enemy_bases = self._estimate_enemy_bases()

        if enemy_bases > 0:
            base_ratio = our_bases / enemy_bases
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

        # Army supply comparison
        our_army_supply = getattr(self.bot, "supply_army", 0)
        enemy_army_supply = self._estimate_enemy_army_supply()

        if enemy_army_supply > 0:
            army_ratio = our_army_supply / enemy_army_supply
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

        # Count tech buildings
        our_tech = self._count_tech_structures()
        enemy_tech = self._estimate_enemy_tech()

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
        """Estimate enemy worker count"""
        if not hasattr(self.bot, "enemy_units"):
            return 16  # Default assumption

        worker_types = {"SCV", "PROBE", "DRONE", "MULE"}
        count = 0
        for unit in self.bot.enemy_units:
            try:
                if unit.type_id.name.upper() in worker_types:
                    count += 1
            except AttributeError:
                continue

        # If we haven't scouted workers, estimate based on bases
        if count == 0:
            enemy_bases = self._estimate_enemy_bases()
            count = enemy_bases * 16  # Assume 16 per base

        return max(count, 16)  # Minimum 16

    def _count_bases(self) -> int:
        """Count our bases"""
        if not hasattr(self.bot, "townhalls"):
            return 0
        return self.bot.townhalls.amount

    def _estimate_enemy_bases(self) -> int:
        """Estimate enemy base count"""
        if not hasattr(self.bot, "enemy_structures"):
            return 1

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

        return max(count, 1)  # Minimum 1

    def _estimate_enemy_army_supply(self) -> int:
        """Estimate enemy army supply"""
        if not hasattr(self.bot, "enemy_units"):
            return 10  # Default assumption

        supply = 0
        supply_costs = {
            # Rough estimates
            "MARINE": 1, "MARAUDER": 2, "SIEGETANK": 3, "THOR": 6,
            "ZEALOT": 2, "STALKER": 2, "IMMORTAL": 4, "COLOSSUS": 6,
            "ZERGLING": 0.5, "ROACH": 2, "HYDRALISK": 2, "ULTRALISK": 6
        }

        for unit in self.bot.enemy_units:
            try:
                if unit.can_attack:
                    unit_name = unit.type_id.name.upper()
                    supply += supply_costs.get(unit_name, 2)  # Default 2
            except AttributeError:
                continue

        return max(supply, 10)  # Minimum 10

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
        """Estimate enemy tech level"""
        if not hasattr(self.bot, "enemy_structures"):
            return 1

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

        return max(tech_count, 1)

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

        if game_time < 180:  # 0-3 minutes
            self.current_build_phase = BuildOrderPhase.OPENING
        elif game_time < 360:  # 3-6 minutes
            self.current_build_phase = BuildOrderPhase.TRANSITION
        elif game_time < 600:  # 6-10 minutes
            self.current_build_phase = BuildOrderPhase.MIDGAME
        else:  # 10+ minutes
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
        """Transition to aggressive mid-game (6-10 min)"""
        self.logger.info("[BUILD] Transitioning to aggressive: Multi-base + Army production")

        # Plan 3rd base
        self._plan_expansion(target_time=380)  # Around 6:20

    def _transition_to_maxout(self) -> None:
        """Transition to late-game maxout (10+ min)"""
        self.logger.info("[BUILD] Transitioning to late-game: Max out army")

        # Plan 4th+ bases
        self._plan_expansion(target_time=650)  # Around 10:50

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

        # Log periodically
        if int(game_time) % 60 == 0 and self.bot.iteration % 22 == 0:
            if self.strategy_scores:
                self.logger.info(f"[STRATEGY_SCORES] {self.strategy_scores}")

    def _calculate_strategy_score(self, strategy: Dict[str, Any]) -> float:
        """
        Calculate effectiveness score for a strategy

        Returns:
            Score: 0.0 (ineffective) to 1.0 (highly effective)
        """
        # Placeholder scoring logic
        # In full implementation, would track:
        # - Units killed vs lost
        # - Resources traded
        # - Territory gained
        # - Enemy production disrupted

        return 0.5  # Neutral baseline

    # ========== RESOURCE ALLOCATION ==========

    def _adjust_resource_priorities(self) -> None:
        """
        Dynamically adjust resource allocation based on game state

        Factors:
        - Win condition
        - Game phase
        - Enemy pressure
        """
        # Reset to defaults
        self.resource_priorities = {
            "economy": 0.4,
            "army": 0.4,
            "tech": 0.1,
            "defense": 0.1
        }

        # Adjust based on win condition
        if self.current_win_condition == WinCondition.LOSING_ARMY:
            # Need more army immediately
            self.resource_priorities["army"] = 0.6
            self.resource_priorities["economy"] = 0.2
            self.resource_priorities["defense"] = 0.2

        elif self.current_win_condition == WinCondition.LOSING_ECONOMY:
            # Need more workers/bases
            self.resource_priorities["economy"] = 0.6
            self.resource_priorities["army"] = 0.2
            self.resource_priorities["defense"] = 0.2

        elif self.current_win_condition in [WinCondition.WINNING_ARMY, WinCondition.WINNING_ECONOMY]:
            # Push advantage
            self.resource_priorities["army"] = 0.6
            self.resource_priorities["economy"] = 0.2
            self.resource_priorities["tech"] = 0.2

        # Adjust for emergency mode
        if self.emergency_active:
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
        """Check if we should expand now"""
        # Check if expansion is in plan
        for planned_time in self.planned_expansions:
            if abs(game_time - planned_time) < 10:  # Within 10 seconds
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

    # ========== PUBLIC API ==========

    def get_win_condition(self) -> WinCondition:
        """Get current win condition"""
        return self.current_win_condition

    def get_build_phase(self) -> BuildOrderPhase:
        """Get current build order phase"""
        return self.current_build_phase

    def should_prioritize_economy(self) -> bool:
        """Check if economy should be prioritized"""
        return self.get_resource_priority("economy") >= 0.4

    def should_prioritize_army(self) -> bool:
        """Check if army should be prioritized"""
        return self.get_resource_priority("army") >= 0.5

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
