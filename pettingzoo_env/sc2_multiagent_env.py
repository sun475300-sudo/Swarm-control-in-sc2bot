"""
Phase 609: PettingZoo Multi-Agent Environment for SC2
=====================================================
pettingzoo_env/sc2_multiagent_env.py

PettingZoo-compatible parallel environment wrapper for StarCraft II
multi-agent scenarios.  Each controllable SC2 unit is mapped to a named
agent that acts simultaneously via the Parallel API.

Key features:
  - SC2ParallelEnv      : Main environment implementing PettingZoo Parallel API
  - AgentObservation    : Per-agent observation dataclass with SC2-specific
                          features (health, position, cooldown, nearby units)
  - SC2ActionSpace      : Action space descriptor for SC2 unit micro-control
  - Parallel step/reset : All agents act simultaneously each game frame
  - Shared team reward  : Team objectives (damage, kills) distributed across
                          cooperating agents with individual bonuses
  - Agent lifecycle     : Dynamic agent registration/removal as units spawn/die
  - Flexible reward     : Configurable cooperative vs individual reward ratio
  - Full NumPy fallback : No hard dependency on PettingZoo or Gymnasium

Dependencies: numpy; pettingzoo & gymnasium optional (fallback provided).
"""

from __future__ import annotations

import argparse
import copy
import logging
import math
import random
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional PettingZoo / Gymnasium imports with fallbacks
# ---------------------------------------------------------------------------
_PETTINGZOO_AVAILABLE = False
_GYM_AVAILABLE = False

try:
    from pettingzoo import ParallelEnv as _PZParallelEnv

    _PETTINGZOO_AVAILABLE = True
except ImportError:

    class _PZParallelEnv:
        """Minimal stub when PettingZoo is not installed."""

        pass


try:
    import gymnasium as gym
    from gymnasium import spaces

    _GYM_AVAILABLE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# SC2 constants
# ---------------------------------------------------------------------------

ZERG_UNIT_TYPES: Dict[str, int] = {
    "zergling": 0,
    "baneling": 1,
    "roach": 2,
    "hydralisk": 3,
    "mutalisk": 4,
    "ultralisk": 5,
    "infestor": 6,
    "corruptor": 7,
    "queen": 8,
    "overseer": 9,
}

# Per-unit observation and action dimensions
UNIT_OBS_DIM: Dict[str, int] = {
    "zergling": 20,
    "baneling": 20,
    "roach": 24,
    "hydralisk": 24,
    "mutalisk": 26,
    "ultralisk": 28,
    "infestor": 28,
    "corruptor": 26,
    "queen": 26,
    "overseer": 22,
}

# Action dimensions: [move_x, move_y, attack_target_id, ability_id, no_op]
UNIT_ACT_DIM: Dict[str, int] = {
    "zergling": 5,
    "baneling": 6,
    "roach": 6,
    "hydralisk": 6,
    "mutalisk": 6,
    "ultralisk": 6,
    "infestor": 7,
    "corruptor": 6,
    "queen": 7,
    "overseer": 5,
}

MAX_AGENTS = 50  # maximum simultaneous agents
MAP_SIZE = 200.0  # normalisation constant for coordinates


# ===================================================================
# AgentObservation
# ===================================================================


