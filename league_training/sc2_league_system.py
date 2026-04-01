# Phase 611: AlphaStar-Style League Training for SC2 Bot
# Implements league system with main agents, exploiters, PFSP, and Nash tracking

from __future__ import annotations

import copy
import json
import math
import os
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import numpy as np
    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False

# ============================================================
# NumPy Fallback Utilities
# ============================================================


def _np_zeros(n: int) -> list:
    return [0.0] * n


def _np_ones(n: int) -> list:
    return [1.0] * n


def _np_mean(vals: list) -> float:
    return sum(vals) / max(len(vals), 1)


def _np_std(vals: list) -> float:
    if len(vals) < 2:
        return 0.0
    m = _np_mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def _np_softmax(logits: list) -> list:
    mx = max(logits) if logits else 0.0
    exps = [math.exp(x - mx) for x in logits]
    s = sum(exps) or 1e-10
    return [e / s for e in exps]


def _np_clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _np_random_normal(mu: float = 0.0, sigma: float = 1.0, size: int = 1) -> list:
    out = []
    for _ in range(size):
        u1 = random.random() or 1e-10
        u2 = random.random()
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        out.append(mu + sigma * z)
    return out


def _weighted_choice(items: list, weights: list) -> Any:
    """Weighted random choice without numpy."""
    total = sum(weights)
    if total <= 0:
        return random.choice(items)
    r = random.random() * total
    cumsum = 0.0
    for item, w in zip(items, weights):
        cumsum += w
        if r <= cumsum:
            return item
    return items[-1]


# ============================================================
# Agent Types
# ============================================================


class AgentType(Enum):
    MAIN_AGENT = "main_agent"
    MAIN_EXPLOITER = "main_exploiter"
    LEAGUE_EXPLOITER = "league_exploiter"


class AgentStatus(Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    RETIRED = "retired"


# ============================================================
# Simulated Policy Weights
# ============================================================


class PolicyWeights:
    """Lightweight policy weight representation for league training."""

    def __init__(self, dim: int = 64):
        self.dim = dim
        if NP_AVAILABLE:
            self.data = np.random.randn(dim).astype(np.float32)
        else:
            self.data = _np_random_normal(0.0, 1.0, dim)

    def copy_from(self, other: PolicyWeights) -> None:
        if NP_AVAILABLE:
            self.data = other.data.copy()
        else:
            self.data = list(other.data)

    def clone(self) -> PolicyWeights:
        w = PolicyWeights.__new__(PolicyWeights)
        w.dim = self.dim
        if NP_AVAILABLE:
            w.data = self.data.copy()
        else:
            w.data = list(self.data)
        return w

    def strength_score(self) -> float:
        """Heuristic strength based on weight norm."""
        if NP_AVAILABLE:
            norm = float(np.linalg.norm(self.data))
        else:
            norm = math.sqrt(sum(w * w for w in self.data))
        return 1.0 / (1.0 + abs(norm - 8.0))

    def to_list(self) -> list:
        return list(self.data) if not NP_AVAILABLE else self.data.tolist()

    @classmethod
    def from_list(cls, data: list) -> PolicyWeights:
        w = cls.__new__(cls)
        w.dim = len(data)
        if NP_AVAILABLE:
            w.data = np.array(data, dtype=np.float32)
        else:
            w.data = list(data)
        return w


# ============================================================
# League Agent
# ============================================================


@dataclass
class LeagueAgent:
    """One agent in the league system."""

    agent_id: str
    agent_type: AgentType
    status: AgentStatus = AgentStatus.ACTIVE
    weights: PolicyWeights = field(default_factory=PolicyWeights)
    elo: float = 1200.0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    training_steps: int = 0
    generation: int = 0
    parent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    frozen_at: Optional[float] = None
    rating_history: List[Tuple[int, float]] = field(default_factory=list)

    # Win rates against specific opponents
    opponent_records: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0}))

    @property
    def win_rate(self) -> float:
        if self.games_played == 0:
            return 0.5
        return self.wins / self.games_played

    def win_rate_vs(self, opponent_id: str) -> float:
        rec = self.opponent_records.get(opponent_id)
        if rec is None:
            return 0.5
        total = rec["wins"] + rec["losses"] + rec["draws"]
        if total == 0:
            return 0.5
        return rec["wins"] / total

    def record_rating(self) -> None:
        self.rating_history.append((self.training_steps, self.elo))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "weights": self.weights.to_list(),
            "elo": self.elo,
            "games_played": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "training_steps": self.training_steps,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "frozen_at": self.frozen_at,
            "rating_history": self.rating_history,
            "opponent_records": dict(self.opponent_records),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> LeagueAgent:
        agent = cls(
            agent_id=d["agent_id"],
            agent_type=AgentType(d["agent_type"]),
            status=AgentStatus(d.get("status", "active")),
            weights=PolicyWeights.from_list(d.get("weights", [0.0] * 64)),
            elo=d.get("elo", 1200.0),
            games_played=d.get("games_played", 0),
            wins=d.get("wins", 0),
            losses=d.get("losses", 0),
            draws=d.get("draws", 0),
            training_steps=d.get("training_steps", 0),
            generation=d.get("generation", 0),
            parent_id=d.get("parent_id"),
            created_at=d.get("created_at", time.time()),
            frozen_at=d.get("frozen_at"),
            rating_history=d.get("rating_history", []),
        )
        opp_recs = d.get("opponent_records", {})
        for opp_id, rec in opp_recs.items():
            agent.opponent_records[opp_id] = rec
        return agent


