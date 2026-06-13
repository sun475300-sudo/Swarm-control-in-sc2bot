# -*- coding: utf-8 -*-
"""Scouting helpers used by roadmap and matchup-specific systems."""

from typing import Dict, Iterable, List, Optional, Set

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:

    class AbilityId:
        MORPH_OVERSEER = "MORPH_OVERSEER"
        SPAWNCHANGELING_SPAWNCHANGELING = "SPAWNCHANGELING_SPAWNCHANGELING"

    class UnitTypeId:
        OVERLORD = "OVERLORD"
        OVERSEER = "OVERSEER"
        ZERGLING = "ZERGLING"
        DARKTEMPLAR = "DARKTEMPLAR"
        BANSHEE = "BANSHEE"
        LURKERMP = "LURKERMP"
        WIDOWMINE = "WIDOWMINE"
        WIDOWMINEBURROWED = "WIDOWMINEBURROWED"
        GHOST = "GHOST"


OVERLORD_SCOUT_INTERVAL_EARLY = 15.0
OVERLORD_SCOUT_INTERVAL_MID = 30.0
ZERGLING_PATROL_INTERVAL = 45.0

CLOAK_UNITS = {
    getattr(UnitTypeId, "DARKTEMPLAR", None),
    getattr(UnitTypeId, "BANSHEE", None),
    getattr(UnitTypeId, "LURKERMP", None),
    getattr(UnitTypeId, "WIDOWMINE", None),
    getattr(UnitTypeId, "WIDOWMINEBURROWED", None),
    getattr(UnitTypeId, "GHOST", None),
}
CLOAK_UNITS.discard(None)

CLOAK_TECH_STRUCTURES = {
    "DARKSHRINE",
    "STARPORT",
    "FUSIONCORE",
    "LURKERDENMP",
    "GHOSTACADEMY",
}


