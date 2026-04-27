"""
Phase 363: Army Micro Controller
Low-level army micromanagement for Zerg: surround, focus fire, retreat,
and Zerg-specific tactics like zergling runbys and baneling splash targeting.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math


@dataclass
class Unit:
    tag: int
    unit_type: str
    position: Tuple[float, float]
    health: float
    max_health: float
    shield: float = 0.0
    energy: float = 0.0
    weapon_cooldown: float = 0.0
    is_flying: bool = False
    speed: float = 2.25
    attack_range: float = 1.0
    damage: float = 5.0

    @property
    def health_pct(self) -> float:
        return self.health / max(self.max_health, 1)

    def dist_to(self, other: "Unit") -> float:
        dx = self.position[0] - other.position[0]
        dy = self.position[1] - other.position[1]
        return math.hypot(dx, dy)

    def dist_to_pos(self, pos: Tuple[float, float]) -> float:
        return math.hypot(self.position[0] - pos[0], self.position[1] - pos[1])


@dataclass
class MicroCommand:
    unit_tag: int
    command: str  # "attack", "move", "hold", "stop", "ability"
    target_tag: Optional[int] = None
    target_pos: Optional[Tuple[float, float]] = None
    ability_id: Optional[int] = None


class ArmyMicro:
    """Unit-level micromanagement controller for Zerg armies."""

    RETREAT_HEALTH_PCT = 0.25
    KITE_BUFFER = 0.5  # extra range buffer for kiting
    SURROUND_RADIUS = 2.5
    BANE_SPLASH_MIN_CLUSTER = 3

    def __init__(self):
        self._commands: List[MicroCommand] = []

    def _emit(self, cmd: MicroCommand):
        self._commands.append(cmd)

    def flush_commands(self) -> List[MicroCommand]:
        cmds = list(self._commands)
        self._commands.clear()
        return cmds

    # ------------------------------------------------------------------
    # Generic algorithms
    # ------------------------------------------------------------------

    def concave_formation(
        self, units: List[Unit], target_pos: Tuple[float, float], radius: float = 6.0
    ) -> List[MicroCommand]:
        """Arrange units in a concave arc facing the target position."""
        cmds: List[MicroCommand] = []
        n = len(units)
        if n == 0:
            return cmds
        angle_step = math.pi / max(n - 1, 1)
        base_angle = math.atan2(
            units[0].position[1] - target_pos[1], units[0].position[0] - target_pos[0]
        )
        for i, unit in enumerate(units):
            angle = base_angle - math.pi / 2 + i * angle_step
            dest = (
                target_pos[0] + radius * math.cos(angle),
                target_pos[1] + radius * math.sin(angle),
            )
            cmds.append(MicroCommand(unit.tag, "move", target_pos=dest))
        return cmds

    def focus_fire_weakest(
        self, our_units: List[Unit], enemy_units: List[Unit]
    ) -> List[MicroCommand]:
        """All units attack the enemy with the lowest effective HP."""
        if not enemy_units:
            return []
        target = min(enemy_units, key=lambda e: e.health + e.shield)
        return [MicroCommand(u.tag, "attack", target_tag=target.tag) for u in our_units]

    def kite_ranged(
        self,
        unit: Unit,
        attacker: Unit,
        retreat_dir: Optional[Tuple[float, float]] = None,
    ) -> MicroCommand:
        """Move unit away from attacker while staying at max range."""
        if retreat_dir is None:
            dx = unit.position[0] - attacker.position[0]
            dy = unit.position[1] - attacker.position[1]
            dist = math.hypot(dx, dy) or 1.0
            retreat_dir = (dx / dist, dy / dist)
        kite_dist = unit.attack_range + self.KITE_BUFFER
        dest = (
            unit.position[0] + retreat_dir[0] * kite_dist,
            unit.position[1] + retreat_dir[1] * kite_dist,
        )
        return MicroCommand(unit.tag, "move", target_pos=dest)

    def surround_enemy(self, our_units: List[Unit], enemy: Unit) -> List[MicroCommand]:
        """Surround a single enemy unit from multiple angles."""
        cmds: List[MicroCommand] = []
        n = len(our_units)
        if n == 0:
            return cmds
        for i, unit in enumerate(our_units):
            angle = (2 * math.pi * i) / n
            pos = (
                enemy.position[0] + self.SURROUND_RADIUS * math.cos(angle),
                enemy.position[1] + self.SURROUND_RADIUS * math.sin(angle),
            )
            cmds.append(MicroCommand(unit.tag, "move", target_pos=pos))
        return cmds

    def retreat_damaged(
        self, units: List[Unit], rally_point: Tuple[float, float]
    ) -> List[MicroCommand]:
        """Order damaged units to retreat to rally point."""
        return [
            MicroCommand(u.tag, "move", target_pos=rally_point)
            for u in units
            if u.health_pct < self.RETREAT_HEALTH_PCT
        ]

    # ------------------------------------------------------------------
    # Zerg-specific tactics
    # ------------------------------------------------------------------

    def zergling_runby(
        self,
        zerglings: List[Unit],
        mineral_line_pos: Tuple[float, float],
        return_pos: Tuple[float, float],
    ) -> List[MicroCommand]:
        """
        Send zerglings on a worker line runby.
        Move to mineral line, attack-move, then return via return_pos.
        """
        cmds: List[MicroCommand] = []
        for zl in zerglings:
            cmds.append(MicroCommand(zl.tag, "move", target_pos=mineral_line_pos))
        # Attack-move at mineral line (simulated as second command wave)
        for zl in zerglings:
            cmds.append(MicroCommand(zl.tag, "attack", target_pos=mineral_line_pos))
        return cmds

    def bane_splash_targeting(
        self, banelings: List[Unit], enemy_units: List[Unit]
    ) -> List[MicroCommand]:
        """
        Assign each baneling to the densest enemy cluster for maximum splash.
        Simple grid-based density heuristic.
        """
        cmds: List[MicroCommand] = []
        if not enemy_units or not banelings:
            return cmds

        # Find the enemy with the most neighbours within 2 range
        def cluster_density(enemy: Unit) -> int:
            return sum(1 for e in enemy_units if enemy.dist_to(e) <= 2.0)

        # Sort enemies by density descending
        sorted_enemies = sorted(enemy_units, key=cluster_density, reverse=True)

        for i, bane in enumerate(banelings):
            target = sorted_enemies[i % len(sorted_enemies)]
            # Use move-attack toward the densest cluster position
            cmds.append(MicroCommand(bane.tag, "attack", target_tag=target.tag))
        return cmds

    def mutalisk_harass(
        self,
        mutalisks: List[Unit],
        enemy_workers: List[Unit],
        enemy_static_defense: List[Unit],
        retreat_pos: Tuple[float, float],
    ) -> List[MicroCommand]:
        """
        Mutalisk hit-and-run harass: attack workers, dodge static defense.
        """
        cmds: List[MicroCommand] = []
        if not mutalisks:
            return cmds

        # Identify turrets/cannons threatening mutalisks
        danger_positions = [sd.position for sd in enemy_static_defense]

        for muta in mutalisks:
            # Retreat if low health
            if muta.health_pct < 0.4:
                cmds.append(MicroCommand(muta.tag, "move", target_pos=retreat_pos))
                continue

            # Avoid static defense radius
            in_danger = any(
                math.hypot(muta.position[0] - dp[0], muta.position[1] - dp[1]) < 7.0
                for dp in danger_positions
            )
            if in_danger:
                cmds.append(MicroCommand(muta.tag, "move", target_pos=retreat_pos))
                continue

            # Attack nearest worker if available
            if enemy_workers:
                closest_worker = min(enemy_workers, key=lambda w: muta.dist_to(w))
                cmds.append(
                    MicroCommand(muta.tag, "attack", target_tag=closest_worker.tag)
                )
            else:
                cmds.append(MicroCommand(muta.tag, "move", target_pos=retreat_pos))

        return cmds

    # ------------------------------------------------------------------
    # Composite decision
    # ------------------------------------------------------------------

    def execute_micro(
        self,
        our_units: List[Unit],
        enemy_units: List[Unit],
        rally_point: Tuple[float, float],
    ) -> List[MicroCommand]:
        """
        High-level micro entry point: retreat damaged, then focus fire weakest.
        """
        cmds: List[MicroCommand] = []
        healthy = [u for u in our_units if u.health_pct >= self.RETREAT_HEALTH_PCT]
        cmds.extend(self.retreat_damaged(our_units, rally_point))
        if healthy and enemy_units:
            cmds.extend(self.focus_fire_weakest(healthy, enemy_units))
        return cmds
