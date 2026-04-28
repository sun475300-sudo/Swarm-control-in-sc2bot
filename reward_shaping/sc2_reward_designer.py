"""
Phase 613: Reward Shaping
SC2 Bot composable reward designer with PBRS, curiosity, and A/B testing.

Features:
  - 15+ reward components for SC2
  - Potential-Based Reward Shaping (PBRS)
  - Curiosity-driven intrinsic reward
  - Reward weight scheduling (shaped -> sparse annealing)
  - A/B testing framework for reward configs
  - Visualization of reward breakdowns
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import numpy as np

    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False


# ─────────────────────────────────────────────
# NumPy fallback helpers
# ─────────────────────────────────────────────


def _np_zeros(shape):
    if NP_AVAILABLE:
        return np.zeros(shape, dtype=np.float32)
    if isinstance(shape, int):
        return [0.0] * shape
    return [[0.0] * shape[1] for _ in range(shape[0])]


def _np_array(data):
    if NP_AVAILABLE:
        return np.array(data, dtype=np.float32)
    return list(data)


def _np_mean(arr):
    if NP_AVAILABLE:
        return float(np.mean(arr))
    if not arr:
        return 0.0
    return sum(arr) / len(arr)


def _np_std(arr):
    if NP_AVAILABLE:
        return float(np.std(arr))
    if len(arr) < 2:
        return 0.0
    m = _np_mean(arr)
    return math.sqrt(sum((x - m) ** 2 for x in arr) / len(arr))


def _np_clip(val, lo, hi):
    return max(lo, min(hi, val))


def _np_dot(a, b):
    if NP_AVAILABLE:
        return float(np.dot(a, b))
    return sum(x * y for x, y in zip(a, b))


# ─────────────────────────────────────────────
# SC2 Game State
# ─────────────────────────────────────────────


@dataclass
class SC2GameState:
    """Snapshot of SC2 game state for reward computation."""

    frame: int = 0
    minerals: float = 50.0
    gas: float = 0.0
    supply_used: int = 12
    supply_max: int = 14
    workers: int = 12
    army_supply: int = 0
    army_value: float = 0.0
    bases: int = 1
    tech_level: float = 0.0  # 0.0 - 1.0
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    units_produced: int = 0
    units_lost: int = 0
    units_killed: int = 0
    resources_gathered: float = 0.0
    map_control: float = 0.0  # 0.0 - 1.0 fraction of map controlled
    scouting_coverage: float = 0.0  # 0.0 - 1.0 fraction of map scouted
    apm: float = 0.0  # actions per minute
    upgrades_completed: int = 0
    enemy_army_value: float = 0.0
    enemy_bases: int = 1
    enemy_workers: int = 12
    income_rate: float = 0.0  # minerals per minute
    idle_workers: int = 0
    production_facilities: int = 1
    creep_spread: float = 0.0  # 0.0 - 1.0
    queen_energy: float = 0.0  # avg queen energy

    def to_vector(self) -> list:
        """Convert to feature vector for potential function input."""
        return [
            self.minerals / 1000.0,
            self.gas / 500.0,
            self.supply_used / 200.0,
            self.supply_max / 200.0,
            self.workers / 80.0,
            self.army_supply / 200.0,
            self.army_value / 5000.0,
            self.bases / 5.0,
            self.tech_level,
            self.damage_dealt / 5000.0,
            self.damage_taken / 5000.0,
            self.units_produced / 200.0,
            self.units_lost / 100.0,
            self.units_killed / 100.0,
            self.resources_gathered / 20000.0,
            self.map_control,
            self.scouting_coverage,
            min(1.0, self.apm / 300.0),
            self.upgrades_completed / 10.0,
            self.enemy_army_value / 5000.0,
            self.enemy_bases / 5.0,
            self.income_rate / 2000.0,
            self.idle_workers / 20.0,
            self.production_facilities / 10.0,
            self.creep_spread,
            self.queen_energy / 200.0,
            self.frame / 20000.0,
        ]

    def state_hash(self) -> str:
        """Discretized hash for curiosity counting."""
        discretized = tuple(
            int(v * 10)
            for v in [
                self.minerals / 200.0,
                self.gas / 100.0,
                self.supply_used / 20.0,
                self.army_value / 500.0,
                self.bases,
                self.tech_level * 5,
                self.map_control * 5,
                self.frame / 2000.0,
            ]
        )
        return hashlib.md5(str(discretized).encode()).hexdigest()[:12]


# ─────────────────────────────────────────────
# Reward Components
# ─────────────────────────────────────────────


class RewardComponentType(str, Enum):
    DAMAGE_DEALT = "damage_dealt"
    DAMAGE_TAKEN = "damage_taken"
    UNITS_PRODUCED = "units_produced"
    UNITS_LOST = "units_lost"
    UNITS_KILLED = "units_killed"
    RESOURCES_GATHERED = "resources_gathered"
    TECH_PROGRESSION = "tech_progression"
    MAP_CONTROL = "map_control"
    ARMY_VALUE = "army_value"
    SUPPLY_EFFICIENCY = "supply_efficiency"
    APM_REWARD = "apm_reward"
    SCOUTING_COVERAGE = "scouting_coverage"
    EXPANSION_TIMING = "expansion_timing"
    WORKER_SATURATION = "worker_saturation"
    INCOME_RATE = "income_rate"
    CREEP_SPREAD = "creep_spread"
    QUEEN_ENERGY = "queen_energy"
    IDLE_WORKERS_PENALTY = "idle_workers_penalty"
    WIN_LOSS = "win_loss"


@dataclass
class RewardComponent:
    """Single composable reward function component."""

    name: RewardComponentType
    weight: float = 1.0
    clip_min: float = -10.0
    clip_max: float = 10.0
    enabled: bool = True
    description: str = ""
    history: List[float] = field(default_factory=list)

    def compute(self, prev: SC2GameState, curr: SC2GameState) -> float:
        """Compute raw reward for this component."""
        raise NotImplementedError

    def weighted_value(self, prev: SC2GameState, curr: SC2GameState) -> float:
        """Compute weighted, clipped reward."""
        if not self.enabled:
            return 0.0
        raw = self.compute(prev, curr)
        clipped = _np_clip(raw, self.clip_min, self.clip_max)
        val = clipped * self.weight
        self.history.append(val)
        if len(self.history) > 500:
            self.history = self.history[-500:]
        return val

    def stats(self) -> Dict[str, Any]:
        """Statistics about this component's contribution."""
        if not self.history:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "count": 0}
        return {
            "mean": _np_mean(self.history),
            "std": _np_std(self.history),
            "min": min(self.history),
            "max": max(self.history),
            "count": len(self.history),
        }


