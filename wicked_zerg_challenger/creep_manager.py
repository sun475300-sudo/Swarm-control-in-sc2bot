#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creep Manager - creep spread automation.

Features:
1) Assigns creep queens (non-inject queens)
2) Influence-map style path expansion toward enemy routes
3) Tumor relay: oldest tumors push farther when ready
"""

from typing import Dict, List, Optional

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
    from combat.formation_manager import FormationManager
except ImportError:
    class UnitTypeId:
        QUEEN = "QUEEN"
        CREEPTUMOR = "CREEPTUMOR"
        CREEPTUMORBURROWED = "CREEPTUMORBURROWED"
        CREEPTUMORQUEEN = "CREEPTUMORQUEEN"
        OVERLORD = "OVERLORD"

    class AbilityId:
        BUILD_CREEPTUMOR_QUEEN = "BUILD_CREEPTUMOR_QUEEN"
        BUILD_CREEPTUMOR_TUMOR = "BUILD_CREEPTUMOR_TUMOR"

    Point2 = tuple
    FormationManager = None


class CreepManager:
    def __init__(self, bot):
        self.bot = bot
        self.creep_queen_tags: List[int] = []
        self.last_creep_spread = 0
        self.spread_interval = 44  # ~2s

    async def on_step(self, iteration: int):
        if iteration - self.last_creep_spread < self.spread_interval:
            return
        self.last_creep_spread = iteration
        await self._assign_creep_queens()
        await self._spread_creep_with_queens()
        await self._relay_tumors()

    async def _assign_creep_queens(self):
        if not hasattr(self.bot, "units"):
            return
        queens = self.bot.units(UnitTypeId.QUEEN)
        if not queens.exists:
            return

        # Exclude inject queens if queen_manager is present
        inject_tags = set()
        queen_manager = getattr(self.bot, "queen_manager", None)
        if queen_manager and hasattr(queen_manager, "queen_hatchery_assignments"):
            inject_tags = set(queen_manager.queen_hatchery_assignments.keys())

        available = [q for q in queens if q.tag not in inject_tags]
        # Keep at most 2 creep queens early, 3 later
        max_creep_queens = 2 if self.bot.time < 360 else 3
        self.creep_queen_tags = [q.tag for q in available[:max_creep_queens]]

    async def _spread_creep_with_queens(self):
        queens = self._get_creep_queens()
        if not queens:
            return
        if not self.bot.enemy_start_locations or not self.bot.townhalls.exists:
            return

        enemy_start = self.bot.enemy_start_locations[0]
        base = self.bot.townhalls.first.position

        # Target points along the main path (influence-style)
        targets = [
            base.towards(enemy_start, 15.0),
            base.towards(enemy_start, 25.0),
            base.towards(enemy_start, 35.0),
        ]
        chokepoints = self._get_chokepoint_targets()
        if chokepoints:
            targets = chokepoints + targets

        for queen in queens:
            if queen.energy < 25:
                continue
            for target in targets:
                placement = await self._find_creep_placement(target)
                if placement is None:
                    continue
                try:
                    await self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, placement))
                    break
                except Exception:
                    continue

    async def _relay_tumors(self):
        if not hasattr(self.bot, "units"):
            return
        tumors = self.bot.units(UnitTypeId.CREEPTUMOR).ready
        if not tumors.exists:
            tumors = self.bot.units(UnitTypeId.CREEPTUMORBURROWED).ready
        if not tumors.exists:
            return
        if not self.bot.enemy_start_locations or not self.bot.townhalls.exists:
            return

        enemy_start = self.bot.enemy_start_locations[0]
        base = self.bot.townhalls.first.position
        sorted_tumors = sorted(tumors, key=lambda t: t.distance_to(enemy_start), reverse=True)

        for tumor in sorted_tumors[:6]:
            target = tumor.position.towards(enemy_start, 9.0)
            placement = await self._find_creep_placement(target)
            if placement is None:
                continue
            try:
                await self.bot.do(tumor(AbilityId.BUILD_CREEPTUMOR_TUMOR, placement))
                break
            except Exception:
                continue

    async def _find_creep_placement(self, target: "Point2") -> Optional["Point2"]:
        try:
            if hasattr(self.bot, "find_placement"):
                return await self.bot.find_placement(
                    AbilityId.BUILD_CREEPTUMOR_QUEEN,
                    near=target,
                    placement_step=4,
                )
        except Exception:
            return None
        return None

    def _get_creep_queens(self):
        if not hasattr(self.bot, "units"):
            return []
        queens = self.bot.units(UnitTypeId.QUEEN)
        return [q for q in queens if q.tag in self.creep_queen_tags]

    def _get_chokepoint_targets(self) -> List["Point2"]:
        if FormationManager is None:
            return []
        try:
            formation = FormationManager(self.bot)
            if hasattr(self.bot, "game_info"):
                points = formation.find_choke_points(self.bot.game_info)
                return points or []
        except Exception:
            return []
        return []