class ScoutingSystem:
    """Roadmap Sprint 2 scouting primitives."""

    def __init__(self, bot):
        self.bot = bot
        self.blackboard = getattr(bot, "blackboard", None)
        self.overlord_scout_tags: Set[int] = set()
        self.zergling_patrol_tags: Set[int] = set()
        self.zergling_route_index: Dict[int, int] = {}
        self.last_zergling_patrol_time = 0.0

    @staticmethod
    def _units_amount(units) -> int:
        if units is None:
            return 0
        amount = getattr(units, "amount", None)
        if isinstance(amount, (int, float)):
            return int(amount)
        try:
            return len(units)
        except TypeError:
            pass
        try:
            return len(list(units))
        except TypeError:
            return 0

    def _has_units(self, units) -> bool:
        return self._units_amount(units) > 0

    def _first_or_random(self, units):
        if not self._has_units(units):
            return None
        for attr in ("first", "random"):
            try:
                unit = getattr(units, attr, None)
            except Exception:
                unit = None
            if unit:
                return unit
        return None

    def get_overlord_scout_interval(self, game_time: Optional[float] = None) -> float:
        if game_time is None:
            game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        if game_time < 300.0:
            return OVERLORD_SCOUT_INTERVAL_EARLY
        return OVERLORD_SCOUT_INTERVAL_MID

    def get_zergling_patrol_interval(self) -> float:
        return ZERGLING_PATROL_INTERVAL

    def get_overlord_scout_pipeline(self) -> List[tuple]:
        return [
            ("enemy_main_ramp", self._enemy_main_ramp()),
            ("enemy_natural", self._enemy_natural()),
            ("enemy_third", self._enemy_third()),
        ]

    def select_overlord_scout_target(
        self, last_scouted_at: Optional[Dict] = None, freshness: float = 45.0
    ):
        game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        for label, position in self.get_overlord_scout_pipeline():
            if position is None:
                continue
            if last_scouted_at is not None:
                last_seen = last_scouted_at.get(position, 0.0)
                if game_time - last_seen < freshness:
                    continue
            self._set("active_overlord_scout_target", label)
            return position
        return self._map_center()

    def register_overlord_scout(self, overlord, target) -> None:
        tag = getattr(overlord, "tag", None)
        if tag is not None:
            self.overlord_scout_tags.add(tag)
        self._issue(overlord.move(target))

    def get_replacement_overlord(self, target=None):
        units = getattr(self.bot, "units", None)
        if not callable(units):
            return None
        try:
            overlords = units(UnitTypeId.OVERLORD).filter(
                lambda unit: getattr(unit, "tag", None) not in self.overlord_scout_tags
            )
        except Exception:
            return None
        if not self._has_units(overlords):
            return None
        if target is not None and hasattr(overlords, "closest_to"):
            return overlords.closest_to(target)
        return self._first_or_random(overlords)

    def record_scouted_location(self, position, label: Optional[str] = None) -> None:
        if label in {"enemy_main_ramp", "enemy_natural", "enemy_third"}:
            self._set("enemy_base_scouted", True)
        if label == "enemy_natural":
            self._set("enemy_natural_scouted", True)
        if label == "enemy_third":
            self._set("enemy_third_scouted", True)
        self._set("last_scouted_position", position)

    def generate_zergling_patrol_route(self) -> List:
        route = []
        third = self._enemy_third()
        fourth = self._enemy_fourth()
        center = self._map_center()
        watchtower = self._watchtower_position()
        for point in (third, fourth, center, watchtower):
            if point is not None:
                route.append(point)
        return route

    def select_zergling_patrol_target(self):
        route = self.generate_zergling_patrol_route()
        if not route:
            return self._map_center()
        index = int(getattr(self.bot, "time", 0.0) // ZERGLING_PATROL_INTERVAL)
        return route[index % len(route)]

    def assign_zergling_patrol(self, zergling) -> bool:
        target = self.select_zergling_patrol_target()
        if not zergling or target is None:
            return False
        tag = getattr(zergling, "tag", None)
        if tag is not None:
            self.zergling_patrol_tags.add(tag)
            self.zergling_route_index[tag] = 0
        self._issue(zergling.move(target))
        return True

    def update_zergling_patrols(self) -> None:
        route = self.generate_zergling_patrol_route()
        if not route:
            return
        units = getattr(self.bot, "units", None)
        for tag in list(self.zergling_patrol_tags):
            unit = None
            try:
                unit = units.find_by_tag(tag) if hasattr(units, "find_by_tag") else None
            except Exception:
                unit = None
            if not unit:
                replacement = self._find_idle_zergling()
                if replacement:
                    self.assign_zergling_patrol(replacement)
                self.zergling_patrol_tags.discard(tag)
                self.zergling_route_index.pop(tag, None)
                continue
            index = self.zergling_route_index.get(tag, 0)
            target = route[index % len(route)]
            try:
                if unit.distance_to(target) < 3:
                    index += 1
                    self.zergling_route_index[tag] = index
                    target = route[index % len(route)]
                self._issue(unit.move(target))
            except Exception:
                continue

    def record_visible_enemy_presence(self) -> None:
        enemies = list(getattr(self.bot, "enemy_units", []) or [])
        structures = list(getattr(self.bot, "enemy_structures", []) or [])
        for structure in structures:
            if self._is_enemy_expansion(structure):
                self._set("enemy_expansion_spotted", getattr(structure, "position", None))
                self._set("enemy_expand_confirmed", True)
        if enemies:
            self._set("last_enemy_seen_time", getattr(self.bot, "time", 0.0))

    def handle_cloak_detection(self) -> bool:
        target = self._cloak_alert_position()
        if target is None:
            return False

        overseer = self._find_available_overseer(target)
        if overseer:
            self._issue(overseer.move(target))
            self._set("overseer_detection_dispatched", True)
            return True

        self._reserve_overseer_morph()
        return False

    def deploy_changeling(self, target=None) -> bool:
        overseer = self._find_available_overseer(target or self._enemy_start())
        if not overseer:
            return False
        ability = getattr(AbilityId, "SPAWNCHANGELING_SPAWNCHANGELING", None)
        if not ability:
            return False
        self._issue(overseer(ability))
        return True

    def _cloak_alert_position(self):
        cloak_units = []
        for enemy in getattr(self.bot, "enemy_units", []) or []:
            type_id = getattr(enemy, "type_id", None)
            if type_id in CLOAK_UNITS or self._type_name(enemy) in {
                "DARKTEMPLAR",
                "BANSHEE",
                "LURKERMP",
                "WIDOWMINE",
                "WIDOWMINEBURROWED",
                "GHOST",
            }:
                cloak_units.append(enemy)
        if cloak_units:
            self._set("cloak_threat_detected", True)
            return getattr(cloak_units[0], "position", None)

        for structure in getattr(self.bot, "enemy_structures", []) or []:
            if self._type_name(structure) in CLOAK_TECH_STRUCTURES:
                self._set("cloak_tech_detected", True)
                return getattr(structure, "position", None) or self._enemy_start()
        if self._get("cloak_threat_detected", False) or self._get("cloak_tech_detected", False):
            return self._get("cloak_threat_position", None) or self._enemy_start()
        return None

    def _reserve_overseer_morph(self) -> None:
        self._set("overseer_morph_requested", True)
        self._set("urgent_overseer", True)
        units = getattr(self.bot, "units", None)
        if not callable(units):
            return
        try:
            overlords = units(UnitTypeId.OVERLORD)
        except Exception:
            return
        overlord = self._first_or_random(overlords)
        ability = getattr(AbilityId, "MORPH_OVERSEER", None)
        if overlord and ability:
            try:
                self._issue(overlord(ability))
            except (AttributeError, TypeError, ValueError, KeyError, RuntimeError):
                pass

    def _find_available_overseer(self, target=None):
        units = getattr(self.bot, "units", None)
        if not callable(units):
            return None
        try:
            overseers = units(UnitTypeId.OVERSEER)
        except Exception:
            return None
        if not self._has_units(overseers):
            return None
        if target is not None and hasattr(overseers, "closest_to"):
            return overseers.closest_to(target)
        return self._first_or_random(overseers)

    def _find_idle_zergling(self):
        units = getattr(self.bot, "units", None)
        if not callable(units):
            return None
        try:
            zerglings = units(UnitTypeId.ZERGLING).filter(
                lambda unit: getattr(unit, "tag", None) not in self.zergling_patrol_tags
                and getattr(unit, "is_idle", True)
            )
        except Exception:
            return None
        return self._first_or_random(zerglings)

    def _enemy_start(self):
        starts = getattr(self.bot, "enemy_start_locations", []) or []
        return starts[0] if starts else None

    def _map_center(self):
        return getattr(getattr(self.bot, "game_info", None), "map_center", None)

    def _enemy_main_ramp(self):
        enemy_start = self._enemy_start()
        center = self._map_center()
        if enemy_start is None:
            return center
        if center is None:
            return enemy_start
        try:
            return enemy_start.towards(center, 8)
        except Exception:
            return enemy_start

    def _enemy_natural(self):
        return self._enemy_expansion_by_index(1)

    def _enemy_third(self):
        return self._enemy_expansion_by_index(2)

    def _enemy_fourth(self):
        return self._enemy_expansion_by_index(3)

    def _enemy_expansion_by_index(self, index: int):
        enemy_start = self._enemy_start()
        expansions = list(getattr(self.bot, "expansion_locations_list", []) or [])
        if not enemy_start or not expansions:
            return None
        try:
            ordered = sorted(expansions, key=lambda pos: pos.distance_to(enemy_start))
        except Exception:
            return None
        candidates = [pos for pos in ordered if pos.distance_to(enemy_start) > 5]
        if len(candidates) > index - 1:
            return candidates[index - 1]
        return candidates[-1] if candidates else None

    def _watchtower_position(self):
        watchtowers = list(getattr(self.bot, "watchtowers", []) or [])
        if watchtowers:
            return getattr(watchtowers[0], "position", watchtowers[0])
        return None

    def _is_enemy_expansion(self, structure) -> bool:
        name = self._type_name(structure)
        if name not in {
            "COMMANDCENTER",
            "ORBITALCOMMAND",
            "PLANETARYFORTRESS",
            "NEXUS",
            "HATCHERY",
            "LAIR",
            "HIVE",
        }:
            return False
        enemy_start = self._enemy_start()
        position = getattr(structure, "position", None)
        if not enemy_start or not position:
            return False
        try:
            return position.distance_to(enemy_start) > 8
        except Exception:
            return False

    @staticmethod
    def _type_name(unit) -> str:
        return getattr(getattr(unit, "type_id", None), "name", "").upper()

    def _issue(self, action) -> None:
        try:
            self.bot.do(action)
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError):
            pass

    def _set(self, key: str, value) -> None:
        if self.blackboard and hasattr(self.blackboard, "set"):
            self.blackboard.set(key, value)

    def _get(self, key: str, default=None):
        if self.blackboard and hasattr(self.blackboard, "get"):
            return self.blackboard.get(key, default)
        return default


