"""
Phase 367: Map Analyzer
Static map analysis for strategic positioning in SC2 ladder play.
Identifies choke points, high ground, expansions, and drop positions.
Analysis results are cached per named map.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Choke:
    position: Tuple[float, float]
    width: float  # in game units
    connects: Tuple[str, str]  # e.g. ("main", "natural")
    is_ramp: bool = False
    defensibility: float = 0.0  # 0.0 (bad) to 1.0 (excellent)

    def __repr__(self):
        return f"Choke(pos={self.position}, w={self.width:.1f}, ramp={self.is_ramp})"


@dataclass
class HighGround:
    position: Tuple[float, float]
    area_radius: float
    overlooks: List[Tuple[float, float]] = field(default_factory=list)
    strategic_value: float = 0.5


@dataclass
class ExpansionLocation:
    position: Tuple[float, float]
    mineral_patches: int = 8
    geysers: int = 2
    distance_from_main: float = 0.0
    is_natural: bool = False
    is_third: bool = False
    defensibility: float = 0.5
    rank: int = 0  # 1 = best, higher = worse

    def __repr__(self):
        return (
            f"Expansion(pos={self.position}, "
            f"nat={self.is_natural}, rank={self.rank})"
        )


@dataclass
class MapAnalysis:
    map_name: str
    size: Tuple[float, float]
    choke_points: List[Choke] = field(default_factory=list)
    high_grounds: List[HighGround] = field(default_factory=list)
    expansions: List[ExpansionLocation] = field(default_factory=list)
    attack_paths: List[List[Tuple[float, float]]] = field(default_factory=list)
    drop_positions: List[Tuple[float, float]] = field(default_factory=list)
    spawn_positions: List[Tuple[float, float]] = field(default_factory=list)


class MapAnalyzer:
    """Analyzes ladder maps and caches strategic data for quick lookup."""

    # Known ladder map definitions (simplified geometric approximations)
    KNOWN_MAPS: Dict[str, Dict] = {
        "BerlingradAIE": {
            "size": (200, 176),
            "spawns": [(32, 32), (168, 144)],
            "naturals_offset": (12, 0),
            "choke_width": 5.5,
        },
        "GoldenWallAIE": {
            "size": (176, 168),
            "spawns": [(28, 28), (148, 140)],
            "naturals_offset": (10, 5),
            "choke_width": 6.0,
        },
        "HardwireAIE": {
            "size": (192, 160),
            "spawns": [(24, 24), (168, 136)],
            "naturals_offset": (0, 12),
            "choke_width": 4.5,
        },
        "MoondanceAIE": {
            "size": (188, 168),
            "spawns": [(24, 28), (164, 140)],
            "naturals_offset": (14, 0),
            "choke_width": 7.0,
        },
        "SiteDeltaAIE": {
            "size": (168, 160),
            "spawns": [(24, 24), (144, 136)],
            "naturals_offset": (0, -12),
            "choke_width": 5.0,
        },
    }

    def __init__(self):
        self._cache: Dict[str, MapAnalysis] = {}

    def _midpoint(
        self, a: Tuple[float, float], b: Tuple[float, float]
    ) -> Tuple[float, float]:
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    def _dist(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(b[0] - a[0], b[1] - a[1])

    # ------------------------------------------------------------------
    # Analysis methods
    # ------------------------------------------------------------------

    def find_choke_points(
        self,
        spawn_a: Tuple[float, float],
        spawn_b: Tuple[float, float],
        choke_width: float = 5.0,
    ) -> List[Choke]:
        """Approximate choke points along the main attack path."""
        mid = self._midpoint(spawn_a, spawn_b)
        q1 = self._midpoint(spawn_a, mid)
        q2 = self._midpoint(mid, spawn_b)

        chokes = [
            Choke(
                position=q1,
                width=choke_width,
                connects=("main_a", "mid"),
                is_ramp=True,
                defensibility=max(0.3, 1.0 - choke_width / 10.0),
            ),
            Choke(
                position=mid,
                width=choke_width * 1.4,
                connects=("mid_a", "mid_b"),
                is_ramp=False,
                defensibility=max(0.2, 0.8 - choke_width / 12.0),
            ),
            Choke(
                position=q2,
                width=choke_width,
                connects=("mid", "main_b"),
                is_ramp=True,
                defensibility=max(0.3, 1.0 - choke_width / 10.0),
            ),
        ]
        return chokes

    def analyze_attack_paths(
        self,
        spawn_a: Tuple[float, float],
        spawn_b: Tuple[float, float],
    ) -> List[List[Tuple[float, float]]]:
        """Return a list of waypoint-based attack paths."""
        direct = [spawn_a, self._midpoint(spawn_a, spawn_b), spawn_b]
        # Flanking path (offset perpendicular to main route)
        dx = spawn_b[0] - spawn_a[0]
        dy = spawn_b[1] - spawn_a[1]
        length = math.hypot(dx, dy) or 1.0
        perp = (-dy / length * 20, dx / length * 20)
        flank = [
            spawn_a,
            (
                self._midpoint(spawn_a, spawn_b)[0] + perp[0],
                self._midpoint(spawn_a, spawn_b)[1] + perp[1],
            ),
            spawn_b,
        ]
        return [direct, flank]

    def rank_expansions(
        self,
        spawn: Tuple[float, float],
        map_size: Tuple[float, float],
        naturals_offset: Tuple[float, float] = (12, 0),
    ) -> List[ExpansionLocation]:
        """
        Generate and rank expansion locations around a spawn point.
        """
        natural_pos = (spawn[0] + naturals_offset[0], spawn[1] + naturals_offset[1])
        center = (map_size[0] / 2, map_size[1] / 2)

        third_offset = (naturals_offset[0] * 1.8, naturals_offset[1] * 1.8)
        third_pos = (spawn[0] + third_offset[0], spawn[1] + third_offset[1])

        fourth_pos = self._midpoint(third_pos, center)

        expansions = [
            ExpansionLocation(
                position=natural_pos,
                distance_from_main=self._dist(spawn, natural_pos),
                is_natural=True,
                defensibility=0.7,
                rank=1,
            ),
            ExpansionLocation(
                position=third_pos,
                distance_from_main=self._dist(spawn, third_pos),
                is_third=True,
                defensibility=0.5,
                rank=2,
            ),
            ExpansionLocation(
                position=fourth_pos,
                distance_from_main=self._dist(spawn, fourth_pos),
                defensibility=0.35,
                rank=3,
            ),
        ]
        return sorted(expansions, key=lambda e: e.rank)

    def find_drop_positions(
        self,
        spawn: Tuple[float, float],
        enemy_spawn: Tuple[float, float],
    ) -> List[Tuple[float, float]]:
        """
        Return positions suitable for drop harassment (behind enemy mineral lines).
        """
        # Approximate drop position as slightly behind enemy spawn
        dx = enemy_spawn[0] - spawn[0]
        dy = enemy_spawn[1] - spawn[1]
        length = math.hypot(dx, dy) or 1.0
        unit = (dx / length, dy / length)

        positions = [
            # Behind mineral line
            (enemy_spawn[0] + unit[0] * 5, enemy_spawn[1] + unit[1] * 5),
            # Flank drop
            (enemy_spawn[0] - unit[1] * 10, enemy_spawn[1] + unit[0] * 10),
            (enemy_spawn[0] + unit[1] * 10, enemy_spawn[1] - unit[0] * 10),
        ]
        return positions

    # ------------------------------------------------------------------
    # Caching entry point
    # ------------------------------------------------------------------

    def analyze_map(
        self,
        map_name: str,
        our_spawn: Tuple[float, float],
        enemy_spawn: Optional[Tuple[float, float]] = None,
    ) -> MapAnalysis:
        """
        Full map analysis with caching.
        Returns cached result if available for this map+spawn combo.
        """
        cache_key = f"{map_name}:{our_spawn}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        known = self.KNOWN_MAPS.get(map_name, {})
        map_size = known.get("size", (200, 200))
        choke_width = known.get("choke_width", 5.5)
        naturals_offset = known.get("naturals_offset", (12, 0))

        if enemy_spawn is None:
            spawns = known.get("spawns", [(32, 32), (168, 144)])
            enemy_spawn = spawns[1] if our_spawn == spawns[0] else spawns[0]

        analysis = MapAnalysis(
            map_name=map_name,
            size=map_size,
            spawn_positions=[our_spawn, enemy_spawn],
        )
        analysis.choke_points = self.find_choke_points(
            our_spawn, enemy_spawn, choke_width
        )
        analysis.attack_paths = self.analyze_attack_paths(our_spawn, enemy_spawn)
        analysis.expansions = self.rank_expansions(our_spawn, map_size, naturals_offset)
        analysis.drop_positions = self.find_drop_positions(our_spawn, enemy_spawn)

        self._cache[cache_key] = analysis
        return analysis

    def get_best_expansion(
        self, map_name: str, our_spawn: Tuple[float, float]
    ) -> Optional[ExpansionLocation]:
        analysis = self.analyze_map(map_name, our_spawn)
        return analysis.expansions[0] if analysis.expansions else None

    def get_main_choke(
        self, map_name: str, our_spawn: Tuple[float, float]
    ) -> Optional[Choke]:
        analysis = self.analyze_map(map_name, our_spawn)
        ramps = [c for c in analysis.choke_points if c.is_ramp]
        return ramps[0] if ramps else None