@dataclass
class AgentObservation:
    """Structured observation for a single SC2 agent/unit.

    Attributes:
        agent_id: Unique identifier for this agent.
        unit_type: SC2 unit type string.
        health: Normalised health [0, 1].
        shield: Normalised shield [0, 1].
        energy: Normalised energy [0, 1].
        pos_x: Normalised x-position [0, 1].
        pos_y: Normalised y-position [0, 1].
        cooldown: Normalised weapon cooldown [0, 1].
        nearby_allies: Number of allied units within sensor range.
        nearby_enemies: Number of enemy units within sensor range.
        relative_enemy_positions: Array of (dx, dy, health) for nearby enemies.
        is_alive: Whether the unit is still alive.
    """

    agent_id: str
    unit_type: str = "zergling"
    health: float = 1.0
    shield: float = 0.0
    energy: float = 0.0
    pos_x: float = 0.5
    pos_y: float = 0.5
    cooldown: float = 0.0
    nearby_allies: int = 0
    nearby_enemies: int = 0
    relative_enemy_positions: np.ndarray = field(
        default_factory=lambda: np.zeros((5, 3), dtype=np.float32)
    )
    is_alive: bool = True

    def to_array(self) -> np.ndarray:
        """Flatten observation into a fixed-size feature vector."""
        base = np.array(
            [
                self.health,
                self.shield,
                self.energy,
                self.pos_x,
                self.pos_y,
                self.cooldown,
                float(self.nearby_allies) / MAX_AGENTS,
                float(self.nearby_enemies) / MAX_AGENTS,
                float(self.is_alive),
                float(ZERG_UNIT_TYPES.get(self.unit_type, 0)) / len(ZERG_UNIT_TYPES),
            ],
            dtype=np.float32,
        )
        enemy_flat = self.relative_enemy_positions.flatten()
        obs_dim = UNIT_OBS_DIM.get(self.unit_type, 20)
        combined = np.concatenate([base, enemy_flat])
        # Pad or truncate to expected dimension
        if len(combined) < obs_dim:
            combined = np.concatenate(
                [combined, np.zeros(obs_dim - len(combined), dtype=np.float32)]
            )
        else:
            combined = combined[:obs_dim]
        return combined


# ===================================================================
# SC2ActionSpace
# ===================================================================


class SC2ActionSpace:
    """Action space descriptor for SC2 unit micro-control.

    Supports both discrete and continuous action modes.
    Discrete actions: no_op, move_up, move_down, move_left, move_right,
                      attack_closest, use_ability
    Continuous actions: (move_dx, move_dy, attack_target_encoding, ability_id)
    """

    DISCRETE_ACTIONS = [
        "no_op",
        "move_up",
        "move_down",
        "move_left",
        "move_right",
        "attack_closest",
        "use_ability",
    ]

    def __init__(
        self,
        unit_type: str = "zergling",
        continuous: bool = False,
    ) -> None:
        self.unit_type = unit_type
        self.continuous = continuous
        self.n_discrete = len(self.DISCRETE_ACTIONS)
        self.act_dim = UNIT_ACT_DIM.get(unit_type, 5)

    def sample(self) -> np.ndarray:
        """Sample a random action."""
        if self.continuous:
            return np.random.uniform(-1.0, 1.0, size=self.act_dim).astype(np.float32)
        action = np.zeros(self.act_dim, dtype=np.float32)
        action[random.randint(0, min(self.n_discrete, self.act_dim) - 1)] = 1.0
        return action

    def no_op(self) -> np.ndarray:
        """Return a no-operation action."""
        action = np.zeros(self.act_dim, dtype=np.float32)
        action[0] = 1.0
        return action

    def gym_space(self) -> Any:
        """Return a gymnasium-compatible space if available."""
        if not _GYM_AVAILABLE:
            return None
        if self.continuous:
            return spaces.Box(
                low=-1.0,
                high=1.0,
                shape=(self.act_dim,),
                dtype=np.float32,
            )
        return spaces.Discrete(self.n_discrete)

    def __repr__(self) -> str:
        mode = "continuous" if self.continuous else "discrete"
        return f"SC2ActionSpace(unit={self.unit_type}, mode={mode}, dim={self.act_dim})"


# ===================================================================
# Reward configuration
# ===================================================================


@dataclass
class RewardConfig:
    """Configurable reward weights for cooperative SC2 tasks."""

    damage_dealt_weight: float = 1.0
    damage_taken_weight: float = -0.5
    kill_reward: float = 5.0
    death_penalty: float = -3.0
    team_objective_weight: float = 2.0
    individual_bonus_weight: float = 0.3
    win_reward: float = 20.0
    lose_penalty: float = -10.0
    cooperative_ratio: float = 0.7  # fraction of reward shared with team

    def compute_agent_reward(
        self,
        damage_dealt: float,
        damage_taken: float,
        kills: int,
        died: bool,
        team_objective_score: float,
        n_alive_allies: int,
    ) -> Tuple[float, float]:
        """Compute individual and team reward components.

        Returns:
            (individual_reward, team_reward)
        """
        individual = (
            self.damage_dealt_weight * damage_dealt
            + self.damage_taken_weight * damage_taken
            + self.kill_reward * kills
            + (self.death_penalty if died else 0.0)
        )
        team = self.team_objective_weight * team_objective_score
        # Distribute team reward evenly among alive allies
        if n_alive_allies > 0:
            team_per_agent = team / n_alive_allies
        else:
            team_per_agent = 0.0

        blended = (
            self.cooperative_ratio * team_per_agent
            + (1.0 - self.cooperative_ratio) * individual
        )
        return individual, blended


