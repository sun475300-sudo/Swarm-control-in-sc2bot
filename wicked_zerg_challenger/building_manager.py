# -*- coding: utf-8 -*-
"""
Building Manager - centralized structure request and placement decisions.
"""

import logging
from typing import Any, Optional

try:
    from sc2.ids.unit_typeid import UnitTypeId
except (ImportError, TypeError):

    class UnitTypeId:
        HATCHERY = "HATCHERY"
        SPINECRAWLER = "SPINECRAWLER"
        SPORECRAWLER = "SPORECRAWLER"
        SPIRE = "SPIRE"

from utils.game_constants import GameFrequencies

logger = logging.getLogger("BuildingManager")


class BuildingManager:
    """Owns building request routing and coarse placement anchors."""

    PRIORITY_CRITICAL = 100
    PRIORITY_STRATEGY = 75
    PRIORITY_MACRO = 25

    DEFENSIVE_TYPES = {
        getattr(UnitTypeId, "SPINECRAWLER", "SPINECRAWLER"),
        getattr(UnitTypeId, "SPORECRAWLER", "SPORECRAWLER"),
    }

    def __init__(self, bot):
        self.bot = bot
        self.blackboard = getattr(bot, "blackboard", None)
        self.logger = logger
        self._ensure_building_coordination()

    async def on_step(self, iteration: int) -> None:
        """Consume urgent blackboard building flags on a low-frequency cadence."""
        if iteration % GameFrequencies.EVERY_SECOND != 0:
            return
        if not self.blackboard or not hasattr(self.blackboard, "get"):
            return

        try:
            if self.blackboard.get("urgent_spore_all_bases", False):
                self.request_defensive_building(spore=True, requester="Blackboard")
            urgent_spine_count = self.blackboard.get("urgent_spine_count", 0) or 0
            urgent_spines = self.blackboard.get("urgent_spine_all_bases", False)
            if urgent_spine_count or urgent_spines:
                count = max(1, int(urgent_spine_count or 1))
                for _ in range(count):
                    self.request_defensive_building(spine=True, requester="Blackboard")
        except Exception as exc:
            self.logger.debug("blackboard building request handling failed: %s", exc)

    def request_defensive_building(
        self,
        spine: bool = False,
        spore: bool = False,
        requester: str = "StrategyManager",
        near: Optional[Any] = None,
    ) -> bool:
        """Queue emergency defensive structures at a safe base anchor."""
        requested = False
        if spine:
            requested |= self.request_structure(
                UnitTypeId.SPINECRAWLER,
                requester=requester,
                priority=self.PRIORITY_CRITICAL,
                near=near,
            )
        if spore:
            requested |= self.request_structure(
                UnitTypeId.SPORECRAWLER,
                requester=requester,
                priority=self.PRIORITY_CRITICAL,
                near=near,
            )
            if self.blackboard and hasattr(self.blackboard, "set"):
                self.blackboard.set("urgent_spore_all_bases", True)
        return requested

    def request_tech_structure(
        self,
        structure_type: Any,
        requester: str = "StrategyManager",
        priority: int = PRIORITY_STRATEGY,
        near: Optional[Any] = None,
    ) -> bool:
        """Queue a tech structure through the central routing layer."""
        return self.request_structure(
            structure_type, requester=requester, priority=priority, near=near
        )

    def request_structure(
        self,
        structure_type: Any,
        requester: str = "BuildingManager",
        priority: int = PRIORITY_MACRO,
        near: Optional[Any] = None,
    ) -> bool:
        """Route structure requests through available coordinators."""
        build_anchor = self.pick_build_location(structure_type, near)

        tech_coordinator = getattr(self.bot, "tech_coordinator", None)
        if tech_coordinator and hasattr(tech_coordinator, "request_structure"):
            try:
                if hasattr(tech_coordinator, "is_planned") and tech_coordinator.is_planned(
                    structure_type
                ):
                    return False
                return bool(
                    tech_coordinator.request_structure(
                        structure_type,
                        build_anchor,
                        priority,
                        requester,
                    )
                )
            except Exception as exc:
                self.logger.debug("tech coordinator request failed: %s", exc)

        building_coord = self._ensure_building_coordination()
        if building_coord and hasattr(building_coord, "request_building"):
            try:
                return bool(building_coord.request_building(structure_type, requester))
            except Exception as exc:
                self.logger.debug("building coordination request failed: %s", exc)

        if self.blackboard and hasattr(self.blackboard, "set"):
            key = self._blackboard_key(structure_type)
            self.blackboard.set(key, True)
        return False

    def can_build(self, structure_type: Any) -> bool:
        """Expose duplicate checks for callers that previously used building_coord."""
        building_coord = self._ensure_building_coordination()
        if building_coord and hasattr(building_coord, "can_build"):
            try:
                return bool(building_coord.can_build(structure_type))
            except Exception:
                return True
        return True

    def pick_build_location(self, structure_type: Any, near: Optional[Any] = None) -> Any:
        """Choose a coarse anchor for construction requests."""
        if near is not None:
            return getattr(near, "position", near)

        if structure_type in self.DEFENSIVE_TYPES:
            threatened_base = self._threatened_base()
            if threatened_base is not None:
                return getattr(threatened_base, "position", threatened_base)

        townhalls = getattr(self.bot, "townhalls", None)
        ready_townhalls = getattr(townhalls, "ready", townhalls)
        first_base = self._first_unit(ready_townhalls) or self._first_unit(townhalls)
        if first_base is not None:
            return getattr(first_base, "position", first_base)

        return getattr(self.bot, "start_location", None)

    def get_building_count(self, structure_type: Any) -> dict:
        building_coord = self._ensure_building_coordination()
        if building_coord and hasattr(building_coord, "get_building_count"):
            try:
                return building_coord.get_building_count(structure_type)
            except Exception:
                pass
        structures = getattr(self.bot, "structures", None)
        try:
            existing = structures(structure_type).amount if structures else 0
        except Exception:
            existing = 0
        try:
            pending = self.bot.already_pending(structure_type)
        except Exception:
            pending = 0
        return {"existing": existing, "pending": pending, "total": existing + pending}

    def _ensure_building_coordination(self):
        building_coord = getattr(self.bot, "building_coord", None)
        if building_coord is not None:
            return building_coord
        try:
            from building_coordination import BuildingCoordination

            building_coord = BuildingCoordination(self.bot)
            self.bot.building_coord = building_coord
            return building_coord
        except Exception:
            return None

    def _threatened_base(self):
        townhalls = list(getattr(self.bot, "townhalls", []) or [])
        enemies = [
            enemy
            for enemy in list(getattr(self.bot, "enemy_units", []) or [])
            if getattr(enemy, "can_attack", True)
        ]
        if not townhalls or not enemies:
            return None

        closest_base = None
        closest_distance = float("inf")
        for base in townhalls:
            base_pos = getattr(base, "position", base)
            for enemy in enemies:
                try:
                    distance = enemy.distance_to(base_pos)
                except Exception:
                    enemy_pos = getattr(enemy, "position", enemy)
                    try:
                        distance = enemy_pos.distance_to(base_pos)
                    except Exception:
                        continue
                if distance < closest_distance:
                    closest_distance = distance
                    closest_base = base

        return closest_base if closest_distance <= 35.0 else None

    @staticmethod
    def _first_unit(units) -> Optional[Any]:
        if not units:
            return None
        first = getattr(units, "first", None)
        if first is not None:
            return first
        try:
            return next(iter(units))
        except Exception:
            return None

    @staticmethod
    def _blackboard_key(structure_type: Any) -> str:
        type_name = getattr(structure_type, "name", str(structure_type)).lower()
        return f"building_request_{type_name}"