# ============================================================
# ELO Rating System with Adjustable K-Factor
# ============================================================


class ELORatingSystem:
    """ELO system with dynamic K-factor based on games played and rating."""

    BASE_K = 32.0
    MIN_K = 8.0
    PROVISIONAL_GAMES = 30

    @classmethod
    def k_factor(cls, agent: LeagueAgent) -> float:
        if agent.games_played < cls.PROVISIONAL_GAMES:
            return cls.BASE_K * 1.5
        if agent.elo > 2200:
            return cls.MIN_K
        if agent.elo > 1800:
            return cls.BASE_K * 0.75
        return cls.BASE_K

    @classmethod
    def expected_score(cls, ra: float, rb: float) -> float:
        return 1.0 / (1.0 + math.pow(10, (rb - ra) / 400.0))

    @classmethod
    def update_ratings(
        cls, agent_a: LeagueAgent, agent_b: LeagueAgent,
        score_a: float, score_b: float,
    ) -> Tuple[float, float]:
        ea = cls.expected_score(agent_a.elo, agent_b.elo)
        eb = cls.expected_score(agent_b.elo, agent_a.elo)
        ka = cls.k_factor(agent_a)
        kb = cls.k_factor(agent_b)
        agent_a.elo += ka * (score_a - ea)
        agent_b.elo += kb * (score_b - eb)
        return agent_a.elo, agent_b.elo


# ============================================================
# Match History Database
# ============================================================


@dataclass
class MatchRecord:
    """Single match result."""

    match_id: str
    agent_a_id: str
    agent_b_id: str
    winner_id: Optional[str]  # None for draws
    score_a: float
    score_b: float
    elo_a_before: float
    elo_b_before: float
    elo_a_after: float
    elo_b_after: float
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class MatchHistoryDB:
    """In-memory match history database."""

    def __init__(self):
        self.records: List[MatchRecord] = []
        self._by_agent: Dict[str, List[int]] = defaultdict(list)

    def add(self, record: MatchRecord) -> None:
        idx = len(self.records)
        self.records.append(record)
        self._by_agent[record.agent_a_id].append(idx)
        self._by_agent[record.agent_b_id].append(idx)

    def get_agent_matches(self, agent_id: str, last_n: Optional[int] = None) -> List[MatchRecord]:
        indices = self._by_agent.get(agent_id, [])
        if last_n is not None:
            indices = indices[-last_n:]
        return [self.records[i] for i in indices]

    def head_to_head(self, a_id: str, b_id: str) -> Dict[str, int]:
        result = {"a_wins": 0, "b_wins": 0, "draws": 0}
        for idx in self._by_agent.get(a_id, []):
            rec = self.records[idx]
            if not (rec.agent_a_id == b_id or rec.agent_b_id == b_id):
                continue
            if rec.winner_id == a_id:
                result["a_wins"] += 1
            elif rec.winner_id == b_id:
                result["b_wins"] += 1
            else:
                result["draws"] += 1
        return result

    def total_matches(self) -> int:
        return len(self.records)

    def recent(self, n: int = 10) -> List[MatchRecord]:
        return self.records[-n:]

    def win_loss_summary(self, agent_id: str) -> Dict[str, int]:
        w, l, d = 0, 0, 0
        for idx in self._by_agent.get(agent_id, []):
            rec = self.records[idx]
            if rec.winner_id == agent_id:
                w += 1
            elif rec.winner_id is None:
                d += 1
            else:
                l += 1
        return {"wins": w, "losses": l, "draws": d}


# ============================================================
# Match Simulator
# ============================================================