# ===================================================================
# Simulated SC2 unit (for demo / testing without SC2 client)
# ===================================================================


@dataclass
class _SimUnit:
    """Internal simulated SC2 unit for environment stepping."""

    agent_id: str
    unit_type: str
    x: float
    y: float
    health: float = 100.0
    max_health: float = 100.0
    shield: float = 0.0
    energy: float = 50.0
    cooldown: float = 0.0
    is_alive: bool = True
    team: int = 0  # 0 = ally, 1 = enemy
    damage: float = 10.0
    attack_range: float = 15.0

    def take_damage(self, dmg: float) -> float:
        """Apply damage, return actual damage dealt."""
        if not self.is_alive:
            return 0.0
        actual = min(dmg, self.health)
        self.health -= actual
        if self.health <= 0.0:
            self.health = 0.0
            self.is_alive = False
        return actual

    def normalised_health(self) -> float:
        return self.health / max(self.max_health, 1.0)


# ===================================================================
# SC2ParallelEnv - PettingZoo Parallel API
# ===================================================================


class SC2ParallelEnv(_PZParallelEnv):
    """PettingZoo Parallel Environment for StarCraft II multi-agent control.

    Each controllable SC2 unit maps to a named agent.  All agents observe
    and act simultaneously each step.  Rewards combine individual performance
    with shared team objectives.

    Usage (with PettingZoo)::

        env = SC2ParallelEnv(agent_types=["zergling"]*4 + ["roach"]*2)
        observations, infos = env.reset()
        while env.agents:
            actions = {agent: env.action_space(agent).sample() for agent in env.agents}
            obs, rewards, terms, truncs, infos = env.step(actions)

    Usage (standalone)::

        env = SC2ParallelEnv()
        obs, infos = env.reset()
        actions = {a: env.action_spaces[a].sample() for a in env.agents}
        obs, rewards, terms, truncs, infos = env.step(actions)
    """

    metadata = {
        "render_modes": ["ansi", "human"],
        "name": "sc2_parallel_v1",
        "is_parallelizable": True,
    }

    def __init__(
        self,
        agent_types: Optional[List[str]] = None,
        n_enemies: int = 6,
        max_steps: int = 200,
        map_size: float = MAP_SIZE,
        continuous_actions: bool = False,
        reward_config: Optional[RewardConfig] = None,
        render_mode: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> None:
        if agent_types is None:
            agent_types = ["zergling"] * 4 + ["roach"] * 2

        self._agent_types = agent_types
        self._n_enemies = n_enemies
        self._max_steps = max_steps
        self._map_size = map_size
        self._continuous = continuous_actions
        self._reward_config = reward_config or RewardConfig()
        self.render_mode = render_mode

        self._rng = random.Random(seed)
        self._np_rng = np.random.RandomState(seed)

        # --- Agent registration ---
        self.possible_agents: List[str] = [
            f"{utype}_{i}" for i, utype in enumerate(agent_types)
        ]
        self.agents: List[str] = []

        # --- Spaces (keyed by agent name) ---
        self._action_space_cache: Dict[str, SC2ActionSpace] = {}
        for agent_name in self.possible_agents:
            utype = agent_name.rsplit("_", 1)[0]
            self._action_space_cache[agent_name] = SC2ActionSpace(
                unit_type=utype,
                continuous=continuous_actions,
            )

        # Runtime state
        self._units: Dict[str, _SimUnit] = {}
        self._enemies: List[_SimUnit] = []
        self._step_count = 0
        self._cumulative_rewards: Dict[str, float] = {}
        self._episode_stats: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # PettingZoo Parallel API methods
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Dict[str, Any]]]:
        """Reset the environment, spawn all units, return initial observations."""
        if seed is not None:
            self._rng = random.Random(seed)
            self._np_rng = np.random.RandomState(seed)

        self._step_count = 0
        self.agents = list(self.possible_agents)
        self._cumulative_rewards = {a: 0.0 for a in self.agents}

        # Spawn allied units
        self._units = {}
        for agent_name in self.possible_agents:
            utype = agent_name.rsplit("_", 1)[0]
            health_map = {
                "zergling": 35.0,
                "baneling": 30.0,
                "roach": 145.0,
                "hydralisk": 80.0,
                "mutalisk": 120.0,
                "ultralisk": 500.0,
                "infestor": 90.0,
                "corruptor": 200.0,
                "queen": 175.0,
                "overseer": 200.0,
            }
            dmg_map = {
                "zergling": 5.0,
                "baneling": 20.0,
                "roach": 16.0,
                "hydralisk": 12.0,
                "mutalisk": 9.0,
                "ultralisk": 35.0,
                "infestor": 0.0,
                "corruptor": 14.0,
                "queen": 8.0,
                "overseer": 0.0,
            }
            hp = health_map.get(utype, 50.0)
            self._units[agent_name] = _SimUnit(
                agent_id=agent_name,
                unit_type=utype,
                x=self._rng.uniform(10, 60),
                y=self._rng.uniform(10, 60),
                health=hp,
                max_health=hp,
                damage=dmg_map.get(utype, 10.0),
                team=0,
            )

        # Spawn enemies
        self._enemies = []
        for i in range(self._n_enemies):
            self._enemies.append(
                _SimUnit(
                    agent_id=f"enemy_{i}",
                    unit_type="roach",
                    x=self._rng.uniform(140, 190),
                    y=self._rng.uniform(140, 190),
                    health=145.0,
                    max_health=145.0,
                    damage=16.0,
                    team=1,
                )
            )

        self._episode_stats = {
            "total_damage_dealt": 0.0,
            "total_damage_taken": 0.0,
            "kills": 0,
            "deaths": 0,
        }

        observations = {a: self.observe(a) for a in self.agents}
        infos = {a: {} for a in self.agents}
        return observations, infos

    def step(
        self,
        actions: Dict[str, np.ndarray],
    ) -> Tuple[
        Dict[str, np.ndarray],
        Dict[str, float],
        Dict[str, bool],
        Dict[str, bool],
        Dict[str, Dict[str, Any]],
    ]:
        """Execute one parallel step for all agents."""
        self._step_count += 1

        rewards: Dict[str, float] = {a: 0.0 for a in self.agents}
        terminations: Dict[str, bool] = {a: False for a in self.agents}
        truncations: Dict[str, bool] = {a: False for a in self.agents}
        infos: Dict[str, Dict[str, Any]] = {a: {} for a in self.agents}

        # --- Process actions for each alive agent ---
        agent_damage: Dict[str, float] = {}
        agent_taken: Dict[str, float] = {}
        agent_kills: Dict[str, int] = {}
        agent_died: Dict[str, bool] = {}

        alive_enemies = [e for e in self._enemies if e.is_alive]

        for agent_name in list(self.agents):
            unit = self._units[agent_name]
            if not unit.is_alive:
                continue

            action = actions.get(agent_name)
            if action is None:
                action = self._action_space_cache[agent_name].no_op()

            dmg_dealt = 0.0
            kills = 0

            if self._continuous:
                # Continuous: action[0] = move_dx, action[1] = move_dy,
                # action[2] = attack_strength
                if len(action) >= 2:
                    unit.x = float(np.clip(unit.x + action[0] * 5.0, 0, self._map_size))
                    unit.y = float(np.clip(unit.y + action[1] * 5.0, 0, self._map_size))
                if len(action) >= 3 and action[2] > 0.0 and alive_enemies:
                    # Attack nearest enemy
                    target = min(
                        alive_enemies,
                        key=lambda e: (e.x - unit.x) ** 2 + (e.y - unit.y) ** 2,
                    )
                    dist = math.sqrt(
                        (target.x - unit.x) ** 2 + (target.y - unit.y) ** 2
                    )
                    if dist <= unit.attack_range:
                        actual = target.take_damage(
                            unit.damage * float(np.clip(action[2], 0, 1))
                        )
                        dmg_dealt += actual
                        if not target.is_alive:
                            kills += 1
            else:
                # Discrete action (one-hot or index)
                if isinstance(action, np.ndarray) and action.ndim > 0:
                    act_idx = int(np.argmax(action))
                else:
                    act_idx = int(action)

                move_speed = 5.0
                if act_idx == 1:  # move_up
                    unit.y = min(self._map_size, unit.y + move_speed)
                elif act_idx == 2:  # move_down
                    unit.y = max(0, unit.y - move_speed)
                elif act_idx == 3:  # move_left
                    unit.x = max(0, unit.x - move_speed)
                elif act_idx == 4:  # move_right
                    unit.x = min(self._map_size, unit.x + move_speed)
                elif act_idx == 5 and alive_enemies:  # attack_closest
                    target = min(
                        alive_enemies,
                        key=lambda e: (e.x - unit.x) ** 2 + (e.y - unit.y) ** 2,
                    )
                    dist = math.sqrt(
                        (target.x - unit.x) ** 2 + (target.y - unit.y) ** 2
                    )
                    if dist <= unit.attack_range:
                        actual = target.take_damage(unit.damage)
                        dmg_dealt += actual
                        if not target.is_alive:
                            kills += 1

            agent_damage[agent_name] = dmg_dealt
            agent_kills[agent_name] = kills
            agent_died[agent_name] = False
            self._episode_stats["total_damage_dealt"] += dmg_dealt
            self._episode_stats["kills"] += kills

        # --- Enemy actions (simple: attack nearest alive ally) ---
        alive_allies = [u for u in self._units.values() if u.is_alive]
        for enemy in alive_enemies:
            if not alive_allies:
                break
            target = min(
                alive_allies,
                key=lambda u: (u.x - enemy.x) ** 2 + (u.y - enemy.y) ** 2,
            )
            dist = math.sqrt((target.x - enemy.x) ** 2 + (target.y - enemy.y) ** 2)
            if dist <= enemy.attack_range:
                actual = target.take_damage(enemy.damage)
                self._episode_stats["total_damage_taken"] += actual
                if target.agent_id in agent_taken:
                    agent_taken[target.agent_id] += actual
                else:
                    agent_taken[target.agent_id] = actual
                if not target.is_alive:
                    agent_died[target.agent_id] = True
                    self._episode_stats["deaths"] += 1

        # --- Compute rewards ---
        n_alive = sum(1 for u in self._units.values() if u.is_alive)
        alive_enemies_after = [e for e in self._enemies if e.is_alive]
        team_objective = float(self._n_enemies - len(alive_enemies_after)) / max(
            self._n_enemies, 1
        )

        # Check win/lose
        all_enemies_dead = len(alive_enemies_after) == 0
        all_allies_dead = n_alive == 0

        for agent_name in list(self.agents):
            dd = agent_damage.get(agent_name, 0.0)
            dt = agent_taken.get(agent_name, 0.0)
            k = agent_kills.get(agent_name, 0)
            died = agent_died.get(agent_name, False)

            _, blended = self._reward_config.compute_agent_reward(
                damage_dealt=dd,
                damage_taken=dt,
                kills=k,
                died=died,
                team_objective_score=team_objective,
                n_alive_allies=max(n_alive, 1),
            )

            if all_enemies_dead:
                blended += self._reward_config.win_reward
            elif all_allies_dead:
                blended += self._reward_config.lose_penalty

            rewards[agent_name] = blended
            self._cumulative_rewards[agent_name] += blended

            # Termination: unit died or game over
            if died or all_enemies_dead or all_allies_dead:
                terminations[agent_name] = True

            # Truncation: max steps reached
            if self._step_count >= self._max_steps:
                truncations[agent_name] = True

            infos[agent_name] = {
                "damage_dealt": dd,
                "damage_taken": dt,
                "kills": k,
                "cumulative_reward": self._cumulative_rewards[agent_name],
            }

        # Remove dead or terminated agents
        self.agents = [
            a
            for a in self.agents
            if not terminations.get(a, False) and not truncations.get(a, False)
        ]

        observations = {a: self.observe(a) for a in self.agents}
        # Include terminal observations for removed agents
        removed = set(rewards.keys()) - set(self.agents)
        for a in removed:
            observations[a] = self.observe(a)

        return observations, rewards, terminations, truncations, infos

    def observe(self, agent: str) -> np.ndarray:
        """Return observation array for a single agent."""
        unit = self._units.get(agent)
        if unit is None or not unit.is_alive:
            utype = agent.rsplit("_", 1)[0]
            obs_dim = UNIT_OBS_DIM.get(utype, 20)
            return np.zeros(obs_dim, dtype=np.float32)

        # Compute relative enemy positions
        alive_enemies = [e for e in self._enemies if e.is_alive]
        # Sort by distance
        alive_enemies.sort(key=lambda e: (e.x - unit.x) ** 2 + (e.y - unit.y) ** 2)
        rel_enemy = np.zeros((5, 3), dtype=np.float32)
        for i, enemy in enumerate(alive_enemies[:5]):
            rel_enemy[i, 0] = (enemy.x - unit.x) / self._map_size
            rel_enemy[i, 1] = (enemy.y - unit.y) / self._map_size
            rel_enemy[i, 2] = enemy.normalised_health()

        nearby_allies = sum(
            1
            for u in self._units.values()
            if u.is_alive
            and u.agent_id != agent
            and math.sqrt((u.x - unit.x) ** 2 + (u.y - unit.y) ** 2) < 30.0
        )
        nearby_enemies = sum(
            1
            for e in self._enemies
            if e.is_alive
            and math.sqrt((e.x - unit.x) ** 2 + (e.y - unit.y) ** 2) < 30.0
        )

        obs = AgentObservation(
            agent_id=agent,
            unit_type=unit.unit_type,
            health=unit.normalised_health(),
            shield=0.0,
            energy=unit.energy / 200.0,
            pos_x=unit.x / self._map_size,
            pos_y=unit.y / self._map_size,
            cooldown=unit.cooldown,
            nearby_allies=nearby_allies,
            nearby_enemies=nearby_enemies,
            relative_enemy_positions=rel_enemy,
            is_alive=unit.is_alive,
        )
        return obs.to_array()

    def observation_space(self, agent: str) -> Any:
        """Return the observation space for an agent."""
        utype = agent.rsplit("_", 1)[0]
        obs_dim = UNIT_OBS_DIM.get(utype, 20)
        if _GYM_AVAILABLE:
            return spaces.Box(
                low=0.0,
                high=1.0,
                shape=(obs_dim,),
                dtype=np.float32,
            )
        return {"type": "Box", "low": 0.0, "high": 1.0, "shape": (obs_dim,)}

    def action_space(self, agent: str) -> Any:
        """Return the action space for an agent."""
        space_obj = self._action_space_cache.get(agent)
        if space_obj is None:
            utype = agent.rsplit("_", 1)[0]
            space_obj = SC2ActionSpace(unit_type=utype, continuous=self._continuous)
        if _GYM_AVAILABLE:
            gym_sp = space_obj.gym_space()
            if gym_sp is not None:
                return gym_sp
        return space_obj

    def render(self) -> Optional[str]:
        """Render the environment state as text."""
        if self.render_mode != "ansi" and self.render_mode != "human":
            return None

        lines = [f"=== SC2 Parallel Env  Step {self._step_count} ==="]
        lines.append(
            f"Alive allies: {sum(1 for u in self._units.values() if u.is_alive)}"
        )
        lines.append(f"Alive enemies: {sum(1 for e in self._enemies if e.is_alive)}")
        for name, unit in self._units.items():
            status = "ALIVE" if unit.is_alive else "DEAD"
            lines.append(
                f"  {name}: {status} hp={unit.health:.0f}/{unit.max_health:.0f} "
                f"pos=({unit.x:.1f}, {unit.y:.1f})"
            )
        output = "\n".join(lines)
        if self.render_mode == "human":
            print(output)
        return output

    def close(self) -> None:
        """Clean up resources."""
        self._units.clear()
        self._enemies.clear()
        self.agents.clear()

    def state(self) -> np.ndarray:
        """Return global state vector (for centralised critics)."""
        parts = []
        for name in self.possible_agents:
            unit = self._units.get(name)
            if unit is not None and unit.is_alive:
                parts.append(
                    np.array(
                        [
                            unit.x / self._map_size,
                            unit.y / self._map_size,
                            unit.normalised_health(),
                            1.0,
                        ],
                        dtype=np.float32,
                    )
                )
            else:
                parts.append(np.zeros(4, dtype=np.float32))
        for enemy in self._enemies:
            if enemy.is_alive:
                parts.append(
                    np.array(
                        [
                            enemy.x / self._map_size,
                            enemy.y / self._map_size,
                            enemy.normalised_health(),
                            1.0,
                        ],
                        dtype=np.float32,
                    )
                )
            else:
                parts.append(np.zeros(4, dtype=np.float32))
        return np.concatenate(parts)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def num_agents(self) -> int:
        return len(self.agents)

    @property
    def max_num_agents(self) -> int:
        return len(self.possible_agents)

    @property
    def action_spaces(self) -> Dict[str, SC2ActionSpace]:
        return dict(self._action_space_cache)

    def get_episode_stats(self) -> Dict[str, Any]:
        """Return accumulated episode statistics."""
        return dict(self._episode_stats)