ZVT_SCOUT_PRIORITIES: Dict[str, List[str]] = {
    "early": [
        "enemy_natural",
        "enemy_main_ramp",
        "enemy_gas_count",
    ],
    "mid": [
        "factory_count",
        "starport_existence",
        "armory_existence",
        "tech_lab_vs_reactor",
    ],
    "late": [
        "fusion_core",
        "ghost_academy",
        "planetary_fortress",
    ],
}


class ZvTScoutingSystem:
    """ZvT scouting priority and blackboard bridge."""

    TERRAN_BASES = {"COMMANDCENTER", "ORBITALCOMMAND", "PLANETARYFORTRESS"}
    TECH_LABS = {"TECHLAB", "BARRACKSTECHLAB", "FACTORYTECHLAB", "STARPORTTECHLAB"}
    REACTORS = {"REACTOR", "BARRACKSREACTOR", "FACTORYREACTOR", "STARPORTREACTOR"}

    def __init__(self, bot):
        self.bot = bot
        self.blackboard = getattr(bot, "blackboard", None)

    def get_phase(self, game_time: Optional[float] = None) -> str:
        if game_time is None:
            game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        if game_time < 180.0:
            return "early"
        if game_time < 480.0:
            return "mid"
        return "late"

    def get_priorities(self, game_time: Optional[float] = None) -> List[str]:
        return list(ZVT_SCOUT_PRIORITIES[self.get_phase(game_time)])

    def select_priority_target(self, last_scouted_at: Optional[Dict] = None):
        if not self._is_terran_matchup():
            return None

        for priority in self.get_priorities():
            if self._priority_resolved(priority):
                continue
            target = self._resolve_priority_position(priority)
            if target is None:
                continue
            if last_scouted_at is not None:
                last_time = last_scouted_at.get(target, 0.0)
                if float(getattr(self.bot, "time", 0.0) or 0.0) - last_time < 45.0:
                    continue
            self._set("zvt_active_scout_priority", priority)
            return target
        return None

    def move_scout_to_next_priority(self, scout) -> bool:
        target = self.select_priority_target()
        if not target or not scout:
            return False
        self.bot.do(scout.move(target))
        return True

    def update_blackboard_from_visible_structures(self) -> None:
        structures = list(getattr(self.bot, "enemy_structures", []) or [])
        counts: Dict[str, int] = {}
        for structure in structures:
            name = self._type_name(structure)
            if not name:
                continue
            counts[name] = counts.get(name, 0) + 1
            self.record_scouted_structure(structure)

        if counts:
            self._set("terran_structure_counts", counts)
            self._set("factory_count", counts.get("FACTORY", 0))
            self._set("enemy_gas_count", counts.get("REFINERY", 0))
            self._set("tech_lab_count", sum(counts.get(name, 0) for name in self.TECH_LABS))
            self._set("reactor_count", sum(counts.get(name, 0) for name in self.REACTORS))

    def record_scouted_structure(self, structure) -> None:
        name = self._type_name(structure)
        if not name:
            return

        if name in self.TERRAN_BASES:
            if name == "PLANETARYFORTRESS":
                self._set("planetary_fortress", True)
            if self._is_enemy_expansion(structure):
                self._set("enemy_expand_confirmed", True)
                self._set("enemy_expansion_spotted", getattr(structure, "position", None))
        elif name == "REFINERY":
            self._increment("enemy_gas_count")
        elif name == "FACTORY":
            self._increment("factory_count")
            self._set("enemy_teching", True)
        elif name == "STARPORT":
            self._set("starport_existence", True)
            self._set("AIR_THREAT_INCOMING", True)
        elif name == "ARMORY":
            self._set("armory_existence", True)
            self._set("enemy_teching", True)
        elif name == "FUSIONCORE":
            self._set("fusion_core", True)
            self._set("AIR_THREAT_INCOMING", True)
        elif name == "GHOSTACADEMY":
            self._set("ghost_academy", True)
        elif name in self.TECH_LABS:
            self._increment("tech_lab_count")
        elif name in self.REACTORS:
            self._increment("reactor_count")
        elif name == "BUNKER":
            self._set("enemy_aggression", True)

    def _priority_resolved(self, priority: str) -> bool:
        resolved_keys = {
            "enemy_natural": "enemy_expand_confirmed",
            "enemy_gas_count": "enemy_gas_count",
            "factory_count": "factory_count",
            "starport_existence": "starport_existence",
            "armory_existence": "armory_existence",
            "fusion_core": "fusion_core",
            "ghost_academy": "ghost_academy",
            "planetary_fortress": "planetary_fortress",
        }
        key = resolved_keys.get(priority)
        if not key:
            return False
        value = self._get(key, False)
        if isinstance(value, int):
            return value > 0
        return bool(value)

    def _resolve_priority_position(self, priority: str):
        enemy_start = self._enemy_start()
        map_center = self._map_center()
        if not enemy_start:
            return map_center

        if priority == "enemy_natural":
            return self._enemy_natural() or enemy_start
        if priority == "enemy_main_ramp" and map_center:
            try:
                return enemy_start.towards(map_center, 8)
            except Exception:
                return enemy_start
        if priority == "planetary_fortress":
            return self._enemy_third() or enemy_start
        return enemy_start

    def _enemy_start(self):
        starts = getattr(self.bot, "enemy_start_locations", []) or []
        return starts[0] if starts else None

    def _map_center(self):
        game_info = getattr(self.bot, "game_info", None)
        return getattr(game_info, "map_center", None)

    def _enemy_natural(self):
        enemy_start = self._enemy_start()
        expansions = list(getattr(self.bot, "expansion_locations_list", []) or [])
        if not enemy_start or not expansions:
            return None
        candidates = []
        for pos in expansions:
            try:
                if pos.distance_to(enemy_start) > 5:
                    candidates.append(pos)
            except Exception:
                continue
        if not candidates:
            return None
        return min(candidates, key=lambda pos: pos.distance_to(enemy_start))

    def _enemy_third(self):
        enemy_start = self._enemy_start()
        expansions = list(getattr(self.bot, "expansion_locations_list", []) or [])
        if not enemy_start or len(expansions) < 3:
            return None
        return sorted(expansions, key=lambda pos: pos.distance_to(enemy_start))[2]

    def _is_enemy_expansion(self, structure) -> bool:
        enemy_start = self._enemy_start()
        position = getattr(structure, "position", None)
        if not enemy_start or not position:
            return False
        try:
            return position.distance_to(enemy_start) > 8
        except Exception:
            return False

    def _is_terran_matchup(self) -> bool:
        race = getattr(self.bot, "enemy_race", None)
        return race is not None and "terran" in str(race).lower()

    @staticmethod
    def _type_name(unit) -> str:
        return getattr(getattr(unit, "type_id", None), "name", "").upper()

    def _set(self, key: str, value) -> None:
        if self.blackboard and hasattr(self.blackboard, "set"):
            self.blackboard.set(key, value)

    def _get(self, key: str, default=None):
        if self.blackboard and hasattr(self.blackboard, "get"):
            return self.blackboard.get(key, default)
        return default

    def _increment(self, key: str) -> None:
        self._set(key, int(self._get(key, 0) or 0) + 1)