class SC2MatchSimulator:
    """Simulate SC2 match outcomes between league agents."""

    @staticmethod
    def agent_strength(agent: LeagueAgent) -> float:
        base = agent.weights.strength_score()
        step_bonus = min(agent.training_steps / 10000.0, 1.0) * 0.3
        type_mod = {
            AgentType.MAIN_AGENT: 0.0,
            AgentType.MAIN_EXPLOITER: 0.05,
            AgentType.LEAGUE_EXPLOITER: -0.05,
        }.get(agent.agent_type, 0.0)
        return base + step_bonus + type_mod

    @classmethod
    def simulate(cls, a: LeagueAgent, b: LeagueAgent) -> Tuple[Optional[str], float, float]:
        """Returns (winner_id or None, score_a, score_b)."""
        str_a = cls.agent_strength(a) + random.gauss(0, 0.15)
        str_b = cls.agent_strength(b) + random.gauss(0, 0.15)
        diff = str_a - str_b

        if abs(diff) < 0.05:
            return None, 0.5, 0.5
        elif diff > 0:
            return a.agent_id, 1.0, 0.0
        else:
            return b.agent_id, 0.0, 1.0


# ============================================================
# Prioritized Fictitious Self-Play (PFSP)
# ============================================================


class PFSPMatchmaker:
    """
    Prioritized Fictitious Self-Play matchmaking.
    Matches agents against opponents where their win rate is closest to 50%,
    prioritizing informative matchups.
    """

    def __init__(self, pfsp_temperature: float = 1.0):
        self.temperature = pfsp_temperature

    def select_opponent(
        self, agent: LeagueAgent, candidates: List[LeagueAgent],
        mode: str = "pfsp",
    ) -> LeagueAgent:
        """
        Select an opponent for the given agent.
        Modes:
          - pfsp: prioritize opponents where win rate is near 50%
          - uniform: random uniform
          - hard: prioritize opponents agent loses to
        """
        if not candidates:
            raise ValueError("No candidates available")

        if mode == "uniform" or len(candidates) == 1:
            return random.choice(candidates)

        weights = []
        for opp in candidates:
            wr = agent.win_rate_vs(opp.agent_id)
            if mode == "pfsp":
                # Prioritize near 50% win rate (most informative)
                priority = math.exp(-abs(wr - 0.5) * 4.0 / max(self.temperature, 0.01))
            elif mode == "hard":
                # Prioritize opponents agent loses to
                priority = max(1.0 - wr, 0.01)
            else:
                priority = 1.0
            weights.append(priority)

        return _weighted_choice(candidates, weights)

    def select_matches(
        self, agents: List[LeagueAgent], all_league: List[LeagueAgent],
        matches_per_agent: int = 2, mode: str = "pfsp",
    ) -> List[Tuple[str, str]]:
        """Select matchups for a batch of agents."""
        matches: List[Tuple[str, str]] = []
        for agent in agents:
            if agent.status != AgentStatus.ACTIVE:
                continue
            candidates = [a for a in all_league if a.agent_id != agent.agent_id]
            if not candidates:
                continue
            for _ in range(matches_per_agent):
                opp = self.select_opponent(agent, candidates, mode=mode)
                matches.append((agent.agent_id, opp.agent_id))
        return matches


# ============================================================
# Nash Equilibrium Tracker
# ============================================================


class NashEquilibriumTracker:
    """
    Track approximate Nash equilibrium via payoff matrix.
    Computes support (play probability) for each agent using
    fictitious play convergence.
    """

    def __init__(self):
        self.payoff_matrix: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.game_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.nash_history: List[Dict[str, float]] = []

    def update(self, a_id: str, b_id: str, score_a: float) -> None:
        """Record match outcome in payoff matrix."""
        self.payoff_matrix[a_id][b_id] += score_a
        self.payoff_matrix[b_id][a_id] += (1.0 - score_a)
        self.game_counts[a_id][b_id] += 1
        self.game_counts[b_id][a_id] += 1

    def average_payoff(self, a_id: str, b_id: str) -> float:
        cnt = self.game_counts[a_id][b_id]
        if cnt == 0:
            return 0.5
        return self.payoff_matrix[a_id][b_id] / cnt

    def compute_nash_approximation(self, agent_ids: List[str]) -> Dict[str, float]:
        """
        Approximate Nash equilibrium via iterative fictitious play.
        Returns a probability distribution over agents.
        """
        n = len(agent_ids)
        if n == 0:
            return {}
        if n == 1:
            return {agent_ids[0]: 1.0}

        # Build payoff matrix
        payoff = [[0.0] * n for _ in range(n)]
        for i, ai in enumerate(agent_ids):
            for j, aj in enumerate(agent_ids):
                if i != j:
                    payoff[i][j] = self.average_payoff(ai, aj) - 0.5

        # Fictitious play iterations
        counts = [1.0] * n
        for _ in range(200):
            # Each player best-responds to current mixed strategy
            probs = [c / sum(counts) for c in counts]
            for i in range(n):
                # Expected payoff of playing against mixed strategy
                best_val = -float("inf")
                best_j = 0
                for j in range(n):
                    expected = sum(probs[k] * payoff[j][k] for k in range(n))
                    if expected > best_val:
                        best_val = expected
                        best_j = j
                counts[best_j] += 1.0

        total = sum(counts)
        result = {aid: counts[i] / total for i, aid in enumerate(agent_ids)}
        self.nash_history.append(result.copy())
        return result

    def nash_exploitability(self, agent_ids: List[str]) -> float:
        """Estimate exploitability of the current Nash approximation."""
        nash = self.compute_nash_approximation(agent_ids)
        if not nash:
            return 0.0

        # Max deviation payoff
        n = len(agent_ids)
        max_deviation = 0.0
        for i, ai in enumerate(agent_ids):
            # Payoff of pure strategy i against Nash mix
            payoff_i = 0.0
            for j, aj in enumerate(agent_ids):
                if i != j:
                    payoff_i += nash.get(aj, 0.0) * self.average_payoff(ai, aj)
            max_deviation = max(max_deviation, abs(payoff_i - 0.5))

        return max_deviation