# ─── Concrete reward components ───


class DamageDealtReward(RewardComponent):
    def __init__(self, weight=1.0):
        super().__init__(
            RewardComponentType.DAMAGE_DEALT,
            weight,
            description="Reward for damage dealt to enemy units",
        )

    def compute(self, prev, curr):
        delta = curr.damage_dealt - prev.damage_dealt
        return delta / 500.0


class DamageTakenReward(RewardComponent):
    def __init__(self, weight=-0.8):
        super().__init__(
            RewardComponentType.DAMAGE_TAKEN,
            weight,
            description="Penalty for damage taken from enemy",
        )

    def compute(self, prev, curr):
        delta = curr.damage_taken - prev.damage_taken
        return delta / 500.0


class UnitsProducedReward(RewardComponent):
    def __init__(self, weight=0.3):
        super().__init__(
            RewardComponentType.UNITS_PRODUCED,
            weight,
            description="Reward for producing units",
        )

    def compute(self, prev, curr):
        delta = curr.units_produced - prev.units_produced
        return float(delta)


class UnitsLostReward(RewardComponent):
    def __init__(self, weight=-0.5):
        super().__init__(
            RewardComponentType.UNITS_LOST,
            weight,
            description="Penalty for losing units",
        )

    def compute(self, prev, curr):
        delta = curr.units_lost - prev.units_lost
        return float(delta)


class UnitsKilledReward(RewardComponent):
    def __init__(self, weight=0.6):
        super().__init__(
            RewardComponentType.UNITS_KILLED,
            weight,
            description="Reward for killing enemy units",
        )

    def compute(self, prev, curr):
        delta = curr.units_killed - prev.units_killed
        return float(delta)


class ResourcesGatheredReward(RewardComponent):
    def __init__(self, weight=0.2):
        super().__init__(
            RewardComponentType.RESOURCES_GATHERED,
            weight,
            description="Reward for total resources gathered",
        )

    def compute(self, prev, curr):
        delta = curr.resources_gathered - prev.resources_gathered
        return delta / 500.0


class TechProgressionReward(RewardComponent):
    def __init__(self, weight=1.0):
        super().__init__(
            RewardComponentType.TECH_PROGRESSION,
            weight,
            description="Reward for tech upgrades",
        )

    def compute(self, prev, curr):
        return (curr.tech_level - prev.tech_level) * 5.0


class MapControlReward(RewardComponent):
    def __init__(self, weight=0.5):
        super().__init__(
            RewardComponentType.MAP_CONTROL,
            weight,
            description="Reward for map control percentage",
        )

    def compute(self, prev, curr):
        return (curr.map_control - prev.map_control) * 3.0


class ArmyValueReward(RewardComponent):
    def __init__(self, weight=0.4):
        super().__init__(
            RewardComponentType.ARMY_VALUE,
            weight,
            description="Reward for building army value",
        )

    def compute(self, prev, curr):
        delta = curr.army_value - prev.army_value
        return delta / 1000.0


class SupplyEfficiencyReward(RewardComponent):
    def __init__(self, weight=0.3):
        super().__init__(
            RewardComponentType.SUPPLY_EFFICIENCY,
            weight,
            description="Reward for efficient supply usage",
        )

    def compute(self, prev, curr):
        if curr.supply_max == 0:
            return 0.0
        ratio = curr.supply_used / curr.supply_max
        # Optimal is 85-95%
        if 0.85 <= ratio <= 0.95:
            return 1.0
        elif ratio > 0.95:
            return -0.5  # supply blocked
        else:
            return ratio - 0.85


class APMReward(RewardComponent):
    def __init__(self, weight=0.1):
        super().__init__(
            RewardComponentType.APM_REWARD,
            weight,
            description="Reward for maintaining reasonable APM",
        )

    def compute(self, prev, curr):
        # Diminishing returns above 150 APM
        if curr.apm < 50:
            return -0.5
        elif curr.apm <= 200:
            return curr.apm / 200.0
        else:
            return 1.0 + 0.1 * math.log(curr.apm / 200.0)


class ScoutingCoverageReward(RewardComponent):
    def __init__(self, weight=0.4):
        super().__init__(
            RewardComponentType.SCOUTING_COVERAGE,
            weight,
            description="Reward for scouting the map",
        )

    def compute(self, prev, curr):
        delta = curr.scouting_coverage - prev.scouting_coverage
        return delta * 5.0


class ExpansionTimingReward(RewardComponent):
    def __init__(self, weight=0.8):
        super().__init__(
            RewardComponentType.EXPANSION_TIMING,
            weight,
            description="Reward for well-timed expansions",
        )

    def compute(self, prev, curr):
        if curr.bases > prev.bases:
            # Reward if workers are saturated
            saturation = curr.workers / max(1, (curr.bases - 1) * 16)
            if saturation >= 0.8:
                return 2.0  # good timing
            elif saturation >= 0.5:
                return 1.0  # okay timing
            else:
                return 0.2  # too early
        return 0.0


class WorkerSaturationReward(RewardComponent):
    def __init__(self, weight=0.5):
        super().__init__(
            RewardComponentType.WORKER_SATURATION,
            weight,
            description="Reward for optimal worker count per base",
        )

    def compute(self, prev, curr):
        ideal = curr.bases * 16
        if ideal == 0:
            return 0.0
        ratio = curr.workers / ideal
        if 0.9 <= ratio <= 1.1:
            return 1.0
        elif ratio < 0.9:
            return ratio
        else:
            return max(0.0, 2.0 - ratio)  # over-saturation penalty


class IncomeRateReward(RewardComponent):
    def __init__(self, weight=0.3):
        super().__init__(
            RewardComponentType.INCOME_RATE,
            weight,
            description="Reward for mineral income rate",
        )

    def compute(self, prev, curr):
        delta = curr.income_rate - prev.income_rate
        return delta / 500.0


