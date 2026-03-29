# -*- coding: utf-8 -*-
"""
Early Scout System.

Lightweight Zergling/Overlord scouting with blackboard synchronization so
opening decisions can consume the scout state reliably.
"""

from typing import Any, Dict, List, Optional, Set

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    class BotAI:
        pass

    class UnitTypeId:
        ZERGLING = "ZERGLING"
        OVERLORD = "OVERLORD"
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        ASSIMILATOR = "ASSIMILATOR"
        REFINERY = "REFINERY"
        HATCHERY = "HATCHERY"
        COMMANDCENTER = "COMMANDCENTER"
        NEXUS = "NEXUS"

    class Point2:
        pass


GAS_BUILDING_TYPES: Set[object] = {
    UnitTypeId.EXTRACTOR,
    UnitTypeId.ASSIMILATOR,
    UnitTypeId.REFINERY,
}

TOWNHALL_TYPE_NAMES = {
    "HATCHERY",
    "LAIR",
    "HIVE",
    "COMMANDCENTER",
    "ORBITALCOMMAND",
    "PLANETARYFORTRESS",
    "NEXUS",
}


class EarlyScoutSystem:
    """Controls early scouting and exposes stable blackboard state."""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.early_game_threshold = 300.0

        self.scout_ling_tags: List[int] = []
        self.max_scout_lings = 3
        self.ling_scouts_assigned = False

        self.scout_overlord_tag: Optional[int] = None
        self.overlord_scout_sent = False

        self.ling_waypoints: Dict[int, List[Point2]] = {}
        self.ling_current_wp: Dict[int, int] = {}
        self.overlord_waypoints: List[Point2] = []
        self.overlord_current_wp = 0

        self.enemy_pool_timing: Optional[float] = None
        self.enemy_gas_timing: Optional[float] = None
        self.enemy_natural_timing: Optional[float] = None
        self.enemy_early_units: Set[int] = set()
        self.proxy_detected = False
        self.cheese_suspected = False

        self.main_base_scouted = False
        self.natural_scouted = False
        self.third_scouted = False

        self._last_update = 0.0
        self._update_interval = 0.5
        self._last_report_time = 0.0
        self._last_rescout_time = 0.0

    def _get_blackboard(self) -> Any:
        return getattr(self.bot, "blackboard", None)

    def _get_enemy_natural_location(self) -> Optional[Point2]:
        enemy_starts = getattr(self.bot, "enemy_start_locations", [])
        if not enemy_starts:
            return None

        enemy_start = enemy_starts[0]
        expansions = getattr(self.bot, "expansion_locations_list", None) or []
        if expansions:
            sorted_exps = sorted(expansions, key=lambda p: p.distance_to(enemy_start))
            for expansion in sorted_exps:
                if expansion.distance_to(enemy_start) > 1:
                    return expansion

        game_info = getattr(self.bot, "game_info", None)
        map_center = getattr(game_info, "map_center", None)
        if map_center is None:
            return None
        return map_center.towards(enemy_start, map_center.distance_to(enemy_start) * 0.65)

    def _is_enemy_townhall(self, structure: Any) -> bool:
        type_id = getattr(structure, "type_id", None)
        if type_id in {
            getattr(UnitTypeId, "HATCHERY", None),
            getattr(UnitTypeId, "COMMANDCENTER", None),
            getattr(UnitTypeId, "NEXUS", None),
        }:
            return True

        type_name = getattr(type_id, "name", str(type_id)).upper()
        return type_name in TOWNHALL_TYPE_NAMES

    def _sync_blackboard_state(self, refresh_report: bool = False) -> None:
        blackboard = self._get_blackboard()
        if refresh_report:
            self._last_report_time = getattr(self.bot, "time", 0.0)

        if not blackboard:
            return

        natural_confirmed = self.enemy_natural_timing is not None
        blackboard.set("early_scout_pool_time", self.enemy_pool_timing)
        blackboard.set("early_scout_gas_time", self.enemy_gas_timing)
        blackboard.set("early_scout_natural_confirmed", natural_confirmed)
        blackboard.set("early_scout_cheese_suspected", self.cheese_suspected)
        blackboard.set("early_scout_last_report_time", self._last_report_time)
        blackboard.set(
            "early_scout_rescout_active",
            getattr(self.bot, "time", 0.0) > self.early_game_threshold,
        )

        # Compatibility keys used by other systems.
        blackboard.set("enemy_pool_timing", self.enemy_pool_timing)
        blackboard.set("enemy_gas_timing", self.enemy_gas_timing)
        blackboard.set("enemy_natural_timing", self.enemy_natural_timing)
        blackboard.set("enemy_is_cheese", self.cheese_suspected)

    async def execute(self, iteration: int) -> None:
        """Main update loop."""
        del iteration

        if self.bot.time - self._last_update < self._update_interval:
            self._sync_blackboard_state(refresh_report=False)
            return
        self._last_update = self.bot.time

        await self._analyze_enemy_info()

        if self.bot.time <= self.early_game_threshold:
            if not self.ling_scouts_assigned:
                await self._assign_zergling_scouts()
            if self.scout_ling_tags:
                await self._manage_zergling_scouts()

        if not self.overlord_scout_sent and self.bot.time > 5:
            await self._send_overlord_scout()
        if self.scout_overlord_tag:
            await self._manage_overlord_scout()

        if self.bot.time > self.early_game_threshold:
            await self._mid_game_rescouting()

        self._sync_blackboard_state(refresh_report=True)

    async def _assign_zergling_scouts(self) -> None:
        pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not pools:
            return

        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if zerglings.amount < 2:
            return

        if not getattr(self.bot, "enemy_start_locations", None):
            return

        if self.ling_scouts_assigned:
            return

        enemy_start = self.bot.enemy_start_locations[0]
        our_base = self.bot.start_location
        map_center = self.bot.game_info.map_center
        scout_lings = zerglings.take(self.max_scout_lings)

        for index, ling in enumerate(scout_lings):
            self.scout_ling_tags.append(ling.tag)
            if index == 0:
                waypoints = [
                    enemy_start,
                    enemy_start.towards(map_center, 8),
                    map_center,
                ]
            else:
                waypoints = [
                    our_base.towards(enemy_start, 20),
                    map_center,
                    enemy_start.towards(our_base, 15),
                ]

            self.ling_waypoints[ling.tag] = waypoints
            self.ling_current_wp[ling.tag] = 0
            self.bot.do(ling.move(waypoints[0]))

        self.ling_scouts_assigned = True
        print(
            f"[EARLY_SCOUT] Sent {len(scout_lings)} Zergling scouts "
            f"at {int(self.bot.time)}s"
        )

    async def _manage_zergling_scouts(self) -> None:
        alive_scouts = self.bot.units(UnitTypeId.ZERGLING).tags_in(self.scout_ling_tags)

        for ling in alive_scouts:
            if ling.tag not in self.ling_waypoints:
                continue

            waypoints = self.ling_waypoints[ling.tag]
            current_wp_idx = self.ling_current_wp.get(ling.tag, 0)
            if current_wp_idx >= len(waypoints):
                continue

            target = waypoints[current_wp_idx]
            if ling.distance_to(target) < 3:
                self.ling_current_wp[ling.tag] = current_wp_idx + 1
                if current_wp_idx == 0:
                    self.main_base_scouted = True
                elif current_wp_idx == 1:
                    self.natural_scouted = True

                if self.ling_current_wp[ling.tag] < len(waypoints):
                    next_target = waypoints[self.ling_current_wp[ling.tag]]
                    self.bot.do(ling.move(next_target))

    async def _send_overlord_scout(self) -> None:
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        if not overlords or self.overlord_scout_sent:
            return

        scout_ol = overlords.first
        self.scout_overlord_tag = scout_ol.tag

        map_center = self.bot.game_info.map_center
        enemy_start = self.bot.enemy_start_locations[0] if self.bot.enemy_start_locations else map_center
        enemy_natural = self._get_enemy_natural_location() or map_center.towards(
            enemy_start,
            max(1, map_center.distance_to(enemy_start) * 0.65),
        )

        self.overlord_waypoints = [
            map_center,
            enemy_natural,
            map_center.towards(enemy_start, 15),
        ]
        self.overlord_current_wp = 0

        self.bot.do(scout_ol.move(self.overlord_waypoints[0]))
        self.overlord_scout_sent = True
        print(f"[EARLY_SCOUT] Sent Overlord scout at {int(self.bot.time)}s")

    async def _manage_overlord_scout(self) -> None:
        overlords = self.bot.units(UnitTypeId.OVERLORD).tags_in([self.scout_overlord_tag])
        if not overlords:
            self.scout_overlord_tag = None
            self.overlord_scout_sent = False
            return

        scout_ol = overlords.first
        if self.overlord_current_wp >= len(self.overlord_waypoints):
            return

        target = self.overlord_waypoints[self.overlord_current_wp]
        if scout_ol.distance_to(target) < 5:
            self.overlord_current_wp += 1
            if self.overlord_current_wp < len(self.overlord_waypoints):
                next_target = self.overlord_waypoints[self.overlord_current_wp]
                self.bot.do(scout_ol.move(next_target))

    async def _analyze_enemy_info(self) -> None:
        structures = getattr(self.bot, "enemy_structures", None)
        if structures:
            enemy_natural = self._get_enemy_natural_location()
            for structure in structures:
                type_id = getattr(structure, "type_id", None)
                type_name = getattr(type_id, "name", str(type_id)).upper()

                if not self.enemy_pool_timing and type_name == "SPAWNINGPOOL":
                    self.enemy_pool_timing = self.bot.time
                    print(f"[EARLY_SCOUT] Enemy pool spotted at {int(self.bot.time)}s")
                    if self.bot.time < 90:
                        self.cheese_suspected = True
                        print("[EARLY_SCOUT] Early pool detected, cheese suspected")

                if not self.enemy_gas_timing and (
                    type_id in GAS_BUILDING_TYPES
                    or type_name in {"EXTRACTOR", "ASSIMILATOR", "REFINERY"}
                ):
                    self.enemy_gas_timing = self.bot.time
                    print(f"[EARLY_SCOUT] Enemy gas spotted at {int(self.bot.time)}s")

                if (
                    enemy_natural is not None
                    and not self.enemy_natural_timing
                    and self._is_enemy_townhall(structure)
                    and structure.distance_to(enemy_natural) <= 8
                ):
                    self.enemy_natural_timing = self.bot.time
                    self.natural_scouted = True
                    print(f"[EARLY_SCOUT] Enemy natural confirmed at {int(self.bot.time)}s")

        enemy_units = getattr(self.bot, "enemy_units", None)
        if enemy_units:
            for unit in enemy_units:
                unit_tag = getattr(unit, "tag", None)
                if unit_tag is not None and unit_tag not in self.enemy_early_units:
                    self.enemy_early_units.add(unit_tag)

    async def _mid_game_rescouting(self) -> None:
        if self.bot.time - self._last_rescout_time < 30.0:
            return
        self._last_rescout_time = self.bot.time

        zerglings = self.bot.units(UnitTypeId.ZERGLING).idle
        if not zerglings.exists or zerglings.amount < 2:
            return
        if not self.bot.enemy_start_locations:
            return

        enemy_start = self.bot.enemy_start_locations[0]
        scout_ling = zerglings.closest_to(enemy_start)
        self.bot.do(scout_ling.attack(enemy_start))

        if int(self.bot.time) % 60 < 5:
            print(f"[EARLY_SCOUT] [{int(self.bot.time)}s] Mid-game rescout sent")

    def is_cheese_detected(self) -> bool:
        return self.cheese_suspected

    def get_scout_status(self) -> str:
        status_parts: List[str] = []

        if self.ling_scouts_assigned:
            zergling_tags: Set[int] = {u.tag for u in self.bot.units(UnitTypeId.ZERGLING)}
            alive_scouts = len([tag for tag in self.scout_ling_tags if tag in zergling_tags])
            status_parts.append(f"Lings:{alive_scouts}/{self.max_scout_lings}")
        else:
            status_parts.append("Lings:idle")

        if self.overlord_scout_sent:
            status_parts.append("OL:active")
        else:
            status_parts.append("OL:idle")

        checkpoints: List[str] = []
        if self.main_base_scouted:
            checkpoints.append("main")
        if self.natural_scouted:
            checkpoints.append("natural")
        if checkpoints:
            status_parts.append(f"Check:{','.join(checkpoints)}")

        if self.cheese_suspected:
            status_parts.append("Cheese!")

        return " | ".join(status_parts) if status_parts else "Scout idle"
