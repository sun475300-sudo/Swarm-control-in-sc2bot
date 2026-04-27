"""
Phase 365: Scouting System
Intel gathering and build order detection for Zerg.
Overlord positioning and drone scout management.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class EnemyBuild(Enum):
    UNKNOWN = "unknown"
    FAST_EXPAND = "fast_expand"
    ONE_BASE_ALL_IN = "one_base_all_in"
    EARLY_AGGRESSION = "early_aggression"
    TIMING_ATTACK = "timing_attack"
    MACRO = "macro"
    PROXY_BUILD = "proxy_build"
    TECH_BUILD = "tech_build"


@dataclass
class ScoutObservation:
    game_time: float
    position: Tuple[float, float]
    unit_type: str
    count: int
    notes: str = ""


@dataclass
class KnowledgeBase:
    opponent_race: str = "Unknown"
    enemy_base_position: Optional[Tuple[float, float]] = None
    scouted_at: float = 0.0
    detected_build: EnemyBuild = EnemyBuild.UNKNOWN
    enemy_unit_counts: Dict[str, int] = field(default_factory=dict)
    enemy_buildings: Dict[str, int] = field(default_factory=dict)
    enemy_tech_level: int = 0  # 0=none, 1=tier1, 2=tier2, 3=tier3
    timing_attack_predicted: bool = False
    predicted_attack_time: float = 0.0
    observations: List[ScoutObservation] = field(default_factory=list)

    def record_unit(self, unit_type: str, count: int = 1):
        self.enemy_unit_counts[unit_type] = (
            self.enemy_unit_counts.get(unit_type, 0) + count
        )

    def record_building(self, building: str):
        self.enemy_buildings[building] = self.enemy_buildings.get(building, 0) + 1


class BuildOrderDetector:
    """Detects opponent build orders from scouting observations."""

    # Terran build signatures
    TERRAN_PROXY_BUILDINGS = {"Barracks", "Factory", "CommandCenter"}
    # Protoss early aggression indicators
    PROTOSS_RUSH_UNITS = {"Zealot", "Adept", "Stalker"}
    # Zerg aggression
    ZERG_RUSH_UNITS = {"Zergling", "Baneling"}

    def detect(self, kb: KnowledgeBase) -> EnemyBuild:
        """Classify the enemy build from current knowledge base."""
        units = kb.enemy_unit_counts
        buildings = kb.enemy_buildings
        race = kb.opponent_race

        # No second base scouted early
        if (
            buildings.get("CommandCenter", 0)
            + buildings.get("Nexus", 0)
            + buildings.get("Hatchery", 0)
            <= 1
        ):
            if kb.scouted_at < 180 and kb.enemy_base_position is not None:
                # Check for proxy
                if any(b in self.TERRAN_PROXY_BUILDINGS for b in buildings):
                    return EnemyBuild.PROXY_BUILD
                # Large army supply without expansion
                total_units = sum(units.values())
                if total_units > 6:
                    return EnemyBuild.ONE_BASE_ALL_IN

        # Fast expand: second CC/Nexus/Hatch very early
        if kb.scouted_at < 150:
            if buildings.get("CommandCenter", 0) >= 2:
                return EnemyBuild.FAST_EXPAND
            if buildings.get("Nexus", 0) >= 2:
                return EnemyBuild.FAST_EXPAND
            if buildings.get("Hatchery", 0) >= 2:
                return EnemyBuild.FAST_EXPAND

        # Early aggression
        if race == "Zerg":
            lings = units.get("Zergling", 0)
            if lings >= 6 and kb.scouted_at < 180:
                return EnemyBuild.EARLY_AGGRESSION
        elif race == "Protoss":
            zealots = units.get("Zealot", 0) + units.get("Adept", 0)
            if zealots >= 4 and kb.scouted_at < 210:
                return EnemyBuild.EARLY_AGGRESSION

        # Tech build detection
        tech_buildings = {"RoboticsFacility", "Starport", "TechLab", "Spire", "Armory"}
        if any(b in buildings for b in tech_buildings):
            return EnemyBuild.TECH_BUILD

        if kb.scouted_at < 300:
            return EnemyBuild.MACRO

        return EnemyBuild.UNKNOWN


class ScoutingSystem:
    """Main scouting controller for drone scouts and overlord positioning."""

    OVERLORD_WATCH_POSITIONS_COUNT = 4
    DRONE_SCOUT_SUPPLY = 17

    def __init__(self):
        self.knowledge_base = KnowledgeBase()
        self._detector = BuildOrderDetector()
        self._overlord_assignments: Dict[int, Tuple[float, float]] = {}  # tag -> pos
        self._drone_scout_tag: Optional[int] = None
        self._scout_route: List[Tuple[float, float]] = []
        self._scout_route_index: int = 0

    # ------------------------------------------------------------------
    # Drone scouting
    # ------------------------------------------------------------------

    def send_drone_scout(
        self,
        drone_tag: int,
        possible_enemy_positions: List[Tuple[float, float]],
        our_base: Tuple[float, float],
    ) -> List[Tuple[int, Tuple[float, float]]]:
        """
        Assign a drone to scout enemy positions.
        Returns list of (unit_tag, destination) move commands.
        """
        self._drone_scout_tag = drone_tag
        # Sort positions by distance from our base (farthest first)
        sorted_positions = sorted(
            possible_enemy_positions,
            key=lambda p: math.hypot(p[0] - our_base[0], p[1] - our_base[1]),
            reverse=True,
        )
        self._scout_route = sorted_positions
        self._scout_route_index = 0
        if sorted_positions:
            return [(drone_tag, sorted_positions[0])]
        return []

    def advance_scout_route(self) -> Optional[Tuple[int, Tuple[float, float]]]:
        """Move scout to next waypoint; returns None if route complete."""
        if self._drone_scout_tag is None:
            return None
        self._scout_route_index += 1
        if self._scout_route_index >= len(self._scout_route):
            return None
        next_pos = self._scout_route[self._scout_route_index]
        return (self._drone_scout_tag, next_pos)

    # ------------------------------------------------------------------
    # Overlord positioning
    # ------------------------------------------------------------------

    def position_overlords_for_vision(
        self, overlord_tags: List[int], watch_positions: List[Tuple[float, float]]
    ) -> Dict[int, Tuple[float, float]]:
        """
        Assign overlords to watch positions (attack paths, expansions).
        Returns {overlord_tag: destination}.
        """
        assignments: Dict[int, Tuple[float, float]] = {}
        n_positions = len(watch_positions)
        for i, tag in enumerate(overlord_tags):
            if n_positions == 0:
                break
            pos = watch_positions[i % n_positions]
            assignments[tag] = pos
        self._overlord_assignments.update(assignments)
        return assignments

    def get_overlord_watch_positions(
        self,
        our_base: Tuple[float, float],
        enemy_base: Optional[Tuple[float, float]],
        map_size: Tuple[float, float] = (200.0, 200.0),
    ) -> List[Tuple[float, float]]:
        """
        Generate recommended overlord watch positions between bases.
        """
        positions = []
        cx, cy = map_size[0] / 2, map_size[1] / 2

        # Center map watch
        positions.append((cx, cy))

        # Mid-point between our base and enemy
        if enemy_base:
            mx = (our_base[0] + enemy_base[0]) / 2
            my = (our_base[1] + enemy_base[1]) / 2
            positions.append((mx, my))
            # Flanking watch point
            positions.append((mx + 15, my - 10))
            positions.append((mx - 15, my + 10))
        else:
            positions.append((our_base[0] + 20, our_base[1]))
            positions.append((our_base[0], our_base[1] + 20))
            positions.append((our_base[0] - 20, our_base[1]))

        return positions[: self.OVERLORD_WATCH_POSITIONS_COUNT]

    # ------------------------------------------------------------------
    # Knowledge base updates
    # ------------------------------------------------------------------

    def update_knowledge_base(
        self,
        game_time: float,
        observed_units: List[Dict],
        observed_buildings: List[Dict],
    ):
        """
        Process new scouting observations and update the knowledge base.
        observed_units: list of {unit_type, count, position}
        observed_buildings: list of {building_type, position}
        """
        kb = self.knowledge_base
        kb.scouted_at = game_time

        for u in observed_units:
            kb.record_unit(u.get("unit_type", "Unknown"), u.get("count", 1))
            obs = ScoutObservation(
                game_time=game_time,
                position=u.get("position", (0.0, 0.0)),
                unit_type=u.get("unit_type", "Unknown"),
                count=u.get("count", 1),
            )
            kb.observations.append(obs)

        for b in observed_buildings:
            kb.record_building(b.get("building_type", "Unknown"))
            if b.get("is_main_base"):
                kb.enemy_base_position = b.get("position")

        kb.detected_build = self._detector.detect(kb)

    def detect_opponent_build(self) -> EnemyBuild:
        """Return the current best guess for opponent build."""
        return self.knowledge_base.detected_build

    def predict_timing_attack(self, game_time: float) -> Optional[float]:
        """
        Predict when a timing attack might arrive based on enemy army supply.
        Returns estimated arrival time or None if no attack predicted.
        """
        kb = self.knowledge_base
        total_army = sum(kb.enemy_unit_counts.values())

        if kb.detected_build in (
            EnemyBuild.ONE_BASE_ALL_IN,
            EnemyBuild.EARLY_AGGRESSION,
        ):
            # Estimate attack arrives in 60-120 seconds from now
            kb.timing_attack_predicted = True
            arrival = game_time + 90.0
            kb.predicted_attack_time = arrival
            return arrival

        if total_army > 20:
            kb.timing_attack_predicted = True
            arrival = game_time + 120.0
            kb.predicted_attack_time = arrival
            return arrival

        return None