ZVP_SCOUT_PRIORITIES: Dict[str, List[str]] = {
    "early": [
        "enemy_natural",
        "forge_timing",
        "gateway_count",
        "cyber_core_timing",
    ],
    "mid": [
        "twilight_council",
        "stargate_existence",
        "robotics_facility",
        "dark_shrine",
        "templar_archives",
    ],
    "late": [
        "fleet_beacon",
        "disruptor_count",
        "archon_count",
        "warp_gate_count",
    ],
}


class ZvPScoutingSystem:
    """ZvP scouting priority and blackboard bridge."""

    PROTOSS_BASES = {"NEXUS"}
    GATEWAYS = {"GATEWAY", "WARPGATE"}

    def __init__(self, bot):
        self.bot = bot
        self.blackboard = getattr(bot, "blackboard", None)

    def get_phase(self, game_time: Optional[float] = None) -> str:
        if game_time is None:
            game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        if game_time < 180.0:
            return "early"
        if game_time < 480.0:
            return "mid"
        return "late"

    def get_priorities(self, game_time: Optional[float] = None) -> List[str]:
        return list(ZVP_SCOUT_PRIORITIES[self.get_phase(game_time)])

    def select_priority_target(self, last_scouted_at: Optional[Dict] = None):
        if not self._is_protoss_matchup():
            return None

        for priority in self.get_priorities():
            if self._priority_resolved(priority):
                continue
            target = self._resolve_priority_position(priority)
            if target is None:
                continue
            if last_scouted_at is not None:
                last_time = last_scouted_at.get(target, 0.0)
                if float(getattr(self.bot, "time", 0.0) or 0.0) - last_time < 45.0:
                    continue
            self._set("zvp_active_scout_priority", priority)
            return target
        return None

    def move_scout_to_next_priority(self, scout) -> bool:
        target = self.select_priority_target()
        if not target or not scout:
            return False
        try:
            self.bot.do(scout.move(target))
            return True
        except Exception:
            return False

    def update_blackboard_from_visible_structures(self) -> None:
        structures = list(getattr(self.bot, "enemy_structures", []) or [])
        counts: Dict[str, int] = {}
        for structure in structures:
            name = self._type_name(structure)
            if not name:
                continue
            counts[name] = counts.get(name, 0) + 1
            self.record_scouted_structure(structure)

        if counts:
            gateway_count = counts.get("GATEWAY", 0) + counts.get("WARPGATE", 0)
            self._set("protoss_structure_counts", counts)
            self._set("gateway_count", gateway_count)
            self._set("warp_gate_count", counts.get("WARPGATE", 0))

        unit_counts: Dict[str, int] = {}
        for unit in getattr(self.bot, "enemy_units", []) or []:
            name = self._type_name(unit)
            if name:
                unit_counts[name] = unit_counts.get(name, 0) + 1
        if unit_counts:
            self._set("disruptor_count", unit_counts.get("DISRUPTOR", 0))
            self._set("archon_count", unit_counts.get("ARCHON", 0))

    def record_scouted_structure(self, structure) -> None:
        name = self._type_name(structure)
        if not name:
            return

        if name in self.PROTOSS_BASES:
            if self._is_enemy_expansion(structure):
                self._set("enemy_expand_confirmed", True)
                self._set("enemy_expansion_spotted", getattr(structure, "position", None))
        elif name == "FORGE":
            self._set("forge_timing", True)
            if self._near_our_base(structure):
                self._mark_cannon_rush(structure)
        elif name in self.GATEWAYS:
            self._increment("gateway_count")
            if name == "WARPGATE":
                self._increment("warp_gate_count")
        elif name == "CYBERNETICSCORE":
            self._set("cyber_core_timing", True)
            self._set("enemy_teching", True)
        elif name == "TWILIGHTCOUNCIL":
            self._set("twilight_council", True)
            self._set("enemy_teching", True)
        elif name == "STARGATE":
            self._set("stargate_existence", True)
            self._set("enemy_stargate_detected", True)
            self._set("AIR_THREAT_INCOMING", True)
        elif name == "ROBOTICSFACILITY":
            self._set("robotics_facility", True)
            self._set("enemy_robo_detected", True)
        elif name == "DARKSHRINE":
            self._set("dark_shrine", True)
            self._set("cloak_tech_detected", True)
            self._set("urgent_overseer", True)
        elif name == "TEMPLARARCHIVE":
            self._set("templar_archives", True)
        elif name == "FLEETBEACON":
            self._set("fleet_beacon", True)
            self._set("AIR_THREAT_INCOMING", True)
        elif name in {"PYLON", "PHOTONCANNON"} and self._near_our_base(structure):
            self._mark_cannon_rush(structure)

    def _mark_cannon_rush(self, structure) -> None:
        self._set("enemy_cannon_rush_detected", True)
        self._set("cannon_rush", True)
        self._set("enemy_proxy_detected", True)
        self._set("enemy_aggression", True)
        self._set("cannon_rush_position", getattr(structure, "position", None))

    def _priority_resolved(self, priority: str) -> bool:
        resolved_keys = {
            "enemy_natural": "enemy_expand_confirmed",
            "forge_timing": "forge_timing",
            "gateway_count": "gateway_count",
            "cyber_core_timing": "cyber_core_timing",
            "twilight_council": "twilight_council",
            "stargate_existence": "stargate_existence",
            "robotics_facility": "robotics_facility",
            "dark_shrine": "dark_shrine",
            "templar_archives": "templar_archives",
            "fleet_beacon": "fleet_beacon",
            "disruptor_count": "disruptor_count",
            "archon_count": "archon_count",
            "warp_gate_count": "warp_gate_count",
        }
        key = resolved_keys.get(priority)
        if not key:
            return False
        value = self._get(key, False)
        if isinstance(value, int):
            return value > 0
        return bool(value)

    def _resolve_priority_position(self, priority: str):
        enemy_start = self._enemy_start()
        map_center = self._map_center()
        if not enemy_start:
            return map_center
        if priority == "enemy_natural":
            return self._enemy_natural() or enemy_start
        if priority in {"forge_timing", "gateway_count", "cyber_core_timing"}:
            return enemy_start
        if priority in {"disruptor_count", "archon_count", "warp_gate_count"}:
            return self._enemy_third() or self._enemy_natural() or enemy_start
        return enemy_start

    def _enemy_start(self):
        starts = getattr(self.bot, "enemy_start_locations", []) or []
        return starts[0] if starts else None

    def _map_center(self):
        game_info = getattr(self.bot, "game_info", None)
        return getattr(game_info, "map_center", None)

    def _enemy_natural(self):
        enemy_start = self._enemy_start()
        expansions = list(getattr(self.bot, "expansion_locations_list", []) or [])
        if not enemy_start or not expansions:
            return None
        candidates = []
        for pos in expansions:
            try:
                if pos.distance_to(enemy_start) > 5:
                    candidates.append(pos)
            except Exception:
                continue
        if not candidates:
            return None
        return min(candidates, key=lambda pos: pos.distance_to(enemy_start))

    def _enemy_third(self):
        enemy_start = self._enemy_start()
        expansions = list(getattr(self.bot, "expansion_locations_list", []) or [])
        if not enemy_start or len(expansions) < 3:
            return None
        return sorted(expansions, key=lambda pos: pos.distance_to(enemy_start))[2]

    def _is_enemy_expansion(self, structure) -> bool:
        enemy_start = self._enemy_start()
        position = getattr(structure, "position", None)
        if not enemy_start or not position:
            return False
        try:
            return position.distance_to(enemy_start) > 8
        except Exception:
            return False

    def _near_our_base(self, structure, distance: float = 18.0) -> bool:
        position = getattr(structure, "position", None)
        if position is None:
            return False
        bases = list(getattr(self.bot, "townhalls", []) or [])
        start = getattr(self.bot, "start_location", None)
        if start is not None:
            bases.append(start)
        for base in bases:
            try:
                if position.distance_to(getattr(base, "position", base)) <= distance:
                    return True
            except Exception:
                continue
        return False

    def _is_protoss_matchup(self) -> bool:
        race = getattr(self.bot, "enemy_race", None)
        return race is not None and "protoss" in str(race).lower()

    @staticmethod
    def _type_name(unit) -> str:
        return getattr(getattr(unit, "type_id", None), "name", "").upper()

    def _set(self, key: str, value) -> None:
        if self.blackboard and hasattr(self.blackboard, "set"):
            self.blackboard.set(key, value)

    def _get(self, key: str, default=None):
        if self.blackboard and hasattr(self.blackboard, "get"):
            return self.blackboard.get(key, default)
        return default

    def _increment(self, key: str) -> None:
        self._set(key, int(self._get(key, 0) or 0) + 1)


