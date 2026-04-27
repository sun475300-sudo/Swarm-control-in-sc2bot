"""
Phase 532: Gymnasium (OpenAI Gym)
SC2 Bot custom Gymnasium environment for RL training
"""

from __future__ import annotations
from typing import Any, Optional, SupportsFloat
import math
import random
from dataclasses import dataclass, field

try:
    import gymnasium as gym
    from gymnasium import spaces
    import numpy as np

    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False
    import math as np


# ─────────────────────────────────────────────
# Observation / Action spaces
# ─────────────────────────────────────────────

OBS_DIM = 16  # feature vector size
ACT_DIM = 7  # discrete actions

"""
Observation features:
0: minerals (normalized 0-1, max 1000)
1: gas (normalized, max 500)
2: supply (normalized, max 200)
3: max_supply (normalized, max 200)
4: workers (normalized, max 80)
5: army_supply (normalized, max 200)
6: frame (normalized, max 20000)
7: enemy_army_supply (normalized, max 200)
8: threat_level (0-1)
9: tech_level (0-1, 0=hatch 0.33=pool 0.66=lair 1=hive)
10: hatchery_count (normalized, max 5)
11: base_count (normalized, max 5)
12: queen_count (normalized, max 10)
13: upgrade_bitmask bit0 (speed)
14: upgrade_bitmask bit1 (carapace)
15: upgrade_bitmask bit2 (missile attacks)

Actions:
0: train_drone
1: train_zergling
2: train_roach
3: build_overlord
4: expand
5: attack_move
6: defend_base
"""


# ─────────────────────────────────────────────
# SC2 Gym Environment
# ─────────────────────────────────────────────


