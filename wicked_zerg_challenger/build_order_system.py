# -*- coding: utf-8 -*-
"""

Build Order Optimization System

Purpose: Stable and optimized automated build order execution
- Standard 12 Pool, 14 Hatch, 14 Gas builds
- Improved timing accuracy
- Win-rate based adjustment
"""

from typing import Optional, List, Dict, Tuple
from enum import Enum
from knowledge_manager import KnowledgeManager # NEW

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        DRONE = "DRONE"
        OVERLORD = "OVERLORD"
        SPAWNINGPOOL = "SPAWNINGPOOL"
        HATCHERY = "HATCHERY"
        EXTRACTOR = "EXTRACTOR"
        ZERGLING = "ZERGLING"
        QUEEN = "QUEEN"
    class AbilityId:
        pass
    class Point2:
        pass


class BuildOrderType(Enum):
    """Build Order Types"""
    STANDARD_12POOL = "STANDARD_12POOL"  # Matches JSON key
    SAFE_14POOL = "SAFE_14POOL"      # Need to add to JSON
    AGGRESSIVE_10POOL = "AGGRESSIVE_10POOL"
    ECONOMY_15HATCH = "ECONOMY_15HATCH"
    HATCH_FIRST_16 = "HATCH_FIRST_16"  # ★ Phase 22: 1분 멀티 빌드 ★
    ROACH_RUSH = "ROACH_RUSH"               # Matches JSON key
    MUTALISK_RUSH = "MUTALISK_RUSH"
    HYDRA_TIMING = "HYDRA_TIMING"
    LURKER_DEFENSE = "LURKER_DEFENSE"


class BuildOrderStep:
    """Build Order Step"""
    def __init__(self, supply: int, action: str, unit_type: UnitTypeId, description: str = ""):
        self.supply = supply  # Supply to execute at
        self.action = action  # "build", "train", "expand"
        self.unit_type = unit_type
        self.description = description
        self.completed = False

    def __repr__(self):
        return f"BuildOrderStep({self.supply} supply: {self.action} {self.unit_type})"


