# Phase 610: Population Based Training for SC2 Agent Optimization
# Implements PBT with exploit/explore, ELO matchmaking, async workers, and checkpointing

from __future__ import annotations

import copy
import json
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False

# ============================================================
# NumPy Fallback Utilities
# ============================================================


def _np_zeros(shape: int | tuple) -> list:
    """Create zero-filled array without numpy."""
    if isinstance(shape, int):
        return [0.0] * shape
    if len(shape) == 1:
        return [0.0] * shape[0]
    return [[0.0] * shape[1] for _ in range(shape[0])]


def _np_random_normal(loc: float = 0.0, scale: float = 1.0, size: int = 1) -> list:
    """Box-Muller transform fallback."""
    results = []
    for _ in range(size):
        u1 = random.random() or 1e-10
        u2 = random.random()
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        results.append(loc + scale * z)
    return results


def _np_mean(values: list) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _np_std(values: list) -> float:
    if not values:
        return 0.0
    m = _np_mean(values)
    var = sum((v - m) ** 2 for v in values) / max(len(values), 1)
    return math.sqrt(var)


def _np_clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _np_softmax(logits: list) -> list:
    max_l = max(logits) if logits else 0.0
    exps = [math.exp(l - max_l) for l in logits]
    total = sum(exps) or 1e-10
    return [e / total for e in exps]


# ============================================================
# SC2-Specific Hyperparameter Definitions
# ============================================================

SC2_HYPERPARAMETER_RANGES: Dict[str, Dict[str, Any]] = {
    "learning_rate": {"min": 1e-5, "max": 1e-2, "log_scale": True, "default": 3e-4},
    "discount_factor": {"min": 0.9, "max": 0.999, "log_scale": False, "default": 0.99},
    "entropy_coeff": {"min": 1e-4, "max": 0.1, "log_scale": True, "default": 0.01},
    "explore_rate": {"min": 0.01, "max": 0.5, "log_scale": False, "default": 0.1},
    "army_weight": {"min": 0.1, "max": 2.0, "log_scale": False, "default": 1.0},
    "eco_weight": {"min": 0.1, "max": 2.0, "log_scale": False, "default": 1.0},
    "clip_ratio": {"min": 0.05, "max": 0.4, "log_scale": False, "default": 0.2},
    "batch_size": {"min": 32, "max": 512, "log_scale": False, "default": 128, "type": "int"},
    "gae_lambda": {"min": 0.9, "max": 1.0, "log_scale": False, "default": 0.95},
    "max_grad_norm": {"min": 0.1, "max": 10.0, "log_scale": True, "default": 0.5},
    "value_loss_coeff": {"min": 0.1, "max": 1.0, "log_scale": False, "default": 0.5},
    "reward_scale": {"min": 0.01, "max": 10.0, "log_scale": True, "default": 1.0},
}


# ============================================================
# Hyperparameter Set
# ============================================================


@dataclass
class HyperparameterSet:
    """A complete set of hyperparameters for one PBT agent."""

    params: Dict[str, float] = field(default_factory=dict)
    generation: int = 0

    @classmethod
    def random(cls, ranges: Optional[Dict[str, Dict]] = None) -> HyperparameterSet:
        """Sample a random hyperparameter configuration."""
        ranges = ranges or SC2_HYPERPARAMETER_RANGES
        params: Dict[str, float] = {}
        for name, spec in ranges.items():
            lo, hi = spec["min"], spec["max"]
            if spec.get("log_scale", False):
                val = math.exp(random.uniform(math.log(lo), math.log(hi)))
            else:
                val = random.uniform(lo, hi)
            if spec.get("type") == "int":
                val = int(round(val))
            params[name] = val
        return cls(params=params, generation=0)

    @classmethod
    def default(cls) -> HyperparameterSet:
        params = {k: v["default"] for k, v in SC2_HYPERPARAMETER_RANGES.items()}
        return cls(params=params, generation=0)

    def perturb(
        self,
        factor_range: Tuple[float, float] = (0.8, 1.2),
        resample_prob: float = 0.2,
        ranges: Optional[Dict[str, Dict]] = None,
    ) -> HyperparameterSet:
        """Create a new set by perturbing current hyperparameters (explore step)."""
        ranges = ranges or SC2_HYPERPARAMETER_RANGES
        new_params: Dict[str, float] = {}
        for name, val in self.params.items():
            spec = ranges.get(name, {})
            lo = spec.get("min", val * 0.1)
            hi = spec.get("max", val * 10.0)

            if random.random() < resample_prob:
                # Full resample
                if spec.get("log_scale", False):
                    new_val = math.exp(random.uniform(math.log(lo), math.log(hi)))
                else:
                    new_val = random.uniform(lo, hi)
            else:
                # Perturb by random factor
                factor = random.uniform(*factor_range)
                new_val = val * factor

            new_val = _np_clip(new_val, lo, hi)
            if spec.get("type") == "int":
                new_val = int(round(new_val))
            new_params[name] = new_val

        return HyperparameterSet(params=new_params, generation=self.generation + 1)

    def to_dict(self) -> Dict[str, Any]:
        return {"params": self.params.copy(), "generation": self.generation}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> HyperparameterSet:
        return cls(params=d["params"], generation=d.get("generation", 0))