class SC2ZergEnv:
    """
    Gymnasium-compatible SC2 Zerg environment.
    Implements gymnasium.Env interface.
    """

    metadata = {"render_modes": ["ansi"]}

    if GYM_AVAILABLE:
        observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(OBS_DIM,),
            dtype="float32",
        )
        action_space = spaces.Discrete(ACT_DIM)

    def __init__(
        self,
        render_mode: Optional[str] = None,
        max_frames: int = 8000,
        enemy_aggression: float = 0.5,
    ):
        self.render_mode = render_mode
        self.max_frames = max_frames
        self.enemy_aggression = enemy_aggression
        self._reset_state()

    def _reset_state(self) -> None:
        self.minerals = 50
        self.gas = 0
        self.supply = 12
        self.max_supply = 14
        self.workers = 12
        self.army_supply = 0
        self.frame = 0
        self.enemy_army = 0
        self.threat = 0.0
        self.tech_level = 0.0
        self.hatcheries = 1
        self.bases = 1
        self.queens = 0
        self.upgrades = [False, False, False]
        self._win = False
        self._lose = False

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[list[float], dict]:
        if seed is not None:
            random.seed(seed)
        self._reset_state()
        return self._observe(), {"frame": 0}

    def step(self, action: int) -> tuple[list[float], float, bool, bool, dict]:
        self.frame += 1
        self._economy_tick()
        self._enemy_tick()
        reward = self._execute_action(action)
        reward += self._survival_reward()
        terminated = self._check_terminal()
        truncated = self.frame >= self.max_frames
        obs = self._observe()
        info = {
            "frame": self.frame,
            "minerals": self.minerals,
            "army": self.army_supply,
        }
        return obs, reward, terminated, truncated, info

    def _economy_tick(self) -> None:
        self.minerals += self.workers * 8 // 10
        if self.tech_level >= 0.33:
            self.gas += 3 * min(2, self.bases)
        self.gas = min(self.gas, 500)

    def _enemy_tick(self) -> None:
        # Enemy grows army over time
        if self.frame % 100 == 0:
            self.enemy_army += int(5 * self.enemy_aggression)
        # Random harassment
        if random.random() < 0.005 * self.enemy_aggression:
            lost = min(self.army_supply, random.randint(1, 5))
            self.army_supply -= lost
            self.supply -= lost
            self.threat = min(1.0, self.threat + 0.2)
        else:
            self.threat = max(0.0, self.threat - 0.01)

    def _execute_action(self, action: int) -> float:
        reward = 0.0
        if action == 0:  # train drone
            if self.minerals >= 50 and self.supply < self.max_supply:
                self.minerals -= 50
                self.workers += 1
                self.supply += 1
                reward = 0.3
        elif action == 1:  # train zergling
            if self.minerals >= 25 and self.supply + 1 <= self.max_supply:
                self.minerals -= 25
                self.army_supply += 1
                self.supply += 1
                reward = 0.2
        elif action == 2:  # train roach
            if (
                self.minerals >= 75
                and self.gas >= 25
                and self.supply + 2 <= self.max_supply
                and self.tech_level >= 0.33
            ):
                self.minerals -= 75
                self.gas -= 25
                self.army_supply += 2
                self.supply += 2
                reward = 0.5
        elif action == 3:  # build overlord
            if self.minerals >= 100:
                self.minerals -= 100
                self.max_supply += 8
                reward = 0.4
        elif action == 4:  # expand
            if self.minerals >= 300 and self.bases < 4:
                self.minerals -= 300
                self.bases += 1
                self.hatcheries += 1
                reward = 1.5
        elif action == 5:  # attack
            if self.army_supply >= self.enemy_army:
                reward = 3.0
                self.enemy_army = max(0, self.enemy_army - self.army_supply // 2)
                self._win = self.enemy_army == 0
            else:
                lost = self.army_supply // 2
                self.army_supply -= lost
                self.supply -= lost
                reward = -0.5
        elif action == 6:  # defend
            if self.threat > 0.5:
                reward = 0.3
            self.threat = max(0.0, self.threat - 0.3)
        return reward

    def _survival_reward(self) -> float:
        # Small reward for staying alive each step
        return 0.01 * (self.workers + self.army_supply) / 50.0

    def _check_terminal(self) -> bool:
        if self._win:
            return True
        if self.workers <= 0 and self.army_supply <= 0:
            self._lose = True
            return True
        return False

    def _observe(self) -> list[float]:
        def clip(v, mx):
            return max(0.0, min(1.0, v / mx))

        return [
            clip(self.minerals, 1000),
            clip(self.gas, 500),
            clip(self.supply, 200),
            clip(self.max_supply, 200),
            clip(self.workers, 80),
            clip(self.army_supply, 200),
            clip(self.frame, self.max_frames),
            clip(self.enemy_army, 200),
            self.threat,
            self.tech_level,
            clip(self.hatcheries, 5),
            clip(self.bases, 5),
            clip(self.queens, 10),
            float(self.upgrades[0]),
            float(self.upgrades[1]),
            float(self.upgrades[2]),
        ]

    def render(self) -> Optional[str]:
        if self.render_mode == "ansi":
            return (
                f"[F{self.frame:5d}] "
                f"Min:{self.minerals:4d} Gas:{self.gas:3d} "
                f"Supply:{self.supply:3d}/{self.max_supply:3d} "
                f"Workers:{self.workers:2d} Army:{self.army_supply:3d} "
                f"Threat:{self.threat:.2f}"
            )
        return None

    def close(self) -> None:
        pass


# ─────────────────────────────────────────────
# Random policy benchmark
# ─────────────────────────────────────────────


def benchmark_random_policy(episodes: int = 10) -> dict:
    results = []
    for ep in range(episodes):
        env = SC2ZergEnv(max_frames=2000)
        obs, _ = env.reset(seed=ep)
        total_reward = 0.0
        terminated = truncated = False
        while not (terminated or truncated):
            action = random.randint(0, ACT_DIM - 1)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
        results.append(
            {
                "episode": ep,
                "total_reward": total_reward,
                "frames": info["frame"],
                "final_army": info["army"],
            }
        )
    return {
        "episodes": episodes,
        "mean_reward": sum(r["total_reward"] for r in results) / episodes,
        "mean_frames": sum(r["frames"] for r in results) / episodes,
    }


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 532: Gymnasium — SC2 Zerg RL Environment")
    print(f"Gymnasium available: {GYM_AVAILABLE}")

    env = SC2ZergEnv(render_mode="ansi", max_frames=500)
    obs, info = env.reset(seed=42)
    print(f"Obs shape: {len(obs)} features")

    total_r = 0.0
    for step in range(500):
        action = random.randint(0, ACT_DIM - 1)
        obs, reward, terminated, truncated, info = env.step(action)
        total_r += reward
        if (step + 1) % 100 == 0:
            print(env.render())
        if terminated or truncated:
            break

    print(f"\nTotal reward: {total_r:.2f} | Final frame: {info['frame']}")

    stats = benchmark_random_policy(episodes=5)
    print(f"\nRandom policy benchmark: {stats}")
