# -*- coding: utf-8 -*-
"""
Lurker Ambush System - Phase 19

Strategic lurker positioning and ambush tactics:
1. Hold fire until 3+ enemies in attack range
2. Coordinate simultaneous attacks for maximum damage
3. Auto-burrow when no enemies nearby
4. Retreat when overwhelmed
5. Priority targeting (high-value units)

Features:
- Patient ambush (wait for multiple targets)
- Burst damage coordination
- Smart retreat logic
- Target prioritization
"""

from typing import Dict, Set, List, Optional
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.unit import Unit
    from sc2.units import Units
    from sc2.position import Point2
except ImportError:
    BotAI = object
    UnitTypeId = object
    AbilityId = object
    Unit = object
    Units = list
    Point2 = tuple


class LurkerAmbushSystem:
    """
    Lurker Ambush Tactical System

    Manages lurker positioning and coordinated attacks for maximum effectiveness.
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("LurkerAmbush")

        # Lurker tracking
        self.lurker_states: Dict[int, str] = {}  # {tag: state}
        # States: "waiting", "attacking", "retreating", "burrowing"

        self.lurker_targets: Dict[int, Set[int]] = {}  # {lurker_tag: {enemy_tags}}
        self.last_attack_time: Dict[int, float] = {}  # {lurker_tag: time}

        # Ambush settings
        self.MIN_TARGETS_FOR_ATTACK = 3  # Minimum enemies before attacking
        self.RETREAT_THRESHOLD = 5  # Retreat if 5+ enemies targeting
        self.ATTACK_COOLDOWN = 2.0  # Cooldown between attacks (seconds)

        # Range settings
        self.LURKER_RANGE = 9  # Lurker attack range (after upgrade: 10)
        self.SAFETY_DISTANCE = 12  # Distance to maintain from enemies

        # Priority targets (high-value units)
        self.HIGH_PRIORITY_TARGETS = {
            # Terran
            UnitTypeId.SIEGETANK,
            UnitTypeId.SIEGETANKSIEGED,
            UnitTypeId.THOR,
            UnitTypeId.MARAUDER,

            # Protoss
            UnitTypeId.COLOSSUS,
            UnitTypeId.IMMORTAL,
            UnitTypeId.DISRUPTOR,
            UnitTypeId.ARCHON,
            UnitTypeId.HIGHTEMPLAR,

            # Zerg
            UnitTypeId.ULTRALISK,
            UnitTypeId.BROODLORD,
            UnitTypeId.INFESTOR,
        }

        # Statistics
        self.ambushes_executed = 0
        self.enemies_killed_in_ambush = 0

    async def on_step(self, iteration: int):
        """Main update loop"""
        try:
            # Update lurker range (check for upgrade)
            if iteration % 220 == 0:  # ~10 seconds
                self._update_lurker_range()

            # Manage all lurkers
            if iteration % 11 == 0:  # ~0.5 seconds
                await self._manage_lurkers()

            # Report statistics
            if iteration % 1100 == 0:  # ~50 seconds
                self._print_report()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[LURKER_AMBUSH] Error: {e}")

    # ========================================
    # Main Lurker Management
    # ========================================

    async def _manage_lurkers(self):
        """Manage all lurkers"""
        if not hasattr(self.bot, "units"):
            return

        lurkers = self.bot.units(UnitTypeId.LURKERMP)
        if not lurkers:
            return

        for lurker in lurkers:
            await self._manage_single_lurker(lurker)

    async def _manage_single_lurker(self, lurker: Unit):
        """Manage individual lurker behavior"""
        # Get current state
        state = self.lurker_states.get(lurker.tag, "waiting")

        # Check if burrowed
        is_burrowed = lurker.is_burrowed

        # Find nearby enemies
        nearby_enemies = self._find_enemies_in_range(lurker)

        # State machine
        if not is_burrowed:
            # Not burrowed - burrow if enemies nearby or if idle
            if nearby_enemies or state == "waiting":
                await self._burrow_lurker(lurker)
                self.lurker_states[lurker.tag] = "burrowing"
            return

        # Burrowed - check for ambush opportunity
        if state == "waiting":
            if len(nearby_enemies) >= self.MIN_TARGETS_FOR_ATTACK:
                # Ambush! Execute attack
                await self._execute_ambush(lurker, nearby_enemies)
                self.lurker_states[lurker.tag] = "attacking"
            # else: keep waiting

        elif state == "attacking":
            # Check if should retreat
            if self._should_retreat(lurker, nearby_enemies):
                await self._retreat_lurker(lurker)
                self.lurker_states[lurker.tag] = "retreating"
            elif len(nearby_enemies) == 0:
                # No more enemies - go back to waiting
                self.lurker_states[lurker.tag] = "waiting"
            else:
                # Continue attacking
                await self._execute_ambush(lurker, nearby_enemies)

        elif state == "retreating":
            # Unburrow and move back
            await self._unburrow_and_retreat(lurker)
            self.lurker_states[lurker.tag] = "waiting"

    # ========================================
    # Ambush Execution
    # ========================================

    async def _execute_ambush(self, lurker: Unit, enemies: Units):
        """Execute coordinated ambush attack"""
        game_time = self.bot.time

        # Check attack cooldown
        last_attack = self.last_attack_time.get(lurker.tag, 0)
        if game_time - last_attack < self.ATTACK_COOLDOWN:
            return  # Still on cooldown

        # Select best target
        target = self._select_best_target(lurker, enemies)
        if not target:
            return

        # Attack!
        self.bot.do(lurker.attack(target))
        self.last_attack_time[lurker.tag] = game_time

        # Update statistics
        self.ambushes_executed += 1

        # Log (first ambush or every 5th)
        if self.ambushes_executed == 1 or self.ambushes_executed % 5 == 0:
            self.logger.info(
                f"[{int(game_time)}s] LURKER AMBUSH #{self.ambushes_executed}! "
                f"Target: {target.type_id.name} ({len(enemies)} enemies in range)"
            )

    def _select_best_target(self, lurker: Unit, enemies: Units) -> Optional[Unit]:
        """Select best target based on priority"""
        if not enemies:
            return None

        # Priority 1: High-value targets
        high_priority = [e for e in enemies if e.type_id in self.HIGH_PRIORITY_TARGETS]
        if high_priority:
            # Closest high-priority target
            return min(high_priority, key=lambda e: e.distance_to(lurker))

        # Priority 2: Closest enemy
        return enemies.closest_to(lurker)

    # ========================================
    # Enemy Detection
    # ========================================

    def _find_enemies_in_range(self, lurker: Unit) -> Units:
        """Find enemies within lurker attack range"""
        if not hasattr(self.bot, "enemy_units"):
            return Units([], self.bot)

        enemy_units = self.bot.enemy_units

        # Filter by range
        if hasattr(enemy_units, "closer_than"):
            nearby = enemy_units.closer_than(self.LURKER_RANGE, lurker)
        else:
            nearby = Units([e for e in enemy_units if e.distance_to(lurker) < self.LURKER_RANGE], self.bot)

        # Filter out air units (lurkers can't attack air)
        ground_enemies = nearby.filter(lambda u: not u.is_flying)

        return ground_enemies

    def _should_retreat(self, lurker: Unit, nearby_enemies: Units) -> bool:
        """Determine if lurker should retreat"""
        # Too many enemies
        if len(nearby_enemies) >= self.RETREAT_THRESHOLD:
            return True

        # HP too low
        if lurker.health_percentage < 0.3:
            return True

        # Detection nearby (enemy has detector)
        if self._has_enemy_detector_nearby(lurker):
            return True

        return False

    def _has_enemy_detector_nearby(self, lurker: Unit) -> bool:
        """Check if enemy has detector nearby"""
        if not hasattr(self.bot, "enemy_units"):
            return False

        # Detector units
        detectors = {
            UnitTypeId.OBSERVER,
            UnitTypeId.OBSERVERSIEGEMODE,
            UnitTypeId.RAVEN,
            UnitTypeId.OVERSEER,
            UnitTypeId.MISSILETURRET,
            UnitTypeId.PHOTONCANNON,
            UnitTypeId.SPORECRAWLER,
        }

        enemy_units = self.bot.enemy_units
        for enemy in enemy_units:
            if enemy.type_id in detectors and enemy.distance_to(lurker) < 12:
                return True

        return False

    # ========================================
    # Burrow/Unburrow
    # ========================================

    async def _burrow_lurker(self, lurker: Unit):
        """Burrow lurker"""
        if lurker.is_burrowed:
            return

        # Check if burrow is available
        if AbilityId.BURROWDOWN_LURKER in await self.bot.get_available_abilities(lurker):
            self.bot.do(lurker(AbilityId.BURROWDOWN_LURKER))

    async def _unburrow_and_retreat(self, lurker: Unit):
        """Unburrow lurker and retreat to safety"""
        if not lurker.is_burrowed:
            # Already unburrowed - retreat
            await self._retreat_lurker(lurker)
            return

        # Unburrow
        if AbilityId.BURROWUP_LURKER in await self.bot.get_available_abilities(lurker):
            self.bot.do(lurker(AbilityId.BURROWUP_LURKER))

    async def _retreat_lurker(self, lurker: Unit):
        """Move lurker to safe position"""
        if not hasattr(self.bot, "start_location"):
            return

        # Retreat toward main base
        retreat_pos = self.bot.start_location
        self.bot.do(lurker.move(retreat_pos))

        game_time = self.bot.time
        self.logger.info(
            f"[{int(game_time)}s] Lurker retreating (HP: {lurker.health_percentage*100:.0f}%)"
        )

    # ========================================
    # Upgrades and Configuration
    # ========================================

    def _update_lurker_range(self):
        """Update lurker range based on upgrades"""
        if not hasattr(self.bot, "state"):
            return

        # Check for Grooved Spines upgrade (lurker range +2)
        try:
            from sc2.ids.upgrade_id import UpgradeId
            if UpgradeId.LURKERRANGE in self.bot.state.upgrades:
                self.LURKER_RANGE = 10  # Base 9 + 1 (upgrade gives +2 but we use 10 for safety)
        except:
            pass

    # ========================================
    # Statistics
    # ========================================

    def _print_report(self):
        """Print ambush statistics"""
        game_time = self.bot.time

        if not hasattr(self.bot, "units"):
            return

        lurkers = self.bot.units(UnitTypeId.LURKERMP)

        # Count by state
        states = {}
        for tag, state in self.lurker_states.items():
            states[state] = states.get(state, 0) + 1

        self.logger.info(
            f"[{int(game_time)}s] === LURKER AMBUSH REPORT ==="
        )
        self.logger.info(
            f"Lurkers: {len(lurkers)} | States: {states}"
        )
        self.logger.info(
            f"Ambushes: {self.ambushes_executed} | Range: {self.LURKER_RANGE}"
        )

    def get_ambush_stats(self) -> Dict:
        """Get ambush statistics"""
        if not hasattr(self.bot, "units"):
            return {}

        lurkers = self.bot.units(UnitTypeId.LURKERMP)

        return {
            "lurkers": len(lurkers),
            "ambushes": self.ambushes_executed,
            "range": self.LURKER_RANGE,
            "states": dict(self.lurker_states),
        }
