# Phase 649: Gazebo ROS2 World Simulation for SC2 Unit Physics
# Physics-accurate robot simulation via Gazebo/ROS2, modelling SC2 units
# as ground robots with realistic sensor suites and combat physics.
#
# Key components:
#   - GazeboWorld: world building, model spawning, physics configuration
#   - ROSBridge: ROS2 topic pub/sub, service calls, action server
#   - RobotModel: SC2-inspired ground robot with sensor payloads
#   - PhysicsEngine: ODE/Bullet-style rigid body dynamics
#   - GazeboSimulator: top-level facade for running full simulations

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
# Vector / Pose helpers
# ============================================================


@dataclass
class Vec3:
    """Lightweight 3-D vector."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, s: float) -> "Vec3":
        return Vec3(self.x * s, self.y * s, self.z * s)

    def __rmul__(self, s: float) -> "Vec3":
        return self.__mul__(s)

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def normalized(self) -> "Vec3":
        m = self.magnitude()
        if m < 1e-9:
            return Vec3()
        return Vec3(self.x / m, self.y / m, self.z / m)

    def distance_to(self, o: "Vec3") -> float:
        return (self - o).magnitude()

    def dot(self, o: "Vec3") -> float:
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: "Vec3") -> "Vec3":
        return Vec3(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class Quaternion:
    """Rotation quaternion (w, x, y, z)."""
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def from_euler(cls, roll: float, pitch: float, yaw: float) -> "Quaternion":
        cr, sr = math.cos(roll / 2), math.sin(roll / 2)
        cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
        cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
        return cls(
            w=cr * cp * cy + sr * sp * sy,
            x=sr * cp * cy - cr * sp * sy,
            y=cr * sp * cy + sr * cp * sy,
            z=cr * cp * sy - sr * sp * cy,
        )

    def to_euler(self) -> Tuple[float, float, float]:
        sinr_cosp = 2.0 * (self.w * self.x + self.y * self.z)
        cosr_cosp = 1.0 - 2.0 * (self.x ** 2 + self.y ** 2)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        sinp = 2.0 * (self.w * self.y - self.z * self.x)
        sinp = max(-1.0, min(1.0, sinp))
        pitch = math.asin(sinp)
        siny_cosp = 2.0 * (self.w * self.z + self.x * self.y)
        cosy_cosp = 1.0 - 2.0 * (self.y ** 2 + self.z ** 2)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        return roll, pitch, yaw

    def to_dict(self) -> Dict[str, float]:
        return {"w": self.w, "x": self.x, "y": self.y, "z": self.z}


@dataclass
class Pose:
    """Position + orientation."""
    position: Vec3 = field(default_factory=Vec3)
    orientation: Quaternion = field(default_factory=Quaternion)

    def to_dict(self) -> Dict[str, Any]:
        return {"position": self.position.to_dict(), "orientation": self.orientation.to_dict()}


# ============================================================
# Enums
# ============================================================

class SC2UnitType(Enum):
    ZERGLING = "zergling"
    ROACH = "roach"
    STALKER = "stalker"
    MARINE = "marine"
    SIEGE_TANK = "siege_tank"
    IMMORTAL = "immortal"


class SensorType(Enum):
    LIDAR = "lidar"
    DEPTH_CAMERA = "depth_camera"
    IMU = "imu"
    CONTACT = "contact"


class PhysicsSolver(Enum):
    ODE = "ode"
    BULLET = "bullet"
    DART = "dart"


class TopicDirection(Enum):
    PUBLISH = "publish"
    SUBSCRIBE = "subscribe"


# ============================================================
# Sensor models
# ============================================================


@dataclass
class SensorReading:
    """Generic sensor reading container."""
    sensor_type: SensorType
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)


class LidarSensor:
    """Simulated 2-D LIDAR (planar scan)."""

    def __init__(self, num_rays: int = 360, max_range: float = 30.0,
                 fov_deg: float = 360.0, noise_std: float = 0.02):
        self.num_rays = num_rays
        self.max_range = max_range
        self.fov_deg = fov_deg
        self.noise_std = noise_std

    def scan(self, pose: Pose, obstacles: List[Tuple[Vec3, float]]) -> SensorReading:
        """Return range readings. Obstacles are (center, radius) spheres."""
        _, _, yaw = pose.orientation.to_euler()
        half_fov = math.radians(self.fov_deg / 2)
        ranges: List[float] = []
        for i in range(self.num_rays):
            angle = yaw - half_fov + (2 * half_fov) * i / max(self.num_rays - 1, 1)
            dx = math.cos(angle)
            dy = math.sin(angle)
            min_r = self.max_range
            for obs_center, obs_radius in obstacles:
                oc = Vec3(obs_center.x - pose.position.x, obs_center.y - pose.position.y, 0)
                proj = oc.x * dx + oc.y * dy
                if proj < 0:
                    continue
                perp2 = oc.x ** 2 + oc.y ** 2 - proj ** 2
                if perp2 < obs_radius ** 2:
                    hit = proj - math.sqrt(max(0, obs_radius ** 2 - perp2))
                    if 0 < hit < min_r:
                        min_r = hit
            min_r += random.gauss(0, self.noise_std)
            ranges.append(max(0.0, min(self.max_range, min_r)))
        return SensorReading(SensorType.LIDAR, time.time(), {"ranges": ranges})


class DepthCameraSensor:
    """Simulated depth camera returning a depth image (as a flat list)."""

    def __init__(self, width: int = 64, height: int = 48,
                 hfov_deg: float = 70.0, max_depth: float = 20.0):
        self.width = width
        self.height = height
        self.hfov_deg = hfov_deg
        self.max_depth = max_depth

    def capture(self, pose: Pose, obstacles: List[Tuple[Vec3, float]]) -> SensorReading:
        depth_map: List[float] = []
        _, _, yaw = pose.orientation.to_euler()
        half_h = math.radians(self.hfov_deg / 2)
        for row in range(self.height):
            for col in range(self.width):
                angle = yaw - half_h + (2 * half_h) * col / max(self.width - 1, 1)
                dx = math.cos(angle)
                dy = math.sin(angle)
                d = self.max_depth
                for oc, orad in obstacles:
                    rel = Vec3(oc.x - pose.position.x, oc.y - pose.position.y, 0)
                    proj = rel.x * dx + rel.y * dy
                    if proj < 0:
                        continue
                    perp2 = rel.x ** 2 + rel.y ** 2 - proj ** 2
                    if perp2 < orad ** 2:
                        hit = proj - math.sqrt(max(0, orad ** 2 - perp2))
                        d = min(d, max(0.0, hit))
                depth_map.append(round(d, 3))
        return SensorReading(SensorType.DEPTH_CAMERA, time.time(), {
            "width": self.width, "height": self.height, "depth": depth_map,
        })


class IMUSensor:
    """Simulated IMU returning linear acceleration and angular velocity."""

    def __init__(self, accel_noise: float = 0.05, gyro_noise: float = 0.01):
        self.accel_noise = accel_noise
        self.gyro_noise = gyro_noise

    def read(self, linear_accel: Vec3, angular_vel: Vec3) -> SensorReading:
        return SensorReading(SensorType.IMU, time.time(), {
            "linear_acceleration": {
                "x": linear_accel.x + random.gauss(0, self.accel_noise),
                "y": linear_accel.y + random.gauss(0, self.accel_noise),
                "z": linear_accel.z + random.gauss(0, self.accel_noise) + 9.81,
            },
            "angular_velocity": {
                "x": angular_vel.x + random.gauss(0, self.gyro_noise),
                "y": angular_vel.y + random.gauss(0, self.gyro_noise),
                "z": angular_vel.z + random.gauss(0, self.gyro_noise),
            },
        })


class ContactSensor:
    """Simulated contact / bumper sensor."""

    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold

    def check(self, pose: Pose, obstacles: List[Tuple[Vec3, float]],
              robot_radius: float = 0.5) -> SensorReading:
        contacts: List[Dict[str, Any]] = []
        for oc, orad in obstacles:
            dist = pose.position.distance_to(oc)
            if dist < (robot_radius + orad + self.threshold):
                contacts.append({
                    "obstacle": oc.to_dict(),
                    "depth": round(robot_radius + orad - dist, 4),
                })
        return SensorReading(SensorType.CONTACT, time.time(), {"contacts": contacts})


# ============================================================
# RobotModel
# ============================================================

# SC2 unit -> robot mapping reference
SC2_ROBOT_SPECS: Dict[str, Dict[str, Any]] = {
    SC2UnitType.ZERGLING.value: {
        "mass": 5.0, "radius": 0.3, "max_speed": 4.7,
        "hp": 35, "armor": 0, "attack_range": 0.5, "dps": 10,
    },
    SC2UnitType.ROACH.value: {
        "mass": 20.0, "radius": 0.6, "max_speed": 2.25,
        "hp": 145, "armor": 1, "attack_range": 4.0, "dps": 8,
    },
    SC2UnitType.STALKER.value: {
        "mass": 15.0, "radius": 0.5, "max_speed": 3.15,
        "hp": 160, "armor": 1, "attack_range": 6.0, "dps": 10,
    },
    SC2UnitType.MARINE.value: {
        "mass": 10.0, "radius": 0.4, "max_speed": 2.81,
        "hp": 45, "armor": 0, "attack_range": 5.0, "dps": 9.8,
    },
    SC2UnitType.SIEGE_TANK.value: {
        "mass": 80.0, "radius": 1.2, "max_speed": 2.25,
        "hp": 175, "armor": 1, "attack_range": 7.0, "dps": 20,
    },
    SC2UnitType.IMMORTAL.value: {
        "mass": 50.0, "radius": 0.9, "max_speed": 2.81,
        "hp": 300, "armor": 1, "attack_range": 6.0, "dps": 19,
    },
}


@dataclass
class RobotModel:
    """Ground robot modelled after an SC2 unit."""

    robot_id: str = field(default_factory=lambda: f"robot-{uuid.uuid4().hex[:8]}")
    unit_type: str = SC2UnitType.MARINE.value
    pose: Pose = field(default_factory=Pose)
    velocity: Vec3 = field(default_factory=Vec3)
    angular_velocity: Vec3 = field(default_factory=Vec3)
    mass: float = 10.0
    radius: float = 0.4
    max_speed: float = 2.81
    hp: float = 45.0
    armor: int = 0
    attack_range: float = 5.0
    dps: float = 9.8
    alive: bool = True
    sensors: Dict[SensorType, Any] = field(default_factory=dict)

    @classmethod
    def from_sc2_unit(cls, unit_type: SC2UnitType, position: Optional[Vec3] = None) -> "RobotModel":
        spec = SC2_ROBOT_SPECS.get(unit_type.value, SC2_ROBOT_SPECS[SC2UnitType.MARINE.value])
        pose = Pose(position=position or Vec3())
        robot = cls(
            unit_type=unit_type.value,
            pose=pose,
            mass=spec["mass"],
            radius=spec["radius"],
            max_speed=spec["max_speed"],
            hp=spec["hp"],
            armor=spec["armor"],
            attack_range=spec["attack_range"],
            dps=spec["dps"],
        )
        robot.sensors[SensorType.LIDAR] = LidarSensor()
        robot.sensors[SensorType.IMU] = IMUSensor()
        robot.sensors[SensorType.CONTACT] = ContactSensor()
        return robot

    def apply_force(self, force: Vec3, dt: float) -> None:
        accel = force * (1.0 / max(self.mass, 0.1))
        self.velocity = self.velocity + accel * dt
        speed = self.velocity.magnitude()
        if speed > self.max_speed:
            self.velocity = self.velocity.normalized() * self.max_speed

    def step(self, dt: float) -> None:
        if not self.alive:
            return
        self.pose.position = self.pose.position + self.velocity * dt

    def take_damage(self, raw_damage: float) -> float:
        effective = max(0.5, raw_damage - self.armor)
        self.hp -= effective
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return effective

    def can_attack(self, target: "RobotModel") -> bool:
        if not self.alive or not target.alive:
            return False
        return self.pose.position.distance_to(target.pose.position) <= self.attack_range

    def attack(self, target: "RobotModel", dt: float) -> float:
        if not self.can_attack(target):
            return 0.0
        damage = self.dps * dt
        return target.take_damage(damage)

    def get_status(self) -> Dict[str, Any]:
        return {
            "robot_id": self.robot_id,
            "unit_type": self.unit_type,
            "alive": self.alive,
            "hp": round(self.hp, 1),
            "position": self.pose.position.to_dict(),
            "speed": round(self.velocity.magnitude(), 2),
        }


# ============================================================
# ROSBridge  (simulated ROS2 interface)
# ============================================================


class ROSBridge:
    """Simulated ROS2 communication layer: topics, services, actions."""

    def __init__(self, node_name: str = "sc2_gazebo_node"):
        self.node_name = node_name
        self._topics: Dict[str, Dict[str, Any]] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._services: Dict[str, Callable] = {}
        self._action_servers: Dict[str, Callable] = {}
        self._message_log: List[Dict[str, Any]] = []

    # ---- topics ----

    def create_publisher(self, topic: str, msg_type: str = "std_msgs/String") -> str:
        self._topics[topic] = {"direction": TopicDirection.PUBLISH.value, "msg_type": msg_type}
        logger.info("Publisher created: %s [%s]", topic, msg_type)
        return topic

    def create_subscription(self, topic: str, callback: Callable,
                            msg_type: str = "std_msgs/String") -> str:
        self._topics[topic] = {"direction": TopicDirection.SUBSCRIBE.value, "msg_type": msg_type}
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        return topic

    def publish(self, topic: str, message: Any) -> bool:
        if topic not in self._topics:
            logger.warning("Topic %s not registered", topic)
            return False
        self._message_log.append({
            "ts": time.time(), "topic": topic, "msg": str(message)[:200],
        })
        for cb in self._subscribers.get(topic, []):
            try:
                cb(message)
            except Exception as exc:
                logger.error("Subscriber callback error on %s: %s", topic, exc)
        return True

    # ---- services ----

    def register_service(self, service_name: str, handler: Callable) -> None:
        self._services[service_name] = handler
        logger.info("Service registered: %s", service_name)

    def call_service(self, service_name: str, request: Any = None) -> Any:
        handler = self._services.get(service_name)
        if handler is None:
            raise RuntimeError(f"Service '{service_name}' not found")
        return handler(request)

    # ---- action server ----

    def register_action_server(self, action_name: str, handler: Callable) -> None:
        self._action_servers[action_name] = handler
        logger.info("Action server registered: %s", action_name)

    def send_goal(self, action_name: str, goal: Any) -> Dict[str, Any]:
        handler = self._action_servers.get(action_name)
        if handler is None:
            return {"status": "rejected", "reason": f"Action '{action_name}' not found"}
        try:
            result = handler(goal)
            return {"status": "succeeded", "result": result}
        except Exception as exc:
            return {"status": "aborted", "reason": str(exc)}

    # ---- inspection ----

    def list_topics(self) -> List[Dict[str, str]]:
        return [{"name": k, **v} for k, v in self._topics.items()]

    def list_services(self) -> List[str]:
        return list(self._services.keys())

    def message_count(self) -> int:
        return len(self._message_log)


# ============================================================
# PhysicsEngine
# ============================================================


class PhysicsEngine:
    """Simple rigid-body physics engine for ground robot simulation."""

    def __init__(self, solver: PhysicsSolver = PhysicsSolver.ODE,
                 gravity: float = -9.81, time_step: float = 0.01,
                 friction: float = 0.5):
        self.solver = solver
        self.gravity = gravity
        self.time_step = time_step
        self.friction = friction
        self._bodies: List[RobotModel] = []
        self._obstacles: List[Tuple[Vec3, float]] = []
        self._sim_time: float = 0.0

    def add_body(self, robot: RobotModel) -> None:
        self._bodies.append(robot)

    def add_obstacle(self, center: Vec3, radius: float) -> None:
        self._obstacles.append((center, radius))

    def clear(self) -> None:
        self._bodies.clear()
        self._obstacles.clear()
        self._sim_time = 0.0

    def _apply_friction(self, robot: RobotModel) -> None:
        speed = robot.velocity.magnitude()
        if speed > 1e-6:
            friction_force = robot.velocity.normalized() * (-self.friction * robot.mass * abs(self.gravity))
            friction_decel = friction_force * (1.0 / robot.mass) * self.time_step
            if friction_decel.magnitude() > speed:
                robot.velocity = Vec3()
            else:
                robot.velocity = robot.velocity + friction_decel

    def _resolve_collisions(self) -> List[Tuple[str, str]]:
        collisions: List[Tuple[str, str]] = []
        # robot-robot
        for i in range(len(self._bodies)):
            for j in range(i + 1, len(self._bodies)):
                a, b = self._bodies[i], self._bodies[j]
                if not a.alive or not b.alive:
                    continue
                dist = a.pose.position.distance_to(b.pose.position)
                min_dist = a.radius + b.radius
                if dist < min_dist and dist > 1e-9:
                    overlap = min_dist - dist
                    normal = (a.pose.position - b.pose.position).normalized()
                    total_mass = a.mass + b.mass
                    a.pose.position = a.pose.position + normal * (overlap * b.mass / total_mass)
                    b.pose.position = b.pose.position - normal * (overlap * a.mass / total_mass)
                    # elastic bounce
                    rel_v = a.velocity - b.velocity
                    vn = rel_v.dot(normal)
                    if vn < 0:
                        impulse = normal * (-(1.5) * vn / (1.0 / a.mass + 1.0 / b.mass))
                        a.velocity = a.velocity + impulse * (1.0 / a.mass)
                        b.velocity = b.velocity - impulse * (1.0 / b.mass)
                    collisions.append((a.robot_id, b.robot_id))
        # robot-obstacle
        for robot in self._bodies:
            if not robot.alive:
                continue
            for obs_c, obs_r in self._obstacles:
                dist = robot.pose.position.distance_to(obs_c)
                min_dist = robot.radius + obs_r
                if dist < min_dist and dist > 1e-9:
                    normal = (robot.pose.position - obs_c).normalized()
                    robot.pose.position = obs_c + normal * min_dist
                    vn = robot.velocity.dot(normal)
                    if vn < 0:
                        robot.velocity = robot.velocity - normal * (2 * vn)
        return collisions

    def step(self) -> Dict[str, Any]:
        for robot in self._bodies:
            if not robot.alive:
                continue
            self._apply_friction(robot)
            robot.step(self.time_step)
        collisions = self._resolve_collisions()
        self._sim_time += self.time_step
        return {
            "sim_time": round(self._sim_time, 4),
            "collisions": collisions,
            "alive": sum(1 for r in self._bodies if r.alive),
        }

    def run(self, duration: float) -> List[Dict[str, Any]]:
        steps = int(duration / self.time_step)
        results: List[Dict[str, Any]] = []
        for _ in range(steps):
            results.append(self.step())
        return results

    def get_obstacles(self) -> List[Tuple[Vec3, float]]:
        return list(self._obstacles)


# ============================================================
# GazeboWorld
# ============================================================


class GazeboWorld:
    """World builder: spawn models, set physics, add obstacles and terrain."""

    def __init__(self, world_name: str = "sc2_battlefield"):
        self.world_name = world_name
        self.models: Dict[str, RobotModel] = {}
        self.obstacles: List[Dict[str, Any]] = []
        self.physics = PhysicsEngine()
        self.ground_plane_size: float = 200.0
        self._spawn_log: List[Dict[str, Any]] = []

    def set_physics(self, solver: PhysicsSolver = PhysicsSolver.ODE,
                    gravity: float = -9.81, time_step: float = 0.01,
                    friction: float = 0.5) -> None:
        self.physics = PhysicsEngine(solver, gravity, time_step, friction)
        logger.info("Physics: solver=%s, gravity=%.2f, dt=%.4f", solver.value, gravity, time_step)

    def spawn_robot(self, unit_type: SC2UnitType,
                    position: Optional[Vec3] = None,
                    robot_id: Optional[str] = None) -> RobotModel:
        robot = RobotModel.from_sc2_unit(unit_type, position)
        if robot_id:
            robot.robot_id = robot_id
        self.models[robot.robot_id] = robot
        self.physics.add_body(robot)
        self._spawn_log.append({
            "ts": time.time(), "id": robot.robot_id, "type": unit_type.value,
            "pos": (position or Vec3()).to_dict(),
        })
        return robot

    def spawn_squad(self, unit_type: SC2UnitType, count: int,
                    center: Vec3, spread: float = 3.0) -> List[RobotModel]:
        robots: List[RobotModel] = []
        for i in range(count):
            angle = 2 * math.pi * i / max(count, 1)
            pos = Vec3(
                center.x + spread * math.cos(angle),
                center.y + spread * math.sin(angle),
                center.z,
            )
            robots.append(self.spawn_robot(unit_type, pos))
        return robots

    def add_obstacle(self, center: Vec3, radius: float, label: str = "rock") -> None:
        self.obstacles.append({"center": center.to_dict(), "radius": radius, "label": label})
        self.physics.add_obstacle(center, radius)

    def add_wall(self, start: Vec3, end: Vec3, thickness: float = 0.5,
                 segment_count: int = 10) -> int:
        """Approximate a wall as a series of sphere obstacles."""
        added = 0
        for i in range(segment_count):
            t = i / max(segment_count - 1, 1)
            cx = start.x + (end.x - start.x) * t
            cy = start.y + (end.y - start.y) * t
            cz = start.z + (end.z - start.z) * t
            self.add_obstacle(Vec3(cx, cy, cz), thickness, label="wall_segment")
            added += 1
        return added

    def add_random_obstacles(self, count: int, bounds: float = 80.0,
                             min_r: float = 0.5, max_r: float = 3.0) -> int:
        for _ in range(count):
            c = Vec3(random.uniform(-bounds, bounds), random.uniform(-bounds, bounds), 0)
            r = random.uniform(min_r, max_r)
            self.add_obstacle(c, r, "random")
        return count

    def get_model(self, robot_id: str) -> Optional[RobotModel]:
        return self.models.get(robot_id)

    def remove_model(self, robot_id: str) -> bool:
        if robot_id in self.models:
            del self.models[robot_id]
            return True
        return False

    def world_summary(self) -> Dict[str, Any]:
        return {
            "world_name": self.world_name,
            "models": len(self.models),
            "obstacles": len(self.obstacles),
            "alive_robots": sum(1 for r in self.models.values() if r.alive),
            "physics_solver": self.physics.solver.value,
        }


# ============================================================
# GazeboSimulator  (top-level facade)
# ============================================================


class GazeboSimulator:
    """Top-level facade: world + ROS bridge + combat simulation."""

    def __init__(self, world_name: str = "sc2_battlefield"):
        self.world = GazeboWorld(world_name)
        self.ros = ROSBridge(node_name=f"{world_name}_node")
        self._setup_ros_infrastructure()
        self._combat_log: List[Dict[str, Any]] = []

    # ---- ROS setup ----

    def _setup_ros_infrastructure(self) -> None:
        self.ros.create_publisher("/cmd_vel", "geometry_msgs/Twist")
        self.ros.create_publisher("/robot_status", "std_msgs/String")
        self.ros.create_publisher("/combat_events", "std_msgs/String")
        self.ros.register_service("/spawn_robot", self._srv_spawn)
        self.ros.register_service("/world_info", self._srv_world_info)
        self.ros.register_action_server("/navigate_to", self._action_navigate)

    def _srv_spawn(self, request: Any) -> Dict[str, Any]:
        if isinstance(request, dict):
            ut = SC2UnitType(request.get("unit_type", "marine"))
            pos = Vec3(**request.get("position", {}))
            robot = self.world.spawn_robot(ut, pos)
            return {"robot_id": robot.robot_id, "status": "spawned"}
        return {"status": "invalid_request"}

    def _srv_world_info(self, _request: Any) -> Dict[str, Any]:
        return self.world.world_summary()

    def _action_navigate(self, goal: Any) -> Dict[str, Any]:
        if isinstance(goal, dict):
            rid = goal.get("robot_id", "")
            target = Vec3(**goal.get("target", {}))
            robot = self.world.get_model(rid)
            if robot is None:
                raise RuntimeError(f"Robot {rid} not found")
            direction = (target - robot.pose.position).normalized()
            robot.velocity = direction * robot.max_speed
            return {"robot_id": rid, "target": target.to_dict(), "eta_s": "simulated"}
        raise RuntimeError("Invalid goal format")

    # ---- simulation ----

    def run_physics(self, duration: float = 5.0) -> List[Dict[str, Any]]:
        return self.world.physics.run(duration)

    def run_combat(self, duration: float = 10.0, dt: float = 0.05) -> Dict[str, Any]:
        """Simulate combat between all robots for *duration* seconds."""
        steps = int(duration / dt)
        robots = list(self.world.models.values())
        total_damage: Dict[str, float] = {r.robot_id: 0.0 for r in robots}
        kills: List[Dict[str, str]] = []

        for _ in range(steps):
            for attacker in robots:
                if not attacker.alive:
                    continue
                for target in robots:
                    if target.robot_id == attacker.robot_id:
                        continue
                    if attacker.can_attack(target):
                        dmg = attacker.attack(target, dt)
                        total_damage[attacker.robot_id] = total_damage.get(attacker.robot_id, 0) + dmg
                        if not target.alive:
                            kills.append({"killer": attacker.robot_id, "victim": target.robot_id})
            # physics step
            for r in robots:
                r.step(dt)

        result = {
            "duration": duration,
            "total_damage": {k: round(v, 1) for k, v in total_damage.items()},
            "kills": kills,
            "survivors": [r.robot_id for r in robots if r.alive],
        }
        self._combat_log.append(result)
        self.ros.publish("/combat_events", json.dumps(result, default=str))
        return result

    # ---- sensor sweep ----

    def sensor_sweep(self, robot_id: str) -> Dict[str, SensorReading]:
        robot = self.world.get_model(robot_id)
        if robot is None:
            return {}
        obs = self.world.physics.get_obstacles()
        readings: Dict[str, SensorReading] = {}
        lidar = robot.sensors.get(SensorType.LIDAR)
        if lidar:
            readings["lidar"] = lidar.scan(robot.pose, obs)
        imu = robot.sensors.get(SensorType.IMU)
        if imu:
            readings["imu"] = imu.read(Vec3(0, 0, 0), robot.angular_velocity)
        contact = robot.sensors.get(SensorType.CONTACT)
        if contact:
            readings["contact"] = contact.check(robot.pose, obs, robot.radius)
        return readings

    # ---- convenience ----

    def spawn(self, unit_type: SC2UnitType, position: Optional[Vec3] = None) -> RobotModel:
        return self.world.spawn_robot(unit_type, position)

    def fleet_status(self) -> List[Dict[str, Any]]:
        return [r.get_status() for r in self.world.models.values()]

    def export_state(self) -> Dict[str, Any]:
        return {
            "world": self.world.world_summary(),
            "robots": self.fleet_status(),
            "ros_topics": self.ros.list_topics(),
            "ros_services": self.ros.list_services(),
            "combat_log": self._combat_log,
        }

    def save_state(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.export_state(), f, indent=2, default=str)
        logger.info("State saved to %s", path)


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    print("=" * 70)
    print("Phase 649: Gazebo ROS2 World Simulation - Demo")
    print("=" * 70)

    sim = GazeboSimulator(world_name="sc2_arena")

    # --- configure physics ---
    print("\n[1] Configure Physics Engine")
    sim.world.set_physics(solver=PhysicsSolver.ODE, gravity=-9.81, time_step=0.01, friction=0.4)
    print(f"    Solver: {sim.world.physics.solver.value}")

    # --- spawn SC2 units as robots ---
    print("\n[2] Spawn SC2 Unit Robots")
    zerglings = sim.world.spawn_squad(SC2UnitType.ZERGLING, count=6, center=Vec3(-20, 0, 0), spread=3.0)
    marines = sim.world.spawn_squad(SC2UnitType.MARINE, count=4, center=Vec3(20, 0, 0), spread=2.5)
    tank = sim.spawn(SC2UnitType.SIEGE_TANK, Vec3(25, 5, 0))
    stalker = sim.spawn(SC2UnitType.STALKER, Vec3(0, 20, 0))
    print(f"    Spawned {len(zerglings)} zerglings, {len(marines)} marines, 1 tank, 1 stalker")
    print(f"    Total models: {sim.world.world_summary()['models']}")

    # --- add obstacles ---
    print("\n[3] Add Obstacles")
    sim.world.add_obstacle(Vec3(0, 0, 0), radius=2.0, label="mineral_patch")
    sim.world.add_wall(Vec3(-30, -30, 0), Vec3(30, -30, 0), thickness=0.5, segment_count=12)
    rnd = sim.world.add_random_obstacles(count=8, bounds=40.0)
    print(f"    Added mineral patch, wall (12 segments), {rnd} random obstacles")
    print(f"    Total obstacles: {len(sim.world.obstacles)}")

    # --- ROS2 topics and services ---
    print("\n[4] ROS2 Infrastructure")
    topics = sim.ros.list_topics()
    services = sim.ros.list_services()
    print(f"    Topics: {[t['name'] for t in topics]}")
    print(f"    Services: {services}")

    # --- ROS2 service call: world info ---
    print("\n[5] ROS2 Service Call: /world_info")
    info = sim.ros.call_service("/world_info")
    for k, v in info.items():
        print(f"    {k}: {v}")

    # --- ROS2 action: navigate ---
    print("\n[6] ROS2 Action: /navigate_to")
    goal = {"robot_id": zerglings[0].robot_id, "target": {"x": 10, "y": 0, "z": 0}}
    result = sim.ros.send_goal("/navigate_to", goal)
    print(f"    Status: {result['status']}")

    # --- sensor sweep ---
    print("\n[7] Sensor Sweep (first zergling)")
    readings = sim.sensor_sweep(zerglings[0].robot_id)
    for name, reading in readings.items():
        data_keys = list(reading.data.keys())
        print(f"    {name}: keys={data_keys}")
    if "lidar" in readings:
        lidar_data = readings["lidar"].data["ranges"]
        print(f"    LIDAR rays: {len(lidar_data)}, min range: {min(lidar_data):.2f} m")

    # --- physics simulation ---
    print("\n[8] Physics Simulation (2 seconds)")
    # Push zerglings toward marines
    for z in zerglings:
        direction = (Vec3(20, 0, 0) - z.pose.position).normalized()
        z.velocity = direction * z.max_speed
    phys_results = sim.run_physics(duration=2.0)
    collision_count = sum(len(r["collisions"]) for r in phys_results)
    print(f"    Physics steps: {len(phys_results)}")
    print(f"    Total collision events: {collision_count}")

    # --- combat simulation ---
    print("\n[9] Combat Simulation (5 seconds)")
    combat = sim.run_combat(duration=5.0, dt=0.05)
    print(f"    Kills: {len(combat['kills'])}")
    for kill in combat["kills"][:5]:
        print(f"      {kill['killer']} -> {kill['victim']}")
    print(f"    Survivors: {len(combat['survivors'])}")

    # --- ROS message count ---
    print("\n[10] ROS2 Message Stats")
    print(f"    Total messages published: {sim.ros.message_count()}")

    # --- fleet status ---
    print("\n[11] Final Fleet Status")
    statuses = sim.fleet_status()
    alive_count = sum(1 for s in statuses if s["alive"])
    dead_count = len(statuses) - alive_count
    print(f"    Alive: {alive_count}, Dead: {dead_count}")
    for s in statuses[:4]:
        state = "ALIVE" if s["alive"] else "DEAD"
        print(f"    {s['robot_id']} ({s['unit_type']}): {state}, HP={s['hp']}")
    if len(statuses) > 4:
        print(f"    ... and {len(statuses) - 4} more robots")

    # --- damage report ---
    print("\n[12] Damage Report")
    top_dmg = sorted(combat["total_damage"].items(), key=lambda x: x[1], reverse=True)
    for rid, dmg in top_dmg[:5]:
        robot = sim.world.get_model(rid)
        utype = robot.unit_type if robot else "?"
        print(f"    {rid} ({utype}): {dmg:.1f} total damage dealt")

    print("\n" + "=" * 70)
    print("Phase 649 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 649: Gazebo registered
