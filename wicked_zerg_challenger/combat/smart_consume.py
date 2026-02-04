# -*- coding: utf-8 -*-
"""
Smart Consume System - Phase 19

Intelligent building consumption for Vipers:
1. Avoid consuming tech buildings (Spire, Infestation Pit, etc.)
2. Prioritize low-value buildings (Evolution Chamber, Spore Crawler, Spine Crawler)
3. Energy-based decision making
4. Safety checks to prevent hurting economy

Features:
- Building priority system
- Critical building protection
- Energy management
- Safety checks
"""

from typing import List, Set, Optional
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.unit import Unit
    from sc2.units import Units
except ImportError:
    BotAI = object
    UnitTypeId = object
    AbilityId = object
    Unit = object
    Units = list


class SmartConsumeSystem:
    """
    Smart Consume System for Vipers

    Manages viper energy by intelligently consuming buildings.
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("SmartConsume")

        # Energy thresholds
        self.CONSUME_ENERGY_THRESHOLD = 150  # Only consume if energy < 150
        self.MIN_ENERGY_AFTER_CONSUME = 50  # Don't consume if it would bring us below 50

        # Building priorities (lower = more likely to consume)
        self.BUILDING_PRIORITIES = {
            # Highest priority (most consumable)
            UnitTypeId.EVOLUTIONCHAMBER: 1,
            UnitTypeId.SPINECRAWLER: 2,
            UnitTypeId.SPORECRAWLER: 2,

            # Medium priority (consume if really needed)
            UnitTypeId.EXTRACTOR: 5,
            UnitTypeId.ROACHWARREN: 6,
            UnitTypeId.BANELINGNEST: 6,
            UnitTypeId.SPAWNINGPOOL: 7,

            # Low priority (avoid consuming)
            UnitTypeId.HYDRALISKDEN: 10,
            UnitTypeId.SPIRE: 15,
            UnitTypeId.INFESTATIONPIT: 15,
            UnitTypeId.NYDUSNETWORK: 15,
            UnitTypeId.ULTRALISKCAVERN: 15,

            # NEVER consume (critical buildings)
            UnitTypeId.HATCHERY: 999,
            UnitTypeId.LAIR: 999,
            UnitTypeId.HIVE: 999,
            UnitTypeId.GREATERSPIRE: 999,
            UnitTypeId.LURKERDENMP: 999,
        }

        # Minimum count protection (don't consume if count <= threshold)
        self.MIN_BUILDING_COUNTS = {
            UnitTypeId.EVOLUTIONCHAMBER: 1,  # Keep at least 1
            UnitTypeId.SPAWNINGPOOL: 1,
            UnitTypeId.SPIRE: 1,
            UnitTypeId.INFESTATIONPIT: 1,
            UnitTypeId.EXTRACTOR: 2,  # Keep at least 2 extractors
        }

        # Statistics
        self.buildings_consumed = 0
        self.energy_gained = 0
        self.last_consume_time = 0

    async def on_step(self, iteration: int):
        """Main update loop"""
        try:
            # Manage vipers
            if iteration % 22 == 0:  # ~1 second
                await self._manage_vipers()

            # Report statistics
            if iteration % 1100 == 0:  # ~50 seconds
                self._print_report()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[SMART_CONSUME] Error: {e}")

    # ========================================
    # Main Viper Management
    # ========================================

    async def _manage_vipers(self):
        """Manage all vipers"""
        if not hasattr(self.bot, "units"):
            return

        vipers = self.bot.units(UnitTypeId.VIPER)
        if not vipers:
            return

        for viper in vipers:
            await self._manage_single_viper(viper)

    async def _manage_single_viper(self, viper: Unit):
        """Manage individual viper"""
        # Check if viper needs energy
        if viper.energy >= self.CONSUME_ENERGY_THRESHOLD:
            return  # Energy is sufficient

        # Find consumable building
        target = self._find_consumable_building(viper)
        if not target:
            return  # No suitable target

        # Consume!
        await self._consume_building(viper, target)

    # ========================================
    # Building Selection
    # ========================================

    def _find_consumable_building(self, viper: Unit) -> Optional[Unit]:
        """Find best building to consume"""
        if not hasattr(self.bot, "structures"):
            return None

        structures = self.bot.structures.ready

        # Filter consumable buildings
        candidates = []
        for structure in structures:
            if self._is_consumable(structure):
                priority = self.BUILDING_PRIORITIES.get(structure.type_id, 50)
                distance = viper.distance_to(structure)
                candidates.append((structure, priority, distance))

        if not candidates:
            return None

        # Sort by priority (low = good), then by distance
        candidates.sort(key=lambda x: (x[1], x[2]))

        # Return best candidate
        return candidates[0][0]

    def _is_consumable(self, structure: Unit) -> bool:
        """Check if building can be consumed"""
        building_type = structure.type_id

        # Priority check (999 = NEVER consume)
        priority = self.BUILDING_PRIORITIES.get(building_type, 50)
        if priority >= 999:
            return False

        # Count check (don't consume if below minimum)
        if building_type in self.MIN_BUILDING_COUNTS:
            min_count = self.MIN_BUILDING_COUNTS[building_type]
            current_count = self.bot.structures(building_type).ready.amount

            if current_count <= min_count:
                return False

        # Building must be completed
        if not structure.is_ready:
            return False

        # Special checks
        if building_type == UnitTypeId.EXTRACTOR:
            # Don't consume extractor if it has workers assigned
            if structure.assigned_harvesters > 0:
                return False

        if building_type in {UnitTypeId.SPINECRAWLER, UnitTypeId.SPORECRAWLER}:
            # Don't consume defense structures if under attack
            if self._is_under_attack():
                return False

        return True

    def _is_under_attack(self) -> bool:
        """Check if we're under attack"""
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "enemy_units"):
            return False

        townhalls = self.bot.townhalls
        enemy_units = self.bot.enemy_units

        if not townhalls.exists or not enemy_units.exists:
            return False

        # Check if enemies near any base
        for townhall in townhalls:
            if hasattr(enemy_units, "closer_than"):
                nearby_enemies = enemy_units.closer_than(25, townhall)
            else:
                nearby_enemies = [e for e in enemy_units if e.distance_to(townhall) < 25]

            if nearby_enemies:
                return True

        return False

    # ========================================
    # Consume Execution
    # ========================================

    async def _consume_building(self, viper: Unit, target: Unit):
        """Execute consume ability"""
        game_time = self.bot.time

        # Double-check viper can use ability
        abilities = await self.bot.get_available_abilities(viper)
        if AbilityId.CONSUME_VIPER not in abilities:
            return

        # Execute consume
        self.bot.do(viper(AbilityId.CONSUME_VIPER, target))

        # Update statistics
        self.buildings_consumed += 1
        self.energy_gained += 50  # Consume gives 50 energy
        self.last_consume_time = game_time

        # Log
        self.logger.info(
            f"[{int(game_time)}s] Viper consumed {target.type_id.name} "
            f"(Total: {self.buildings_consumed}, Energy: {viper.energy:.0f} -> {viper.energy+50:.0f})"
        )

    # ========================================
    # Statistics
    # ========================================

    def _print_report(self):
        """Print consume statistics"""
        game_time = self.bot.time

        if not hasattr(self.bot, "units"):
            return

        vipers = self.bot.units(UnitTypeId.VIPER)

        # Average viper energy
        avg_energy = sum(v.energy for v in vipers) / len(vipers) if vipers else 0

        self.logger.info(
            f"[{int(game_time)}s] === SMART CONSUME REPORT ==="
        )
        self.logger.info(
            f"Vipers: {len(vipers)} | Avg Energy: {avg_energy:.1f}"
        )
        self.logger.info(
            f"Consumed: {self.buildings_consumed} buildings | Energy gained: {self.energy_gained}"
        )

    def get_consume_stats(self) -> dict:
        """Get consume statistics"""
        if not hasattr(self.bot, "units"):
            return {}

        vipers = self.bot.units(UnitTypeId.VIPER)

        return {
            "vipers": len(vipers),
            "buildings_consumed": self.buildings_consumed,
            "energy_gained": self.energy_gained,
            "last_consume_time": self.last_consume_time,
        }

    # ========================================
    # Configuration
    # ========================================

    def protect_building(self, building_type: UnitTypeId):
        """Add building type to protected list"""
        self.BUILDING_PRIORITIES[building_type] = 999

    def set_min_building_count(self, building_type: UnitTypeId, count: int):
        """Set minimum count for building type"""
        self.MIN_BUILDING_COUNTS[building_type] = count