# ============================================================
# League Statistics Dashboard
# ============================================================


class LeagueDashboard:
    """Generate league statistics and ASCII visualizations."""

    @staticmethod
    def agent_summary_table(agents: List[LeagueAgent]) -> str:
        sorted_agents = sorted(agents, key=lambda a: a.elo, reverse=True)
        lines = [
            f"{'Rank':>4s} {'Agent':>16s} {'Type':>16s} {'Status':>8s} "
            f"{'ELO':>7s} {'WR':>6s} {'Games':>6s} {'Steps':>7s} {'Gen':>4s}"
        ]
        lines.append("-" * 100)
        for rank, agent in enumerate(sorted_agents, 1):
            lines.append(
                f"{rank:4d} {agent.agent_id:>16s} {agent.agent_type.value:>16s} "
                f"{agent.status.value:>8s} {agent.elo:7.1f} {agent.win_rate:6.1%} "
                f"{agent.games_played:6d} {agent.training_steps:7d} {agent.generation:4d}"
            )
        return "\n".join(lines)

    @staticmethod
    def elo_history_chart(agents: List[LeagueAgent], width: int = 60, height: int = 15) -> str:
        """ASCII chart of ELO ratings over time."""
        all_data: List[Tuple[str, List[Tuple[int, float]]]] = []
        for agent in agents:
            if agent.rating_history:
                all_data.append((agent.agent_id, agent.rating_history))

        if not all_data:
            return "(no rating history)"

        all_vals = [v for _, hist in all_data for _, v in hist]
        all_steps = [s for _, hist in all_data for s, _ in hist]
        if not all_vals:
            return "(empty)"

        lo, hi = min(all_vals), max(all_vals)
        if lo == hi:
            hi = lo + 50
        min_s, max_s = min(all_steps), max(all_steps)
        if min_s == max_s:
            max_s = min_s + 1

        symbols = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop"
        canvas = [[" "] * width for _ in range(height)]

        for idx, (aid, hist) in enumerate(all_data):
            sym = symbols[idx % len(symbols)]
            for step, val in hist:
                x = int((step - min_s) / (max_s - min_s) * (width - 1))
                y = int((val - lo) / (hi - lo) * (height - 1))
                y = max(0, min(height - 1, y))
                canvas[height - 1 - y][x] = sym

        lines = ["  ELO Ratings Over Training Steps"]
        legend = "  Legend: " + ", ".join(
            f"{symbols[i % len(symbols)]}={aid[:10]}" for i, (aid, _) in enumerate(all_data[:10])
        )
        lines.append(legend)
        lines.append(f"  {hi:.0f} |")
        for row in canvas:
            lines.append("       |" + "".join(row))
        lines.append(f"  {lo:.0f} |" + "-" * width)
        lines.append(f"       step {min_s} -> {max_s}")
        return "\n".join(lines)

    @staticmethod
    def type_distribution(agents: List[LeagueAgent]) -> str:
        counts: Dict[str, int] = defaultdict(int)
        active_counts: Dict[str, int] = defaultdict(int)
        for a in agents:
            counts[a.agent_type.value] += 1
            if a.status == AgentStatus.ACTIVE:
                active_counts[a.agent_type.value] += 1
        lines = ["  Agent Type Distribution:"]
        for t in AgentType:
            lines.append(f"    {t.value:>20s}: {counts[t.value]:3d} total, "
                         f"{active_counts[t.value]:3d} active")
        return "\n".join(lines)

    @staticmethod
    def win_rate_matrix(agents: List[LeagueAgent], top_n: int = 8) -> str:
        """Show head-to-head win rate matrix for top agents."""
        sorted_a = sorted(agents, key=lambda a: a.elo, reverse=True)[:top_n]
        ids = [a.agent_id for a in sorted_a]

        header = "         " + " ".join(f"{aid[:6]:>6s}" for aid in ids)
        lines = ["  Win Rate Matrix (row vs col):", header]
        for a in sorted_a:
            row = f"{a.agent_id[:8]:>8s} "
            for b in sorted_a:
                if a.agent_id == b.agent_id:
                    row += "   --- "
                else:
                    wr = a.win_rate_vs(b.agent_id)
                    row += f" {wr:5.1%} "
            lines.append(row)
        return "\n".join(lines)