class CreepSpreadReward(RewardComponent):
    def __init__(self, weight=0.2):
        super().__init__(
            RewardComponentType.CREEP_SPREAD,
            weight,
            description="Reward for creep spread (Zerg)",
        )

    def compute(self, prev, curr):
        return (curr.creep_spread - prev.creep_spread) * 5.0


class QueenEnergyReward(RewardComponent):
    def __init__(self, weight=0.15):
        super().__init__(
            RewardComponentType.QUEEN_ENERGY,
            weight,
            description="Penalty for high unused queen energy",
        )

    def compute(self, prev, curr):
        # Penalize unused queen energy (should inject/spread creep)
        if curr.queen_energy > 50:
            return -(curr.queen_energy - 50) / 150.0
        return 0.1  # small reward for using energy


class IdleWorkersPenalty(RewardComponent):
    def __init__(self, weight=-0.4):
        super().__init__(
            RewardComponentType.IDLE_WORKERS_PENALTY,
            weight,
            description="Penalty for idle workers",
        )

    def compute(self, prev, curr):
        return float(curr.idle_workers)


class WinLossReward(RewardComponent):
    def __init__(self, weight=10.0):
        super().__init__(
            RewardComponentType.WIN_LOSS,
            weight,
            description="Sparse reward for game outcome",
        )

    def compute(self, prev, curr):
        # Called externally with game result
        return 0.0


# ─────────────────────────────────────────────
# Potential-Based Reward Shaping (PBRS)
# ─────────────────────────────────────────────


class PotentialFunction:
    """
    Potential-based reward shaping (Ng et al., 1999).
    F(s, s') = gamma * phi(s') - phi(s)
    Guarantees optimal policy invariance.
    """

    def __init__(self, gamma: float = 0.99, weights: Optional[List[float]] = None):
        self.gamma = gamma
        # Weights for potential function over state features
        default_weights = [
            0.1,  # minerals
            0.15,  # gas
            0.05,  # supply_used
            0.05,  # supply_max
            0.3,  # workers
            0.2,  # army_supply
            0.4,  # army_value
            0.5,  # bases
            0.6,  # tech_level
            0.3,  # damage_dealt
            -0.2,  # damage_taken
            0.15,  # units_produced
            -0.3,  # units_lost
            0.35,  # units_killed
            0.2,  # resources_gathered
            0.5,  # map_control
            0.3,  # scouting
            0.05,  # apm
            0.4,  # upgrades
            -0.3,  # enemy_army
            -0.4,  # enemy_bases
            0.2,  # income
            -0.1,  # idle_workers
            0.15,  # production_facilities
            0.2,  # creep
            -0.05,  # queen_energy
            0.0,  # frame (time-neutral)
        ]
        self.weights = weights if weights is not None else default_weights

    def phi(self, state: SC2GameState) -> float:
        """Compute potential value for a state."""
        features = state.to_vector()
        n = min(len(features), len(self.weights))
        return _np_dot(features[:n], self.weights[:n])

    def shaping_reward(self, prev: SC2GameState, curr: SC2GameState) -> float:
        """
        F(s, s') = gamma * phi(s') - phi(s)
        This is guaranteed to preserve optimal policy (PBRS theorem).
        """
        return self.gamma * self.phi(curr) - self.phi(prev)


# ─────────────────────────────────────────────
# Curiosity-Driven Intrinsic Reward
# ─────────────────────────────────────────────


class CuriosityReward:
    """
    Count-based intrinsic reward for exploration.
    Reward inversely proportional to state visitation count.
    """

    def __init__(self, beta: float = 0.1, decay: float = 0.999, max_count: int = 1000):
        self.beta = beta
        self.decay = decay
        self.max_count = max_count
        self.visit_counts: Dict[str, int] = collections.defaultdict(int)
        self.total_visits = 0

    def compute(self, state: SC2GameState) -> float:
        """Compute curiosity reward: beta / sqrt(N(s))."""
        h = state.state_hash()
        self.visit_counts[h] += 1
        self.total_visits += 1
        count = self.visit_counts[h]
        return self.beta / math.sqrt(count)

    def decay_counts(self):
        """Apply decay to all visit counts for non-stationarity."""
        for key in self.visit_counts:
            self.visit_counts[key] = max(1, int(self.visit_counts[key] * self.decay))

    def unique_states(self) -> int:
        return len(self.visit_counts)

    def stats(self) -> Dict[str, Any]:
        counts = list(self.visit_counts.values())
        return {
            "unique_states": self.unique_states(),
            "total_visits": self.total_visits,
            "avg_count": _np_mean(counts) if counts else 0.0,
            "max_count": max(counts) if counts else 0,
            "min_count": min(counts) if counts else 0,
        }


# ─────────────────────────────────────────────
# Reward Normalizer
# ─────────────────────────────────────────────


class RewardNormalizer:
    """
    Running mean/variance normalization with clipping.
    Uses Welford's online algorithm for numerical stability.
    """

    def __init__(self, clip_range: float = 5.0, epsilon: float = 1e-8):
        self.clip_range = clip_range
        self.epsilon = epsilon
        self.mean = 0.0
        self.var = 1.0
        self.count = 0
        self._m2 = 0.0

    def update(self, value: float):
        """Update running statistics."""
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self._m2 += delta * delta2
        self.var = self._m2 / max(1, self.count) + self.epsilon

    def normalize(self, value: float) -> float:
        """Normalize and clip value."""
        self.update(value)
        normalized = (value - self.mean) / math.sqrt(self.var)
        return _np_clip(normalized, -self.clip_range, self.clip_range)

    def stats(self) -> Dict[str, float]:
        return {
            "mean": self.mean,
            "std": math.sqrt(self.var),
            "count": self.count,
        }


# ─────────────────────────────────────────────
# Reward Weight Scheduler
# ─────────────────────────────────────────────


