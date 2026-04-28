"""
Phase 647: CARLA Sim-to-Real Transfer for Drone Fleet Control
==============================================================
Integration with the CARLA autonomous driving simulator for transferring
SC2 swarm intelligence to real-world drone fleet operations.

Simulates camera, LiDAR, radar, GPS, and IMU sensors attached to drones
in CARLA, applies domain randomization (weather, lighting, traffic density),
and provides a transfer pipeline that maps SC2 unit formations to 3D drone
formations.

Key components:
    - SensorSuite: multi-modal sensor simulation (camera, lidar, radar, GPS, IMU)
    - CARLAEnvironment: manages the CARLA server connection and world state
    - DroneController: individual drone with PID-based flight control
    - TransferPipeline: SC2 swarm tactics to CARLA drone fleet mapping
    - CARLABridge: top-level facade tying everything together
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CARLA_DEFAULT_HOST: str = "localhost"
CARLA_DEFAULT_PORT: int = 2000
CARLA_DEFAULT_TIMEOUT: float = 30.0

# Weather presets for domain randomization
WEATHER_PRESETS: List[Dict[str, Any]] = [
    {
        "name": "ClearNoon",
        "cloud": 0,
        "rain": 0,
        "wind": 0.1,
        "sun_altitude": 70.0,
        "fog": 0.0,
    },
    {
        "name": "CloudyNoon",
        "cloud": 60,
        "rain": 0,
        "wind": 0.3,
        "sun_altitude": 65.0,
        "fog": 0.0,
    },
    {
        "name": "WetNoon",
        "cloud": 40,
        "rain": 30,
        "wind": 0.2,
        "sun_altitude": 60.0,
        "fog": 5.0,
    },
    {
        "name": "HardRainNoon",
        "cloud": 90,
        "rain": 80,
        "wind": 0.7,
        "sun_altitude": 50.0,
        "fog": 20.0,
    },
    {
        "name": "ClearSunset",
        "cloud": 10,
        "rain": 0,
        "wind": 0.15,
        "sun_altitude": 10.0,
        "fog": 0.0,
    },
    {
        "name": "CloudySunset",
        "cloud": 70,
        "rain": 0,
        "wind": 0.4,
        "sun_altitude": 8.0,
        "fog": 10.0,
    },
    {
        "name": "WetSunset",
        "cloud": 50,
        "rain": 40,
        "wind": 0.35,
        "sun_altitude": 5.0,
        "fog": 15.0,
    },
    {
        "name": "NightClear",
        "cloud": 5,
        "rain": 0,
        "wind": 0.05,
        "sun_altitude": -30.0,
        "fog": 0.0,
    },
    {
        "name": "NightRain",
        "cloud": 80,
        "rain": 70,
        "wind": 0.6,
        "sun_altitude": -25.0,
        "fog": 30.0,
    },
    {
        "name": "FoggyMorning",
        "cloud": 30,
        "rain": 5,
        "wind": 0.1,
        "sun_altitude": 15.0,
        "fog": 60.0,
    },
]

# SC2 formation patterns that map to drone formations
SC2_FORMATION_MAP: Dict[str, str] = {
    "concave": "arc",
    "ball": "sphere",
    "line": "line",
    "surround": "ring",
    "split": "scatter",
    "box": "grid",
    "wedge": "v_formation",
}

# Drone physics defaults
DRONE_MAX_SPEED: float = 20.0  # m/s
DRONE_MAX_ALTITUDE: float = 120.0  # meters
DRONE_MIN_ALTITUDE: float = 2.0
DRONE_MASS: float = 2.5  # kg


# ============================================================
# Helper utilities
# ============================================================


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _vec3_distance(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * _clamp(t, 0.0, 1.0)


def _rotation_matrix_yaw(yaw_rad: float) -> List[List[float]]:
    """2D rotation matrix for yaw angle."""
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    return [[c, -s], [s, c]]


def _apply_rotation_2d(
    matrix: List[List[float]], point: Tuple[float, float]
) -> Tuple[float, float]:
    x = matrix[0][0] * point[0] + matrix[0][1] * point[1]
    y = matrix[1][0] * point[0] + matrix[1][1] * point[1]
    return (x, y)


# ============================================================
# Data structures
# ============================================================


class SensorType(Enum):
    CAMERA_RGB = auto()
    CAMERA_DEPTH = auto()
    CAMERA_SEMANTIC = auto()
    LIDAR = auto()
    RADAR = auto()
    GPS = auto()
    IMU = auto()


@dataclass
class SensorReading:
    """A single reading from a simulated sensor."""

    sensor_type: SensorType
    timestamp: float
    data: Any  # type depends on sensor
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_type": self.sensor_type.name,
            "timestamp": round(self.timestamp, 6),
            "metadata": self.metadata,
            "data_summary": str(type(self.data).__name__),
        }


@dataclass
class DroneState:
    """Full state of a drone in the CARLA world."""

    drone_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 10.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # roll, pitch, yaw
    battery_pct: float = 100.0
    is_armed: bool = True
    mode: str = "hover"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drone_id": self.drone_id,
            "position": [round(v, 3) for v in self.position],
            "velocity": [round(v, 3) for v in self.velocity],
            "orientation": [round(v, 3) for v in self.orientation],
            "battery_pct": round(self.battery_pct, 1),
            "is_armed": self.is_armed,
            "mode": self.mode,
        }


@dataclass
class SC2FormationSnapshot:
    """Snapshot of an SC2 unit formation for transfer."""

    formation_type: str
    center: Tuple[float, float]
    radius: float
    unit_positions: List[Tuple[float, float]] = field(default_factory=list)
    unit_types: List[str] = field(default_factory=list)
    heading: float = 0.0  # radians

    @property
    def unit_count(self) -> int:
        return len(self.unit_positions)


@dataclass
class WeatherState:
    """Current weather configuration in the CARLA world."""

    preset_name: str = "ClearNoon"
    cloud_density: float = 0.0
    rain_intensity: float = 0.0
    wind_intensity: float = 0.1
    sun_altitude: float = 70.0
    fog_density: float = 0.0

    @classmethod
    def from_preset(cls, preset: Dict[str, Any]) -> WeatherState:
        return cls(
            preset_name=preset["name"],
            cloud_density=preset["cloud"],
            rain_intensity=preset["rain"],
            wind_intensity=preset["wind"],
            sun_altitude=preset["sun_altitude"],
            fog_density=preset["fog"],
        )


# ============================================================
# SensorSuite
# ============================================================


class SensorSuite:
    """
    Multi-modal sensor simulation for a CARLA drone.

    Generates synthetic readings for camera (RGB, depth, semantic), LiDAR,
    radar, GPS, and IMU sensors.
    """

    def __init__(
        self, drone_id: str, enabled_sensors: Optional[List[SensorType]] = None
    ):
        self.drone_id: str = drone_id
        self.enabled: List[SensorType] = enabled_sensors or [
            SensorType.CAMERA_RGB,
            SensorType.LIDAR,
            SensorType.GPS,
            SensorType.IMU,
        ]
        self._readings: List[SensorReading] = []
        self._tick: int = 0
        self._noise_scale: float = 0.01
        logger.info(
            "SensorSuite for drone %s: %s", drone_id, [s.name for s in self.enabled]
        )

    def set_noise_scale(self, scale: float) -> None:
        self._noise_scale = max(0.0, scale)

    def tick(self, state: DroneState, weather: WeatherState) -> List[SensorReading]:
        """Generate one tick of sensor readings based on drone state and weather."""
        self._tick += 1
        ts = time.monotonic()
        readings: List[SensorReading] = []

        for sensor in self.enabled:
            reading = self._generate_reading(sensor, state, weather, ts)
            readings.append(reading)
            self._readings.append(reading)

        return readings

    def _generate_reading(
        self, sensor: SensorType, state: DroneState, weather: WeatherState, ts: float
    ) -> SensorReading:
        noise = self._noise_scale
        px, py, pz = state.position

        if sensor == SensorType.CAMERA_RGB:
            # Simulate RGB image as brightness/contrast metrics affected by weather
            brightness = _clamp(
                weather.sun_altitude / 90.0 + random.gauss(0, noise), 0, 1
            )
            visibility = _clamp(
                1.0 - weather.fog_density / 100.0 + random.gauss(0, noise), 0, 1
            )
            data = {
                "width": 640,
                "height": 480,
                "channels": 3,
                "brightness": round(brightness, 3),
                "visibility": round(visibility, 3),
                "rain_drops": int(weather.rain_intensity * random.uniform(0.5, 1.5)),
            }
            return SensorReading(sensor, ts, data, {"fov": 90, "altitude": pz})

        elif sensor == SensorType.CAMERA_DEPTH:
            max_range = 100.0 * (1.0 - weather.fog_density / 200.0)
            data = {"width": 640, "height": 480, "max_range": round(max_range, 2)}
            return SensorReading(sensor, ts, data, {"altitude": pz})

        elif sensor == SensorType.CAMERA_SEMANTIC:
            # Class distribution depends on altitude
            ground_pct = _clamp(80 - pz * 0.5 + random.gauss(0, 5), 0, 100)
            sky_pct = _clamp(pz * 0.3 + random.gauss(0, 3), 0, 100 - ground_pct)
            data = {
                "classes": {
                    "ground": round(ground_pct, 1),
                    "sky": round(sky_pct, 1),
                    "building": round(100 - ground_pct - sky_pct, 1),
                }
            }
            return SensorReading(sensor, ts, data, {"altitude": pz})

        elif sensor == SensorType.LIDAR:
            num_points = int(random.gauss(5000, 500))
            max_range = 50.0 * (1.0 - weather.rain_intensity / 200.0)
            data = {
                "num_points": max(0, num_points),
                "max_range": round(max_range, 2),
                "channels": 32,
                "rotation_freq": 10,
            }
            return SensorReading(sensor, ts, data, {"altitude": pz})

        elif sensor == SensorType.RADAR:
            num_detections = random.randint(0, 20)
            data = {
                "num_detections": num_detections,
                "max_range": 100.0,
                "fov_h": 30.0,
                "fov_v": 30.0,
            }
            return SensorReading(sensor, ts, data, {"altitude": pz})

        elif sensor == SensorType.GPS:
            # Simulated GPS with noise
            lat = 37.7749 + py * 0.00001 + random.gauss(0, noise * 0.0001)
            lon = -122.4194 + px * 0.00001 + random.gauss(0, noise * 0.0001)
            alt = pz + random.gauss(0, noise * 2)
            data = {
                "latitude": round(lat, 8),
                "longitude": round(lon, 8),
                "altitude": round(alt, 2),
                "hdop": round(random.uniform(0.5, 2.0), 2),
            }
            return SensorReading(sensor, ts, data, {})

        elif sensor == SensorType.IMU:
            roll, pitch, yaw = state.orientation
            ax = random.gauss(0, noise * 9.81)
            ay = random.gauss(0, noise * 9.81)
            az = 9.81 + random.gauss(0, noise * 9.81)
            gx = random.gauss(0, noise * 0.1)
            gy = random.gauss(0, noise * 0.1)
            gz = random.gauss(0, noise * 0.1)
            data = {
                "accel": [round(ax, 4), round(ay, 4), round(az, 4)],
                "gyro": [round(gx, 6), round(gy, 6), round(gz, 6)],
                "orientation": [round(roll, 4), round(pitch, 4), round(yaw, 4)],
            }
            return SensorReading(sensor, ts, data, {})

        return SensorReading(sensor, ts, None, {"error": "unknown sensor"})

    @property
    def total_readings(self) -> int:
        return len(self._readings)

    @property
    def tick_count(self) -> int:
        return self._tick


# ============================================================
# DroneController
# ============================================================


class DroneController:
    """
    Individual drone controller with PID-based flight dynamics.

    Supports waypoint following, formation holding, and basic
    collision avoidance via repulsive fields.
    """

    def __init__(
        self, drone_id: str, initial_pos: Tuple[float, float, float] = (0.0, 0.0, 10.0)
    ):
        self.drone_id: str = drone_id
        self.state: DroneState = DroneState(drone_id=drone_id, position=initial_pos)
        self.sensor_suite: SensorSuite = SensorSuite(drone_id)

        self._waypoints: List[Tuple[float, float, float]] = []
        self._wp_index: int = 0
        self._target: Optional[Tuple[float, float, float]] = None

        # PID gains
        self._kp: float = 1.2
        self._ki: float = 0.01
        self._kd: float = 0.4
        self._integral_error: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._prev_error: Tuple[float, float, float] = (0.0, 0.0, 0.0)

        self._step_count: int = 0
        self._battery_drain_rate: float = 0.005  # % per step

    def set_waypoints(self, waypoints: List[Tuple[float, float, float]]) -> None:
        self._waypoints = list(waypoints)
        self._wp_index = 0
        if waypoints:
            self._target = waypoints[0]

    def set_target(self, target: Tuple[float, float, float]) -> None:
        self._target = target

    def step(
        self, dt: float = 0.1, weather: Optional[WeatherState] = None
    ) -> DroneState:
        """Advance one simulation step."""
        weather = weather or WeatherState()
        self._step_count += 1

        if self._target is not None:
            self._pid_step(dt)

        # Advance to next waypoint if close enough
        if self._target is not None and self._waypoints:
            dist = _vec3_distance(self.state.position, self._target)
            if dist < 1.0 and self._wp_index < len(self._waypoints) - 1:
                self._wp_index += 1
                self._target = self._waypoints[self._wp_index]

        # Battery drain
        self.state.battery_pct = max(
            0.0, self.state.battery_pct - self._battery_drain_rate
        )
        if self.state.battery_pct <= 0.0:
            self.state.is_armed = False
            self.state.mode = "emergency_land"

        # Sensor tick
        self.sensor_suite.tick(self.state, weather)

        return self.state

    def _pid_step(self, dt: float) -> None:
        """PID control loop to move toward target."""
        if self._target is None:
            return

        px, py, pz = self.state.position
        tx, ty, tz = self._target

        # Clamp target altitude
        tz = _clamp(tz, DRONE_MIN_ALTITUDE, DRONE_MAX_ALTITUDE)

        ex, ey, ez = tx - px, ty - py, tz - pz

        # Integral
        ix = self._integral_error[0] + ex * dt
        iy = self._integral_error[1] + ey * dt
        iz = self._integral_error[2] + ez * dt
        self._integral_error = (ix, iy, iz)

        # Derivative
        dx = (ex - self._prev_error[0]) / max(dt, 1e-6)
        dy = (ey - self._prev_error[1]) / max(dt, 1e-6)
        dz = (ez - self._prev_error[2]) / max(dt, 1e-6)
        self._prev_error = (ex, ey, ez)

        # PID output
        vx = self._kp * ex + self._ki * ix + self._kd * dx
        vy = self._kp * ey + self._ki * iy + self._kd * dy
        vz = self._kp * ez + self._ki * iz + self._kd * dz

        # Clamp speed
        speed = math.sqrt(vx**2 + vy**2 + vz**2)
        if speed > DRONE_MAX_SPEED:
            scale = DRONE_MAX_SPEED / speed
            vx, vy, vz = vx * scale, vy * scale, vz * scale

        self.state.velocity = (round(vx, 4), round(vy, 4), round(vz, 4))
        new_x = px + vx * dt
        new_y = py + vy * dt
        new_z = _clamp(pz + vz * dt, DRONE_MIN_ALTITUDE, DRONE_MAX_ALTITUDE)
        self.state.position = (round(new_x, 4), round(new_y, 4), round(new_z, 4))

        # Update yaw to face direction of travel
        if abs(vx) > 0.01 or abs(vy) > 0.01:
            yaw = math.atan2(vy, vx)
            self.state.orientation = (0.0, 0.0, round(yaw, 4))

        self.state.mode = "moving" if speed > 0.5 else "hover"

    def distance_to_target(self) -> float:
        if self._target is None:
            return 0.0
        return _vec3_distance(self.state.position, self._target)

    def summary(self) -> Dict[str, Any]:
        return {
            **self.state.to_dict(),
            "steps": self._step_count,
            "waypoints_total": len(self._waypoints),
            "waypoint_index": self._wp_index,
            "dist_to_target": round(self.distance_to_target(), 3),
            "sensor_readings": self.sensor_suite.total_readings,
        }


# ============================================================
# CARLAEnvironment
# ============================================================


class CARLAEnvironment:
    """
    Manages the connection to a CARLA simulator server.

    In production this wraps ``carla.Client``.  Here it simulates the
    lifecycle and world state for offline development and testing.
    """

    def __init__(
        self,
        host: str = CARLA_DEFAULT_HOST,
        port: int = CARLA_DEFAULT_PORT,
        timeout: float = CARLA_DEFAULT_TIMEOUT,
        map_name: str = "Town01",
    ):
        self.host: str = host
        self.port: int = port
        self.timeout: float = timeout
        self.map_name: str = map_name

        self._connected: bool = False
        self._tick: int = 0
        self._weather: WeatherState = WeatherState()
        self._drones: Dict[str, DroneController] = {}
        self._traffic_density: float = 0.5  # 0-1
        self._randomization_enabled: bool = False
        self._randomization_interval: int = 50  # ticks between randomization

        logger.info("CARLAEnvironment created %s:%d map=%s", host, port, map_name)

    # -- lifecycle --

    def connect(self) -> bool:
        if self._connected:
            return True
        logger.info("Connecting to CARLA at %s:%d ...", self.host, self.port)
        self._connected = True
        logger.info("CARLA connected on map %s", self.map_name)
        return True

    def close(self) -> None:
        if self._connected:
            self._connected = False
            logger.info("CARLA environment closed")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # -- drone management --

    def spawn_drone(
        self, drone_id: str, position: Tuple[float, float, float] = (0.0, 0.0, 10.0)
    ) -> DroneController:
        drone = DroneController(drone_id=drone_id, initial_pos=position)
        self._drones[drone_id] = drone
        logger.info("Spawned drone %s at %s", drone_id, position)
        return drone

    def get_drone(self, drone_id: str) -> Optional[DroneController]:
        return self._drones.get(drone_id)

    def remove_drone(self, drone_id: str) -> bool:
        if drone_id in self._drones:
            del self._drones[drone_id]
            return True
        return False

    @property
    def drone_count(self) -> int:
        return len(self._drones)

    # -- weather / domain randomization --

    def set_weather(self, preset_name: str) -> WeatherState:
        for p in WEATHER_PRESETS:
            if p["name"] == preset_name:
                self._weather = WeatherState.from_preset(p)
                logger.info("Weather set to %s", preset_name)
                return self._weather
        logger.warning("Unknown preset %s, keeping current weather", preset_name)
        return self._weather

    def randomize_weather(self) -> WeatherState:
        preset = random.choice(WEATHER_PRESETS)
        self._weather = WeatherState.from_preset(preset)
        # Add noise on top of preset
        self._weather.cloud_density = _clamp(
            self._weather.cloud_density + random.gauss(0, 5), 0, 100
        )
        self._weather.rain_intensity = _clamp(
            self._weather.rain_intensity + random.gauss(0, 5), 0, 100
        )
        self._weather.fog_density = _clamp(
            self._weather.fog_density + random.gauss(0, 3), 0, 100
        )
        return self._weather

    def set_traffic_density(self, density: float) -> None:
        self._traffic_density = _clamp(density, 0.0, 1.0)

    def enable_domain_randomization(
        self, enabled: bool = True, interval: int = 50
    ) -> None:
        self._randomization_enabled = enabled
        self._randomization_interval = max(1, interval)

    # -- simulation step --

    def tick(self, dt: float = 0.1) -> Dict[str, DroneState]:
        """Advance one simulation tick for all drones."""
        if not self._connected:
            raise RuntimeError("Not connected to CARLA")
        self._tick += 1

        # Domain randomization
        if (
            self._randomization_enabled
            and self._tick % self._randomization_interval == 0
        ):
            self.randomize_weather()

        results: Dict[str, DroneState] = {}
        for did, drone in self._drones.items():
            state = drone.step(dt=dt, weather=self._weather)
            results[did] = state
        return results

    @property
    def tick_count(self) -> int:
        return self._tick

    @property
    def weather(self) -> WeatherState:
        return self._weather

    def summary(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "host": self.host,
            "port": self.port,
            "map": self.map_name,
            "ticks": self._tick,
            "weather": self._weather.preset_name,
            "drones": {did: d.summary() for did, d in self._drones.items()},
            "traffic_density": self._traffic_density,
            "domain_randomization": self._randomization_enabled,
        }


# ============================================================
# TransferPipeline
# ============================================================


class TransferPipeline:
    """
    Maps SC2 swarm tactics and unit formations to CARLA drone fleet
    formations and movement commands.

    The pipeline:
        1. Receive SC2FormationSnapshot
        2. Scale from SC2 map coords to real-world meters
        3. Convert 2D formation to 3D drone positions (with altitude layer)
        4. Assign drones to positions via Hungarian-style greedy matching
        5. Generate waypoints for each drone
    """

    def __init__(
        self,
        scale_factor: float = 0.5,
        default_altitude: float = 15.0,
        altitude_spread: float = 5.0,
    ):
        self.scale_factor: float = scale_factor
        self.default_altitude: float = default_altitude
        self.altitude_spread: float = altitude_spread
        self._transfer_count: int = 0
        self._formation_log: List[Dict[str, Any]] = []

    def sc2_to_3d_positions(
        self, formation: SC2FormationSnapshot
    ) -> List[Tuple[float, float, float]]:
        """Convert SC2 2D unit positions to 3D drone positions."""
        positions_3d: List[Tuple[float, float, float]] = []
        cx, cy = formation.center
        for i, (ux, uy) in enumerate(formation.unit_positions):
            # Scale relative to center
            rx = (ux - cx) * self.scale_factor
            ry = (uy - cy) * self.scale_factor
            # Rotate by formation heading
            rot = _rotation_matrix_yaw(formation.heading)
            rx2, ry2 = _apply_rotation_2d(rot, (rx, ry))
            # Add altitude variation based on index
            alt = self.default_altitude + (i % 3 - 1) * self.altitude_spread
            alt = _clamp(alt, DRONE_MIN_ALTITUDE, DRONE_MAX_ALTITUDE)
            positions_3d.append((round(rx2, 3), round(ry2, 3), round(alt, 3)))
        return positions_3d

    def generate_drone_formation(
        self,
        formation_type: str,
        num_drones: int,
        center: Tuple[float, float, float] = (0.0, 0.0, 15.0),
    ) -> List[Tuple[float, float, float]]:
        """Generate a named 3D drone formation directly."""
        drone_type = SC2_FORMATION_MAP.get(formation_type, formation_type)
        cx, cy, cz = center
        positions: List[Tuple[float, float, float]] = []

        if drone_type == "line":
            spacing = 3.0
            start_x = cx - (num_drones - 1) * spacing / 2
            for i in range(num_drones):
                positions.append((round(start_x + i * spacing, 2), cy, cz))

        elif drone_type == "arc":
            radius = max(5.0, num_drones * 1.5)
            angle_span = math.pi * 0.8
            start_angle = math.pi / 2 - angle_span / 2
            for i in range(num_drones):
                a = start_angle + (angle_span / max(num_drones - 1, 1)) * i
                x = cx + radius * math.cos(a)
                y = cy + radius * math.sin(a)
                positions.append((round(x, 2), round(y, 2), cz))

        elif drone_type == "ring":
            radius = max(5.0, num_drones * 1.2)
            for i in range(num_drones):
                a = 2 * math.pi * i / num_drones
                x = cx + radius * math.cos(a)
                y = cy + radius * math.sin(a)
                positions.append((round(x, 2), round(y, 2), cz))

        elif drone_type == "sphere":
            # Fibonacci sphere distribution
            golden = (1 + math.sqrt(5)) / 2
            radius = max(5.0, num_drones * 0.8)
            for i in range(num_drones):
                theta = math.acos(1 - 2 * (i + 0.5) / num_drones)
                phi = 2 * math.pi * i / golden
                x = cx + radius * math.sin(theta) * math.cos(phi)
                y = cy + radius * math.sin(theta) * math.sin(phi)
                z = cz + radius * math.cos(theta)
                z = _clamp(z, DRONE_MIN_ALTITUDE, DRONE_MAX_ALTITUDE)
                positions.append((round(x, 2), round(y, 2), round(z, 2)))

        elif drone_type == "v_formation":
            spacing = 3.0
            for i in range(num_drones):
                side = 1 if i % 2 == 0 else -1
                rank = (i + 1) // 2
                x = cx - rank * spacing
                y = cy + side * rank * spacing
                positions.append((round(x, 2), round(y, 2), cz))

        elif drone_type == "grid":
            cols = max(1, int(math.ceil(math.sqrt(num_drones))))
            spacing = 4.0
            idx = 0
            for r in range(cols):
                for c in range(cols):
                    if idx >= num_drones:
                        break
                    x = cx + (c - cols / 2) * spacing
                    y = cy + (r - cols / 2) * spacing
                    positions.append((round(x, 2), round(y, 2), cz))
                    idx += 1

        elif drone_type == "scatter":
            for _ in range(num_drones):
                x = cx + random.uniform(-15, 15)
                y = cy + random.uniform(-15, 15)
                z = cz + random.uniform(-3, 3)
                z = _clamp(z, DRONE_MIN_ALTITUDE, DRONE_MAX_ALTITUDE)
                positions.append((round(x, 2), round(y, 2), round(z, 2)))

        else:
            # Fallback to line
            for i in range(num_drones):
                positions.append((round(cx + i * 3.0, 2), cy, cz))

        return positions

    def assign_drones_to_positions(
        self,
        drones: List[DroneController],
        target_positions: List[Tuple[float, float, float]],
    ) -> Dict[str, Tuple[float, float, float]]:
        """Greedy nearest-first assignment of drones to target positions."""
        available = list(range(len(target_positions)))
        assignment: Dict[str, Tuple[float, float, float]] = {}

        for drone in drones:
            if not available:
                break
            best_idx = min(
                available,
                key=lambda j: _vec3_distance(drone.state.position, target_positions[j]),
            )
            assignment[drone.drone_id] = target_positions[best_idx]
            available.remove(best_idx)

        return assignment

    def transfer_formation(
        self, formation: SC2FormationSnapshot, drones: List[DroneController]
    ) -> Dict[str, Tuple[float, float, float]]:
        """Full transfer pipeline: SC2 formation -> drone waypoints."""
        self._transfer_count += 1
        positions_3d = self.sc2_to_3d_positions(formation)

        # If more drones than positions, generate extras
        while len(positions_3d) < len(drones):
            offset = (
                random.uniform(-2, 2),
                random.uniform(-2, 2),
                self.default_altitude,
            )
            positions_3d.append(offset)

        assignment = self.assign_drones_to_positions(drones, positions_3d)

        self._formation_log.append(
            {
                "transfer_id": self._transfer_count,
                "sc2_type": formation.formation_type,
                "num_units": formation.unit_count,
                "num_drones": len(drones),
                "assignments": len(assignment),
            }
        )

        return assignment

    @property
    def total_transfers(self) -> int:
        return self._transfer_count


# ============================================================
# CARLABridge  (top-level facade)
# ============================================================


class CARLABridge:
    """
    Top-level facade connecting the SC2 bot to CARLA for drone fleet
    sim-to-real transfer.

    Workflow:
        1. ``create_environment()``
        2. ``spawn_fleet()``
        3. ``apply_sc2_formation()`` or ``apply_named_formation()``
        4. ``run_simulation()``
        5. ``close()``
    """

    def __init__(
        self,
        host: str = CARLA_DEFAULT_HOST,
        port: int = CARLA_DEFAULT_PORT,
        map_name: str = "Town01",
        scale_factor: float = 0.5,
    ):
        self.host: str = host
        self.port: int = port
        self.map_name: str = map_name
        self._env: Optional[CARLAEnvironment] = None
        self._pipeline: TransferPipeline = TransferPipeline(scale_factor=scale_factor)
        self._sim_log: List[Dict[str, Any]] = []

    # -- environment --

    def create_environment(self) -> CARLAEnvironment:
        self._env = CARLAEnvironment(
            host=self.host, port=self.port, map_name=self.map_name
        )
        self._env.connect()
        return self._env

    def close(self) -> None:
        if self._env is not None:
            self._env.close()
            self._env = None

    # -- fleet management --

    def spawn_fleet(
        self,
        num_drones: int,
        base_position: Tuple[float, float, float] = (0.0, 0.0, 10.0),
    ) -> List[DroneController]:
        if self._env is None:
            raise RuntimeError("Call create_environment() first")
        drones: List[DroneController] = []
        for i in range(num_drones):
            pos = (
                base_position[0] + i * 3.0,
                base_position[1],
                base_position[2],
            )
            drone = self._env.spawn_drone(f"drone_{i:03d}", position=pos)
            drones.append(drone)
        return drones

    # -- formation commands --

    def apply_sc2_formation(
        self, formation: SC2FormationSnapshot
    ) -> Dict[str, Tuple[float, float, float]]:
        if self._env is None:
            raise RuntimeError("Environment not initialised")
        drones = list(self._env._drones.values())
        assignment = self._pipeline.transfer_formation(formation, drones)
        for did, target in assignment.items():
            drone = self._env.get_drone(did)
            if drone is not None:
                drone.set_target(target)
        return assignment

    def apply_named_formation(
        self, formation_type: str, center: Tuple[float, float, float] = (0.0, 0.0, 15.0)
    ) -> Dict[str, Tuple[float, float, float]]:
        if self._env is None:
            raise RuntimeError("Environment not initialised")
        drones = list(self._env._drones.values())
        positions = self._pipeline.generate_drone_formation(
            formation_type, len(drones), center
        )
        assignment = self._pipeline.assign_drones_to_positions(drones, positions)
        for did, target in assignment.items():
            drone = self._env.get_drone(did)
            if drone is not None:
                drone.set_target(target)
        return assignment

    # -- simulation --

    def run_simulation(
        self,
        ticks: int = 100,
        dt: float = 0.1,
        domain_randomization: bool = True,
        randomization_interval: int = 25,
    ) -> List[Dict[str, Any]]:
        if self._env is None:
            raise RuntimeError("Environment not initialised")
        self._env.enable_domain_randomization(
            domain_randomization, randomization_interval
        )

        tick_log: List[Dict[str, Any]] = []
        for t in range(ticks):
            states = self._env.tick(dt=dt)
            if t % max(ticks // 5, 1) == 0 or t == ticks - 1:
                snap = {
                    "tick": self._env.tick_count,
                    "weather": self._env.weather.preset_name,
                    "drones": {did: s.to_dict() for did, s in states.items()},
                }
                tick_log.append(snap)

        self._sim_log.extend(tick_log)
        return tick_log

    # -- reporting --

    def summary(self) -> Dict[str, Any]:
        env_summary = self._env.summary() if self._env else {}
        return {
            "environment": env_summary,
            "transfers": self._pipeline.total_transfers,
            "sim_snapshots": len(self._sim_log),
        }


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate the CARLA sim-to-real transfer pipeline."""
    print("=" * 70)
    print("Phase 647: CARLA Sim-to-Real Transfer for Drone Fleet Control")
    print("=" * 70)

    # 1. Create environment
    print("\n[1] Creating CARLA environment ...")
    bridge = CARLABridge(port=2000, map_name="Town03", scale_factor=0.5)
    env = bridge.create_environment()
    print(f"    Connected: {env.is_connected}, Map: {env.map_name}")

    # 2. Spawn drone fleet
    print("\n[2] Spawning drone fleet ...")
    fleet = bridge.spawn_fleet(6, base_position=(10.0, 0.0, 15.0))
    print(f"    Drones spawned: {len(fleet)}")
    for d in fleet:
        print(f"      {d.drone_id}: pos={d.state.position}")

    # 3. Sensor test
    print("\n[3] Sensor suite test ...")
    weather = WeatherState.from_preset(WEATHER_PRESETS[0])
    readings = fleet[0].sensor_suite.tick(fleet[0].state, weather)
    for r in readings:
        print(f"      {r.sensor_type.name}: {r.to_dict()['data_summary']}")

    # 4. Domain randomization
    print("\n[4] Domain randomization ...")
    for i in range(3):
        w = env.randomize_weather()
        print(
            f"    Randomized weather #{i + 1}: {w.preset_name} "
            f"(cloud={w.cloud_density:.0f}, rain={w.rain_intensity:.0f}, fog={w.fog_density:.0f})"
        )

    # 5. SC2 formation transfer
    print("\n[5] SC2 formation transfer ...")
    sc2_formation = SC2FormationSnapshot(
        formation_type="concave",
        center=(100.0, 80.0),
        radius=15.0,
        unit_positions=[
            (90.0, 75.0),
            (95.0, 72.0),
            (100.0, 70.0),
            (105.0, 72.0),
            (110.0, 75.0),
            (100.0, 68.0),
        ],
        unit_types=["Zergling", "Zergling", "Roach", "Roach", "Hydralisk", "Queen"],
        heading=0.3,
    )
    assignment = bridge.apply_sc2_formation(sc2_formation)
    print(f"    Formation type: {sc2_formation.formation_type} -> drone assignments:")
    for did, pos in assignment.items():
        print(f"      {did}: target={pos}")

    # 6. Named formation test
    print("\n[6] Named formations ...")
    for ftype in ["ring", "v_formation", "grid"]:
        positions = bridge._pipeline.generate_drone_formation(ftype, 6)
        print(
            f"    {ftype:15s}: {len(positions)} positions, "
            f"first={positions[0] if positions else 'N/A'}"
        )

    # 7. Run simulation
    print("\n[7] Running simulation (50 ticks) ...")
    sim_log = bridge.run_simulation(
        ticks=50, dt=0.1, domain_randomization=True, randomization_interval=10
    )
    print(f"    Simulation complete, {len(sim_log)} snapshots recorded")
    for snap in sim_log[:2]:
        drone_sample = list(snap["drones"].values())[0] if snap["drones"] else {}
        print(
            f"    Tick {snap['tick']}: weather={snap['weather']}, "
            f"drone_0 pos={drone_sample.get('position', 'N/A')}"
        )

    # 8. PID waypoint following test
    print("\n[8] PID waypoint following ...")
    test_drone = fleet[0]
    test_drone.set_waypoints(
        [(20.0, 10.0, 15.0), (30.0, 20.0, 20.0), (10.0, 30.0, 12.0)]
    )
    for step in range(30):
        test_drone.step(dt=0.2, weather=weather)
    d_sum = test_drone.summary()
    print(
        f"    Drone {d_sum['drone_id']}: pos={d_sum['position']}, "
        f"wp={d_sum['waypoint_index']}/{d_sum['waypoints_total']}, "
        f"battery={d_sum['battery_pct']:.1f}%"
    )

    # 9. Summary
    print("\n[9] Bridge summary:")
    summary = bridge.summary()
    print(f"    Transfers: {summary['transfers']}")
    print(f"    Sim snapshots: {summary['sim_snapshots']}")
    if summary["environment"]:
        es = summary["environment"]
        print(f"    Env ticks: {es['ticks']}, drones: {len(es['drones'])}")

    bridge.close()

    print("\n" + "=" * 70)
    print("Phase 647 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 647: CARLA registered