# ============================================================
# SC2 League System (Main Class)
# ============================================================


class SC2LeagueSystem:
    """
    AlphaStar-style league training system for SC2 bots.

    Manages three types of agents:
    - Main agents: train against full league, occasionally frozen
    - Main exploiters: specifically target main agents' weaknesses
    - League exploiters: target entire league weaknesses

    Uses PFSP matchmaking and tracks Nash equilibrium approximation.
    """

    def __init__(
        self,
        num_main_agents: int = 3,
        num_main_exploiters: int = 2,
        num_league_exploiters: int = 2,
        weight_dim: int = 64,
        freeze_after_steps: int = 2000,
        promotion_win_rate: float = 0.7,
        max_frozen_copies: int = 20,
        pfsp_temperature: float = 1.0,
        seed: Optional[int] = None,
    ):
        if seed is not None:
            random.seed(seed)
            if NP_AVAILABLE:
                np.random.seed(seed)

        self.weight_dim = weight_dim
        self.freeze_after_steps = freeze_after_steps
        self.promotion_win_rate = promotion_win_rate
        self.max_frozen_copies = max_frozen_copies
        self.iteration = 0

        # All agents (active + frozen)
        self.agents: Dict[str, LeagueAgent] = {}
        self.matchmaker = PFSPMatchmaker(pfsp_temperature=pfsp_temperature)
        self.match_db = MatchHistoryDB()
        self.nash_tracker = NashEquilibriumTracker()
        self.dashboard = LeagueDashboard()

        # Counters
        self.total_freezes = 0
        self.total_promotions = 0

        # Initialize population
        self._init_population(num_main_agents, num_main_exploiters, num_league_exploiters)

    def _init_population(self, n_main: int, n_mexpl: int, n_lexpl: int) -> None:
        idx = 0
        for _ in range(n_main):
            aid = f"main_{idx:03d}"
            self.agents[aid] = LeagueAgent(
                agent_id=aid, agent_type=AgentType.MAIN_AGENT,
                weights=PolicyWeights(self.weight_dim),
            )
            idx += 1
        for _ in range(n_mexpl):
            aid = f"mexpl_{idx:03d}"
            self.agents[aid] = LeagueAgent(
                agent_id=aid, agent_type=AgentType.MAIN_EXPLOITER,
                weights=PolicyWeights(self.weight_dim),
            )
            idx += 1
        for _ in range(n_lexpl):
            aid = f"lexpl_{idx:03d}"
            self.agents[aid] = LeagueAgent(
                agent_id=aid, agent_type=AgentType.LEAGUE_EXPLOITER,
                weights=PolicyWeights(self.weight_dim),
            )
            idx += 1

    # --------------------------------------------------------
    # Agent Access Helpers
    # --------------------------------------------------------

    @property
    def active_agents(self) -> List[LeagueAgent]:
        return [a for a in self.agents.values() if a.status == AgentStatus.ACTIVE]

    @property
    def frozen_agents(self) -> List[LeagueAgent]:
        return [a for a in self.agents.values() if a.status == AgentStatus.FROZEN]

    @property
    def main_agents(self) -> List[LeagueAgent]:
        return [a for a in self.agents.values()
                if a.agent_type == AgentType.MAIN_AGENT and a.status == AgentStatus.ACTIVE]

    @property
    def all_league_agents(self) -> List[LeagueAgent]:
        """All agents in the league (active + frozen, but not retired)."""
        return [a for a in self.agents.values() if a.status != AgentStatus.RETIRED]

    def get_agent(self, agent_id: str) -> Optional[LeagueAgent]:
        return self.agents.get(agent_id)

    # --------------------------------------------------------
    # Training Step Simulation
    # --------------------------------------------------------

    def _simulate_training(self, agent: LeagueAgent, steps: int = 100) -> None:
        """Simulate training an agent for some steps."""
        if agent.status != AgentStatus.ACTIVE:
            return
        agent.training_steps += steps
        # Perturb weights slightly (simulating gradient updates)
        if NP_AVAILABLE:
            noise = np.random.randn(agent.weights.dim).astype(np.float32) * 0.01
            agent.weights.data = agent.weights.data + noise
        else:
            noise = _np_random_normal(0, 0.01, agent.weights.dim)
            agent.weights.data = [w + n for w, n in zip(agent.weights.data, noise)]

    # --------------------------------------------------------
    # Match Execution
    # --------------------------------------------------------

    def play_match(self, a_id: str, b_id: str) -> MatchRecord:
        """Play a match between two agents and record results."""
        a = self.agents[a_id]
        b = self.agents[b_id]
        elo_a_before = a.elo
        elo_b_before = b.elo

        winner_id, score_a, score_b = SC2MatchSimulator.simulate(a, b)

        # Update ELO
        ELORatingSystem.update_ratings(a, b, score_a, score_b)

        # Update game counts
        a.games_played += 1
        b.games_played += 1

        if winner_id == a_id:
            a.wins += 1
            b.losses += 1
            a.opponent_records[b_id]["wins"] += 1
            b.opponent_records[a_id]["losses"] += 1
        elif winner_id == b_id:
            b.wins += 1
            a.losses += 1
            b.opponent_records[a_id]["wins"] += 1
            a.opponent_records[b_id]["losses"] += 1
        else:
            a.draws += 1
            b.draws += 1
            a.opponent_records[b_id]["draws"] += 1
            b.opponent_records[a_id]["draws"] += 1

        # Update Nash tracker
        self.nash_tracker.update(a_id, b_id, score_a)

        # Record to match DB
        record = MatchRecord(
            match_id=f"match_{uuid.uuid4().hex[:8]}",
            agent_a_id=a_id, agent_b_id=b_id,
            winner_id=winner_id,
            score_a=score_a, score_b=score_b,
            elo_a_before=elo_a_before, elo_b_before=elo_b_before,
            elo_a_after=a.elo, elo_b_after=b.elo,
        )
        self.match_db.add(record)
        return record

    # --------------------------------------------------------
    # Matchmaking (per agent type)
    # --------------------------------------------------------

    def generate_matchups(self, matches_per_agent: int = 2) -> List[Tuple[str, str]]:
        """Generate matchups according to agent type rules."""
        all_matches: List[Tuple[str, str]] = []
        league = self.all_league_agents

        for agent in self.active_agents:
            if agent.agent_type == AgentType.MAIN_AGENT:
                # Main agents play against full league (PFSP)
                candidates = [a for a in league if a.agent_id != agent.agent_id]
                mode = "pfsp"
            elif agent.agent_type == AgentType.MAIN_EXPLOITER:
                # Main exploiters target only active main agents
                candidates = [a for a in self.main_agents if a.agent_id != agent.agent_id]
                if not candidates:
                    candidates = [a for a in league if a.agent_id != agent.agent_id]
                mode = "hard"
            elif agent.agent_type == AgentType.LEAGUE_EXPLOITER:
                # League exploiters target entire league
                candidates = [a for a in league if a.agent_id != agent.agent_id]
                mode = "pfsp"
            else:
                continue

            if not candidates:
                continue

            for _ in range(matches_per_agent):
                opp = self.matchmaker.select_opponent(agent, candidates, mode=mode)
                all_matches.append((agent.agent_id, opp.agent_id))

        return all_matches

    # --------------------------------------------------------
    # Freezing and Promotion Logic
    # --------------------------------------------------------

    def check_freeze_conditions(self) -> List[str]:
        """Check which agents should be frozen (snapshot into league)."""
        frozen_ids: List[str] = []
        current_frozen_count = len(self.frozen_agents)

        for agent in self.active_agents:
            if agent.agent_type != AgentType.MAIN_AGENT:
                continue
            if agent.training_steps < self.freeze_after_steps:
                continue
            if current_frozen_count >= self.max_frozen_copies:
                continue

            # Freeze: create a frozen copy, reset the active agent
            frozen_id = f"{agent.agent_id}_f{self.total_freezes:03d}"
            frozen_copy = LeagueAgent(
                agent_id=frozen_id,
                agent_type=AgentType.MAIN_AGENT,
                status=AgentStatus.FROZEN,
                weights=agent.weights.clone(),
                elo=agent.elo,
                games_played=agent.games_played,
                wins=agent.wins,
                losses=agent.losses,
                draws=agent.draws,
                training_steps=agent.training_steps,
                generation=agent.generation,
                parent_id=agent.agent_id,
                frozen_at=time.time(),
                rating_history=list(agent.rating_history),
            )
            # Copy opponent records
            for opp_id, rec in agent.opponent_records.items():
                frozen_copy.opponent_records[opp_id] = dict(rec)

            self.agents[frozen_id] = frozen_copy
            self.total_freezes += 1
            current_frozen_count += 1

            # Reset active agent's training counter (it keeps learning)
            agent.generation += 1
            agent.training_steps = 0
            frozen_ids.append(frozen_id)

        return frozen_ids

    def check_promotion_conditions(self) -> List[str]:
        """
        Check exploiters for promotion.
        If an exploiter achieves high win rate against all main agents,
        it gets promoted to main agent.
        """
        promoted: List[str] = []

        for agent in self.active_agents:
            if agent.agent_type not in (AgentType.MAIN_EXPLOITER, AgentType.LEAGUE_EXPLOITER):
                continue
            if agent.games_played < 20:
                continue

            main_ids = [a.agent_id for a in self.main_agents]
            if not main_ids:
                continue

            # Check win rate against main agents
            win_rates = [agent.win_rate_vs(mid) for mid in main_ids]
            avg_wr = _np_mean(win_rates)

            if avg_wr >= self.promotion_win_rate:
                # Promote: change type to main agent
                old_type = agent.agent_type
                agent.agent_type = AgentType.MAIN_AGENT
                agent.generation += 1
                self.total_promotions += 1
                promoted.append(agent.agent_id)

                # Spawn a new exploiter to replace
                new_id = f"{'mexpl' if old_type == AgentType.MAIN_EXPLOITER else 'lexpl'}_{len(self.agents):03d}"
                new_agent = LeagueAgent(
                    agent_id=new_id,
                    agent_type=old_type,
                    weights=PolicyWeights(self.weight_dim),
                    parent_id=agent.agent_id,
                )
                self.agents[new_id] = new_agent

        return promoted

    # --------------------------------------------------------
    # Full Training Iteration
    # --------------------------------------------------------

    def train_iteration(self, train_steps: int = 100, matches_per_agent: int = 2) -> Dict[str, Any]:
        """One full league training iteration."""
        self.iteration += 1
        results: Dict[str, Any] = {"iteration": self.iteration}

        # 1. Train all active agents
        for agent in self.active_agents:
            self._simulate_training(agent, steps=train_steps)

        # 2. Generate and play matches
        matchups = self.generate_matchups(matches_per_agent=matches_per_agent)
        match_results = []
        for a_id, b_id in matchups:
            if a_id in self.agents and b_id in self.agents:
                rec = self.play_match(a_id, b_id)
                match_results.append(rec)

        results["matches_played"] = len(match_results)

        # 3. Record rating histories
        for agent in self.active_agents:
            agent.record_rating()

        # 4. Freeze check (every 5 iterations)
        frozen = []
        if self.iteration % 5 == 0:
            frozen = self.check_freeze_conditions()
        results["frozen"] = frozen

        # 5. Promotion check (every 10 iterations)
        promoted = []
        if self.iteration % 10 == 0:
            promoted = self.check_promotion_conditions()
        results["promoted"] = promoted

        # 6. Stats
        elos = [a.elo for a in self.active_agents]
        results["elo_mean"] = _np_mean(elos) if elos else 0.0
        results["elo_max"] = max(elos) if elos else 0.0
        results["elo_min"] = min(elos) if elos else 0.0
        results["active_agents"] = len(self.active_agents)
        results["frozen_agents"] = len(self.frozen_agents)
        results["total_agents"] = len(self.agents)
        results["total_matches"] = self.match_db.total_matches()

        return results

    def run(self, num_iterations: int = 50, train_steps: int = 100,
            matches_per_agent: int = 2) -> List[Dict[str, Any]]:
        """Run full league training."""
        all_results = []
        for _ in range(num_iterations):
            r = self.train_iteration(train_steps, matches_per_agent)
            all_results.append(r)
        return all_results

    # --------------------------------------------------------
    # Nash Equilibrium
    # --------------------------------------------------------

    def compute_nash(self) -> Dict[str, float]:
        active_ids = [a.agent_id for a in self.active_agents]
        return self.nash_tracker.compute_nash_approximation(active_ids)

    def nash_exploitability(self) -> float:
        active_ids = [a.agent_id for a in self.active_agents]
        return self.nash_tracker.nash_exploitability(active_ids)

    # --------------------------------------------------------
    # Dashboard Output
    # --------------------------------------------------------

    def league_summary(self) -> str:
        lines = ["=" * 100]
        lines.append(f"  SC2 League System  |  Iteration: {self.iteration}  |  "
                      f"Freezes: {self.total_freezes}  Promotions: {self.total_promotions}")
        lines.append("=" * 100)
        lines.append("")
        lines.append(self.dashboard.agent_summary_table(list(self.agents.values())))
        lines.append("")
        lines.append(self.dashboard.type_distribution(list(self.agents.values())))
        lines.append("")
        lines.append(f"  Total matches: {self.match_db.total_matches()}")
        lines.append(f"  Nash exploitability: {self.nash_exploitability():.4f}")
        lines.append("=" * 100)
        return "\n".join(lines)

    def elo_chart(self) -> str:
        return self.dashboard.elo_history_chart(list(self.agents.values()))

    def win_rate_matrix(self) -> str:
        return self.dashboard.win_rate_matrix(list(self.agents.values()))

    # --------------------------------------------------------
    # Checkpoint Save/Load
    # --------------------------------------------------------

    def save_checkpoint(self, path: str) -> str:
        data = {
            "iteration": self.iteration,
            "total_freezes": self.total_freezes,
            "total_promotions": self.total_promotions,
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()},
            "match_count": self.match_db.total_matches(),
            "nash_history_len": len(self.nash_tracker.nash_history),
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def load_checkpoint(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.iteration = data.get("iteration", 0)
        self.total_freezes = data.get("total_freezes", 0)
        self.total_promotions = data.get("total_promotions", 0)
        self.agents.clear()
        for aid, ad in data.get("agents", {}).items():
            self.agents[aid] = LeagueAgent.from_dict(ad)


# ============================================================
# CLI Demo
# ============================================================


def run_league_demo() -> None:
    """Run a full league training demo with console output."""
    print("=" * 70)
    print("  Phase 611: SC2 AlphaStar-Style League Training Demo")
    print("=" * 70)
    print()

    league = SC2LeagueSystem(
        num_main_agents=3,
        num_main_exploiters=2,
        num_league_exploiters=2,
        weight_dim=32,
        freeze_after_steps=500,
        promotion_win_rate=0.65,
        max_frozen_copies=10,
        pfsp_temperature=1.0,
        seed=42,
    )

    print(f"[Init] Main agents: {len(league.main_agents)}")
    print(f"[Init] Total agents: {len(league.agents)}")
    print(f"[Init] Weight dim: {league.weight_dim}")
    print()

    # List initial agents
    print("--- Initial Agents ---")
    for aid, agent in sorted(league.agents.items()):
        print(f"  {aid}: type={agent.agent_type.value}, elo={agent.elo:.0f}")
    print()

    # Training loop
    num_iters = 40
    print(f"--- Running {num_iters} league iterations ---")
    for i in range(num_iters):
        result = league.train_iteration(train_steps=100, matches_per_agent=2)
        if (i + 1) % 5 == 0:
            frozen_str = f", frozen={result['frozen']}" if result["frozen"] else ""
            promoted_str = f", promoted={result['promoted']}" if result["promoted"] else ""
            print(
                f"  Iter {result['iteration']:3d}: "
                f"matches={result['matches_played']:3d}  "
                f"elo_mean={result['elo_mean']:.1f}  "
                f"elo_max={result['elo_max']:.1f}  "
                f"active={result['active_agents']}  "
                f"frozen={result['frozen_agents']}  "
                f"total={result['total_agents']}"
                f"{frozen_str}{promoted_str}"
            )
    print()

    # Full league summary
    print(league.league_summary())
    print()

    # ELO chart
    print(league.elo_chart())
    print()

    # Win rate matrix
    print(league.win_rate_matrix())
    print()

    # Nash equilibrium
    print("--- Nash Equilibrium Approximation ---")
    nash = league.compute_nash()
    for aid, prob in sorted(nash.items(), key=lambda x: -x[1]):
        print(f"  {aid:>20s}: {prob:.4f}")
    print(f"  Exploitability: {league.nash_exploitability():.4f}")
    print()

    # Recent matches
    print("--- Recent Matches ---")
    for rec in league.match_db.recent(5):
        winner_str = rec.winner_id or "DRAW"
        print(
            f"  {rec.agent_a_id} vs {rec.agent_b_id}: "
            f"winner={winner_str}  "
            f"elo: {rec.elo_a_before:.0f}->{rec.elo_a_after:.0f} / "
            f"{rec.elo_b_before:.0f}->{rec.elo_b_after:.0f}"
        )
    print()

    # Head-to-head example
    agents_list = list(league.agents.keys())
    if len(agents_list) >= 2:
        a, b = agents_list[0], agents_list[1]
        h2h = league.match_db.head_to_head(a, b)
        print(f"--- Head-to-Head: {a} vs {b} ---")
        print(f"  {a} wins: {h2h['a_wins']}, {b} wins: {h2h['b_wins']}, draws: {h2h['draws']}")
    print()

    # Checkpoint save/load test
    ckpt_path = "league_demo_checkpoint.json"
    league.save_checkpoint(ckpt_path)
    print(f"[Checkpoint] Saved to: {ckpt_path}")

    league2 = SC2LeagueSystem(num_main_agents=1, seed=99)
    league2.load_checkpoint(ckpt_path)
    print(f"[Checkpoint] Loaded {len(league2.agents)} agents, iteration={league2.iteration}")

    # Clean up
    try:
        os.remove(ckpt_path)
        print(f"[Cleanup] Removed {ckpt_path}")
    except OSError:
        pass

    # Type distribution
    print()
    print(league.dashboard.type_distribution(list(league.agents.values())))

    print()
    print("=" * 70)
    print("  Phase 611 Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    run_league_demo()