class RewardWeightScheduler:
    """
    Schedules reward weights to anneal from fully-shaped to sparse rewards.
    Supports linear, cosine, and exponential schedules.
    """

    def __init__(
        self,
        total_steps: int = 100_000,
        schedule_type: str = "cosine",
        warmup_fraction: float = 0.1,
        min_shaping_weight: float = 0.0,
    ):
        self.total_steps = total_steps
        self.schedule_type = schedule_type
        self.warmup_steps = int(total_steps * warmup_fraction)
        self.min_shaping_weight = min_shaping_weight
        self.current_step = 0

    def step(self) -> float:
        """Advance one step and return current shaping weight [0,1]."""
        self.current_step += 1
        return self.get_weight()

    def get_weight(self) -> float:
        """Get current shaping weight (1.0 = fully shaped, 0.0 = sparse only)."""
        if self.current_step <= self.warmup_steps:
            return 1.0

        progress = (self.current_step - self.warmup_steps) / max(
            1, self.total_steps - self.warmup_steps
        )
        progress = min(1.0, progress)

        if self.schedule_type == "linear":
            w = 1.0 - progress
        elif self.schedule_type == "cosine":
            w = 0.5 * (1.0 + math.cos(math.pi * progress))
        elif self.schedule_type == "exponential":
            w = math.exp(-3.0 * progress)
        else:
            w = 1.0 - progress

        return max(self.min_shaping_weight, w)

    def stats(self) -> Dict[str, Any]:
        return {
            "step": self.current_step,
            "total_steps": self.total_steps,
            "weight": self.get_weight(),
            "schedule": self.schedule_type,
            "progress": f"{self.current_step / self.total_steps:.1%}",
        }


# ─────────────────────────────────────────────
# Reward Configuration
# ─────────────────────────────────────────────


@dataclass
class RewardConfig:
    """Complete reward configuration for A/B testing."""

    name: str = "default"
    component_weights: Dict[str, float] = field(default_factory=dict)
    use_pbrs: bool = True
    pbrs_gamma: float = 0.99
    use_curiosity: bool = True
    curiosity_beta: float = 0.1
    normalize: bool = True
    clip_range: float = 5.0
    schedule_type: str = "cosine"
    schedule_steps: int = 100_000
    sparse_weight: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "component_weights": self.component_weights,
            "use_pbrs": self.use_pbrs,
            "use_curiosity": self.use_curiosity,
            "curiosity_beta": self.curiosity_beta,
            "normalize": self.normalize,
            "schedule_type": self.schedule_type,
        }


# Preset configurations for A/B testing
REWARD_PRESETS: Dict[str, RewardConfig] = {
    "aggressive": RewardConfig(
        name="aggressive",
        component_weights={
            "damage_dealt": 2.0,
            "units_killed": 1.5,
            "army_value": 1.0,
            "damage_taken": -0.5,
            "map_control": 0.8,
            "resources_gathered": 0.1,
            "worker_saturation": 0.2,
        },
        use_pbrs=True,
        use_curiosity=False,
        schedule_type="linear",
    ),
    "economic": RewardConfig(
        name="economic",
        component_weights={
            "resources_gathered": 2.0,
            "worker_saturation": 1.5,
            "expansion_timing": 1.2,
            "income_rate": 1.0,
            "supply_efficiency": 0.8,
            "tech_progression": 0.5,
            "idle_workers_penalty": -1.0,
        },
        use_pbrs=True,
        use_curiosity=True,
        curiosity_beta=0.05,
        schedule_type="cosine",
    ),
    "balanced": RewardConfig(
        name="balanced",
        component_weights={
            "damage_dealt": 1.0,
            "damage_taken": -0.8,
            "units_produced": 0.3,
            "units_lost": -0.5,
            "units_killed": 0.6,
            "resources_gathered": 0.5,
            "tech_progression": 0.8,
            "map_control": 0.5,
            "army_value": 0.4,
            "supply_efficiency": 0.3,
            "scouting_coverage": 0.4,
            "expansion_timing": 0.7,
            "worker_saturation": 0.5,
            "income_rate": 0.3,
        },
        use_pbrs=True,
        use_curiosity=True,
        curiosity_beta=0.1,
        schedule_type="cosine",
    ),
    "sparse_only": RewardConfig(
        name="sparse_only",
        component_weights={},
        use_pbrs=False,
        use_curiosity=False,
        normalize=False,
        sparse_weight=20.0,
    ),
    "curiosity_heavy": RewardConfig(
        name="curiosity_heavy",
        component_weights={
            "scouting_coverage": 1.0,
            "map_control": 0.8,
            "tech_progression": 0.5,
        },
        use_pbrs=False,
        use_curiosity=True,
        curiosity_beta=0.5,
        schedule_type="exponential",
    ),
}


# ─────────────────────────────────────────────
# SC2 Reward Designer
# ─────────────────────────────────────────────


