# -*- coding: utf-8 -*-
"""
Mutalisk Micro Controller - Advanced Mutalisk tactics

Features:
1. Regen Dance: Damaged Mutalisks retreat to regenerate health
2. Magic Box: Spread formation against splash damage units (Thor, Archon)
3. Bounce targeting optimization
"""

import math
from typing import Dict, List, Optional, Set, Tuple

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit
except ImportError:
    UnitTypeId = None
    Point2 = None
    Unit = None


ANTI_AIR_THREAT_NAMES = {"THOR", "ARCHON", "QUEEN", "MARINE", "HYDRALISK"}


class MutaliskMicroController:
    """
    Advanced Mutalisk micro management.

    Key tactics:
    - Regen Dance: Rotate damaged units out of combat
    - Magic Box: 3D sphere formation against splash damage
    """

    def __init__(
        self,
        regen_threshold: float = 0.5,  # Retreat when HP < 50%
        regen_target: float = 0.9,  # Return when HP > 90%
        regen_cooldown: float = 3.0,  # Minimum time between regen cycles
        magic_box_radius: float = 2.5,  # Spread radius for magic box
    ):
        """
        Initialize Mutalisk micro controller.

        Args:
            regen_threshold: Health ratio below which to retreat for regen
            regen_target: Health ratio above which to return to combat
            regen_cooldown: Seconds between regen checks
            magic_box_radius: Radius for magic box spread formation
        """
        self.regen_threshold = regen_threshold
        self.regen_target = regen_target
        self.regen_cooldown = regen_cooldown
        self.magic_box_radius = magic_box_radius

        # Regen Dance state tracking
        self.regenerating_units: Dict[int, float] = {}  # unit_tag -> start_time
        self.last_regen_check: float = 0.0

        # Splash damage unit types (Magic Box triggers)
        self.splash_threats: Set = set()
        self.anti_air_threats: Set = set()
        if UnitTypeId:
            self.splash_threats = {
                UnitTypeId.THOR,
                UnitTypeId.THORAP,
                UnitTypeId.ARCHON,
                UnitTypeId.PHOENIX,  # With range upgrade
                UnitTypeId.TEMPEST,
            }
            self.anti_air_threats = {
                getattr(UnitTypeId, name, None) for name in ANTI_AIR_THREAT_NAMES
            }
            self.anti_air_threats.discard(None)

    def should_use_magic_box(self, enemy_units) -> bool:
        """
        Check if Magic Box formation should be used.

        Args:
            enemy_units: All visible enemy units

        Returns:
            True if splash threats are detected
        """
        if not enemy_units or not self.splash_threats:
            return False

        for enemy in enemy_units:
            if enemy.type_id in self.splash_threats:
                return True

        return False

    def get_magic_box_position(
        self, unit: Unit, target_center: object, unit_index: int, total_units: int
    ) -> Optional[object]:
        """
        Calculate Magic Box position for a Mutalisk.

        Spreads units in a spherical pattern around the target.

        Args:
            unit: The Mutalisk
            target_center: Center position to attack
            unit_index: Index of this unit in the group
            total_units: Total number of Mutalisks

        Returns:
            Offset position for Magic Box formation
        """
        if not Point2 or total_units == 0:
            return None

        # Use golden angle for even distribution
        # https://en.wikipedia.org/wiki/Golden_angle
        golden_angle = math.pi * (3.0 - math.sqrt(5.0))  # ~137.5 degrees

        # Calculate angle for this unit
        theta = unit_index * golden_angle

        # Spiral radius increases with index
        radius_factor = math.sqrt(unit_index / max(total_units, 1))
        radius = self.magic_box_radius * radius_factor

        # Calculate offset position
        offset_x = radius * math.cos(theta)
        offset_y = radius * math.sin(theta)

        return Point2((target_center.x + offset_x, target_center.y + offset_y))

    def get_regen_status(self, unit: Unit, current_time: float) -> Tuple[bool, bool]:
        """
        Get regeneration status for a Mutalisk.

        Args:
            unit: The Mutalisk
            current_time: Current game time in seconds

        Returns:
            Tuple of (should_start_regen, should_end_regen)
        """
        unit_tag = unit.tag
        health_ratio = self._get_health_ratio(unit)

        # Check if already regenerating
        if unit_tag in self.regenerating_units:
            regen_start = self.regenerating_units[unit_tag]
            time_regenerating = current_time - regen_start

            # End regeneration if:
            # 1. Health above target threshold
            # 2. Or regenerating for at least 3 seconds (minimum regen time)
            if health_ratio >= self.regen_target or time_regenerating >= 3.0:
                return (False, True)  # End regen

            return (False, False)  # Continue regen

        # Start regeneration if health below threshold
        if health_ratio < self.regen_threshold:
            return (True, False)  # Start regen

        return (False, False)  # No change

    def mark_regenerating(self, unit_tag: int, current_time: float):
        """Mark a unit as regenerating."""
        self.regenerating_units[unit_tag] = current_time

    def end_regenerating(self, unit_tag: int):
        """Remove a unit from regenerating state."""
        if unit_tag in self.regenerating_units:
            del self.regenerating_units[unit_tag]

    def get_regen_position(self, unit: Unit, bot) -> Optional[object]:
        """
        Get safe position for regeneration.

        Args:
            unit: The Mutalisk
            bot: Bot instance

        Returns:
            Safe position away from enemies
        """
        # Retreat towards our main base
        townhalls = getattr(bot, "townhalls", None)
        main_base = None
        if townhalls is not None:
            if hasattr(townhalls, "exists") and townhalls.exists:
                main_base = getattr(townhalls.first, "position", townhalls.first)
            else:
                try:
                    townhall_list = list(townhalls or [])
                    if townhall_list:
                        main_base = getattr(townhall_list[0], "position", townhall_list[0])
                except TypeError:
                    main_base = None

        if main_base is not None:

            # Move 10 units towards base from current position
            direction_x = main_base.x - unit.position.x
            direction_y = main_base.y - unit.position.y
            length = math.hypot(direction_x, direction_y)

            if length > 0:
                norm_x = direction_x / length
                norm_y = direction_y / length

                target_x = unit.position.x + norm_x * 10
                target_y = unit.position.y + norm_y * 10
                if Point2 is not None:
                    try:
                        return Point2((target_x, target_y))
                    except Exception:
                        pass
                # Fallback: use unit.position.towards if available
                if hasattr(unit.position, "towards"):
                    try:
                        return unit.position.towards(main_base, 10)
                    except Exception:
                        pass

        # Fallback: move away from current position
        if hasattr(bot, "start_location"):
            return bot.start_location

        return None

    def get_anti_air_threats(self, enemy_units, around=None) -> List:
        """Return anti-air threats close enough to zone Mutalisks."""
        if not enemy_units:
            return []

        threats = []
        for enemy in enemy_units:
            name = getattr(getattr(enemy, "type_id", None), "name", "").upper()
            unit_type = getattr(enemy, "type_id", None)
            try:
                type_matches = unit_type in self.anti_air_threats
            except TypeError:
                type_matches = False
            if name not in ANTI_AIR_THREAT_NAMES and not type_matches:
                continue
            if around is None:
                threats.append(enemy)
                continue
            try:
                threat_range = max(
                    float(getattr(enemy, "air_range", 0) or 0),
                    float(getattr(enemy, "ground_range", 0) or 0),
                    5.0,
                )
                if around.distance_to(enemy) <= threat_range + 2.0:
                    threats.append(enemy)
            except Exception:
                threats.append(enemy)
        return threats

    def should_retreat_from_anti_air(self, unit: Unit, enemy_units) -> bool:
        return bool(self.get_anti_air_threats(enemy_units, around=unit))

    def select_bounce_target(self, enemy_units):
        """Pick the target with the densest nearby pack for bounce damage."""
        enemies = list(enemy_units or [])
        if not enemies:
            return None

        best = None
        best_score = None
        for enemy in enemies:
            try:
                nearby = sum(1 for other in enemies if enemy.distance_to(other) <= 3.0)
            except Exception:
                nearby = 1
            worker_bonus = (
                2
                if getattr(getattr(enemy, "type_id", None), "name", "")
                in {"SCV", "PROBE", "DRONE"}
                else 0
            )
            low_hp_bonus = 1 if getattr(enemy, "health_percentage", 1.0) < 0.35 else 0
            score = nearby + worker_bonus + low_hp_bonus
            if best_score is None or score > best_score:
                best = enemy
                best_score = score
        return best

    def get_stack_point(self, mutalisks) -> Optional[object]:
        """Return a single stack point for synchronized Mutalisk attacks."""
        muta_list = list(mutalisks or [])
        if not muta_list:
            return None
        if not Point2:
            return getattr(muta_list[0], "position", None)
        x = sum(muta.position.x for muta in muta_list) / len(muta_list)
        y = sum(muta.position.y for muta in muta_list) / len(muta_list)
        return Point2((x, y))

    async def execute_hit_and_run(
        self, mutalisks, enemy_units, bot, current_time: float
    ) -> bool:
        """Stack, focus bounce targets, and retreat from anti-air range."""
        muta_list = list(mutalisks or [])
        if not muta_list:
            return False

        actions = []
        combat_ready = []
        for muta in muta_list:
            if self._get_health_ratio(muta) < self.regen_threshold:
                self.mark_regenerating(muta.tag, current_time)
                regen_pos = self.get_regen_position(muta, bot)
                if regen_pos:
                    actions.append(muta.move(regen_pos))
                continue
            combat_ready.append(muta)

        if not combat_ready:
            await self._issue(bot, actions)
            return bool(actions)

        stack_point = self.get_stack_point(combat_ready)
        target = self.select_bounce_target(enemy_units)
        for muta in combat_ready:
            threats = self.get_anti_air_threats(enemy_units, around=muta)
            if threats:
                closest = min(threats, key=lambda enemy: muta.distance_to(enemy))
                actions.append(muta.move(muta.position.towards(closest.position, -7)))
                continue
            if stack_point is not None:
                try:
                    if muta.distance_to(stack_point) > 1.5 and len(combat_ready) >= 3:
                        actions.append(muta.move(stack_point))
                        continue
                except Exception:
                    pass
            if target:
                actions.append(muta.attack(target))

        await self._issue(bot, actions)
        return bool(actions)

    def is_regenerating(self, unit_tag: int) -> bool:
        """Check if a unit is currently regenerating."""
        return unit_tag in self.regenerating_units

    @staticmethod
    def _get_health_ratio(unit: Unit) -> float:
        """Get unit's current health ratio (0-1)."""
        health = getattr(unit, "health", 0)
        health_max = getattr(unit, "health_max", 1)
        if health_max <= 0:
            return 1.0
        return max(0.0, min(1.0, health / health_max))

    async def execute_regen_dance(
        self, mutalisks, current_time: float, bot
    ) -> Tuple[List, List]:
        """
        Execute Regen Dance logic.

        Args:
            mutalisks: All Mutalisks
            current_time: Current game time
            bot: Bot instance

        Returns:
            Tuple of (combat_ready_mutalisks, regenerating_mutalisks)
        """
        combat_ready = []
        regenerating = []
        actions = []

        for muta in mutalisks:
            start_regen, end_regen = self.get_regen_status(muta, current_time)

            if start_regen:
                # Start regeneration
                self.mark_regenerating(muta.tag, current_time)
                regen_pos = self.get_regen_position(muta, bot)
                if regen_pos:
                    try:
                        actions.append(muta.move(regen_pos))
                        regenerating.append(muta)
                    except Exception:
                        combat_ready.append(muta)
                else:
                    combat_ready.append(muta)

            elif end_regen:
                # End regeneration
                self.end_regenerating(muta.tag)
                combat_ready.append(muta)

            elif self.is_regenerating(muta.tag):
                # Continue regenerating
                regen_pos = self.get_regen_position(muta, bot)
                if regen_pos:
                    try:
                        actions.append(muta.move(regen_pos))
                        regenerating.append(muta)
                    except Exception:
                        combat_ready.append(muta)
                else:
                    combat_ready.append(muta)

            else:
                # Combat ready
                combat_ready.append(muta)

        # Execute all move actions
        if actions:
            await self._issue(bot, actions)

        return combat_ready, regenerating

    async def execute_magic_box(self, mutalisks, target_position: object, bot):
        """
        Execute Magic Box formation.

        Args:
            mutalisks: All Mutalisks to position
            target_position: Center position to attack from
            bot: Bot instance
        """
        if not mutalisks:
            return

        actions = []
        total = len(mutalisks)

        for index, muta in enumerate(mutalisks):
            magic_pos = self.get_magic_box_position(muta, target_position, index, total)

            if magic_pos:
                try:
                    # Move to magic box position, then attack
                    actions.append(muta.move(magic_pos))
                except Exception:
                    continue

        if actions:
            await self._issue(bot, actions)

    @staticmethod
    async def _issue(bot, actions: List) -> None:
        for action in actions:
            try:
                result = bot.do(action)
                if hasattr(result, "__await__"):
                    await result
            except Exception:
                pass
