#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intel Manager - lightweight information manager with update/on_step bridge.
"""

from __future__ import annotations

import asyncio
from typing import Optional


class IntelManager:
    """Collects intel and bridges update() to on_step()."""

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 8
        self.enemy_race_name: Optional[str] = None

        # Enemy composition tracking
        self.enemy_army_supply = 0
        self.enemy_worker_count = 0
        self.enemy_base_count = 0
        self.enemy_tech_buildings = set()

        # Threat tracking
        self._under_attack = False
        self._attack_position = None
        self._last_attack_time = 0.0

        # Enemy unit type counts
        self.enemy_unit_counts = {}

    async def on_step(self, iteration: int) -> None:
        if iteration - self.last_update < self.update_interval:
            return
        self.last_update = iteration

        try:
            result = self.update(iteration)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            return

    def update(self, iteration: int) -> None:
        # Update enemy race
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race is None:
            self.enemy_race_name = None
        elif hasattr(enemy_race, "name"):
            self.enemy_race_name = str(enemy_race.name)
        else:
            self.enemy_race_name = str(enemy_race)

        # Update enemy unit composition
        self._update_enemy_composition()

        # Update threat status
        self._update_threat_status()

    def _update_enemy_composition(self) -> None:
        """Track enemy army composition."""
        enemy_units = getattr(self.bot, "enemy_units", [])
        enemy_structures = getattr(self.bot, "enemy_structures", [])

        # Count enemy units by type
        self.enemy_unit_counts = {}
        self.enemy_army_supply = 0
        self.enemy_worker_count = 0

        worker_names = {'SCV', 'PROBE', 'DRONE'}
        for unit in enemy_units:
            type_name = getattr(unit.type_id, "name", str(unit.type_id))
            self.enemy_unit_counts[type_name] = self.enemy_unit_counts.get(type_name, 0) + 1

            # Estimate supply
            supply = getattr(unit, "supply_cost", 1)
            if type_name.upper() in worker_names:
                self.enemy_worker_count += 1
            else:
                self.enemy_army_supply += supply

        # Count enemy bases
        base_types = {'COMMANDCENTER', 'COMMANDCENTERFLYING', 'ORBITALCOMMAND',
                     'ORBITALCOMMANDFLYING', 'PLANETARYFORTRESS',
                     'NEXUS', 'HATCHERY', 'LAIR', 'HIVE'}
        self.enemy_base_count = sum(
            1 for s in enemy_structures
            if getattr(s.type_id, "name", "").upper() in base_types
        )

        # Track tech buildings
        tech_buildings = {'FACTORY', 'STARPORT', 'ARMORY', 'FUSIONCORE',
                         'ROBOTICSFACILITY', 'STARGATE', 'DARKSHRINE',
                         'TEMPLARARCHIVE', 'FLEETBEACON',
                         'SPIRE', 'GREATERSPIRE', 'INFESTATIONPIT'}
        self.enemy_tech_buildings = {
            getattr(s.type_id, "name", "").upper()
            for s in enemy_structures
            if getattr(s.type_id, "name", "").upper() in tech_buildings
        }

    def _update_threat_status(self) -> None:
        """Check if we're under attack."""
        enemy_units = getattr(self.bot, "enemy_units", [])
        townhalls = getattr(self.bot, "townhalls", [])

        if not townhalls:
            self._under_attack = False
            return

        current_time = getattr(self.bot, "time", 0.0)

        # Check for enemies near our bases
        for th in townhalls:
            for enemy in enemy_units:
                try:
                    if enemy.distance_to(th.position) < 25:
                        self._under_attack = True
                        self._attack_position = enemy.position
                        self._last_attack_time = current_time
                        return
                except Exception:
                    continue

        # Clear attack flag after 10 seconds of no enemies
        if current_time - self._last_attack_time > 10:
            self._under_attack = False
            self._attack_position = None

    def is_under_attack(self) -> bool:
        """Check if any base is under attack."""
        return self._under_attack

    def get_attack_position(self):
        """Get position where attack is happening."""
        return self._attack_position

    def get_enemy_army_supply(self) -> int:
        """Get estimated enemy army supply."""
        return self.enemy_army_supply

    def get_enemy_composition(self) -> dict:
        """Get enemy unit type counts."""
        return self.enemy_unit_counts.copy()

    def has_enemy_tech(self, tech_name: str) -> bool:
        """Check if enemy has specific tech building."""
        return tech_name.upper() in self.enemy_tech_buildings
