"""
Phase 646: Unity ML-Agents Bridge for SC2 3D Visualization
===========================================================
Bridge between the SC2 bot and Unity ML-Agents for real-time 3D
visualization and reinforcement learning training.

Provides side-channel communication to stream game state into a Unity
scene, map SC2 units to 3D prefabs, and receive rendered observations
back.  The training integration wraps the Unity Academy API so that
PPO / SAC policies can be trained directly from SC2 match data.

Key components:
    - ObservationChannel: packages SC2 observations for Unity consumption
    - ActionChannel: translates Unity decisions back to SC2 commands
    - UnityEnvironment: manages the Unity process and gRPC connection
    - UnityAgent: single agent within the Unity environment
    - UnityBridge: top-level facade connecting SC2 bot to Unity ML-Agents
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import struct
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

UNITY_DEFAULT_PORT: int = 5005
UNITY_DEFAULT_TIMEOUT: float = 60.0
GRPC_MAX_MSG_SIZE: int = 4 * 1024 * 1024  # 4 MiB

SC2_RACES = ("Zerg", "Terran", "Protoss")

# Mapping of SC2 unit type IDs to Unity prefab names
SC2_UNIT_PREFAB_MAP: Dict[str, str] = {
    "Zergling": "Prefab_Zergling",
    "Baneling": "Prefab_Baneling",
    "Roach": "Prefab_Roach",
    "Hydralisk": "Prefab_Hydralisk",
    "Mutalisk": "Prefab_Mutalisk",
    "Ultralisk": "Prefab_Ultralisk",
    "Queen": "Prefab_Queen",
    "Overlord": "Prefab_Overlord",
    "Drone": "Prefab_Drone",
    "Larva": "Prefab_Larva",
    "Marine": "Prefab_Marine",
    "Marauder": "Prefab_Marauder",
    "SiegeTank": "Prefab_SiegeTank",
    "Medivac": "Prefab_Medivac",
    "Viking": "Prefab_Viking",
    "Zealot": "Prefab_Zealot",
    "Stalker": "Prefab_Stalker",
    "Colossus": "Prefab_Colossus",
    "Immortal": "Prefab_Immortal",
    "VoidRay": "Prefab_VoidRay",
}

# Unity ML-Agents training hyper-param defaults
DEFAULT_PPO_CONFIG: Dict[str, Any] = {
    "trainer_type": "ppo",
    "batch_size": 1024,
    "buffer_size": 10240,
    "learning_rate": 3.0e-4,
    "beta": 5.0e-3,
    "epsilon": 0.2,
    "lambd": 0.95,
    "num_epoch": 3,
    "hidden_units": 256,
    "num_layers": 2,
    "max_steps": 500000,
    "normalize": True,
}

DEFAULT_SAC_CONFIG: Dict[str, Any] = {
    "trainer_type": "sac",
    "batch_size": 256,
    "buffer_size": 50000,
    "buffer_init_steps": 1000,
    "learning_rate": 3.0e-4,
    "init_entcoef": 1.0,
    "tau": 0.005,
    "hidden_units": 256,
    "num_layers": 2,
    "max_steps": 500000,
    "normalize": True,
}

# ============================================================
# Helper utilities
# ============================================================


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _vec3_distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def _sc2_pos_to_unity(x: float, y: float, map_scale: float = 1.0) -> Tuple[float, float, float]:
    """Convert SC2 2D map coordinates to Unity 3D world coordinates."""
    return (x * map_scale, 0.0, y * map_scale)


def _unity_pos_to_sc2(ux: float, _uy: float, uz: float, map_scale: float = 1.0) -> Tuple[float, float]:
    """Convert Unity 3D world coordinates back to SC2 2D."""
    return (ux / max(map_scale, 1e-9), uz / max(map_scale, 1e-9))


def _encode_float_list(values: List[float]) -> bytes:
    """Pack a list of floats into a little-endian binary blob."""
    return struct.pack(f"<{len(values)}f", *values)


def _decode_float_list(data: bytes) -> List[float]:
    """Unpack a little-endian float blob."""
    n = len(data) // 4
    return list(struct.unpack(f"<{n}f", data[:n * 4]))


# ============================================================
# Data structures
# ============================================================


class ChannelType(Enum):
    OBSERVATION = auto()
    ACTION = auto()
    REWARD = auto()
    STATUS = auto()


@dataclass
class UnitSnapshot:
    """Snapshot of a single SC2 unit for transmission to Unity."""
    unit_id: int
    unit_type: str
    owner: int  # 1 = self, 2 = enemy
    x: float
    y: float
    health: float
    health_max: float
    shield: float = 0.0
    shield_max: float = 0.0
    energy: float = 0.0
    facing: float = 0.0  # radians
    is_selected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type,
            "owner": self.owner,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "health": round(self.health, 1),
            "health_max": round(self.health_max, 1),
            "shield": round(self.shield, 1),
            "shield_max": round(self.shield_max, 1),
            "energy": round(self.energy, 1),
            "facing": round(self.facing, 4),
            "is_selected": self.is_selected,
        }


@dataclass
class GameStatePacket:
    """Full game-state snapshot transmitted through the observation channel."""
    game_loop: int
    minerals: int
    vespene: int
    supply_used: int
    supply_cap: int
    units: List[UnitSnapshot] = field(default_factory=list)
    camera_pos: Tuple[float, float] = (0.0, 0.0)
    map_name: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "game_loop": self.game_loop,
            "minerals": self.minerals,
            "vespene": self.vespene,
            "supply_used": self.supply_used,
            "supply_cap": self.supply_cap,
            "camera_pos": list(self.camera_pos),
            "map_name": self.map_name,
            "units": [u.to_dict() for u in self.units],
        })

    def to_float_obs(self, max_units: int = 64) -> List[float]:
        """Flatten game state into a fixed-length float vector for RL."""
        obs: List[float] = [
            float(self.game_loop),
            float(self.minerals),
            float(self.vespene),
            float(self.supply_used),
            float(self.supply_cap),
            self.camera_pos[0],
            self.camera_pos[1],
        ]
        for i in range(max_units):
            if i < len(self.units):
                u = self.units[i]
                obs.extend([u.x, u.y, u.health, u.shield, u.energy, u.facing, float(u.owner)])
            else:
                obs.extend([0.0] * 7)
        return obs


@dataclass
class ActionPacket:
    """Actions received from Unity back to the SC2 bot."""
    agent_id: str
    continuous_actions: List[float] = field(default_factory=list)
    discrete_actions: List[int] = field(default_factory=list)
    text_command: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "continuous": self.continuous_actions,
            "discrete": self.discrete_actions,
            "text_command": self.text_command,
        }


# ============================================================
# ObservationChannel
# ============================================================


class ObservationChannel:
    """
    Side channel that packages SC2 observations and sends them to Unity.

    Serialises *GameStatePacket* objects into binary or JSON payloads.
    Unity-side consumers (C# ``SideChannel`` implementations) reconstruct
    the 3D scene from this data.
    """

    def __init__(self, channel_id: Optional[str] = None, binary_mode: bool = True):
        self.channel_id: str = channel_id or str(uuid.uuid4())
        self.binary_mode: bool = binary_mode
        self._buffer: List[bytes] = []
        self._send_count: int = 0
        self._last_send_time: float = 0.0
        logger.info("ObservationChannel created id=%s binary=%s", self.channel_id, binary_mode)

    # -- public API --

    def enqueue(self, packet: GameStatePacket) -> None:
        """Serialise a game-state packet and add it to the send buffer."""
        if self.binary_mode:
            payload = _encode_float_list(packet.to_float_obs())
        else:
            payload = packet.to_json().encode("utf-8")
        self._buffer.append(payload)

    def flush(self) -> List[bytes]:
        """Return all pending payloads and clear the buffer."""
        out = list(self._buffer)
        self._send_count += len(out)
        self._buffer.clear()
        self._last_send_time = time.monotonic()
        return out

    @property
    def pending_count(self) -> int:
        return len(self._buffer)

    @property
    def total_sent(self) -> int:
        return self._send_count

    def build_unit_prefab_list(self, units: List[UnitSnapshot]) -> List[Dict[str, Any]]:
        """Map SC2 units to Unity prefab spawn instructions."""
        result: List[Dict[str, Any]] = []
        for u in units:
            prefab = SC2_UNIT_PREFAB_MAP.get(u.unit_type, "Prefab_Generic")
            ux, uy, uz = _sc2_pos_to_unity(u.x, u.y)
            result.append({
                "prefab": prefab,
                "position": [ux, uy, uz],
                "rotation_y": math.degrees(u.facing),
                "unit_id": u.unit_id,
                "owner": u.owner,
                "health_pct": u.health / max(u.health_max, 1.0),
            })
        return result


# ============================================================
# ActionChannel
# ============================================================


class ActionChannel:
    """
    Side channel that receives actions produced by Unity ML-Agents policies
    and translates them into SC2 bot commands.
    """

    def __init__(self, channel_id: Optional[str] = None):
        self.channel_id: str = channel_id or str(uuid.uuid4())
        self._inbox: List[ActionPacket] = []
        self._recv_count: int = 0
        logger.info("ActionChannel created id=%s", self.channel_id)

    def receive_raw(self, data: bytes) -> ActionPacket:
        """Decode a raw byte payload into an ActionPacket."""
        try:
            obj = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            floats = _decode_float_list(data)
            obj = {"agent_id": "default", "continuous": floats, "discrete": []}
        pkt = ActionPacket(
            agent_id=obj.get("agent_id", "default"),
            continuous_actions=obj.get("continuous", []),
            discrete_actions=obj.get("discrete", []),
            text_command=obj.get("text_command", ""),
        )
        self._inbox.append(pkt)
        self._recv_count += 1
        return pkt

    def poll(self) -> List[ActionPacket]:
        """Return all queued actions and clear the inbox."""
        actions = list(self._inbox)
        self._inbox.clear()
        return actions

    @property
    def total_received(self) -> int:
        return self._recv_count

    def interpret_sc2_action(self, pkt: ActionPacket) -> Dict[str, Any]:
        """
        Convert an ActionPacket into SC2 bot-level instructions.

        Continuous actions:
            [0] target_x  (normalised 0-1)
            [1] target_y  (normalised 0-1)
            [2] aggression (0-1)

        Discrete actions:
            [0] action_type  0=hold, 1=move, 2=attack, 3=retreat
            [1] ability_idx  index into ability table
        """
        action_type_map = {0: "hold", 1: "move", 2: "attack", 3: "retreat"}
        ca = pkt.continuous_actions
        da = pkt.discrete_actions

        target_x = _clamp(ca[0], 0.0, 1.0) if len(ca) > 0 else 0.5
        target_y = _clamp(ca[1], 0.0, 1.0) if len(ca) > 1 else 0.5
        aggression = _clamp(ca[2], 0.0, 1.0) if len(ca) > 2 else 0.5
        action_type = action_type_map.get(da[0] if da else 0, "hold")
        ability_idx = da[1] if len(da) > 1 else 0

        return {
            "action": action_type,
            "target": (target_x, target_y),
            "aggression": round(aggression, 3),
            "ability_idx": ability_idx,
            "raw_continuous": ca,
            "raw_discrete": da,
        }


# ============================================================
# UnityAgent
# ============================================================


@dataclass
class AgentSpec:
    """Specification of an agent's observation / action spaces."""
    obs_size: int = 455  # 7 globals + 64 units * 7 features
    continuous_action_size: int = 3
    discrete_branches: List[int] = field(default_factory=lambda: [4, 16])
    visual_obs_shape: Optional[Tuple[int, int, int]] = None  # H, W, C


class UnityAgent:
    """
    Represents a single RL agent inside the Unity environment.

    Tracks cumulative reward, episode length, and action history.
    """

    def __init__(self, agent_id: str, spec: Optional[AgentSpec] = None, behavior_name: str = "SC2Brain"):
        self.agent_id: str = agent_id
        self.spec: AgentSpec = spec or AgentSpec()
        self.behavior_name: str = behavior_name
        self.cumulative_reward: float = 0.0
        self.episode_step: int = 0
        self.done: bool = False
        self._action_history: List[ActionPacket] = []
        self._obs_history: List[List[float]] = []
        self._episode_rewards: List[float] = []

    def step(self, obs: List[float], reward: float, done: bool) -> None:
        """Record one environment step."""
        self._obs_history.append(obs)
        self.cumulative_reward += reward
        self.episode_step += 1
        self.done = done
        if done:
            self._episode_rewards.append(self.cumulative_reward)

    def record_action(self, action: ActionPacket) -> None:
        self._action_history.append(action)

    def reset(self) -> None:
        self.cumulative_reward = 0.0
        self.episode_step = 0
        self.done = False

    @property
    def mean_episode_reward(self) -> float:
        if not self._episode_rewards:
            return 0.0
        return sum(self._episode_rewards) / len(self._episode_rewards)

    @property
    def total_episodes(self) -> int:
        return len(self._episode_rewards)

    def summary(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "behavior": self.behavior_name,
            "episodes": self.total_episodes,
            "mean_reward": round(self.mean_episode_reward, 4),
            "current_step": self.episode_step,
            "done": self.done,
        }


# ============================================================
# UnityEnvironment
# ============================================================


class UnityEnvironment:
    """
    Manages the connection to a Unity ML-Agents environment.

    In production this would launch the Unity binary and communicate over
    gRPC.  Here we simulate the lifecycle for integration testing.
    """

    def __init__(
        self,
        env_path: Optional[str] = None,
        port: int = UNITY_DEFAULT_PORT,
        timeout: float = UNITY_DEFAULT_TIMEOUT,
        no_graphics: bool = False,
        seed: int = 0,
    ):
        self.env_path: Optional[str] = env_path
        self.port: int = port
        self.timeout: float = timeout
        self.no_graphics: bool = no_graphics
        self.seed: int = seed

        self._connected: bool = False
        self._step_count: int = 0
        self._agents: Dict[str, UnityAgent] = {}
        self._obs_channel = ObservationChannel(binary_mode=True)
        self._act_channel = ActionChannel()
        self._academy_params: Dict[str, Any] = {}

        logger.info("UnityEnvironment created port=%d seed=%d", port, seed)

    # -- lifecycle --

    def connect(self) -> bool:
        """Establish gRPC connection to Unity (simulated)."""
        if self._connected:
            logger.warning("Already connected")
            return True
        logger.info("Connecting to Unity on port %d ...", self.port)
        # Simulate handshake delay
        self._connected = True
        logger.info("Unity connected successfully")
        return True

    def close(self) -> None:
        if self._connected:
            self._connected = False
            logger.info("Unity environment closed")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # -- agent management --

    def register_agent(self, agent_id: str, spec: Optional[AgentSpec] = None) -> UnityAgent:
        agent = UnityAgent(agent_id=agent_id, spec=spec)
        self._agents[agent_id] = agent
        logger.info("Registered agent %s", agent_id)
        return agent

    def get_agent(self, agent_id: str) -> Optional[UnityAgent]:
        return self._agents.get(agent_id)

    # -- step --

    def send_game_state(self, packet: GameStatePacket) -> None:
        """Push a game-state packet through the observation channel."""
        if not self._connected:
            raise RuntimeError("Not connected to Unity")
        self._obs_channel.enqueue(packet)
        self._obs_channel.flush()
        self._step_count += 1

    def receive_actions(self) -> List[ActionPacket]:
        """Poll the action channel for any pending decisions."""
        return self._act_channel.poll()

    def step_agents(self, packet: GameStatePacket, rewards: Optional[Dict[str, float]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Full environment step: send observations, generate simulated actions,
        and update agent bookkeeping.
        """
        self.send_game_state(packet)
        rewards = rewards or {}

        results: Dict[str, Dict[str, Any]] = {}
        obs_vec = packet.to_float_obs()
        for aid, agent in self._agents.items():
            r = rewards.get(aid, 0.0)
            agent.step(obs_vec, r, done=False)

            # Simulate Unity returning an action
            spec = agent.spec
            cont = [random.uniform(-1, 1) for _ in range(spec.continuous_action_size)]
            disc = [random.randint(0, b - 1) for b in spec.discrete_branches]
            pkt = ActionPacket(agent_id=aid, continuous_actions=cont, discrete_actions=disc)
            agent.record_action(pkt)

            cmd = self._act_channel.interpret_sc2_action(pkt)
            results[aid] = cmd

        return results

    # -- academy configuration --

    def set_academy_params(self, **kwargs: Any) -> None:
        self._academy_params.update(kwargs)
        logger.info("Academy params updated: %s", list(kwargs.keys()))

    def get_training_config(self, algorithm: str = "ppo") -> Dict[str, Any]:
        if algorithm == "sac":
            cfg = dict(DEFAULT_SAC_CONFIG)
        else:
            cfg = dict(DEFAULT_PPO_CONFIG)
        cfg.update(self._academy_params)
        return cfg

    @property
    def step_count(self) -> int:
        return self._step_count

    def summary(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "port": self.port,
            "step_count": self._step_count,
            "agents": {aid: a.summary() for aid, a in self._agents.items()},
            "obs_sent": self._obs_channel.total_sent,
            "acts_received": self._act_channel.total_received,
        }


# ============================================================
# UnityBridge  (top-level facade)
# ============================================================


class UnityBridge:
    """
    Top-level bridge connecting the SC2 bot to Unity ML-Agents.

    Workflow:
        1. ``create_environment()``  -- launch Unity
        2. ``register_agents()``     -- set up RL agents
        3. per game-loop: ``push_frame()`` + ``pull_actions()``
        4. ``run_training_episode()`` -- full episode loop
        5. ``close()``
    """

    def __init__(
        self,
        env_path: Optional[str] = None,
        port: int = UNITY_DEFAULT_PORT,
        map_scale: float = 1.0,
        max_units: int = 64,
    ):
        self.env_path: Optional[str] = env_path
        self.port: int = port
        self.map_scale: float = map_scale
        self.max_units: int = max_units

        self._env: Optional[UnityEnvironment] = None
        self._frame_counter: int = 0
        self._episode_counter: int = 0
        self._training_log: List[Dict[str, Any]] = []
        self._prefab_cache: Dict[str, str] = dict(SC2_UNIT_PREFAB_MAP)

    # -- environment management --

    def create_environment(self, seed: int = 42, no_graphics: bool = False) -> UnityEnvironment:
        self._env = UnityEnvironment(
            env_path=self.env_path,
            port=self.port,
            seed=seed,
            no_graphics=no_graphics,
        )
        self._env.connect()
        return self._env

    def register_agents(self, agent_ids: Optional[List[str]] = None) -> List[UnityAgent]:
        if self._env is None:
            raise RuntimeError("Call create_environment() first")
        ids = agent_ids or ["sc2_commander"]
        return [self._env.register_agent(aid) for aid in ids]

    def close(self) -> None:
        if self._env is not None:
            self._env.close()
            self._env = None

    # -- per-frame communication --

    def push_frame(self, packet: GameStatePacket) -> None:
        """Send one frame of SC2 game state to Unity for rendering."""
        if self._env is None:
            raise RuntimeError("Environment not initialised")
        self._env.send_game_state(packet)
        self._frame_counter += 1

    def pull_actions(self) -> List[ActionPacket]:
        if self._env is None:
            return []
        return self._env.receive_actions()

    # -- training --

    def run_training_episode(
        self,
        steps: int = 200,
        algorithm: str = "ppo",
        reward_fn: Optional[Callable[[GameStatePacket, int], Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """
        Simulate a full training episode.

        Parameters
        ----------
        steps : int
            Number of environment steps per episode.
        algorithm : str
            ``"ppo"`` or ``"sac"``.
        reward_fn : callable, optional
            Custom reward function ``(packet, step) -> {agent_id: reward}``.
        """
        if self._env is None:
            raise RuntimeError("Environment not initialised")

        self._episode_counter += 1
        config = self._env.get_training_config(algorithm)
        episode_rewards: Dict[str, float] = defaultdict(float)

        for step_i in range(steps):
            # Build a synthetic game state for training
            packet = self._build_synthetic_state(step_i, steps)
            if reward_fn is not None:
                rewards = reward_fn(packet, step_i)
            else:
                rewards = self._default_reward(packet, step_i)

            actions = self._env.step_agents(packet, rewards)
            for aid, r in rewards.items():
                episode_rewards[aid] += r

        # Finalise episode
        for agent in self._env._agents.values():
            agent._episode_rewards.append(agent.cumulative_reward)
            agent.reset()

        record = {
            "episode": self._episode_counter,
            "algorithm": algorithm,
            "steps": steps,
            "rewards": dict(episode_rewards),
            "config_snapshot": config,
        }
        self._training_log.append(record)
        return record

    def run_training(
        self,
        num_episodes: int = 10,
        steps_per_episode: int = 200,
        algorithm: str = "ppo",
    ) -> List[Dict[str, Any]]:
        """Run multiple training episodes and return logs."""
        results: List[Dict[str, Any]] = []
        for _ in range(num_episodes):
            rec = self.run_training_episode(steps=steps_per_episode, algorithm=algorithm)
            results.append(rec)
        return results

    # -- prefab management --

    def register_prefab(self, unit_type: str, prefab_name: str) -> None:
        self._prefab_cache[unit_type] = prefab_name

    def get_prefab(self, unit_type: str) -> str:
        return self._prefab_cache.get(unit_type, "Prefab_Generic")

    def map_units_to_scene(self, units: List[UnitSnapshot]) -> List[Dict[str, Any]]:
        """Build a list of Unity scene spawn/update instructions."""
        scene: List[Dict[str, Any]] = []
        for u in units:
            prefab = self.get_prefab(u.unit_type)
            ux, uy, uz = _sc2_pos_to_unity(u.x, u.y, self.map_scale)
            scene.append({
                "prefab": prefab,
                "position": [round(ux, 3), round(uy, 3), round(uz, 3)],
                "rotation_y": round(math.degrees(u.facing), 2),
                "scale": 1.0,
                "unit_id": u.unit_id,
                "owner": u.owner,
                "health_pct": round(u.health / max(u.health_max, 1.0), 3),
                "shield_pct": round(u.shield / max(u.shield_max, 1.0), 3) if u.shield_max > 0 else 0.0,
            })
        return scene

    # -- internal helpers --

    def _build_synthetic_state(self, step: int, total: int) -> GameStatePacket:
        """Create a synthetic game state for training without a live SC2 game."""
        num_units = random.randint(8, self.max_units)
        units: List[UnitSnapshot] = []
        unit_types = list(SC2_UNIT_PREFAB_MAP.keys())
        for i in range(num_units):
            ut = random.choice(unit_types)
            owner = 1 if i < num_units // 2 else 2
            hp_max = random.uniform(35, 500)
            units.append(UnitSnapshot(
                unit_id=i,
                unit_type=ut,
                owner=owner,
                x=random.uniform(0, 200),
                y=random.uniform(0, 200),
                health=random.uniform(1, hp_max),
                health_max=hp_max,
                shield=random.uniform(0, 100),
                shield_max=100.0 if "Protoss" in ut or ut in ("Zealot", "Stalker", "Colossus", "Immortal", "VoidRay") else 0.0,
                energy=random.uniform(0, 200),
                facing=random.uniform(0, 2 * math.pi),
            ))

        return GameStatePacket(
            game_loop=step * 16,
            minerals=random.randint(0, 5000),
            vespene=random.randint(0, 3000),
            supply_used=random.randint(20, 200),
            supply_cap=200,
            units=units,
            camera_pos=(random.uniform(0, 200), random.uniform(0, 200)),
            map_name="TrainingMap",
        )

    @staticmethod
    def _default_reward(packet: GameStatePacket, step: int) -> Dict[str, float]:
        """Simple reward: ratio of own health to total health on the field."""
        own_hp = sum(u.health for u in packet.units if u.owner == 1)
        enemy_hp = sum(u.health for u in packet.units if u.owner == 2)
        total = own_hp + enemy_hp
        reward = (own_hp - enemy_hp) / max(total, 1.0)
        return {"sc2_commander": round(reward, 4)}

    # -- reporting --

    @property
    def total_frames(self) -> int:
        return self._frame_counter

    @property
    def total_episodes(self) -> int:
        return self._episode_counter

    def summary(self) -> Dict[str, Any]:
        env_summary = self._env.summary() if self._env else {}
        return {
            "frames_pushed": self._frame_counter,
            "episodes_trained": self._episode_counter,
            "prefab_count": len(self._prefab_cache),
            "environment": env_summary,
        }


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate the Unity ML-Agents bridge for SC2."""
    print("=" * 70)
    print("Phase 646: Unity ML-Agents Bridge for SC2 3D Visualization")
    print("=" * 70)

    # 1. Create bridge and environment
    print("\n[1] Creating Unity bridge and environment ...")
    bridge = UnityBridge(port=5005, map_scale=0.5, max_units=32)
    env = bridge.create_environment(seed=42, no_graphics=True)
    agents = bridge.register_agents(["sc2_commander", "sc2_scout"])
    print(f"    Environment connected: {env.is_connected}")
    print(f"    Agents registered: {[a.agent_id for a in agents]}")

    # 2. Observation channel test
    print("\n[2] Testing ObservationChannel ...")
    obs_ch = ObservationChannel(binary_mode=True)
    units = [
        UnitSnapshot(1, "Zergling", 1, 50.0, 50.0, 35.0, 35.0, facing=1.57),
        UnitSnapshot(2, "Marine", 2, 60.0, 55.0, 45.0, 45.0, facing=3.14),
        UnitSnapshot(3, "Stalker", 1, 48.0, 52.0, 80.0, 80.0, shield=80.0, shield_max=80.0),
    ]
    packet = GameStatePacket(
        game_loop=160, minerals=400, vespene=200,
        supply_used=44, supply_cap=60, units=units,
        camera_pos=(50.0, 50.0), map_name="CatalystLE",
    )
    obs_ch.enqueue(packet)
    payloads = obs_ch.flush()
    print(f"    Payloads flushed: {len(payloads)}, total bytes: {sum(len(p) for p in payloads)}")
    print(f"    Float obs vector length: {len(packet.to_float_obs())}")

    # 3. Action channel test
    print("\n[3] Testing ActionChannel ...")
    act_ch = ActionChannel()
    raw_action = json.dumps({
        "agent_id": "sc2_commander",
        "continuous": [0.7, 0.3, 0.8],
        "discrete": [2, 5],
    }).encode("utf-8")
    act_pkt = act_ch.receive_raw(raw_action)
    sc2_cmd = act_ch.interpret_sc2_action(act_pkt)
    print(f"    Received action: type={sc2_cmd['action']}, target={sc2_cmd['target']}, aggression={sc2_cmd['aggression']}")

    # 4. Unit-to-prefab mapping
    print("\n[4] Mapping SC2 units to Unity prefabs ...")
    scene = bridge.map_units_to_scene(units)
    for item in scene:
        print(f"    {item['prefab']:20s} pos={item['position']} rot_y={item['rotation_y']}")

    # 5. Training episode
    print("\n[5] Running training episodes ...")
    results = bridge.run_training(num_episodes=3, steps_per_episode=50, algorithm="ppo")
    for rec in results:
        rewards = rec["rewards"]
        print(f"    Episode {rec['episode']}: steps={rec['steps']}, "
              f"rewards={{{', '.join(f'{k}: {v:.3f}' for k, v in rewards.items())}}}")

    # 6. SAC training test
    print("\n[6] Running SAC training ...")
    sac_results = bridge.run_training(num_episodes=2, steps_per_episode=30, algorithm="sac")
    for rec in sac_results:
        print(f"    Episode {rec['episode']}: algorithm={rec['algorithm']}, steps={rec['steps']}")

    # 7. Summary
    print("\n[7] Bridge summary:")
    summary = bridge.summary()
    print(f"    Frames pushed: {summary['frames_pushed']}")
    print(f"    Episodes trained: {summary['episodes_trained']}")
    print(f"    Prefab count: {summary['prefab_count']}")
    if summary["environment"]:
        env_s = summary["environment"]
        print(f"    Env steps: {env_s['step_count']}, obs sent: {env_s['obs_sent']}")

    bridge.close()

    print("\n" + "=" * 70)
    print("Phase 646 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 646: Unity ML-Agents registered