# ===================================================================
# Demo
# ===================================================================


def demo(
    n_episodes: int = 3,
    max_steps: int = 50,
    agent_types: Optional[List[str]] = None,
    continuous: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Run a demonstration of the SC2 PettingZoo parallel environment.

    Args:
        n_episodes: Number of episodes to run.
        max_steps: Maximum steps per episode.
        agent_types: List of unit types for agents.
        continuous: Use continuous action space.
        verbose: Print step-by-step info.

    Returns:
        Dictionary with demo results.
    """
    if agent_types is None:
        agent_types = ["zergling"] * 4 + ["roach"] * 2

    env = SC2ParallelEnv(
        agent_types=agent_types,
        max_steps=max_steps,
        continuous_actions=continuous,
        render_mode="ansi" if verbose else None,
    )

    all_returns: List[float] = []

    for ep in range(n_episodes):
        obs, infos = env.reset(seed=42 + ep)
        episode_rewards: Dict[str, float] = {a: 0.0 for a in env.possible_agents}
        step = 0

        if verbose:
            print(f"\n{'='*60}")
            print(f" Episode {ep + 1}/{n_episodes}")
            print(f" Agents: {env.agents}")
            print(f"{'='*60}")

        while env.agents:
            # Random policy
            actions = {}
            for agent in env.agents:
                space = env._action_space_cache[agent]
                actions[agent] = space.sample()

            obs, rewards, terminations, truncations, infos = env.step(actions)

            for agent, r in rewards.items():
                episode_rewards[agent] = episode_rewards.get(agent, 0.0) + r

            step += 1
            if verbose and step % 10 == 0:
                rendered = env.render()
                if rendered:
                    print(rendered)

        ep_return = sum(episode_rewards.values())
        all_returns.append(ep_return)
        stats = env.get_episode_stats()

        if verbose:
            print(f"\n  Episode {ep+1} finished at step {step}")
            print(f"  Total return: {ep_return:.2f}")
            print(f"  Stats: {stats}")

    env.close()

    mean_return = float(np.mean(all_returns)) if all_returns else 0.0
    results = {
        "mean_return": mean_return,
        "all_returns": all_returns,
        "n_episodes": n_episodes,
        "agent_types": agent_types,
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f" PettingZoo SC2 Demo Complete")
        print(f" Mean return: {mean_return:.2f}")
        print(f"{'='*60}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 609: PettingZoo Multi-Agent Environment for SC2",
    )
    parser.add_argument("--episodes", type=int, default=3, help="Number of episodes")
    parser.add_argument(
        "--max-steps", type=int, default=50, help="Max steps per episode"
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        default=["zergling", "zergling", "zergling", "zergling", "roach", "roach"],
        choices=list(ZERG_UNIT_TYPES.keys()),
        help="Agent unit types",
    )
    parser.add_argument(
        "--continuous", action="store_true", help="Use continuous actions"
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if not args.quiet else logging.WARNING)
    result = demo(
        n_episodes=args.episodes,
        max_steps=args.max_steps,
        agent_types=args.agents,
        continuous=args.continuous,
        verbose=not args.quiet,
    )
    if not args.quiet:
        print(f"\nFinal mean return: {result['mean_return']:.2f}")


if __name__ == "__main__":
    main()

# Phase 609: PettingZoo registered
