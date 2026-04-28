"""
Phase 349: Self-Play Manager
Self-play matchmaking and opponent pool management for SC2 bot training.
"""

import copy
import math
import os
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import torch


class AgentRole(Enum):
    MAIN_AGENT = "main_agent"
    LEAGUE_EXPLOITER = "league_exploiter"
    MAIN_EXPLOITER = "main_exploiter"


@dataclass
class OpponentEntry:
    checkpoint_path: str
    elo: float = 1000.0
    wins: int = 0
    losses: int = 0
    role: AgentRole = AgentRole.MAIN_AGENT
    step: int = 0

    @property
    def games_played(self) -> int:
        return self.wins + self.losses

    @property
    def win_rate(self) -> float:
        if self.games_played == 0:
            return 0.5
        return self.wins / self.games_played


class OpponentPool:
    """Stores and manages past model checkpoints for self-play."""

    def __init__(
        self, max_size: int = 20, checkpoint_dir: str = "checkpoints/opponents"
    ):
        self.max_size = max_size
        self.checkpoint_dir = checkpoint_dir
        self.pool: List[OpponentEntry] = []
        os.makedirs(checkpoint_dir, exist_ok=True)

    def add(
        self,
        model: torch.nn.Module,
        step: int,
        elo: float = 1000.0,
        role: AgentRole = AgentRole.MAIN_AGENT,
    ) -> OpponentEntry:
        path = os.path.join(self.checkpoint_dir, f"opponent_step{step}.pt")
        torch.save(model.state_dict(), path)
        entry = OpponentEntry(checkpoint_path=path, elo=elo, role=role, step=step)
        self.pool.append(entry)
        if len(self.pool) > self.max_size:
            self.pool.pop(0)
        return entry

    def sample_opponent(self, strategy: str = "pfsp") -> Optional[OpponentEntry]:
        if not self.pool:
            return None
        if strategy == "uniform":
            return random.choice(self.pool)
        if strategy == "pfsp":
            # Prioritized Fictitious Self-Play: weight by (1 - win_rate)
            weights = [max(0.05, 1.0 - e.win_rate) for e in self.pool]
            total = sum(weights)
            probs = [w / total for w in weights]
            return random.choices(self.pool, weights=probs, k=1)[0]
        if strategy == "latest":
            return self.pool[-1]
        return random.choice(self.pool)

    def load_opponent_model(
        self, entry: OpponentEntry, model_cls, model_kwargs: Dict
    ) -> torch.nn.Module:
        model = model_cls(**model_kwargs)
        model.load_state_dict(torch.load(entry.checkpoint_path, map_location="cpu"))
        model.eval()
        return model

    def __len__(self) -> int:
        return len(self.pool)


def calculate_elo(
    winner_elo: float, loser_elo: float, k: float = 32.0
) -> Tuple[float, float]:
    """Compute new Elo ratings after a match."""
    expected_win = 1.0 / (1.0 + math.pow(10, (loser_elo - winner_elo) / 400.0))
    new_winner = winner_elo + k * (1.0 - expected_win)
    new_loser = loser_elo + k * (0.0 - (1.0 - expected_win))
    return new_winner, new_loser


class SelfPlayManager:
    """Orchestrates league training across agent roles."""

    ROLE_SAMPLE_PROBS: Dict[AgentRole, float] = {
        AgentRole.MAIN_AGENT: 0.35,
        AgentRole.LEAGUE_EXPLOITER: 0.35,
        AgentRole.MAIN_EXPLOITER: 0.30,
    }

    def __init__(
        self,
        main_model: torch.nn.Module,
        pool: OpponentPool,
        checkpoint_interval: int = 1000,
    ):
        self.main_model = main_model
        self.pool = pool
        self.checkpoint_interval = checkpoint_interval
        self.match_history: List[Dict] = []
        self.step = 0
        self.main_elo = 1000.0

    def sample_opponent(self) -> Optional[OpponentEntry]:
        role_weights = list(self.ROLE_SAMPLE_PROBS.values())
        chosen_role = random.choices(
            list(self.ROLE_SAMPLE_PROBS.keys()), weights=role_weights, k=1
        )[0]
        role_pool = [e for e in self.pool.pool if e.role == chosen_role]
        if not role_pool:
            return self.pool.sample_opponent(strategy="pfsp")
        weights = [max(0.05, 1.0 - e.win_rate) for e in role_pool]
        total = sum(weights)
        probs = [w / total for w in weights]
        return random.choices(role_pool, weights=probs, k=1)[0]

    def add_to_pool(self, role: AgentRole = AgentRole.MAIN_AGENT) -> OpponentEntry:
        model_copy = copy.deepcopy(self.main_model)
        entry = self.pool.add(model_copy, step=self.step, elo=self.main_elo, role=role)
        return entry

    def run_match(
        self, env, opponent_entry: OpponentEntry, model_cls, model_kwargs: Dict
    ) -> Dict:
        opponent_model = self.pool.load_opponent_model(
            opponent_entry, model_cls, model_kwargs
        )
        obs = env.reset()
        done = False
        total_reward = 0.0
        steps = 0
        while not done and steps < 10000:
            obs_t = torch.FloatTensor(obs).unsqueeze(0)
            with torch.no_grad():
                logits, _ = self.main_model(obs_t)
            from torch.distributions import Categorical

            action = Categorical(logits=logits).sample().item()
            obs, reward, done, info = env.step(action)
            total_reward += reward
            steps += 1

        result = {
            "winner": "main" if total_reward > 0 else "opponent",
            "total_reward": total_reward,
            "steps": steps,
            "opponent_step": opponent_entry.step,
            "opponent_role": opponent_entry.role.value,
        }
        self._update_records(opponent_entry, won=(total_reward > 0))
        self.match_history.append(result)
        self.step += steps
        if self.step % self.checkpoint_interval < steps:
            self.add_to_pool()
        return result

    def _update_records(self, opponent: OpponentEntry, won: bool) -> None:
        if won:
            opponent.losses += 1
            self.main_elo, opponent.elo = calculate_elo(self.main_elo, opponent.elo)
        else:
            opponent.wins += 1
            opponent.elo, self.main_elo = calculate_elo(opponent.elo, self.main_elo)

    def get_stats(self) -> Dict:
        total = len(self.match_history)
        wins = sum(1 for m in self.match_history if m["winner"] == "main")
        return {
            "total_matches": total,
            "wins": wins,
            "win_rate": wins / total if total else 0.0,
            "main_elo": self.main_elo,
            "pool_size": len(self.pool),
        }