class BuildOrderSystem:
    """

    Build Order System (Data-Driven by KnowledgeManager)
    
    Key Features:
    1. Load build order data via KnowledgeManager
    2. JSON-based automated execution
    3. Real-time progress tracking
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.knowledge_manager = KnowledgeManager() # Initialize Knowledge Manager
        self.enabled = True
        self.build_order_active = True

        # Current Build Order (Selected by enemy race)
        self.current_build_order: BuildOrderType = self._select_build_by_enemy_race()
        self.build_steps: List[BuildOrderStep] = []
        self.current_step_index = 0

        # Timing tracking
        self.step_timings: Dict[int, float] = {}  # supply -> game_time
        self.missed_timings: List[str] = []

        # Performance Stats
        self.build_order_stats = {
            BuildOrderType.STANDARD_12POOL: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.SAFE_14POOL: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.AGGRESSIVE_10POOL: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.ECONOMY_15HATCH: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.HATCH_FIRST_16: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.ROACH_RUSH: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.MUTALISK_RUSH: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.HYDRA_TIMING: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.LURKER_DEFENSE: {"games": 0, "wins": 0, "avg_timing": 0.0},
        }

        # Build Order End Time
        self.build_order_end_time = 300.0  # 5 minutes

        # ★ Phase 22: 확장 타이밍 검증 ★
        self.expansion_timing_target = 60.0  # 1분 멀티 목표
        self.expansion_actual_time = 0.0     # 실제 확장 시작 시간
        self.expansion_timing_verified = False

        # Initialization
        self._setup_build_order()

    def _select_build_by_enemy_race(self) -> BuildOrderType:
        """
        Select best build order by enemy race

        Returns:
            BuildOrderType: Selected Build Order
        """
        if not hasattr(self.bot, "enemy_race") or not self.bot.enemy_race:
            return BuildOrderType.ROACH_RUSH  # Fallback

        race_name = str(self.bot.enemy_race).lower()

        if "protoss" in race_name:
            # vs Protoss: 14-pool (Safe opening vs Stargate or Proxies)
            # Transition to Hydralisk/Roach
            return BuildOrderType.SAFE_14POOL
        elif "terran" in race_name:
            # vs Terran: 12-pool (Early pressure or Reaper defense)
            # Delay Terran expansion
            return BuildOrderType.STANDARD_12POOL
        else:
            # vs Zerg: 14-pool (Mirror matchup stability)
            # Secure economy while matching pool timing
            return BuildOrderType.SAFE_14POOL

    def _setup_build_order(self) -> None:
        """Setup current build order (From KnowledgeManager)"""
        build_key = self.current_build_order.value
        build_data = self.knowledge_manager.get_build_order(build_key)

        if build_data:
            self.build_steps = self._parse_build_steps(build_data.get("steps", []))
            print(f"[BUILD_ORDER] Loaded '{build_data.get('name')}' from KnowledgeManager")
        else:
            print(f"[BUILD_ORDER] Error: '{build_key}' not found in KnowledgeManager.")
            self.build_steps = []

        self.current_step_index = 0
        print(f"[BUILD_ORDER] Build Order Set: {self.current_build_order.value}")
        print(f"[BUILD_ORDER] Total {len(self.build_steps)} steps")

    def _parse_build_steps(self, steps_data: List[Dict]) -> List[BuildOrderStep]:
        """Parse JSON steps into objects"""
        parsed_steps = []
        for step in steps_data:
            try:
                # Convert string unit type to UnitTypeId enum
                unit_str = step["unit_type"]
                # Handle UnitTypeId attribute lookup safely
                if hasattr(UnitTypeId, unit_str):
                    unit_type = getattr(UnitTypeId, unit_str)
                else:
                    # Try uppercase just in case
                    unit_type = getattr(UnitTypeId, unit_str.upper())
                
                parsed_steps.append(BuildOrderStep(
                    supply=step["supply"],
                    action=step["action"],
                    unit_type=unit_type,
                    description=step["description"]
                ))
            except Exception as e:
                print(f"[BUILD_ORDER] Error parsing step {step}: {e}")
        return parsed_steps

    async def execute(self, iteration: int) -> None:
        """
        Execute build order every frame
        """
        # Disable after 3 mins
        if self.bot.time > self.build_order_end_time:
            if self.build_order_active:
                self.build_order_active = False
                print(f"[BUILD_ORDER] Build Order Steps Completed (Game Time: {int(self.bot.time)}s)")
            return

        if not self.enabled or not self.build_order_active:
            return

        # Check current supply
        current_supply = int(self.bot.supply_used)
 
        # Check next step
        if self.current_step_index >= len(self.build_steps):
            return

        current_step = self.build_steps[self.current_step_index]

        # Check supply requirement
        if current_supply >= current_step.supply:
            # Execute step
            success = await self._execute_step(current_step)

            if success:
                # Record timing
                self.step_timings[current_step.supply] = self.bot.time
                print(f"[BUILD_ORDER] [OK] {current_step.supply} Supply: {current_step.description} (Timing: {int(self.bot.time)}s)")
 
                # Next step
                current_step.completed = True
                self.current_step_index += 1

    async def _execute_step(self, step: BuildOrderStep) -> bool:
        """Execute Build Order Step"""
        try:
            if step.action == "build":
                return await self._build_structure(step.unit_type)
            elif step.action == "train":
                return await self._train_unit(step.unit_type)
            elif step.action == "expand":
                return await self._expand(step.unit_type)
            return False
        except Exception as e:
            print(f"[BUILD_ORDER] Step Execution Failed: {e}")
            return False

    async def _build_structure(self, structure_type: UnitTypeId) -> bool:
        """Build Structure"""
        # Skip if already exists or pending
        if self.bot.structures(structure_type).exists:
            return True
        if self.bot.already_pending(structure_type) > 0:
            return True

        # Check Resources
        if not self.bot.can_afford(structure_type):
            return False

        # Check Workers
        if not self.bot.workers:
            return False

        # Use TechCoordinator if available
        tech_coordinator = getattr(self.bot, "tech_coordinator", None)
        PRIORITY_BUILD_ORDER = 50

        # Build Spawning Pool
        if structure_type == UnitTypeId.SPAWNINGPOOL:
            main_base = self.bot.townhalls.first
            # Calculate approx location
            pos = main_base.position.towards(self.bot.game_info.map_center, 5)
            
            if tech_coordinator:
                 if not tech_coordinator.is_planned(structure_type):
                    tech_coordinator.request_structure(
                        UnitTypeId.SPAWNINGPOOL,
                        pos,
                        PRIORITY_BUILD_ORDER,
                        "BuildOrderSystem"
                    )
                    return True # Request accepted, move to next step
            else:
                worker = self.bot.workers.random
                location = await self.bot.find_placement(
                    UnitTypeId.SPAWNINGPOOL,
                    pos,
                    max_distance=15,
                    placement_step=2
                )
                if location:
                    worker.build(UnitTypeId.SPAWNINGPOOL, location)
                    return True

        # Build Extractor
        elif structure_type == UnitTypeId.EXTRACTOR:
            if self.bot.townhalls:
                main_base = self.bot.townhalls.first
                geysers = self.bot.vespene_geyser.closer_than(10, main_base)

                for geyser in geysers:
                    if not self.bot.structures(UnitTypeId.EXTRACTOR).closer_than(1, geyser):
                        if tech_coordinator:
                             # Request on this specific geyser
                             # TechCoordinator handles duplication checks but we check here too
                             tech_coordinator.request_structure(
                                UnitTypeId.EXTRACTOR,
                                geyser, # Pass Unit object as location
                                PRIORITY_BUILD_ORDER,
                                "BuildOrderSystem"
                            )
                             return True
                        else:
                            worker = self.bot.workers.closest_to(geyser)
                            if worker:
                                worker.build_gas(geyser)
                                return True
        
        # General Structure Fallback (e.g. Roach Warren)
        else:
             if self.bot.townhalls:
                pos = self.bot.townhalls.first.position
                if tech_coordinator:
                    if not tech_coordinator.is_planned(structure_type):
                        tech_coordinator.request_structure(
                            structure_type,
                            pos,
                            PRIORITY_BUILD_ORDER,
                            "BuildOrderSystem"
                        )
                        return True
                else:
                    await self.bot.build(structure_type, near=pos)
                    return True

        return False

    async def _train_unit(self, unit_type: UnitTypeId) -> bool:
        """Train Unit"""
        # Check Resources
        if not self.bot.can_afford(unit_type):
            return False

        # Train Overlord
        if unit_type == UnitTypeId.OVERLORD:
            if self.bot.larva:
                larva = self.bot.larva.first
                larva.train(UnitTypeId.OVERLORD)
                return True

        # Train Queen
        elif unit_type == UnitTypeId.QUEEN:
            # Check Spawning Pool
            if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
                return False

            # Find Idle Hatchery
            for hatchery in self.bot.townhalls.ready.idle:
                if self.bot.can_afford(UnitTypeId.QUEEN):
                    hatchery.train(UnitTypeId.QUEEN)
                    return True

        # Train Zergling
        elif unit_type == UnitTypeId.ZERGLING:
            # Check Spawning Pool
            if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
                return False

            if self.bot.larva:
                larva = self.bot.larva.first
                larva.train(UnitTypeId.ZERGLING)
                return True

        # Train Drone
        elif unit_type == UnitTypeId.DRONE:
            if self.bot.larva:
                larva = self.bot.larva.first
                larva.train(UnitTypeId.DRONE)
                return True

        return False

    async def _expand(self, structure_type: UnitTypeId) -> bool:
        """
        Expand Base
        ★ Phase 22: 확장 타이밍 기록 + 1분 멀티 검증 ★
        """
        # Skip if already expanded
        if self.bot.townhalls.amount >= 2:
            if not self.expansion_timing_verified:
                self._verify_expansion_timing()
            return True
        if self.bot.already_pending(UnitTypeId.HATCHERY) > 0:
            if self.expansion_actual_time == 0:
                self.expansion_actual_time = self.bot.time
                print(f"[BUILD_ORDER] ★ Natural expansion started at {int(self.bot.time)}s ★")
            return True

        # Check Resources
        if not self.bot.can_afford(UnitTypeId.HATCHERY):
            # ★ Phase 22: 1분 멀티 경고 - 60초 넘었는데 아직 확장 못 함 ★
            if self.bot.time > self.expansion_timing_target and self.expansion_actual_time == 0:
                print(f"[BUILD_ORDER] ⚠ WARNING: Natural expansion delayed! ({int(self.bot.time)}s > {int(self.expansion_timing_target)}s target)")
            return False

        # Find Expansion Location
        location = await self.bot.get_next_expansion()
        if location:
            # Use TechCoordinator if available
            tech_coordinator = getattr(self.bot, "tech_coordinator", None)
            PRIORITY_EXPANSION = 55  # ★ Phase 22: 확장 우선순위 상향 (50 → 55)

            if tech_coordinator:
                if not tech_coordinator.is_planned(UnitTypeId.HATCHERY):
                    tech_coordinator.request_structure(
                        UnitTypeId.HATCHERY,
                        location,
                        PRIORITY_EXPANSION,
                        "BuildOrderSystem"
                    )
                    self.expansion_actual_time = self.bot.time
                    print(f"[BUILD_ORDER] ★ Natural expansion ordered at {int(self.bot.time)}s ★")
                    return True
            else:
                worker = self.bot.workers.random
                if worker:
                    worker.build(UnitTypeId.HATCHERY, location)
                    self.expansion_actual_time = self.bot.time
                    print(f"[BUILD_ORDER] ★ Natural expansion ordered at {int(self.bot.time)}s ★")
                    return True

        return False

    def _verify_expansion_timing(self):
        """★ Phase 22: 확장 타이밍 검증 ★"""
        if self.expansion_timing_verified:
            return

        self.expansion_timing_verified = True
        actual = self.expansion_actual_time

        if actual == 0:
            print(f"[BUILD_ORDER] ⚠ Expansion timing: NOT RECORDED")
            return

        target = self.expansion_timing_target
        diff = actual - target

        if diff <= 5:
            print(f"[BUILD_ORDER] ✓ EXPANSION TIMING: {int(actual)}s (Target: {int(target)}s) - ON TIME")
        elif diff <= 15:
            print(f"[BUILD_ORDER] △ EXPANSION TIMING: {int(actual)}s (Target: {int(target)}s) - SLIGHTLY LATE (+{int(diff)}s)")
        else:
            print(f"[BUILD_ORDER] ✗ EXPANSION TIMING: {int(actual)}s (Target: {int(target)}s) - LATE (+{int(diff)}s)")

    def select_build_order_by_win_rate(self) -> BuildOrderType:
        """Auto-select Build Order by Win Rate"""
        # Calculate Win Rates
        win_rates = {}
        for build_type, stats in self.build_order_stats.items():
            if stats["games"] > 0:
                win_rates[build_type] = stats["wins"] / stats["games"]
            else:
                win_rates[build_type] = 0.0

        # Select Best Build (Min 5 games)
        best_build = BuildOrderType.STANDARD_12POOL
        best_win_rate = 0.0

        for build_type, win_rate in win_rates.items():
            if self.build_order_stats[build_type]["games"] >= 5 and win_rate > best_win_rate:
                best_build = build_type
                best_win_rate = win_rate

        return best_build

    def record_game_result(self, build_order: BuildOrderType, won: bool) -> None:
        """Record Game Result"""
        if build_order in self.build_order_stats:
            self.build_order_stats[build_order]["games"] += 1
            if won:
                self.build_order_stats[build_order]["wins"] += 1

    def get_progress(self) -> str:
        """Return Build Order Progress"""
        if not self.build_order_active:
            return "Build Order Complete"

        completed = sum(1 for step in self.build_steps if step.completed)
        total = len(self.build_steps)

        if total > 0:
            progress = f"{completed}/{total} ({int(completed/total*100)}%)"
        else:
            progress = "0/0"

        # Current Target
        if self.current_step_index < len(self.build_steps):
            next_step = self.build_steps[self.current_step_index]
            target = f"Next: {next_step.supply} Supply {next_step.description}"
        else:
            target = "All Steps Completed"

        return f"{progress} | {target}"

    def get_stats_summary(self) -> str:
        """Build Order Stats Summary"""
        lines = []
        lines.append("\n[BUILD_ORDER] === Build Order Stats ===")

        for build_type, stats in self.build_order_stats.items():
            games = stats["games"]
            wins = stats["wins"]
            win_rate = (wins / games * 100) if games > 0 else 0.0

            lines.append(f"  {build_type.value}: {wins}/{games} wins ({win_rate:.1f}%)")

        lines.append("=" * 40)
        return "\n".join(lines)
