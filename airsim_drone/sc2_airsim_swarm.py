# Phase 648: AirSim Drone Swarm Simulator for SC2 Tactics Transfer
# High-fidelity drone swarm simulation via AirSim, mapping SC2 zergling
# surround tactics to real-world drone encirclement maneuvers.
#
# Key components:
#   - AirSimDrone: individual drone state, control, and telemetry
#   - SwarmFormation: V-shape, line, circle, grid, and custom formations
#   - FlightController: PID-based flight stabilisation and waypoint tracking
#   - CollisionAvoidance: potential field + velocity obstacle methods
#   - AirSimSwarm: top-level orchestrator for multi-drone missions

from __future__ import annotations

import json
import logging
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# Vector3 helper
# ============================================================


@dataclass
class Vector3:
    """Lightweight 3-D vector for positions / velocities."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vector3":
        return self.__mul__(scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> "Vector3":
        m = self.magnitude()
        if m < 1e-9:
            return Vector3(0.0, 0.0, 0.0)
        return Vector3(self.x / m, self.y / m, self.z / m)

    def dot(self, other: "Vector3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def distance_to(self, other: "Vector3") -> float:
        return (self - other).magnitude()

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> "Vector3":
        return cls(d.get("x", 0.0), d.get("y", 0.0), d.get("z", 0.0))


# ============================================================
# Enums
# ============================================================


class DroneState(Enum):
    IDLE = auto()
    TAKING_OFF = auto()
    HOVERING = auto()
    MOVING = auto()
    LANDING = auto()
    CRASHED = auto()


class FormationType(Enum):
    V_SHAPE = "v_shape"
    LINE = "line"
    CIRCLE = "circle"
    GRID = "grid"
    CUSTOM = "custom"


class AvoidanceMethod(Enum):
    POTENTIAL_FIELD = "potential_field"
    VELOCITY_OBSTACLE = "velocity_obstacle"
    HYBRID = "hybrid"


# ============================================================
# PID Controller
# ============================================================


class PIDController:
    """Simple 1-D PID controller for flight axis stabilisation."""

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.1,
        output_min: float = -10.0,
        output_max: float = 10.0,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self._integral: float = 0.0
        self._prev_error: float = 0.0

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, error: float, dt: float) -> float:
        if dt <= 0:
            return 0.0
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt
        self._prev_error = error
        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(self.output_min, min(self.output_max, output))


# ============================================================
# AirSimDrone
# ============================================================


@dataclass
class AirSimDrone:
    """Individual drone with state, position, velocity, and telemetry."""

    drone_id: str = field(default_factory=lambda: f"drone-{uuid.uuid4().hex[:8]}")
    position: Vector3 = field(default_factory=Vector3)
    velocity: Vector3 = field(default_factory=Vector3)
    orientation_yaw: float = 0.0  # degrees
    state: DroneState = DroneState.IDLE
    battery_pct: float = 100.0
    max_speed: float = 15.0  # m/s
    home_position: Vector3 = field(default_factory=Vector3)
    waypoints: List[Vector3] = field(default_factory=list)
    current_wp_idx: int = 0
    telemetry_log: List[Dict[str, Any]] = field(default_factory=list)

    # ---- lifecycle ----

    def takeoff(self, altitude: float = 10.0) -> bool:
        if self.state not in (DroneState.IDLE, DroneState.HOVERING):
            logger.warning(
                "Drone %s cannot take off from state %s", self.drone_id, self.state
            )
            return False
        self.state = DroneState.TAKING_OFF
        self.home_position = Vector3(self.position.x, self.position.y, self.position.z)
        self.position.z = altitude
        self.state = DroneState.HOVERING
        self._log_telemetry("takeoff", {"altitude": altitude})
        return True

    def land(self) -> bool:
        if self.state == DroneState.CRASHED:
            return False
        self.state = DroneState.LANDING
        self.position.z = 0.0
        self.velocity = Vector3()
        self.state = DroneState.IDLE
        self._log_telemetry("land")
        return True

    def hover(self) -> None:
        self.velocity = Vector3()
        self.state = DroneState.HOVERING
        self._log_telemetry("hover")

    # ---- movement ----

    def move_to(self, target: Vector3, speed: Optional[float] = None) -> None:
        speed = min(speed or self.max_speed, self.max_speed)
        direction = (target - self.position).normalized()
        self.velocity = direction * speed
        self.state = DroneState.MOVING
        self.waypoints = [target]
        self.current_wp_idx = 0
        self._log_telemetry("move_to", {"target": target.to_dict(), "speed": speed})

    def step(self, dt: float) -> None:
        """Advance simulation by *dt* seconds."""
        if self.state == DroneState.MOVING:
            self.position = self.position + self.velocity * dt
            self.battery_pct = max(0.0, self.battery_pct - 0.005 * dt)
            # Check waypoint arrival
            if self.waypoints and self.current_wp_idx < len(self.waypoints):
                wp = self.waypoints[self.current_wp_idx]
                if self.position.distance_to(wp) < 0.5:
                    self.current_wp_idx += 1
                    if self.current_wp_idx >= len(self.waypoints):
                        self.hover()
        elif self.state == DroneState.HOVERING:
            self.battery_pct = max(0.0, self.battery_pct - 0.001 * dt)

        if self.battery_pct <= 0.0:
            self.state = DroneState.CRASHED
            self.velocity = Vector3()

    # ---- telemetry ----

    def _log_telemetry(
        self, event: str, extra: Optional[Dict[str, Any]] = None
    ) -> None:
        entry: Dict[str, Any] = {
            "ts": time.time(),
            "drone": self.drone_id,
            "event": event,
            "pos": self.position.to_dict(),
            "state": self.state.name,
            "battery": round(self.battery_pct, 2),
        }
        if extra:
            entry.update(extra)
        self.telemetry_log.append(entry)

    def get_status(self) -> Dict[str, Any]:
        return {
            "drone_id": self.drone_id,
            "state": self.state.name,
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
            "battery_pct": round(self.battery_pct, 2),
            "waypoints_remaining": max(0, len(self.waypoints) - self.current_wp_idx),
        }


# ============================================================
# SwarmFormation
# ============================================================


class SwarmFormation:
    """Compute target positions for a fleet of drones in various formations."""

    def __init__(self, spacing: float = 5.0):
        self.spacing = spacing
        self._custom_offsets: List[Vector3] = []

    # ---- formation generators ----

    def v_shape(
        self, center: Vector3, count: int, heading_deg: float = 0.0
    ) -> List[Vector3]:
        positions: List[Vector3] = []
        rad = math.radians(heading_deg)
        half_angle = math.radians(30)
        for i in range(count):
            side = 1 if i % 2 == 0 else -1
            rank = (i + 1) // 2
            dx = -rank * self.spacing * math.cos(half_angle)
            dy = side * rank * self.spacing * math.sin(half_angle)
            rx = dx * math.cos(rad) - dy * math.sin(rad)
            ry = dx * math.sin(rad) + dy * math.cos(rad)
            positions.append(Vector3(center.x + rx, center.y + ry, center.z))
        return positions

    def line(
        self, center: Vector3, count: int, heading_deg: float = 0.0
    ) -> List[Vector3]:
        positions: List[Vector3] = []
        rad = math.radians(heading_deg)
        start_offset = -(count - 1) / 2.0 * self.spacing
        for i in range(count):
            offset = start_offset + i * self.spacing
            dx = offset * math.sin(rad)
            dy = offset * math.cos(rad)
            positions.append(Vector3(center.x + dx, center.y + dy, center.z))
        return positions

    def circle(
        self, center: Vector3, count: int, radius: Optional[float] = None
    ) -> List[Vector3]:
        radius = radius or (self.spacing * count / (2 * math.pi))
        positions: List[Vector3] = []
        for i in range(count):
            angle = 2 * math.pi * i / count
            positions.append(
                Vector3(
                    center.x + radius * math.cos(angle),
                    center.y + radius * math.sin(angle),
                    center.z,
                )
            )
        return positions

    def grid(self, center: Vector3, count: int) -> List[Vector3]:
        cols = max(1, int(math.ceil(math.sqrt(count))))
        rows = max(1, int(math.ceil(count / cols)))
        positions: List[Vector3] = []
        for idx in range(count):
            r, c = divmod(idx, cols)
            ox = (c - (cols - 1) / 2.0) * self.spacing
            oy = (r - (rows - 1) / 2.0) * self.spacing
            positions.append(Vector3(center.x + ox, center.y + oy, center.z))
        return positions

    def set_custom(self, offsets: List[Vector3]) -> None:
        self._custom_offsets = list(offsets)

    def custom(self, center: Vector3, count: int) -> List[Vector3]:
        positions: List[Vector3] = []
        for i in range(count):
            if i < len(self._custom_offsets):
                o = self._custom_offsets[i]
            else:
                o = Vector3(random.uniform(-10, 10), random.uniform(-10, 10), 0)
            positions.append(center + o)
        return positions

    def compute(
        self,
        formation: FormationType,
        center: Vector3,
        count: int,
        heading_deg: float = 0.0,
    ) -> List[Vector3]:
        if formation == FormationType.V_SHAPE:
            return self.v_shape(center, count, heading_deg)
        elif formation == FormationType.LINE:
            return self.line(center, count, heading_deg)
        elif formation == FormationType.CIRCLE:
            return self.circle(center, count)
        elif formation == FormationType.GRID:
            return self.grid(center, count)
        elif formation == FormationType.CUSTOM:
            return self.custom(center, count)
        raise ValueError(f"Unknown formation type: {formation}")

    # ---- SC2 tactic mapping ----

    def zergling_surround(
        self, target: Vector3, count: int, radius: float = 8.0
    ) -> List[Vector3]:
        """Map zergling surround micro to drone encirclement positions."""
        return self.circle(target, count, radius=radius)

    def baneling_split_approach(
        self, target: Vector3, count: int, spread: float = 12.0
    ) -> List[Vector3]:
        """Map baneling split pattern to spread-out approach vectors."""
        positions: List[Vector3] = []
        for i in range(count):
            angle = 2 * math.pi * i / count + random.uniform(-0.2, 0.2)
            r = spread + random.uniform(-2, 2)
            positions.append(
                Vector3(
                    target.x + r * math.cos(angle),
                    target.y + r * math.sin(angle),
                    target.z,
                )
            )
        return positions


# ============================================================
# FlightController
# ============================================================


class FlightController:
    """PID-based flight controller for individual drone stabilisation."""

    def __init__(self, kp: float = 2.0, ki: float = 0.05, kd: float = 0.8):
        self._pid_x = PIDController(kp, ki, kd)
        self._pid_y = PIDController(kp, ki, kd)
        self._pid_z = PIDController(kp, ki, kd)
        self._target: Optional[Vector3] = None

    def set_target(self, target: Vector3) -> None:
        self._target = target

    def reset(self) -> None:
        self._pid_x.reset()
        self._pid_y.reset()
        self._pid_z.reset()
        self._target = None

    def compute_velocity(self, current: Vector3, dt: float) -> Vector3:
        if self._target is None:
            return Vector3()
        ex = self._target.x - current.x
        ey = self._target.y - current.y
        ez = self._target.z - current.z
        vx = self._pid_x.compute(ex, dt)
        vy = self._pid_y.compute(ey, dt)
        vz = self._pid_z.compute(ez, dt)
        return Vector3(vx, vy, vz)

    def is_arrived(self, current: Vector3, threshold: float = 0.5) -> bool:
        if self._target is None:
            return True
        return current.distance_to(self._target) < threshold

    def track_waypoints(
        self,
        drone: AirSimDrone,
        waypoints: List[Vector3],
        dt: float = 0.1,
        max_steps: int = 2000,
    ) -> List[Dict[str, Any]]:
        """Run PID tracking through a sequence of waypoints (simulation)."""
        trajectory: List[Dict[str, Any]] = []
        for wp in waypoints:
            self.set_target(wp)
            self._pid_x.reset()
            self._pid_y.reset()
            self._pid_z.reset()
            for _ in range(max_steps):
                vel = self.compute_velocity(drone.position, dt)
                # clamp speed
                speed = vel.magnitude()
                if speed > drone.max_speed:
                    vel = vel.normalized() * drone.max_speed
                drone.velocity = vel
                drone.position = drone.position + vel * dt
                trajectory.append(
                    {"pos": drone.position.to_dict(), "vel": vel.to_dict()}
                )
                if self.is_arrived(drone.position):
                    break
        drone.hover()
        return trajectory


# ============================================================
# CollisionAvoidance
# ============================================================


class CollisionAvoidance:
    """Multi-drone collision avoidance with potential field and velocity obstacle methods."""

    def __init__(
        self,
        method: AvoidanceMethod = AvoidanceMethod.POTENTIAL_FIELD,
        safety_radius: float = 2.0,
        influence_radius: float = 8.0,
    ):
        self.method = method
        self.safety_radius = safety_radius
        self.influence_radius = influence_radius
        self._repulsion_gain: float = 5.0
        self._vo_time_horizon: float = 3.0

    # ---- potential field ----

    def _potential_field_force(
        self, drone: AirSimDrone, neighbours: List[AirSimDrone]
    ) -> Vector3:
        repulsion = Vector3()
        for nb in neighbours:
            if nb.drone_id == drone.drone_id:
                continue
            dist = drone.position.distance_to(nb.position)
            if dist < self.influence_radius and dist > 1e-6:
                direction = (drone.position - nb.position).normalized()
                strength = self._repulsion_gain * (
                    1.0 / dist - 1.0 / self.influence_radius
                )
                strength = max(0.0, strength)
                repulsion = repulsion + direction * strength
        return repulsion

    # ---- velocity obstacle ----

    def _velocity_obstacle_adjust(
        self, drone: AirSimDrone, neighbours: List[AirSimDrone]
    ) -> Vector3:
        adjustment = Vector3()
        for nb in neighbours:
            if nb.drone_id == drone.drone_id:
                continue
            rel_pos = nb.position - drone.position
            dist = rel_pos.magnitude()
            if dist < 1e-6 or dist > self.influence_radius:
                continue
            rel_vel = drone.velocity - nb.velocity
            # time to closest approach
            ttc = -rel_pos.dot(rel_vel) / max(rel_vel.dot(rel_vel), 1e-9)
            ttc = max(0.0, min(ttc, self._vo_time_horizon))
            closest_dist = (rel_pos + rel_vel * ttc).magnitude()
            if closest_dist < self.safety_radius * 2:
                away = (drone.position - nb.position).normalized()
                urgency = 1.0 - (closest_dist / (self.safety_radius * 2))
                adjustment = adjustment + away * urgency * self._repulsion_gain
        return adjustment

    # ---- public API ----

    def compute_avoidance(
        self, drone: AirSimDrone, neighbours: List[AirSimDrone]
    ) -> Vector3:
        if self.method == AvoidanceMethod.POTENTIAL_FIELD:
            return self._potential_field_force(drone, neighbours)
        elif self.method == AvoidanceMethod.VELOCITY_OBSTACLE:
            return self._velocity_obstacle_adjust(drone, neighbours)
        elif self.method == AvoidanceMethod.HYBRID:
            pf = self._potential_field_force(drone, neighbours)
            vo = self._velocity_obstacle_adjust(drone, neighbours)
            return pf * 0.5 + vo * 0.5
        return Vector3()

    def check_collision(self, drone_a: AirSimDrone, drone_b: AirSimDrone) -> bool:
        return drone_a.position.distance_to(drone_b.position) < self.safety_radius

    def all_collisions(self, drones: List[AirSimDrone]) -> List[Tuple[str, str]]:
        collisions: List[Tuple[str, str]] = []
        for i in range(len(drones)):
            for j in range(i + 1, len(drones)):
                if self.check_collision(drones[i], drones[j]):
                    collisions.append((drones[i].drone_id, drones[j].drone_id))
        return collisions


# ============================================================
# AirSimSwarm  (top-level orchestrator)
# ============================================================


class AirSimSwarm:
    """Orchestrate multi-drone swarm missions with formation flying and
    collision avoidance, transferring SC2 swarm tactics to real-world drones."""

    def __init__(
        self,
        num_drones: int = 6,
        formation_spacing: float = 5.0,
        avoidance_method: AvoidanceMethod = AvoidanceMethod.HYBRID,
    ):
        self.drones: List[AirSimDrone] = [
            AirSimDrone(drone_id=f"drone-{i:03d}") for i in range(num_drones)
        ]
        self.formation = SwarmFormation(spacing=formation_spacing)
        self.collision_avoidance = CollisionAvoidance(method=avoidance_method)
        self.flight_controller = FlightController()
        self.mission_log: List[Dict[str, Any]] = []
        self._sim_time: float = 0.0

    # ---- fleet lifecycle ----

    def takeoff_all(self, altitude: float = 10.0) -> int:
        count = 0
        for d in self.drones:
            if d.takeoff(altitude):
                count += 1
        self._log("takeoff_all", {"altitude": altitude, "count": count})
        return count

    def land_all(self) -> int:
        count = 0
        for d in self.drones:
            if d.land():
                count += 1
        self._log("land_all", {"count": count})
        return count

    # ---- formation commands ----

    def set_formation(
        self, formation: FormationType, center: Vector3, heading_deg: float = 0.0
    ) -> List[Vector3]:
        targets = self.formation.compute(
            formation, center, len(self.drones), heading_deg
        )
        for drone, target in zip(self.drones, targets):
            drone.move_to(target)
        self._log(
            "set_formation",
            {
                "type": formation.value,
                "center": center.to_dict(),
                "heading": heading_deg,
            },
        )
        return targets

    def encircle_target(self, target: Vector3, radius: float = 8.0) -> List[Vector3]:
        """SC2 zergling-surround inspired encirclement maneuver."""
        targets = self.formation.zergling_surround(target, len(self.drones), radius)
        for drone, tgt in zip(self.drones, targets):
            drone.move_to(tgt)
        self._log("encircle_target", {"target": target.to_dict(), "radius": radius})
        return targets

    def split_approach(self, target: Vector3, spread: float = 12.0) -> List[Vector3]:
        """SC2 baneling-split inspired spread-out approach."""
        targets = self.formation.baneling_split_approach(
            target, len(self.drones), spread
        )
        for drone, tgt in zip(self.drones, targets):
            drone.move_to(tgt)
        self._log("split_approach", {"target": target.to_dict(), "spread": spread})
        return targets

    # ---- simulation step ----

    def step(self, dt: float = 0.1) -> Dict[str, Any]:
        """Advance entire swarm by dt seconds with collision avoidance."""
        collisions_before = self.collision_avoidance.all_collisions(self.drones)
        for drone in self.drones:
            if drone.state == DroneState.MOVING:
                avoidance_vec = self.collision_avoidance.compute_avoidance(
                    drone, self.drones
                )
                drone.velocity = drone.velocity + avoidance_vec * dt
                # clamp
                speed = drone.velocity.magnitude()
                if speed > drone.max_speed:
                    drone.velocity = drone.velocity.normalized() * drone.max_speed
            drone.step(dt)
        self._sim_time += dt
        return {
            "sim_time": round(self._sim_time, 3),
            "active": sum(
                1
                for d in self.drones
                if d.state not in (DroneState.IDLE, DroneState.CRASHED)
            ),
            "collisions": len(collisions_before),
        }

    def run_simulation(
        self, duration: float = 10.0, dt: float = 0.1
    ) -> List[Dict[str, Any]]:
        steps = int(duration / dt)
        results: List[Dict[str, Any]] = []
        for _ in range(steps):
            result = self.step(dt)
            results.append(result)
        return results

    # ---- queries ----

    def fleet_status(self) -> List[Dict[str, Any]]:
        return [d.get_status() for d in self.drones]

    def average_battery(self) -> float:
        if not self.drones:
            return 0.0
        return sum(d.battery_pct for d in self.drones) / len(self.drones)

    def swarm_centroid(self) -> Vector3:
        if not self.drones:
            return Vector3()
        sx = sum(d.position.x for d in self.drones)
        sy = sum(d.position.y for d in self.drones)
        sz = sum(d.position.z for d in self.drones)
        n = len(self.drones)
        return Vector3(sx / n, sy / n, sz / n)

    def swarm_spread(self) -> float:
        """Max distance from centroid to any drone."""
        c = self.swarm_centroid()
        return max((d.position.distance_to(c) for d in self.drones), default=0.0)

    # ---- waypoint mission ----

    def assign_waypoint_mission(
        self, waypoints_per_drone: Dict[str, List[Vector3]]
    ) -> int:
        assigned = 0
        for drone in self.drones:
            wps = waypoints_per_drone.get(drone.drone_id, [])
            if wps:
                drone.waypoints = list(wps)
                drone.current_wp_idx = 0
                drone.move_to(wps[0])
                assigned += 1
        self._log("waypoint_mission", {"assigned": assigned})
        return assigned

    # ---- serialisation ----

    def export_telemetry(self) -> Dict[str, Any]:
        return {
            "mission_log": self.mission_log,
            "drones": {d.drone_id: d.telemetry_log for d in self.drones},
            "sim_time": self._sim_time,
        }

    def save_telemetry(self, path: str) -> None:
        data = self.export_telemetry()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info("Telemetry saved to %s", path)

    # ---- internal ----

    def _log(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        entry: Dict[str, Any] = {"ts": time.time(), "event": event}
        if data:
            entry.update(data)
        self.mission_log.append(entry)


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    print("=" * 70)
    print("Phase 648: AirSim Drone Swarm Simulator - Demo")
    print("=" * 70)

    swarm = AirSimSwarm(num_drones=8, formation_spacing=6.0)

    # --- takeoff ---
    print("\n[1] Takeoff all drones")
    taken = swarm.takeoff_all(altitude=15.0)
    print(f"    {taken} drones airborne")
    print(f"    Average battery: {swarm.average_battery():.1f}%")

    # --- V-shape formation ---
    print("\n[2] V-shape formation")
    center = Vector3(50.0, 50.0, 15.0)
    targets = swarm.set_formation(FormationType.V_SHAPE, center, heading_deg=45.0)
    sim_result = swarm.run_simulation(duration=5.0, dt=0.1)
    print(f"    Simulation steps: {len(sim_result)}")
    print(f"    Final collisions: {sim_result[-1]['collisions']}")
    print(f"    Swarm spread: {swarm.swarm_spread():.2f} m")

    # --- line formation ---
    print("\n[3] Line formation")
    targets = swarm.set_formation(
        FormationType.LINE, Vector3(100, 50, 15), heading_deg=90.0
    )
    sim_result = swarm.run_simulation(duration=5.0, dt=0.1)
    print(
        f"    Centroid: x={swarm.swarm_centroid().x:.1f}, y={swarm.swarm_centroid().y:.1f}"
    )

    # --- circle formation ---
    print("\n[4] Circle formation")
    targets = swarm.set_formation(FormationType.CIRCLE, Vector3(100, 100, 15))
    sim_result = swarm.run_simulation(duration=5.0, dt=0.1)
    print(f"    Swarm spread: {swarm.swarm_spread():.2f} m")

    # --- grid formation ---
    print("\n[5] Grid formation")
    targets = swarm.set_formation(FormationType.GRID, Vector3(50, 100, 15))
    sim_result = swarm.run_simulation(duration=3.0, dt=0.1)
    print(f"    Active drones: {sim_result[-1]['active']}")

    # --- SC2 zergling surround (encirclement) ---
    print("\n[6] SC2 Zergling Surround -> Drone Encirclement")
    enemy_pos = Vector3(200, 200, 15)
    swarm.encircle_target(enemy_pos, radius=10.0)
    sim_result = swarm.run_simulation(duration=8.0, dt=0.1)
    print(f"    Encircling target at ({enemy_pos.x}, {enemy_pos.y})")
    print(f"    Final spread: {swarm.swarm_spread():.2f} m")
    print(f"    Collisions during maneuver: {sum(r['collisions'] for r in sim_result)}")

    # --- SC2 baneling split approach ---
    print("\n[7] SC2 Baneling Split -> Spread Approach")
    swarm.split_approach(Vector3(300, 300, 15), spread=15.0)
    sim_result = swarm.run_simulation(duration=5.0, dt=0.1)
    print(f"    Spread: {swarm.swarm_spread():.2f} m")

    # --- collision avoidance comparison ---
    print("\n[8] Collision Avoidance Methods Comparison")
    for method in AvoidanceMethod:
        test_swarm = AirSimSwarm(num_drones=6, avoidance_method=method)
        test_swarm.takeoff_all(altitude=10.0)
        # Force drones toward same point to stress-test avoidance
        for d in test_swarm.drones:
            d.move_to(Vector3(0, 0, 10))
        results = test_swarm.run_simulation(duration=5.0, dt=0.1)
        total_col = sum(r["collisions"] for r in results)
        print(f"    {method.value:20s} -> total collision events: {total_col}")

    # --- PID waypoint tracking ---
    print("\n[9] PID Waypoint Tracking (single drone)")
    fc = FlightController(kp=3.0, ki=0.1, kd=1.0)
    test_drone = AirSimDrone(drone_id="pid-test")
    test_drone.takeoff(altitude=10.0)
    waypoints = [
        Vector3(10, 0, 10),
        Vector3(10, 10, 10),
        Vector3(0, 10, 10),
        Vector3(0, 0, 10),
    ]
    traj = fc.track_waypoints(test_drone, waypoints, dt=0.05)
    print(f"    Trajectory points: {len(traj)}")
    print(
        f"    Final position: ({test_drone.position.x:.2f}, {test_drone.position.y:.2f}, {test_drone.position.z:.2f})"
    )

    # --- fleet status ---
    print("\n[10] Fleet Status Summary")
    statuses = swarm.fleet_status()
    for s in statuses[:3]:
        print(f"    {s['drone_id']}: state={s['state']}, battery={s['battery_pct']}%")
    print(f"    ... and {len(statuses) - 3} more drones")

    # --- landing ---
    print("\n[11] Land all drones")
    landed = swarm.land_all()
    print(f"    {landed} drones landed")
    print(f"    Mission log entries: {len(swarm.mission_log)}")

    print("\n" + "=" * 70)
    print("Phase 648 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 648: AirSim registered
