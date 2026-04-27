"""
Phase 531: NVIDIA Isaac Sim / Isaac Lab
SC2 Bot drone swarm simulation mapped to Isaac robotics framework
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math
import random


try:
    import omni.isaac.lab  # type: ignore

    ISAAC_AVAILABLE = True
except ImportError:
    ISAAC_AVAILABLE = False


# ─────────────────────────────────────────────
# Vector2D primitive
# ─────────────────────────────────────────────


@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, s: float) -> "Vec2":
        return Vec2(self.x * s, self.y * s)

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    def normalized(self) -> "Vec2":
        m = self.magnitude()
        if m < 1e-9:
            return Vec2(0, 0)
        return Vec2(self.x / m, self.y / m)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y

    def distance_to(self, other: "Vec2") -> float:
        return (self - other).magnitude()


# ─────────────────────────────────────────────
# SC2 Drone (maps to Isaac Lab "agent")
# ─────────────────────────────────────────────


@dataclass
class SC2Drone:
    """Individual unit agent in the swarm."""

    agent_id: int
    position: Vec2
    velocity: Vec2 = field(default_factory=Vec2)
    health: float = 40.0
    max_health: float = 40.0
    role: str = "worker"  # worker | fighter | scout
    carrying: int = 0  # minerals carried
    target: Optional[Vec2] = None
    state: str = "idle"  # idle | moving | mining | returning | attacking

    MAX_SPEED = 2.81
    MINE_RANGE = 1.5
    ATTACK_RANGE = 0.0  # workers can't attack directly

    @property
    def alive(self) -> bool:
        return self.health > 0

    def seek(self, target: Vec2) -> Vec2:
        desired = (target - self.position).normalized() * self.MAX_SPEED
        return desired - self.velocity

    def flee(self, threat: Vec2) -> Vec2:
        away = (self.position - threat).normalized() * self.MAX_SPEED
        return away - self.velocity

    def update(self, dt: float = 0.1) -> None:
        if self.target and self.state == "moving":
            steer = self.seek(self.target)
            max_force = 0.5
            steer_m = steer.magnitude()
            if steer_m > max_force:
                steer = steer * (max_force / steer_m)
            self.velocity = self.velocity + steer
            v_m = self.velocity.magnitude()
            if v_m > self.MAX_SPEED:
                self.velocity = self.velocity * (self.MAX_SPEED / v_m)
            self.position = self.position + self.velocity * dt

            if self.position.distance_to(self.target) < 0.5:
                self.state = "idle"


# ─────────────────────────────────────────────
# Swarm controller (Isaac Lab "env" analog)
# ─────────────────────────────────────────────


@dataclass
class SwarmEnvironment:
    """Manages a swarm of SC2 drone agents."""

    width: float = 100.0
    height: float = 100.0
    drones: list[SC2Drone] = field(default_factory=list)
    minerals_patches: list[Vec2] = field(default_factory=list)
    hatchery: Vec2 = field(default_factory=lambda: Vec2(10, 10))
    frame: int = 0
    total_minerals: int = 0

    FLOCKING_RADIUS = 8.0
    SEPARATION_RADIUS = 2.0

    def spawn_drone(self, role: str = "worker") -> SC2Drone:
        drone = SC2Drone(
            agent_id=len(self.drones),
            position=Vec2(
                self.hatchery.x + random.uniform(-3, 3),
                self.hatchery.y + random.uniform(-3, 3),
            ),
            role=role,
        )
        self.drones.append(drone)
        return drone

    def _separation(self, drone: SC2Drone) -> Vec2:
        """Avoid crowding neighbors."""
        steer = Vec2()
        count = 0
        for other in self.drones:
            if other.agent_id == drone.agent_id:
                continue
            d = drone.position.distance_to(other.position)
            if 0 < d < self.SEPARATION_RADIUS:
                diff = (drone.position - other.position).normalized()
                steer = Vec2(steer.x + diff.x / d, steer.y + diff.y / d)
                count += 1
        if count > 0:
            steer = Vec2(steer.x / count, steer.y / count)
        return steer

    def _cohesion(self, drone: SC2Drone) -> Vec2:
        """Move toward average flock position."""
        center = Vec2()
        count = 0
        for other in self.drones:
            if other.agent_id == drone.agent_id:
                continue
            if drone.position.distance_to(other.position) < self.FLOCKING_RADIUS:
                center = Vec2(center.x + other.position.x, center.y + other.position.y)
                count += 1
        if count > 0:
            center = Vec2(center.x / count, center.y / count)
            return drone.seek(center) * 0.5
        return Vec2()

    def _assign_mining_targets(self) -> None:
        if not self.minerals_patches:
            return
        for drone in self.drones:
            if drone.role == "worker" and drone.state == "idle":
                # Find nearest patch
                nearest = min(
                    self.minerals_patches, key=lambda p: drone.position.distance_to(p)
                )
                drone.target = nearest
                drone.state = "moving"

    def _collect_minerals(self) -> None:
        for drone in self.drones:
            if drone.role != "worker":
                continue
            for patch in self.minerals_patches:
                if drone.position.distance_to(patch) < drone.MINE_RANGE:
                    drone.carrying += 5
                    drone.target = self.hatchery
                    drone.state = "moving"
                    break
            # Return to hatchery
            if drone.carrying >= 8 and drone.position.distance_to(self.hatchery) < 1.5:
                self.total_minerals += drone.carrying
                drone.carrying = 0
                drone.state = "idle"

    def step(self, dt: float = 0.1) -> dict:
        self._assign_mining_targets()
        self._collect_minerals()

        for drone in self.drones:
            sep = self._separation(drone) * 1.5
            drone.velocity = Vec2(
                drone.velocity.x + sep.x,
                drone.velocity.y + sep.y,
            )
            drone.update(dt)

        self.frame += 1
        return {
            "frame": self.frame,
            "drones": len(self.drones),
            "total_minerals": self.total_minerals,
            "alive": sum(1 for d in self.drones if d.alive),
        }


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 531: Isaac Sim — SC2 Drone Swarm")
    print(f"Isaac Sim available: {ISAAC_AVAILABLE}")

    env = SwarmEnvironment()
    env.minerals_patches = [
        Vec2(25, 25),
        Vec2(27, 25),
        Vec2(25, 27),
        Vec2(29, 25),
        Vec2(31, 25),
    ]

    for _ in range(12):
        env.spawn_drone(role="worker")
    env.spawn_drone(role="scout")

    for step in range(200):
        state = env.step()
        if step % 50 == 0:
            print(
                f"  Step {state['frame']:4d} | "
                f"Drones: {state['drones']} | "
                f"Minerals: {state['total_minerals']}"
            )

    print(f"\nFinal minerals collected: {env.total_minerals}")
