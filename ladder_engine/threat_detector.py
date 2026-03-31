"""
Phase 368: Threat Detector
Real-time threat detection and defensive response system for Zerg.
Detects early aggression, timing attacks, all-ins, drops, and proxy builds.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from enum import Enum


class ThreatLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ThreatType(Enum):
    EARLY_AGGRESSION = "early_aggression"
    TIMING_ATTACK = "timing_attack"
    ALL_IN = "all_in"
    DROP_HARASSMENT = "drop_harassment"
    PROXY_BUILD = "proxy_build"
    CANNON_RUSH = "cannon_rush"
    NYDUS_WORM = "nydus_worm"


@dataclass
class ThreatEvent:
    threat_type: ThreatType
    level: ThreatLevel
    game_time: float
    position: Optional[Tuple[float, float]]
    description: str
    enemy_supply: int = 0
    distance_to_base: float = 999.0

    def __repr__(self):
        return (
            f"Threat({self.threat_type.value}, {self.level.name}, "
            f"t={self.game_time:.0f}s)"
        )


@dataclass
class DefensiveResponse:
    threat_type: ThreatType
    actions: List[str] = field(default_factory=list)
    priority: float = 0.5

    def add_action(self, action: str):
        self.actions.append(action)


class ThreatDetector:
    """Monitors game state and raises threat events with defensive responses."""

    # Thresholds
    EARLY_AGGRESSION_TIME = 240.0       # < 4 min
    PROXY_MAX_DISTANCE_FROM_SPAWN = 60  # tiles
    DROP_DETECT_RADIUS = 15.0           # near our base
    ALL_IN_ARMY_RATIO = 0.85            # army/supply > 85% = all-in signal
    TIMING_ARMY_THRESHOLD = 25          # enemy army supply for timing

    def __init__(self):
        self._active_threats: Dict[ThreatType, ThreatEvent] = {}
        self._response_history: List[DefensiveResponse] = []
        self._callbacks: List[Callable[[ThreatEvent], None]] = []

    def register_callback(self, cb: Callable[[ThreatEvent], None]):
        """Register a function to be called whenever a new threat is detected."""
        self._callbacks.append(cb)

    def _fire(self, event: ThreatEvent):
        self._active_threats[event.threat_type] = event
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Detection routines
    # ------------------------------------------------------------------

    def detect_early_aggression(
        self,
        game_time: float,
        enemy_units_near_our_base: List[Dict],
        our_base_pos: Tuple[float, float],
    ) -> Optional[ThreatEvent]:
        """Detect enemy units approaching base before 4 minutes."""
        if game_time > self.EARLY_AGGRESSION_TIME:
            return None
        total_units = sum(u.get("count", 1) for u in enemy_units_near_our_base)
        if total_units < 2:
            return None

        level = ThreatLevel.HIGH if total_units >= 6 else ThreatLevel.MEDIUM
        event = ThreatEvent(
            threat_type=ThreatType.EARLY_AGGRESSION,
            level=level,
            game_time=game_time,
            position=our_base_pos,
            description=f"{total_units} enemy units approaching base at {game_time:.0f}s",
            enemy_supply=total_units,
        )
        self._fire(event)
        return event

    def detect_timing_attack(
        self,
        game_time: float,
        enemy_army_supply: int,
        our_army_supply: int,
        enemy_moving_toward_us: bool,
    ) -> Optional[ThreatEvent]:
        """Detect structured timing attack based on army size and movement."""
        if enemy_army_supply < self.TIMING_ARMY_THRESHOLD:
            return None
        if not enemy_moving_toward_us:
            return None

        ratio = our_army_supply / max(enemy_army_supply, 1)
        if ratio >= 1.2:
            level = ThreatLevel.LOW
        elif ratio >= 0.9:
            level = ThreatLevel.MEDIUM
        elif ratio >= 0.6:
            level = ThreatLevel.HIGH
        else:
            level = ThreatLevel.CRITICAL

        event = ThreatEvent(
            threat_type=ThreatType.TIMING_ATTACK,
            level=level,
            game_time=game_time,
            position=None,
            description=(
                f"Timing attack detected: enemy {enemy_army_supply} vs our {our_army_supply} supply"
            ),
            enemy_supply=enemy_army_supply,
        )
        self._fire(event)
        return event

    def detect_all_in(
        self,
        enemy_worker_count: int,
        enemy_total_supply: int,
        enemy_army_supply: int,
    ) -> Optional[ThreatEvent]:
        """Detect all-in when enemy has almost stopped droning."""
        if enemy_total_supply == 0:
            return None
        army_ratio = enemy_army_supply / max(enemy_total_supply, 1)
        if army_ratio < self.ALL_IN_ARMY_RATIO:
            return None

        event = ThreatEvent(
            threat_type=ThreatType.ALL_IN,
            level=ThreatLevel.CRITICAL,
            game_time=0.0,
            position=None,
            description=(
                f"All-in detected: {army_ratio:.0%} army ratio, "
                f"{enemy_worker_count} workers"
            ),
            enemy_supply=enemy_army_supply,
        )
        self._fire(event)
        return event

    def detect_drop_harassment(
        self,
        game_time: float,
        enemy_transport_units: List[Dict],
        our_base_pos: Tuple[float, float],
    ) -> Optional[ThreatEvent]:
        """Detect drop ships / overlord drops heading toward our base."""
        transports_near = [
            t for t in enemy_transport_units
            if _dist(t.get("position", (999, 999)), our_base_pos) < self.DROP_DETECT_RADIUS
        ]
        if not transports_near:
            return None

        event = ThreatEvent(
            threat_type=ThreatType.DROP_HARASSMENT,
            level=ThreatLevel.HIGH,
            game_time=game_time,
            position=transports_near[0].get("position"),
            description=f"{len(transports_near)} drop transport(s) detected near base",
        )
        self._fire(event)
        return event

    def detect_proxy_build(
        self,
        game_time: float,
        enemy_buildings: List[Dict],
        enemy_spawn_pos: Tuple[float, float],
    ) -> Optional[ThreatEvent]:
        """Detect proxy buildings placed far from enemy spawn."""
        proxy_buildings = [
            b for b in enemy_buildings
            if _dist(b.get("position", enemy_spawn_pos), enemy_spawn_pos)
            > self.PROXY_MAX_DISTANCE_FROM_SPAWN
        ]
        if not proxy_buildings:
            return None

        event = ThreatEvent(
            threat_type=ThreatType.PROXY_BUILD,
            level=ThreatLevel.HIGH,
            game_time=game_time,
            position=proxy_buildings[0].get("position"),
            description=f"Proxy building detected: {proxy_buildings[0].get('building_type')}",
        )
        self._fire(event)
        return event

    # ------------------------------------------------------------------
    # Defensive responses
    # ------------------------------------------------------------------

    def generate_response(self, event: ThreatEvent) -> DefensiveResponse:
        """Generate defensive actions for a given threat event."""
        response = DefensiveResponse(
            threat_type=event.threat_type,
            priority=event.level.value / 4.0,
        )

        if event.threat_type == ThreatType.EARLY_AGGRESSION:
            response.add_action("Build Spine Crawler at natural ramp")
            response.add_action("Pull queen to natural entrance")
            if event.level == ThreatLevel.HIGH:
                response.add_action("Pull workers to defend (3-5 drones)")

        elif event.threat_type == ThreatType.TIMING_ATTACK:
            response.add_action("Cancel expansion if under construction")
            if event.level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
                response.add_action("Pull all queens to front")
                response.add_action("Build 2x Spine Crawlers at natural")
                response.add_action("Produce lings/roaches for reinforce")
            else:
                response.add_action("Hold position at choke point")

        elif event.threat_type == ThreatType.ALL_IN:
            response.add_action("Build Spine Crawlers at both bases")
            response.add_action("Pull workers to defend (6-8 drones)")
            response.add_action("Produce maximum army units now")
            response.add_action("Cancel non-essential production")

        elif event.threat_type == ThreatType.DROP_HARASSMENT:
            response.add_action("Move spore crawlers to mineral line")
            response.add_action("Assign 4 queens to anti-drop patrol")
            response.add_action("Pull nearby army units to intercept")

        elif event.threat_type == ThreatType.PROXY_BUILD:
            response.add_action("Send 3 zerglings to destroy proxy")
            response.add_action("Build extra lings for early defense")

        self._response_history.append(response)
        return response

    def get_current_max_threat(self) -> ThreatLevel:
        """Return highest active threat level."""
        if not self._active_threats:
            return ThreatLevel.NONE
        return max(e.level for e in self._active_threats.values())

    def clear_threat(self, threat_type: ThreatType):
        self._active_threats.pop(threat_type, None)

    def active_threats(self) -> List[ThreatEvent]:
        return list(self._active_threats.values())


def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    import math
    return math.hypot(a[0] - b[0], a[1] - b[1])
