"""
Phase 527: ROS2 Robotics
SC2 Bot mapped to ROS2 paradigm — spatial navigation & unit coordination
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable
import math
import time
import threading

# ─────────────────────────────────────────────
# ROS2 interface stubs (for testing without ROS2)
# ─────────────────────────────────────────────

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist, PoseStamped, Point
    from std_msgs.msg import Float32MultiArray, String
    from nav_msgs.msg import OccupancyGrid, Path

    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False

    class Point:
        def __init__(self):
            self.x = self.y = self.z = 0.0

    class Twist:
        def __init__(self):
            self.linear = Point()
            self.angular = Point()


# ─────────────────────────────────────────────
# SC2 Spatial types
# ─────────────────────────────────────────────


@dataclass
class SC2Position:
    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: "SC2Position") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def direction_to(self, other: "SC2Position") -> float:
        return math.atan2(other.y - self.y, other.x - self.x)

    def move_toward(self, target: "SC2Position", speed: float) -> "SC2Position":
        dist = self.distance_to(target)
        if dist < speed:
            return target
        angle = self.direction_to(target)
        return SC2Position(
            self.x + speed * math.cos(angle),
            self.y + speed * math.sin(angle),
        )


@dataclass
class SC2Unit:
    unit_id: int
    unit_type: str
    position: SC2Position
    health: float
    max_health: float
    speed: float = 2.8
    is_selected: bool = False

    @property
    def health_pct(self) -> float:
        return self.health / max(1, self.max_health)


# ─────────────────────────────────────────────
# Occupancy grid (ROS2 OccupancyGrid analog)
# ─────────────────────────────────────────────


@dataclass
class MapGrid:
    width: int
    height: int
    resolution: float = 1.0
    data: list[int] = field(default_factory=list)

    def __post_init__(self):
        if not self.data:
            self.data = [0] * (self.width * self.height)

    def get_cell(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.data[y * self.width + x]
        return -1

    def set_cell(self, x: int, y: int, value: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.data[y * self.width + x] = value

    def is_walkable(self, x: int, y: int) -> bool:
        return self.get_cell(x, y) == 0


# ─────────────────────────────────────────────
# A* pathfinding (ROS2 nav2 analog)
# ─────────────────────────────────────────────


def astar(
    grid: MapGrid, start: tuple[int, int], goal: tuple[int, int]
) -> list[tuple[int, int]]:
    from heapq import heappush, heappop

    def heuristic(a, b):
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    open_set: list[tuple[float, tuple[int, int]]] = []
    heappush(open_set, (0.0, start))
    came_from: dict[tuple, tuple] = {}
    g_score: dict[tuple, float] = {start: 0.0}
    f_score: dict[tuple, float] = {start: heuristic(start, goal)}

    neighbors_4 = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    neighbors_diag = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

    while open_set:
        _, current = heappop(open_set)
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return list(reversed(path))

        for dx, dy in neighbors_4 + neighbors_diag:
            nx, ny = current[0] + dx, current[1] + dy
            neighbor = (nx, ny)
            if not grid.is_walkable(nx, ny):
                continue
            move_cost = 1.414 if dx != 0 and dy != 0 else 1.0
            tent_g = g_score[current] + move_cost
            if tent_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tent_g
                f_score[neighbor] = tent_g + heuristic(neighbor, goal)
                heappush(open_set, (f_score[neighbor], neighbor))

    return []  # no path found


# ─────────────────────────────────────────────
# SC2 Bot Node (ROS2 Node equivalent)
# ─────────────────────────────────────────────


class SC2BotNode:
    """ROS2-style node for SC2 bot control."""

    def __init__(self, node_name: str = "sc2_bot"):
        self.node_name = node_name
        self.units: dict[int, SC2Unit] = {}
        self.map_grid: Optional[MapGrid] = None
        self._callbacks: dict[str, list[Callable]] = {}
        self._running = False
        self._frame = 0
        print(f"[{node_name}] Node initialized")

    # Topic-style subscription
    def subscribe(self, topic: str, callback: Callable) -> None:
        self._callbacks.setdefault(topic, []).append(callback)

    def publish(self, topic: str, msg: any) -> None:
        for cb in self._callbacks.get(topic, []):
            cb(msg)

    # Action server equivalent
    def navigate_unit(self, unit_id: int, goal: SC2Position) -> list[SC2Position]:
        unit = self.units.get(unit_id)
        if unit is None or self.map_grid is None:
            return []

        start_cell = (int(unit.position.x), int(unit.position.y))
        goal_cell = (int(goal.x), int(goal.y))
        raw_path = astar(self.map_grid, start_cell, goal_cell)
        return [SC2Position(float(x), float(y)) for x, y in raw_path]

    # Parameter server equivalent
    _params: dict[str, any] = {
        "max_workers": 22,
        "attack_threshold": 0.6,
        "expand_minerals": 300,
        "army_composition": {"zergling": 0.5, "roach": 0.3, "hydralisk": 0.2},
    }

    @classmethod
    def get_param(cls, key: str, default=None):
        return cls._params.get(key, default)

    # Timer callback (ros2 timer equivalent)
    def on_timer(self) -> None:
        self._frame += 1
        self.publish("/bot/frame", self._frame)
        if self._frame % 10 == 0:
            self._update_threat_map()

    def _update_threat_map(self) -> None:
        # Emit threat level for each unit
        for uid, unit in self.units.items():
            if unit.health_pct < 0.3:
                self.publish("/bot/retreat", uid)

    def spin_once(self) -> None:
        self.on_timer()

    def add_unit(self, unit: SC2Unit) -> None:
        self.units[unit.unit_id] = unit

    def update_unit(self, uid: int, pos: SC2Position, hp: float) -> None:
        if uid in self.units:
            self.units[uid].position = pos
            self.units[uid].health = hp


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 527: ROS2 Robotics — SC2 Bot Navigation Node")
    print(f"ROS2 available: {ROS2_AVAILABLE}")

    node = SC2BotNode("sc2_zerg_bot")
    grid = MapGrid(width=32, height=32)

    # Block some cells
    for x in range(10, 15):
        grid.set_cell(x, 16, 100)  # wall

    node.map_grid = grid
    node.add_unit(SC2Unit(1, "zergling", SC2Position(5, 5), 35, 35))
    node.add_unit(SC2Unit(2, "roach", SC2Position(7, 5), 145, 145))

    # Subscribe to retreat events
    retreated = []
    node.subscribe("/bot/retreat", lambda uid: retreated.append(uid))

    # Simulate
    for _ in range(20):
        node.spin_once()

    # Pathfind
    goal = SC2Position(25, 20)
    path = node.navigate_unit(1, goal)
    print(f"Path length: {len(path)} steps")
    if path:
        print(f"  Start: ({path[0].x:.0f}, {path[0].y:.0f})")
        print(f"  End:   ({path[-1].x:.0f}, {path[-1].y:.0f})")

    print(f"Frame: {node._frame}, Retreated units: {retreated}")