ZVZ_SCOUT_PRIORITIES: Dict[str, List[str]] = {
    "early": [
        "spawning_pool_timing",
        "gas_timing",
        "drone_count",
        "baneling_nest",
    ],
    "mid": [
        "roach_warren",
        "lair_timing",
        "spire_existence",
        "expansion_count",
    ],
    "late": [
        "hive_timing",
        "greater_spire",
        "infestation_pit",
        "ultralisk_cavern",
    ],
}


class ZvZScoutingSystem:
    """ZvZ scouting priority and blackboard bridge."""

    def __init__(self, bot):
        self.bot = bot
        self.blackboard = getattr(bot, "blackboard", None)

    def get_phase(self, game_time: Optional[float] = None) -> str:
        if game_time is None:
            game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        if game_time < 180.0:
            return "early"
        if game_time < 480.0:
            return "mid"
        return "late"

    def get_priorities(self, game_time: Optional[float] = None) -> List[str]:
        return list(ZVZ_SCOUT_PRIORITIES[self.get_phase(game_time)])

    def select_priority_target(self, last_scouted_at: Optional[Dict] = None):
        if not self._is_zerg_matchup():
            return None
        for priority in self.get_priorities():
            if self._priority_resolved(priority):
                continue
            target = self._resolve_priority_position(priority)
            if target is None:
                continue
            if last_scouted_at is not None:
                last_time = last_scouted_at.get(target, 0.0)
                if float(getattr(self.bot, "time", 0.0) or 0.0) - last_time < 45.0:
                    continue
            self._set("zvz_active_scout_priority", priority)
            return target
        return None

    def update_blackboard_from_visible_structures(self) -> None:
        structures = list(getattr(self.bot, "enemy_structures", []) or [])
        expansion_count = 0
        for structure in structures:
            if self._type_name(structure) in {"HATCHERY", "LAIR", "HIVE"}:
                expansion_count += 1
            self.record_scouted_structure(structure)
        if expansion_count:
            self._set("expansion_count", expansion_count)

        unit_counts: Dict[str, int] = {}
        for unit in getattr(self.bot, "enemy_units", []) or []:
            name = self._type_name(unit)
            if name:
                unit_counts[name] = unit_counts.get(name, 0) + 1
        if unit_counts:
            self._set("drone_count", unit_counts.get("DRONE", 0))
            if (
                unit_counts.get("ZERGLING", 0) >= 10
                and float(getattr(self.bot, "time", 0.0) or 0.0) < 240.0
            ):
                self._set("enemy_ling_flood_detected", True)

    def record_scouted_structure(self, structure) -> None:
        name = self._type_name(structure)
        if not name:
            return

        game_time = float(getattr(self.bot, "time", 0.0) or 0.0)
        if name == "SPAWNINGPOOL":
            self._set("spawning_pool_timing", game_time)
            if game_time <= 90.0:
                self._set("enemy_12pool_detected", True)
        elif name == "EXTRACTOR":
            self._set("gas_timing", game_time)
        elif name == "BANELINGNEST":
            self._set("baneling_nest", True)
            self._set("enemy_baneling_rush", True)
        elif name == "ROACHWARREN":
            self._set("roach_warren", True)
            self._set("enemy_roach_detected", True)
        elif name == "LAIR":
            self._set("lair_timing", game_time)
        elif name == "SPIRE":
            self._set("spire_existence", True)
            self._set("AIR_THREAT_INCOMING", True)
        elif name == "HIVE":
            self._set("hive_timing", game_time)
        elif name == "GREATERSPIRE":
            self._set("greater_spire", True)
        elif name == "INFESTATIONPIT":
            self._set("infestation_pit", True)
        elif name == "ULTRALISKCAVERN":
            self._set("ultralisk_cavern", True)

    def _priority_resolved(self, priority: str) -> bool:
        value = self._get(priority, False)
        if isinstance(value, int):
            return value > 0
        return bool(value)

    def _resolve_priority_position(self, priority: str):
        enemy_start = self._enemy_start()
        if priority == "expansion_count":
            return self._enemy_natural() or enemy_start
        return enemy_start or self._map_center()

    def _enemy_start(self):
        starts = getattr(self.bot, "enemy_start_locations", []) or []
        return starts[0] if starts else None

    def _map_center(self):
        return getattr(getattr(self.bot, "game_info", None), "map_center", None)

    def _enemy_natural(self):
        enemy_start = self._enemy_start()
        expansions = list(getattr(self.bot, "expansion_locations_list", []) or [])
        if not enemy_start or not expansions:
            return None
        candidates = []
        for pos in expansions:
            try:
                if pos.distance_to(enemy_start) > 5:
                    candidates.append(pos)
            except Exception:
                continue
        if not candidates:
            return None
        return min(candidates, key=lambda pos: pos.distance_to(enemy_start))

    def _is_zerg_matchup(self) -> bool:
        race = getattr(self.bot, "enemy_race", None)
        return race is not None and "zerg" in str(race).lower()

    @staticmethod
    def _type_name(unit) -> str:
        return getattr(getattr(unit, "type_id", None), "name", "").upper()

    def _set(self, key: str, value) -> None:
        if self.blackboard and hasattr(self.blackboard, "set"):
            self.blackboard.set(key, value)

    def _get(self, key: str, default=None):
        if self.blackboard and hasattr(self.blackboard, "get"):
            return self.blackboard.get(key, default)
        return default