class SC2RewardDesigner:
    """
    Composable reward function designer for StarCraft II RL.

    Combines:
    - 15+ domain-specific reward components
    - Potential-Based Reward Shaping (PBRS)
    - Curiosity-driven intrinsic motivation
    - Reward normalization and clipping
    - Weight annealing from shaped to sparse
    """

    def __init__(self, config: Optional[RewardConfig] = None):
        self.config = config or RewardConfig()

        # Build reward components
        self.components: Dict[str, RewardComponent] = self._build_components()

        # PBRS
        self.pbrs = (
            PotentialFunction(gamma=self.config.pbrs_gamma)
            if self.config.use_pbrs
            else None
        )

        # Curiosity
        self.curiosity = (
            CuriosityReward(beta=self.config.curiosity_beta)
            if self.config.use_curiosity
            else None
        )

        # Normalizer
        self.normalizer = (
            RewardNormalizer(clip_range=self.config.clip_range)
            if self.config.normalize
            else None
        )

        # Scheduler
        self.scheduler = RewardWeightScheduler(
            total_steps=self.config.schedule_steps,
            schedule_type=self.config.schedule_type,
        )

        # Tracking
        self.total_reward_history: List[float] = []
        self.component_history: Dict[str, List[float]] = collections.defaultdict(list)
        self.pbrs_history: List[float] = []
        self.curiosity_history: List[float] = []
        self.sparse_history: List[float] = []
        self.shaping_weight_history: List[float] = []
        self.steps = 0

    def _build_components(self) -> Dict[str, RewardComponent]:
        """Instantiate all reward components with configured weights."""
        component_classes = {
            "damage_dealt": DamageDealtReward,
            "damage_taken": DamageTakenReward,
            "units_produced": UnitsProducedReward,
            "units_lost": UnitsLostReward,
            "units_killed": UnitsKilledReward,
            "resources_gathered": ResourcesGatheredReward,
            "tech_progression": TechProgressionReward,
            "map_control": MapControlReward,
            "army_value": ArmyValueReward,
            "supply_efficiency": SupplyEfficiencyReward,
            "apm_reward": APMReward,
            "scouting_coverage": ScoutingCoverageReward,
            "expansion_timing": ExpansionTimingReward,
            "worker_saturation": WorkerSaturationReward,
            "income_rate": IncomeRateReward,
            "creep_spread": CreepSpreadReward,
            "queen_energy": QueenEnergyReward,
            "idle_workers_penalty": IdleWorkersPenalty,
        }

        components = {}
        cw = self.config.component_weights

        for name, cls in component_classes.items():
            comp = cls()
            if name in cw:
                comp.weight = cw[name]
                comp.enabled = True
            elif cw:
                # If weights specified, disable unmentioned components
                comp.enabled = False
            components[name] = comp

        return components

    def compute_reward(
        self,
        prev_state: SC2GameState,
        curr_state: SC2GameState,
        game_result: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compute total reward from all sources.

        Args:
            prev_state: Previous game state
            curr_state: Current game state
            game_result: Optional sparse game result (+1 win, -1 loss, None ongoing)

        Returns:
            Dictionary with total reward and breakdown
        """
        self.steps += 1
        shaping_weight = self.scheduler.step()

        # 1. Component rewards
        component_rewards: Dict[str, float] = {}
        shaped_total = 0.0
        for name, comp in self.components.items():
            val = comp.weighted_value(prev_state, curr_state)
            component_rewards[name] = val
            shaped_total += val

        # 2. PBRS
        pbrs_reward = 0.0
        if self.pbrs is not None:
            pbrs_reward = self.pbrs.shaping_reward(prev_state, curr_state)
            shaped_total += pbrs_reward

        # 3. Curiosity
        curiosity_reward = 0.0
        if self.curiosity is not None:
            curiosity_reward = self.curiosity.compute(curr_state)
            shaped_total += curiosity_reward

        # 4. Sparse reward
        sparse_reward = 0.0
        if game_result is not None:
            sparse_reward = game_result * self.config.sparse_weight

        # 5. Blend shaped and sparse using schedule
        total = shaping_weight * shaped_total + sparse_reward

        # 6. Normalize
        if self.normalizer is not None:
            total = self.normalizer.normalize(total)

        # Track history
        self.total_reward_history.append(total)
        for name, val in component_rewards.items():
            self.component_history[name].append(val)
        self.pbrs_history.append(pbrs_reward)
        self.curiosity_history.append(curiosity_reward)
        self.sparse_history.append(sparse_reward)
        self.shaping_weight_history.append(shaping_weight)

        # Trim histories
        max_hist = 2000
        if len(self.total_reward_history) > max_hist:
            self.total_reward_history = self.total_reward_history[-max_hist:]
            self.pbrs_history = self.pbrs_history[-max_hist:]
            self.curiosity_history = self.curiosity_history[-max_hist:]
            self.sparse_history = self.sparse_history[-max_hist:]
            self.shaping_weight_history = self.shaping_weight_history[-max_hist:]
            for k in self.component_history:
                self.component_history[k] = self.component_history[k][-max_hist:]

        return {
            "total": total,
            "shaped": shaped_total,
            "sparse": sparse_reward,
            "pbrs": pbrs_reward,
            "curiosity": curiosity_reward,
            "shaping_weight": shaping_weight,
            "components": component_rewards,
        }

    def compute_game_end_reward(
        self,
        prev_state: SC2GameState,
        curr_state: SC2GameState,
        won: bool,
    ) -> Dict[str, Any]:
        """Convenience: compute reward at game end with win/loss signal."""
        result = 1.0 if won else -1.0
        return self.compute_reward(prev_state, curr_state, game_result=result)

    def set_component_weight(self, name: str, weight: float):
        """Dynamically adjust a component's weight."""
        if name in self.components:
            self.components[name].weight = weight
            self.components[name].enabled = True

    def disable_component(self, name: str):
        """Disable a reward component."""
        if name in self.components:
            self.components[name].enabled = False

    def enable_component(self, name: str):
        """Enable a reward component."""
        if name in self.components:
            self.components[name].enabled = True

    def component_contributions(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each reward component."""
        result = {}
        for name, comp in self.components.items():
            if comp.enabled:
                result[name] = {
                    "weight": comp.weight,
                    **comp.stats(),
                }
        if self.pbrs:
            result["pbrs"] = {
                "weight": "auto",
                "mean": _np_mean(self.pbrs_history) if self.pbrs_history else 0.0,
                "std": _np_std(self.pbrs_history) if self.pbrs_history else 0.0,
                "count": len(self.pbrs_history),
            }
        if self.curiosity:
            result["curiosity"] = {
                "weight": self.config.curiosity_beta,
                **self.curiosity.stats(),
            }
        return result

    def visualize_contributions(self, last_n: int = 100) -> str:
        """
        ASCII visualization of reward component contributions.
        Shows relative magnitude of each component.
        """
        lines = []
        lines.append("=" * 70)
        lines.append("  Reward Component Contributions (last {} steps)".format(last_n))
        lines.append("=" * 70)

        contributions = {}
        for name, comp in self.components.items():
            if comp.enabled and comp.history:
                recent = comp.history[-last_n:]
                contributions[name] = _np_mean(recent)

        if self.pbrs_history:
            contributions["pbrs"] = _np_mean(self.pbrs_history[-last_n:])
        if self.curiosity_history:
            contributions["curiosity"] = _np_mean(self.curiosity_history[-last_n:])

        if not contributions:
            lines.append("  (no data)")
            return "\n".join(lines)

        max_abs = max(abs(v) for v in contributions.values()) or 1.0
        bar_width = 40

        # Sort by absolute contribution
        sorted_items = sorted(
            contributions.items(), key=lambda x: abs(x[1]), reverse=True
        )
        for name, val in sorted_items:
            norm = val / max_abs
            bar_len = int(abs(norm) * bar_width)
            if val >= 0:
                bar = " " * bar_width + "|" + "#" * bar_len
            else:
                padding = bar_width - bar_len
                bar = " " * padding + "#" * bar_len + "|"
            lines.append(f"  {name:25s} {bar} {val:+.4f}")

        # Total reward trend
        if self.total_reward_history:
            recent_total = self.total_reward_history[-last_n:]
            lines.append(f"\n  Total reward (mean): {_np_mean(recent_total):+.4f}")
            lines.append(f"  Total reward (std):  {_np_std(recent_total):.4f}")

        # Shaping weight
        if self.shaping_weight_history:
            lines.append(
                f"  Shaping weight:      {self.shaping_weight_history[-1]:.4f}"
            )

        lines.append("=" * 70)
        return "\n".join(lines)

    def visualize_reward_trend(self, last_n: int = 50) -> str:
        """ASCII chart of total reward over time."""
        lines = []
        lines.append("  Reward Trend (last {} steps)".format(last_n))

        recent = self.total_reward_history[-last_n:]
        if not recent:
            lines.append("  (no data)")
            return "\n".join(lines)

        r_min = min(recent)
        r_max = max(recent)
        r_range = r_max - r_min if r_max > r_min else 1.0
        chart_width = 50

        for i, r in enumerate(recent):
            norm = (r - r_min) / r_range
            bar_len = int(norm * chart_width)
            lines.append(
                f"  {i:3d}|{'#' * bar_len}{' ' * (chart_width - bar_len)}| " f"{r:+.3f}"
            )

        return "\n".join(lines)

    def summary(self) -> Dict[str, Any]:
        """Complete reward designer summary."""
        return {
            "config": self.config.to_dict(),
            "steps": self.steps,
            "total_reward_mean": (
                _np_mean(self.total_reward_history)
                if self.total_reward_history
                else 0.0
            ),
            "total_reward_std": (
                _np_std(self.total_reward_history) if self.total_reward_history else 0.0
            ),
            "shaping_weight": self.scheduler.get_weight(),
            "normalizer": self.normalizer.stats() if self.normalizer else None,
            "curiosity": self.curiosity.stats() if self.curiosity else None,
            "components": self.component_contributions(),
        }


# ─────────────────────────────────────────────
# A/B Testing Framework
# ─────────────────────────────────────────────


@dataclass
class ABTestResult:
    """Results from one A/B test trial."""

    config_name: str
    episode_rewards: List[float] = field(default_factory=list)
    win_rate: float = 0.0
    avg_reward: float = 0.0
    reward_std: float = 0.0
    total_episodes: int = 0
    avg_episode_length: float = 0.0
    final_shaping_weight: float = 0.0


class RewardABTester:
    """
    A/B testing framework for comparing reward configurations.
    Runs simulated episodes under different reward designs and
    reports comparative statistics.
    """

    def __init__(
        self,
        configs: Optional[Dict[str, RewardConfig]] = None,
        seed: Optional[int] = None,
    ):
        self.configs = configs or REWARD_PRESETS
        self.results: Dict[str, ABTestResult] = {}
        self.seed = seed

    def _simulate_game_step(self, state: SC2GameState, step: int) -> SC2GameState:
        """Simulate one game step with randomized events."""
        new = SC2GameState(
            frame=state.frame + 16,
            minerals=state.minerals + state.workers * 0.8 - random.uniform(0, 100),
            gas=state.gas + max(0, state.workers * 0.1 - random.uniform(0, 20)),
            supply_used=state.supply_used + (1 if random.random() < 0.15 else 0),
            supply_max=state.supply_max + (8 if random.random() < 0.05 else 0),
            workers=state.workers + (1 if random.random() < 0.1 else 0),
            army_supply=state.army_supply + (1 if random.random() < 0.12 else 0),
            army_value=max(0, state.army_value + random.uniform(-20, 50)),
            bases=state.bases + (1 if random.random() < 0.02 else 0),
            tech_level=min(
                1.0, state.tech_level + (0.1 if random.random() < 0.03 else 0)
            ),
            damage_dealt=state.damage_dealt + random.uniform(0, 30),
            damage_taken=state.damage_taken + random.uniform(0, 20),
            units_produced=state.units_produced + (1 if random.random() < 0.15 else 0),
            units_lost=state.units_lost + (1 if random.random() < 0.08 else 0),
            units_killed=state.units_killed + (1 if random.random() < 0.1 else 0),
            resources_gathered=state.resources_gathered + state.workers * 0.8,
            map_control=_np_clip(state.map_control + random.gauss(0, 0.02), 0, 1),
            scouting_coverage=min(
                1.0, state.scouting_coverage + random.uniform(0, 0.01)
            ),
            apm=max(0, state.apm + random.gauss(0, 10)),
            upgrades_completed=state.upgrades_completed
            + (1 if random.random() < 0.02 else 0),
            enemy_army_value=max(0, state.enemy_army_value + random.uniform(-10, 40)),
            enemy_bases=state.enemy_bases + (1 if random.random() < 0.01 else 0),
            enemy_workers=state.enemy_workers + (1 if random.random() < 0.05 else 0),
            income_rate=state.workers * 50.0 + random.gauss(0, 50),
            idle_workers=max(0, int(random.gauss(1, 2))),
            production_facilities=state.production_facilities
            + (1 if random.random() < 0.03 else 0),
            creep_spread=min(1.0, state.creep_spread + random.uniform(0, 0.005)),
            queen_energy=_np_clip(state.queen_energy + random.gauss(2, 5), 0, 200),
        )
        new.minerals = max(0, new.minerals)
        new.gas = max(0, new.gas)
        return new

    def run_test(
        self, episodes: int = 50, steps_per_episode: int = 200, verbose: bool = True
    ) -> Dict[str, ABTestResult]:
        """
        Run A/B test across all configurations.

        Args:
            episodes: Number of simulated episodes per configuration
            steps_per_episode: Steps per episode
            verbose: Print progress

        Returns:
            Results dictionary keyed by config name
        """
        if verbose:
            print("=" * 70)
            print("  Reward A/B Testing Framework")
            print(f"  Configs: {list(self.configs.keys())}")
            print(f"  Episodes per config: {episodes}")
            print("=" * 70)

        for config_name, config in self.configs.items():
            if self.seed is not None:
                random.seed(self.seed)
                if NP_AVAILABLE:
                    np.random.seed(self.seed)

            designer = SC2RewardDesigner(config)
            result = ABTestResult(config_name=config_name)
            wins = 0

            for ep in range(episodes):
                state = SC2GameState()
                ep_reward = 0.0

                for step in range(steps_per_episode):
                    prev = state
                    state = self._simulate_game_step(state, step)

                    game_result = None
                    if step == steps_per_episode - 1:
                        won = (
                            state.army_value > state.enemy_army_value
                            and state.bases >= state.enemy_bases
                        )
                        game_result = 1.0 if won else -1.0
                        if won:
                            wins += 1

                    r = designer.compute_reward(prev, state, game_result)
                    ep_reward += r["total"]

                result.episode_rewards.append(ep_reward)

            result.total_episodes = episodes
            result.avg_reward = _np_mean(result.episode_rewards)
            result.reward_std = _np_std(result.episode_rewards)
            result.win_rate = wins / episodes
            result.final_shaping_weight = designer.scheduler.get_weight()

            self.results[config_name] = result

            if verbose:
                print(f"\n  Config: {config_name}")
                print(
                    f"    Avg Reward: {result.avg_reward:+.2f} "
                    f"(std: {result.reward_std:.2f})"
                )
                print(f"    Win Rate: {result.win_rate:.1%}")
                print(f"    Shaping Weight: {result.final_shaping_weight:.3f}")

        return self.results

    def comparison_report(self) -> str:
        """Generate a comparison report of all tested configurations."""
        lines = []
        lines.append("=" * 70)
        lines.append("  A/B Test Comparison Report")
        lines.append("=" * 70)
        lines.append(
            f"  {'Config':<20s} {'Avg Reward':>12s} {'Std':>8s} "
            f"{'Win Rate':>10s} {'Shaping W':>10s}"
        )
        lines.append("  " + "-" * 62)

        sorted_results = sorted(
            self.results.values(), key=lambda r: r.avg_reward, reverse=True
        )
        best = sorted_results[0] if sorted_results else None

        for r in sorted_results:
            marker = " *" if r is best else "  "
            lines.append(
                f"{marker}{r.config_name:<20s} {r.avg_reward:>+12.2f} "
                f"{r.reward_std:>8.2f} {r.win_rate:>9.1%} "
                f"{r.final_shaping_weight:>10.3f}"
            )

        if best:
            lines.append(
                f"\n  Best config: {best.config_name} "
                f"(avg reward: {best.avg_reward:+.2f}, "
                f"win rate: {best.win_rate:.1%})"
            )

        # Effect size (Cohen's d) between best and worst
        if len(sorted_results) >= 2:
            worst = sorted_results[-1]
            pooled_std = math.sqrt((best.reward_std**2 + worst.reward_std**2) / 2)
            if pooled_std > 0:
                cohens_d = (best.avg_reward - worst.avg_reward) / pooled_std
                lines.append(
                    f"  Effect size (best vs worst): Cohen's d = {cohens_d:.2f}"
                )

        lines.append("=" * 70)
        return "\n".join(lines)


# ─────────────────────────────────────────────
# CLI Demo
# ─────────────────────────────────────────────


def demo_reward_computation():
    """Demo: compute rewards with all components."""
    print("\n--- Reward Computation Demo ---\n")
    designer = SC2RewardDesigner(REWARD_PRESETS["balanced"])

    prev = SC2GameState()
    print("  Computing rewards over 30 simulated steps...")
    for i in range(30):
        curr = SC2GameState(
            frame=prev.frame + 16,
            minerals=prev.minerals + prev.workers * 0.5,
            gas=prev.gas + 3,
            supply_used=prev.supply_used + (1 if random.random() < 0.2 else 0),
            supply_max=prev.supply_max + (8 if random.random() < 0.1 else 0),
            workers=prev.workers + (1 if random.random() < 0.15 else 0),
            army_supply=prev.army_supply + (1 if random.random() < 0.1 else 0),
            army_value=prev.army_value + random.uniform(-10, 30),
            bases=prev.bases + (1 if random.random() < 0.03 else 0),
            tech_level=min(1.0, prev.tech_level + random.uniform(0, 0.05)),
            damage_dealt=prev.damage_dealt + random.uniform(0, 20),
            damage_taken=prev.damage_taken + random.uniform(0, 10),
            units_produced=prev.units_produced + (1 if random.random() < 0.1 else 0),
            units_lost=prev.units_lost + (1 if random.random() < 0.05 else 0),
            units_killed=prev.units_killed + (1 if random.random() < 0.08 else 0),
            resources_gathered=prev.resources_gathered + prev.workers * 0.5,
            map_control=min(1.0, prev.map_control + random.uniform(0, 0.02)),
            scouting_coverage=min(
                1.0, prev.scouting_coverage + random.uniform(0, 0.01)
            ),
            apm=max(0, 120 + random.gauss(0, 20)),
            income_rate=prev.workers * 50.0,
            idle_workers=max(0, int(random.gauss(0.5, 1))),
            creep_spread=min(1.0, prev.creep_spread + random.uniform(0, 0.005)),
            queen_energy=max(0, prev.queen_energy + random.gauss(2, 3)),
        )

        game_result = None
        if i == 29:
            game_result = 1.0  # simulate win

        result = designer.compute_reward(prev, curr, game_result)

        if (i + 1) % 10 == 0 or i == 29:
            print(
                f"  Step {i+1:3d}: total={result['total']:+.4f}, "
                f"shaped={result['shaped']:+.4f}, "
                f"sparse={result['sparse']:+.4f}, "
                f"pbrs={result['pbrs']:+.4f}, "
                f"curiosity={result['curiosity']:.4f}"
            )
        prev = curr

    print("\n" + designer.visualize_contributions(last_n=30))


def demo_pbrs():
    """Demo: Potential-Based Reward Shaping."""
    print("\n--- PBRS Demo ---\n")
    pbrs = PotentialFunction(gamma=0.99)

    s1 = SC2GameState(minerals=200, workers=20, army_value=500, bases=2)
    s2 = SC2GameState(minerals=300, workers=25, army_value=800, bases=2)
    s3 = SC2GameState(minerals=100, workers=15, army_value=200, bases=1)

    print(f"  phi(s1) = {pbrs.phi(s1):.4f}")
    print(f"  phi(s2) = {pbrs.phi(s2):.4f}")
    print(f"  phi(s3) = {pbrs.phi(s3):.4f}")
    print(f"  F(s1->s2) = {pbrs.shaping_reward(s1, s2):+.4f} (improvement)")
    print(f"  F(s2->s3) = {pbrs.shaping_reward(s2, s3):+.4f} (regression)")
    print(f"  F(s1->s3) = {pbrs.shaping_reward(s1, s3):+.4f} (regression)")


def demo_curiosity():
    """Demo: curiosity-driven intrinsic reward."""
    print("\n--- Curiosity Reward Demo ---\n")
    curiosity = CuriosityReward(beta=0.5)

    states = []
    for i in range(20):
        s = SC2GameState(
            minerals=random.randint(0, 5) * 200,
            workers=random.randint(10, 30),
            army_value=random.randint(0, 3) * 500,
            bases=random.randint(1, 3),
            frame=i * 1000,
        )
        reward = curiosity.compute(s)
        states.append((s.state_hash()[:8], reward))

    print("  State Hash | Curiosity Reward")
    print("  " + "-" * 30)
    for h, r in states:
        bar = "#" * int(r * 40)
        print(f"  {h}   | {r:.4f} {bar}")

    print(f"\n  Stats: {curiosity.stats()}")


def demo_weight_scheduler():
    """Demo: reward weight annealing schedules."""
    print("\n--- Weight Scheduler Demo ---\n")

    for stype in ["linear", "cosine", "exponential"]:
        sched = RewardWeightScheduler(
            total_steps=100, schedule_type=stype, warmup_fraction=0.1
        )
        weights = []
        for _ in range(100):
            weights.append(sched.step())

        print(f"  Schedule: {stype}")
        print(
            f"    Start: {weights[0]:.3f}, "
            f"Mid: {weights[49]:.3f}, "
            f"End: {weights[-1]:.3f}"
        )
        # Mini chart
        chart = "    "
        for i in range(0, 100, 5):
            h = int(weights[i] * 8)
            chart += ["_", ".", ":", "-", "=", "+", "#", "@", "M"][h]
        print(chart)
        print()


def demo_normalizer():
    """Demo: reward normalizer with Welford's algorithm."""
    print("\n--- Reward Normalizer Demo ---\n")
    norm = RewardNormalizer(clip_range=3.0)

    raw_values = [random.gauss(5, 10) for _ in range(50)]
    normalized = []
    for v in raw_values:
        normalized.append(norm.normalize(v))

    print(
        f"  Raw:        mean={_np_mean(raw_values):.2f}, "
        f"std={_np_std(raw_values):.2f}"
    )
    print(
        f"  Normalized: mean={_np_mean(normalized):.2f}, "
        f"std={_np_std(normalized):.2f}"
    )
    print(f"  Normalizer stats: {norm.stats()}")


def demo_ab_testing():
    """Demo: A/B testing of reward configurations."""
    print("\n--- A/B Testing Demo ---\n")

    # Test a subset of presets
    configs = {k: REWARD_PRESETS[k] for k in ["aggressive", "economic", "balanced"]}
    tester = RewardABTester(configs=configs, seed=42)
    tester.run_test(episodes=20, steps_per_episode=50, verbose=True)
    print("\n" + tester.comparison_report())


def demo_custom_config():
    """Demo: creating a custom reward configuration."""
    print("\n--- Custom Config Demo ---\n")
    config = RewardConfig(
        name="custom_zerg_rush",
        component_weights={
            "damage_dealt": 3.0,
            "units_produced": 1.0,
            "army_value": 2.0,
            "resources_gathered": 0.5,
            "expansion_timing": 0.3,
            "supply_efficiency": 0.5,
        },
        use_pbrs=True,
        use_curiosity=True,
        curiosity_beta=0.2,
        schedule_type="linear",
        schedule_steps=500,
    )

    designer = SC2RewardDesigner(config)
    prev = SC2GameState()

    rewards = []
    for step in range(50):
        curr = SC2GameState(
            frame=prev.frame + 16,
            minerals=max(0, prev.minerals + 20 - random.uniform(0, 40)),
            army_value=prev.army_value + random.uniform(10, 40),
            damage_dealt=prev.damage_dealt + random.uniform(5, 25),
            damage_taken=prev.damage_taken + random.uniform(0, 10),
            units_produced=prev.units_produced + (1 if random.random() < 0.3 else 0),
            workers=prev.workers,
            supply_used=prev.supply_used + (1 if random.random() < 0.2 else 0),
            supply_max=prev.supply_max + (8 if random.random() < 0.08 else 0),
            resources_gathered=prev.resources_gathered + 20,
            bases=prev.bases,
        )
        r = designer.compute_reward(prev, curr)
        rewards.append(r["total"])
        prev = curr

    print(f"  Config: {config.name}")
    print(f"  Avg reward: {_np_mean(rewards):+.4f}")
    print(
        f"  Components enabled: "
        f"{[n for n, c in designer.components.items() if c.enabled]}"
    )
    print(
        f"\n  Summary: {json.dumps(designer.summary(), indent=2, default=str)[:500]}..."
    )


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 613: SC2 Reward Shaping Designer"
    )
    parser.add_argument(
        "--demo",
        choices=[
            "reward",
            "pbrs",
            "curiosity",
            "scheduler",
            "normalizer",
            "ab",
            "custom",
            "all",
        ],
        default="all",
        help="Demo to run",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)
    if NP_AVAILABLE:
        np.random.seed(args.seed)

    print("=" * 70)
    print("  Phase 613: SC2 Reward Shaping Designer")
    print(f"  NumPy available: {NP_AVAILABLE}")
    print(f"  Reward components: {len(RewardComponentType)}")
    print(f"  Preset configs: {list(REWARD_PRESETS.keys())}")
    print("=" * 70)

    demos = {
        "reward": demo_reward_computation,
        "pbrs": demo_pbrs,
        "curiosity": demo_curiosity,
        "scheduler": demo_weight_scheduler,
        "normalizer": demo_normalizer,
        "ab": demo_ab_testing,
        "custom": demo_custom_config,
    }

    if args.demo == "all":
        for name, fn in demos.items():
            fn()
    else:
        demos[args.demo]()

    print("\nPhase 613 demo complete.")


if __name__ == "__main__":
    main()