# ============================================================
# Simulated Neural Network Weights
# ============================================================


class SimulatedWeights:
    """Lightweight weight placeholder for PBT copy operations."""

    def __init__(self, dim: int = 64):
        self.dim = dim
        if NP_AVAILABLE:
            self.data = np.random.randn(dim).astype(np.float32)
        else:
            self.data = _np_random_normal(0.0, 1.0, dim)

    def copy_from(self, other: SimulatedWeights) -> None:
        if NP_AVAILABLE:
            self.data = other.data.copy()
        else:
            self.data = list(other.data)

    def clone(self) -> SimulatedWeights:
        w = SimulatedWeights.__new__(SimulatedWeights)
        w.dim = self.dim
        if NP_AVAILABLE:
            w.data = self.data.copy()
        else:
            w.data = list(self.data)
        return w

    def to_list(self) -> list:
        if NP_AVAILABLE:
            return self.data.tolist()
        return list(self.data)

    @classmethod
    def from_list(cls, data: list) -> SimulatedWeights:
        w = cls.__new__(cls)
        w.dim = len(data)
        if NP_AVAILABLE:
            w.data = np.array(data, dtype=np.float32)
        else:
            w.data = list(data)
        return w


# ============================================================
# PBT Agent
# ============================================================


@dataclass
class PBTAgent:
    """One member of the PBT population."""

    agent_id: str
    hyperparams: HyperparameterSet
    weights: SimulatedWeights
    elo: float = 1200.0
    fitness: float = 0.0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    training_steps: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    parent_id: Optional[str] = None

    @property
    def win_rate(self) -> float:
        if self.games_played == 0:
            return 0.5
        return self.wins / self.games_played

    def record_snapshot(self) -> None:
        """Store current state in history for tracking."""
        self.history.append({
            "step": self.training_steps,
            "fitness": self.fitness,
            "elo": self.elo,
            "win_rate": self.win_rate,
            "hyperparams": self.hyperparams.params.copy(),
            "timestamp": time.time(),
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "hyperparams": self.hyperparams.to_dict(),
            "weights": self.weights.to_list(),
            "elo": self.elo,
            "fitness": self.fitness,
            "games_played": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "training_steps": self.training_steps,
            "history": self.history,
            "created_at": self.created_at,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PBTAgent:
        return cls(
            agent_id=d["agent_id"],
            hyperparams=HyperparameterSet.from_dict(d["hyperparams"]),
            weights=SimulatedWeights.from_list(d["weights"]),
            elo=d.get("elo", 1200.0),
            fitness=d.get("fitness", 0.0),
            games_played=d.get("games_played", 0),
            wins=d.get("wins", 0),
            losses=d.get("losses", 0),
            draws=d.get("draws", 0),
            training_steps=d.get("training_steps", 0),
            history=d.get("history", []),
            created_at=d.get("created_at", time.time()),
            parent_id=d.get("parent_id"),
        )


# ============================================================
# ELO Rating System
# ============================================================


class ELORating:
    """Standard ELO rating calculator with dynamic K-factor."""

    K_NEW = 40.0        # K for agents with < 30 games
    K_STANDARD = 20.0   # K for established agents
    K_HIGH = 10.0       # K for high-rated agents (>2000)

    @classmethod
    def expected_score(cls, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))

    @classmethod
    def k_factor(cls, agent: PBTAgent) -> float:
        if agent.games_played < 30:
            return cls.K_NEW
        if agent.elo >= 2000:
            return cls.K_HIGH
        return cls.K_STANDARD

    @classmethod
    def update(cls, winner: PBTAgent, loser: PBTAgent, draw: bool = False) -> Tuple[float, float]:
        """Update ELO ratings after a match. Returns (new_winner_elo, new_loser_elo)."""
        expected_w = cls.expected_score(winner.elo, loser.elo)
        expected_l = cls.expected_score(loser.elo, winner.elo)
        k_w = cls.k_factor(winner)
        k_l = cls.k_factor(loser)

        if draw:
            score_w, score_l = 0.5, 0.5
        else:
            score_w, score_l = 1.0, 0.0

        new_w = winner.elo + k_w * (score_w - expected_w)
        new_l = loser.elo + k_l * (score_l - expected_l)
        winner.elo = new_w
        loser.elo = new_l
        return new_w, new_l


# ============================================================
# Match Simulator
# ============================================================


class SC2MatchSimulator:
    """Simulate SC2 matches between two PBT agents using heuristic fitness."""

    @staticmethod
    def compute_agent_strength(agent: PBTAgent) -> float:
        """Heuristic strength based on hyperparameters and training progress."""
        hp = agent.hyperparams.params
        lr = hp.get("learning_rate", 3e-4)
        gamma = hp.get("discount_factor", 0.99)
        entropy = hp.get("entropy_coeff", 0.01)
        army_w = hp.get("army_weight", 1.0)
        eco_w = hp.get("eco_weight", 1.0)

        # Ideal ranges for SC2 training
        lr_score = 1.0 - abs(math.log(lr) - math.log(3e-4)) / 5.0
        gamma_score = 1.0 - abs(gamma - 0.99) * 10.0
        entropy_score = 1.0 - abs(math.log(entropy + 1e-10) - math.log(0.01)) / 5.0
        balance_score = 1.0 - abs(army_w - eco_w) * 0.3

        base_strength = (lr_score + gamma_score + entropy_score + balance_score) / 4.0
        # Training progress bonus
        progress_bonus = min(agent.training_steps / 10000.0, 1.0) * 0.3
        # Weight quality (norm proximity to ideal)
        if NP_AVAILABLE:
            weight_quality = 1.0 / (1.0 + abs(float(np.linalg.norm(agent.weights.data)) - 8.0))
        else:
            norm = math.sqrt(sum(w * w for w in agent.weights.data))
            weight_quality = 1.0 / (1.0 + abs(norm - 8.0))

        return _np_clip(base_strength + progress_bonus + weight_quality * 0.1, 0.0, 2.0)

    @classmethod
    def simulate_match(cls, agent_a: PBTAgent, agent_b: PBTAgent) -> Tuple[str, float, float]:
        """
        Simulate a match. Returns (result, score_a, score_b).
        result is 'a_wins', 'b_wins', or 'draw'.
        """
        str_a = cls.compute_agent_strength(agent_a) + random.gauss(0, 0.15)
        str_b = cls.compute_agent_strength(agent_b) + random.gauss(0, 0.15)
        diff = str_a - str_b

        if abs(diff) < 0.05:
            return "draw", 0.5, 0.5
        elif diff > 0:
            return "a_wins", 1.0, 0.0
        else:
            return "b_wins", 0.0, 1.0


# ============================================================
# Async Worker Pool Simulation
# ============================================================


@dataclass
class WorkerTask:
    """A training or evaluation task for async execution."""

    task_id: str
    task_type: str           # 'train' or 'evaluate'
    agent_id: str
    opponent_id: Optional[str] = None
    steps: int = 100
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    submit_time: float = field(default_factory=time.time)
    complete_time: Optional[float] = None


class AsyncWorkerPool:
    """Simulated async worker pool for PBT training tasks."""

    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.task_queue: List[WorkerTask] = []
        self.active_tasks: Dict[str, WorkerTask] = {}
        self.completed_tasks: List[WorkerTask] = []
        self.total_submitted = 0
        self.total_completed = 0

    def submit_train_task(self, agent_id: str, steps: int = 100) -> str:
        task_id = f"train_{uuid.uuid4().hex[:8]}"
        task = WorkerTask(
            task_id=task_id, task_type="train",
            agent_id=agent_id, steps=steps,
        )
        self.task_queue.append(task)
        self.total_submitted += 1
        return task_id

    def submit_eval_task(self, agent_id: str, opponent_id: str) -> str:
        task_id = f"eval_{uuid.uuid4().hex[:8]}"
        task = WorkerTask(
            task_id=task_id, task_type="evaluate",
            agent_id=agent_id, opponent_id=opponent_id,
        )
        self.task_queue.append(task)
        self.total_submitted += 1
        return task_id

    def step(self, agents: Dict[str, PBTAgent]) -> List[WorkerTask]:
        """Process tasks synchronously (simulating async completion)."""
        completed_this_step: List[WorkerTask] = []

        # Move pending to active
        while self.task_queue and len(self.active_tasks) < self.num_workers:
            task = self.task_queue.pop(0)
            task.status = "running"
            self.active_tasks[task.task_id] = task

        # Complete active tasks (instant simulation)
        for task_id in list(self.active_tasks.keys()):
            task = self.active_tasks[task_id]
            agent = agents.get(task.agent_id)
            if agent is None:
                task.status = "failed"
                task.result = {"error": f"Agent {task.agent_id} not found"}
            elif task.task_type == "train":
                # Simulate training: update weights slightly, increase steps
                agent.training_steps += task.steps
                if NP_AVAILABLE:
                    noise = np.random.randn(agent.weights.dim).astype(np.float32)
                    lr = agent.hyperparams.params.get("learning_rate", 3e-4)
                    agent.weights.data += noise * float(lr) * 10.0
                else:
                    lr = agent.hyperparams.params.get("learning_rate", 3e-4)
                    noise = _np_random_normal(0, 1, agent.weights.dim)
                    agent.weights.data = [
                        w + n * lr * 10.0 for w, n in zip(agent.weights.data, noise)
                    ]
                agent.fitness = SC2MatchSimulator.compute_agent_strength(agent)
                task.result = {
                    "steps_completed": task.steps,
                    "new_fitness": agent.fitness,
                    "total_steps": agent.training_steps,
                }
                task.status = "completed"
            elif task.task_type == "evaluate":
                opponent = agents.get(task.opponent_id)
                if opponent is None:
                    task.status = "failed"
                    task.result = {"error": f"Opponent {task.opponent_id} not found"}
                else:
                    result, score_a, score_b = SC2MatchSimulator.simulate_match(agent, opponent)
                    draw = result == "draw"
                    if result == "a_wins":
                        ELORating.update(agent, opponent, draw=False)
                        agent.wins += 1
                        opponent.losses += 1
                    elif result == "b_wins":
                        ELORating.update(opponent, agent, draw=False)
                        agent.losses += 1
                        opponent.wins += 1
                    else:
                        ELORating.update(agent, opponent, draw=True)
                        agent.draws += 1
                        opponent.draws += 1
                    agent.games_played += 1
                    opponent.games_played += 1
                    task.result = {
                        "result": result,
                        "score_a": score_a, "score_b": score_b,
                        "new_elo_a": agent.elo, "new_elo_b": opponent.elo,
                    }
                    task.status = "completed"

            task.complete_time = time.time()
            completed_this_step.append(task)
            del self.active_tasks[task_id]
            self.completed_tasks.append(task)
            self.total_completed += 1

        return completed_this_step

    @property
    def pending_count(self) -> int:
        return len(self.task_queue) + len(self.active_tasks)

    def stats(self) -> Dict[str, int]:
        return {
            "num_workers": self.num_workers,
            "pending": len(self.task_queue),
            "active": len(self.active_tasks),
            "completed": self.total_completed,
            "total_submitted": self.total_submitted,
        }


# ============================================================
# Hyperparameter Schedule Tracker
# ============================================================


class HyperparamScheduleTracker:
    """Track hyperparameter changes over PBT generations for visualization."""

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def record(self, agent_id: str, generation: int, step: int,
               hyperparams: Dict[str, float], fitness: float, elo: float) -> None:
        self.records.append({
            "agent_id": agent_id,
            "generation": generation,
            "step": step,
            "hyperparams": hyperparams.copy(),
            "fitness": fitness,
            "elo": elo,
            "timestamp": time.time(),
        })

    def get_agent_history(self, agent_id: str) -> List[Dict[str, Any]]:
        return [r for r in self.records if r["agent_id"] == agent_id]

    def get_param_timeline(self, param_name: str) -> Dict[str, List[Tuple[int, float]]]:
        """Return {agent_id: [(step, value), ...]} for a given parameter."""
        timeline: Dict[str, List[Tuple[int, float]]] = {}
        for r in self.records:
            aid = r["agent_id"]
            if aid not in timeline:
                timeline[aid] = []
            val = r["hyperparams"].get(param_name)
            if val is not None:
                timeline[aid].append((r["step"], val))
        return timeline

    def summary_table(self) -> str:
        """Return ASCII table of latest hyperparams per agent."""
        if not self.records:
            return "(no records)"
        latest: Dict[str, Dict] = {}
        for r in self.records:
            latest[r["agent_id"]] = r

        param_names = sorted(SC2_HYPERPARAMETER_RANGES.keys())
        header = f"{'Agent':>12s} {'ELO':>7s} {'Fit':>6s} | " + " | ".join(
            f"{p[:8]:>8s}" for p in param_names
        )
        lines = [header, "-" * len(header)]
        for aid in sorted(latest.keys()):
            r = latest[aid]
            vals = " | ".join(
                f"{r['hyperparams'].get(p, 0.0):>8.4g}" for p in param_names
            )
            lines.append(f"{aid[:12]:>12s} {r['elo']:7.1f} {r['fitness']:6.3f} | {vals}")
        return "\n".join(lines)

    def render_ascii_chart(self, param_name: str, width: int = 60, height: int = 15) -> str:
        """Render a simple ASCII chart of a parameter across agents."""
        timeline = self.get_param_timeline(param_name)
        if not timeline:
            return f"(no data for {param_name})"

        all_vals = [v for pairs in timeline.values() for _, v in pairs]
        if not all_vals:
            return "(empty)"
        lo, hi = min(all_vals), max(all_vals)
        if lo == hi:
            hi = lo + 1.0

        lines = [f"  {param_name} over training steps"]
        lines.append(f"  {hi:.4g} |")
        canvas = [[" "] * width for _ in range(height)]

        symbols = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop"
        all_steps = [s for pairs in timeline.values() for s, _ in pairs]
        min_step, max_step = min(all_steps), max(all_steps)
        if min_step == max_step:
            max_step = min_step + 1

        for idx, (aid, pairs) in enumerate(sorted(timeline.items())):
            sym = symbols[idx % len(symbols)]
            for step, val in pairs:
                x = int((step - min_step) / (max_step - min_step) * (width - 1))
                y = int((val - lo) / (hi - lo) * (height - 1))
                y = max(0, min(height - 1, y))
                canvas[height - 1 - y][x] = sym

        for row in canvas:
            lines.append("        |" + "".join(row))
        lines.append(f"  {lo:.4g} |" + "-" * width)
        lines.append(f"        step {min_step} -> {max_step}")
        return "\n".join(lines)


# ============================================================
# SC2 PBT Trainer (Main Class)
# ============================================================


class SC2PBTTrainer:
    """
    Population-Based Training for SC2 bots.

    Manages a population of N agents, each with different hyperparameters.
    Periodically runs exploit (copy weights from top performer) and explore
    (perturb hyperparameters) on underperforming agents.
    """

    def __init__(
        self,
        population_size: int = 8,
        weight_dim: int = 64,
        num_workers: int = 4,
        exploit_top_frac: float = 0.2,
        exploit_bottom_frac: float = 0.2,
        perturb_factor_range: Tuple[float, float] = (0.8, 1.2),
        resample_prob: float = 0.25,
        checkpoint_dir: Optional[str] = None,
        eval_interval: int = 5,
        train_steps_per_iter: int = 200,
        seed: Optional[int] = None,
    ):
        if seed is not None:
            random.seed(seed)
            if NP_AVAILABLE:
                np.random.seed(seed)

        self.population_size = population_size
        self.weight_dim = weight_dim
        self.exploit_top_frac = exploit_top_frac
        self.exploit_bottom_frac = exploit_bottom_frac
        self.perturb_factor_range = perturb_factor_range
        self.resample_prob = resample_prob
        self.checkpoint_dir = checkpoint_dir
        self.eval_interval = eval_interval
        self.train_steps_per_iter = train_steps_per_iter

        # Initialize population
        self.agents: Dict[str, PBTAgent] = {}
        for i in range(population_size):
            aid = f"agent_{i:03d}"
            agent = PBTAgent(
                agent_id=aid,
                hyperparams=HyperparameterSet.random(),
                weights=SimulatedWeights(dim=weight_dim),
            )
            self.agents[aid] = agent

        self.worker_pool = AsyncWorkerPool(num_workers=num_workers)
        self.schedule_tracker = HyperparamScheduleTracker()
        self.iteration = 0
        self.exploit_count = 0
        self.explore_count = 0

    # --------------------------------------------------------
    # Tournament Selection with ELO-based Matchmaking
    # --------------------------------------------------------

    def select_matches_elo(self, num_matches: int = 4) -> List[Tuple[str, str]]:
        """Select matches weighted by ELO proximity (closer ratings = more likely)."""
        agent_ids = list(self.agents.keys())
        if len(agent_ids) < 2:
            return []

        matches: List[Tuple[str, str]] = []
        for _ in range(num_matches):
            a_id = random.choice(agent_ids)
            a_elo = self.agents[a_id].elo
            # Weight opponents by ELO proximity
            candidates = [aid for aid in agent_ids if aid != a_id]
            if not candidates:
                continue
            weights = []
            for cid in candidates:
                diff = abs(self.agents[cid].elo - a_elo)
                weights.append(1.0 / (1.0 + diff / 200.0))
            probs = _np_softmax(weights)
            # Weighted random choice
            r = random.random()
            cumsum = 0.0
            chosen = candidates[-1]
            for cid, p in zip(candidates, probs):
                cumsum += p
                if r <= cumsum:
                    chosen = cid
                    break
            matches.append((a_id, chosen))
        return matches

    # --------------------------------------------------------
    # Exploit: Copy Weights from Top Performer
    # --------------------------------------------------------

    def exploit(self) -> List[str]:
        """
        Bottom agents copy weights from top agents.
        Returns list of agent IDs that were exploited.
        """
        sorted_agents = sorted(
            self.agents.values(), key=lambda a: a.fitness, reverse=True
        )
        n = len(sorted_agents)
        top_k = max(1, int(n * self.exploit_top_frac))
        bottom_k = max(1, int(n * self.exploit_bottom_frac))

        top_agents = sorted_agents[:top_k]
        bottom_agents = sorted_agents[-bottom_k:]
        exploited: List[str] = []

        for bottom_agent in bottom_agents:
            donor = random.choice(top_agents)
            bottom_agent.weights.copy_from(donor.weights)
            bottom_agent.parent_id = donor.agent_id
            self.exploit_count += 1
            exploited.append(bottom_agent.agent_id)

        return exploited

    # --------------------------------------------------------
    # Explore: Perturb Hyperparameters
    # --------------------------------------------------------

    def explore(self, agent_ids: List[str]) -> None:
        """Perturb hyperparameters for given agents (explore step)."""
        for aid in agent_ids:
            agent = self.agents.get(aid)
            if agent is None:
                continue
            agent.hyperparams = agent.hyperparams.perturb(
                factor_range=self.perturb_factor_range,
                resample_prob=self.resample_prob,
            )
            self.explore_count += 1

    # --------------------------------------------------------
    # Training Iteration
    # --------------------------------------------------------

    def train_iteration(self) -> Dict[str, Any]:
        """Run one PBT iteration: train, evaluate, exploit, explore."""
        self.iteration += 1
        results: Dict[str, Any] = {"iteration": self.iteration}

        # Step 1: Submit training tasks for all agents
        for aid in self.agents:
            self.worker_pool.submit_train_task(aid, steps=self.train_steps_per_iter)

        # Process training
        train_results = self.worker_pool.step(self.agents)
        results["train_tasks"] = len(train_results)

        # Step 2: Evaluation matches (periodic)
        eval_results = []
        if self.iteration % self.eval_interval == 0:
            matches = self.select_matches_elo(num_matches=self.population_size)
            for a_id, b_id in matches:
                self.worker_pool.submit_eval_task(a_id, b_id)
            eval_results = self.worker_pool.step(self.agents)
        results["eval_tasks"] = len(eval_results)

        # Step 3: Exploit and Explore (after evaluation rounds)
        exploited = []
        if self.iteration % self.eval_interval == 0 and self.iteration > self.eval_interval:
            exploited = self.exploit()
            self.explore(exploited)
        results["exploited"] = exploited

        # Step 4: Record schedule snapshots
        for aid, agent in self.agents.items():
            self.schedule_tracker.record(
                agent_id=aid,
                generation=agent.hyperparams.generation,
                step=agent.training_steps,
                hyperparams=agent.hyperparams.params,
                fitness=agent.fitness,
                elo=agent.elo,
            )
            agent.record_snapshot()

        # Compute population stats
        fitnesses = [a.fitness for a in self.agents.values()]
        elos = [a.elo for a in self.agents.values()]
        results["fitness_mean"] = _np_mean(fitnesses)
        results["fitness_std"] = _np_std(fitnesses)
        results["fitness_max"] = max(fitnesses) if fitnesses else 0.0
        results["elo_mean"] = _np_mean(elos)
        results["elo_max"] = max(elos) if elos else 0.0
        results["elo_min"] = min(elos) if elos else 0.0

        return results

    def run(self, num_iterations: int = 50) -> List[Dict[str, Any]]:
        """Run full PBT training loop."""
        all_results: List[Dict[str, Any]] = []
        for _ in range(num_iterations):
            result = self.train_iteration()
            all_results.append(result)
        return all_results

    # --------------------------------------------------------
    # Best Agent
    # --------------------------------------------------------

    def best_agent(self) -> PBTAgent:
        return max(self.agents.values(), key=lambda a: a.fitness)

    def ranked_agents(self) -> List[PBTAgent]:
        return sorted(self.agents.values(), key=lambda a: a.elo, reverse=True)

    # --------------------------------------------------------
    # Checkpoint Management
    # --------------------------------------------------------

    def save_checkpoint(self, path: Optional[str] = None) -> str:
        """Save entire population to JSON checkpoint."""
        if path is None:
            if self.checkpoint_dir:
                os.makedirs(self.checkpoint_dir, exist_ok=True)
                path = os.path.join(self.checkpoint_dir, f"pbt_checkpoint_iter{self.iteration}.json")
            else:
                path = f"pbt_checkpoint_iter{self.iteration}.json"

        data = {
            "iteration": self.iteration,
            "population_size": self.population_size,
            "exploit_count": self.exploit_count,
            "explore_count": self.explore_count,
            "agents": {aid: agent.to_dict() for aid, agent in self.agents.items()},
            "schedule_records": self.schedule_tracker.records,
            "worker_stats": self.worker_pool.stats(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def load_checkpoint(self, path: str) -> None:
        """Load population from JSON checkpoint."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.iteration = data.get("iteration", 0)
        self.exploit_count = data.get("exploit_count", 0)
        self.explore_count = data.get("explore_count", 0)
        self.agents.clear()
        for aid, agent_data in data.get("agents", {}).items():
            self.agents[aid] = PBTAgent.from_dict(agent_data)
        self.schedule_tracker.records = data.get("schedule_records", [])
        self.population_size = len(self.agents)

    # --------------------------------------------------------
    # Visualization and Reporting
    # --------------------------------------------------------

    def population_summary(self) -> str:
        """Generate population summary table."""
        lines = ["=" * 80]
        lines.append(f"  PBT Population Summary  |  Iteration: {self.iteration}  |  "
                      f"Exploits: {self.exploit_count}  Explores: {self.explore_count}")
        lines.append("=" * 80)
        lines.append(
            f"{'Agent':>12s} {'ELO':>7s} {'Fit':>6s} {'WR':>5s} "
            f"{'Games':>5s} {'Steps':>7s} {'Gen':>4s} {'LR':>10s} {'Ent':>10s}"
        )
        lines.append("-" * 80)

        for agent in self.ranked_agents():
            hp = agent.hyperparams.params
            lines.append(
                f"{agent.agent_id:>12s} {agent.elo:7.1f} {agent.fitness:6.3f} "
                f"{agent.win_rate:5.1%} {agent.games_played:5d} "
                f"{agent.training_steps:7d} {agent.hyperparams.generation:4d} "
                f"{hp.get('learning_rate', 0):10.2e} {hp.get('entropy_coeff', 0):10.2e}"
            )

        lines.append("-" * 80)
        fitnesses = [a.fitness for a in self.agents.values()]
        lines.append(f"  Fitness: mean={_np_mean(fitnesses):.4f}  "
                      f"std={_np_std(fitnesses):.4f}  max={max(fitnesses):.4f}")
        lines.append(f"  Worker pool: {self.worker_pool.stats()}")
        lines.append("=" * 80)
        return "\n".join(lines)

    def fitness_over_time_chart(self, width: int = 60, height: int = 12) -> str:
        """ASCII chart of mean/max fitness over iterations."""
        if not self.schedule_tracker.records:
            return "(no training data yet)"

        # Group by step
        step_fitness: Dict[int, List[float]] = {}
        for r in self.schedule_tracker.records:
            s = r["step"]
            if s not in step_fitness:
                step_fitness[s] = []
            step_fitness[s].append(r["fitness"])

        steps_sorted = sorted(step_fitness.keys())
        means = [_np_mean(step_fitness[s]) for s in steps_sorted]
        maxes = [max(step_fitness[s]) for s in steps_sorted]

        if not means:
            return "(empty)"

        all_vals = means + maxes
        lo, hi = min(all_vals), max(all_vals)
        if lo == hi:
            hi = lo + 1.0

        canvas = [[" "] * width for _ in range(height)]
        min_s, max_s = steps_sorted[0], steps_sorted[-1]
        if min_s == max_s:
            max_s = min_s + 1

        for step, val in zip(steps_sorted, means):
            x = int((step - min_s) / (max_s - min_s) * (width - 1))
            y = int((val - lo) / (hi - lo) * (height - 1))
            y = max(0, min(height - 1, y))
            canvas[height - 1 - y][x] = "o"

        for step, val in zip(steps_sorted, maxes):
            x = int((step - min_s) / (max_s - min_s) * (width - 1))
            y = int((val - lo) / (hi - lo) * (height - 1))
            y = max(0, min(height - 1, y))
            canvas[height - 1 - y][x] = "*"

        lines = ["  Fitness over time (o=mean, *=max)"]
        lines.append(f"  {hi:.3f} |")
        for row in canvas:
            lines.append("        |" + "".join(row))
        lines.append(f"  {lo:.3f} |" + "-" * width)
        lines.append(f"        step {min_s} -> {max_s}")
        return "\n".join(lines)


# ============================================================
# CLI Demo
# ============================================================


def run_pbt_demo() -> None:
    """Run a full PBT training demo with console output."""
    print("=" * 70)
    print("  Phase 610: SC2 Population-Based Training Demo")
    print("=" * 70)
    print()

    trainer = SC2PBTTrainer(
        population_size=8,
        weight_dim=32,
        num_workers=4,
        eval_interval=3,
        train_steps_per_iter=100,
        seed=42,
    )

    print(f"[Init] Population size: {trainer.population_size}")
    print(f"[Init] Weight dim: {trainer.weight_dim}")
    print(f"[Init] Workers: {trainer.worker_pool.num_workers}")
    print()

    # Initial hyperparameters
    print("--- Initial Hyperparameters ---")
    for aid, agent in sorted(trainer.agents.items()):
        lr = agent.hyperparams.params.get("learning_rate", 0)
        ent = agent.hyperparams.params.get("entropy_coeff", 0)
        army = agent.hyperparams.params.get("army_weight", 0)
        eco = agent.hyperparams.params.get("eco_weight", 0)
        print(f"  {aid}: lr={lr:.2e} ent={ent:.2e} army={army:.2f} eco={eco:.2f}")
    print()

    # Training loop
    num_iters = 30
    print(f"--- Running {num_iters} PBT iterations ---")
    for i in range(num_iters):
        result = trainer.train_iteration()
        if (i + 1) % 5 == 0:
            print(
                f"  Iter {result['iteration']:3d}: "
                f"fit_mean={result['fitness_mean']:.4f} "
                f"fit_max={result['fitness_max']:.4f} "
                f"elo_mean={result['elo_mean']:.1f} "
                f"elo_max={result['elo_max']:.1f} "
                f"exploited={len(result['exploited'])}"
            )
    print()

    # Population summary
    print(trainer.population_summary())
    print()

    # Fitness chart
    print(trainer.fitness_over_time_chart())
    print()

    # Hyperparameter schedule for learning_rate
    print(trainer.schedule_tracker.render_ascii_chart("learning_rate"))
    print()

    # Best agent
    best = trainer.best_agent()
    print(f"--- Best Agent ---")
    print(f"  ID: {best.agent_id}")
    print(f"  ELO: {best.elo:.1f}")
    print(f"  Fitness: {best.fitness:.4f}")
    print(f"  Win rate: {best.win_rate:.1%}")
    print(f"  Training steps: {best.training_steps}")
    print(f"  Generation: {best.hyperparams.generation}")
    print(f"  Hyperparams:")
    for k, v in sorted(best.hyperparams.params.items()):
        print(f"    {k}: {v:.6g}")
    print()

    # Checkpoint save/load test
    ckpt_path = trainer.save_checkpoint("pbt_demo_checkpoint.json")
    print(f"[Checkpoint] Saved to: {ckpt_path}")

    trainer2 = SC2PBTTrainer(population_size=1, seed=99)
    trainer2.load_checkpoint(ckpt_path)
    print(f"[Checkpoint] Loaded {len(trainer2.agents)} agents, iteration={trainer2.iteration}")

    # Verify loaded agent matches
    best2 = trainer2.best_agent()
    print(f"[Checkpoint] Best agent after load: {best2.agent_id} ELO={best2.elo:.1f}")

    # Clean up
    try:
        os.remove(ckpt_path)
        print(f"[Cleanup] Removed {ckpt_path}")
    except OSError:
        pass

    # Schedule summary
    print()
    print("--- Hyperparameter Schedule Summary ---")
    print(trainer.schedule_tracker.summary_table())
    print()

    # Worker pool stats
    print(f"--- Worker Pool Stats ---")
    for k, v in trainer.worker_pool.stats().items():
        print(f"  {k}: {v}")

    print()
    print("=" * 70)
    print("  Phase 610 Demo Complete")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Aliases for spec-requested class names
# ---------------------------------------------------------------------------
PBTMember = PBTAgent
PBTPopulation = SC2PBTTrainer  # population manager
PBTTrainer = SC2PBTTrainer
demo = run_pbt_demo


if __name__ == "__main__":
    run_pbt_demo()

# Phase 610: PBT registered
