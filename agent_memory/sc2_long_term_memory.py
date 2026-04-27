"""
Phase 632: Long-Term Agent Memory System for SC2

Persistent memory architecture for StarCraft II AI agents.
Provides episodic memory (game experiences), semantic memory (learned facts),
and working memory (current-game context) with consolidation and forgetting curves.
"""

import math
import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from collections import defaultdict


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_WORKING_MEMORY_SIZE = 64
DEFAULT_DECAY_RATE = 0.02
DEFAULT_CONSOLIDATION_THRESHOLD = 3
DEFAULT_SIMILARITY_THRESHOLD = 0.75
SC2_RACES = ("Zerg", "Terran", "Protoss")
SC2_MATCHUPS = [f"{a}v{b}" for a in SC2_RACES for b in SC2_RACES]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MemoryType(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    WORKING = "working"


class Outcome(Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MemoryEntry:
    """Single memory record with metadata for retrieval and decay."""

    key: str
    content: Dict[str, Any]
    memory_type: MemoryType
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)

    # --- helpers ---

    def touch(self) -> None:
        """Record an access, refreshing the last-accessed timestamp."""
        self.access_count += 1
        self.last_accessed = time.time()

    def strength(
        self, now: Optional[float] = None, decay_rate: float = DEFAULT_DECAY_RATE
    ) -> float:
        """
        Compute memory strength via Ebbinghaus-inspired forgetting curve.
        S(t) = importance * exp(-decay * dt) * log2(2 + access_count)
        """
        now = now or time.time()
        dt = max(now - self.last_accessed, 0.0)
        base = self.importance * math.exp(-decay_rate * dt)
        rehearsal_boost = math.log2(2 + self.access_count)
        return base * rehearsal_boost

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "importance": self.importance,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        data = dict(data)
        data["memory_type"] = MemoryType(data["memory_type"])
        return cls(**data)


# ---------------------------------------------------------------------------
# Episodic Memory
# ---------------------------------------------------------------------------


class EpisodicMemory:
    """
    Stores concrete game experiences: (state, action, outcome, timestamp).
    Each episode is one complete game or a significant in-game event.
    """

    def __init__(self, capacity: int = 5000, decay_rate: float = DEFAULT_DECAY_RATE):
        self.capacity = capacity
        self.decay_rate = decay_rate
        self._episodes: List[MemoryEntry] = []

    # -- storage --

    def store(
        self,
        game_state: Dict[str, Any],
        action: str,
        outcome: Outcome,
        opponent_race: str = "Unknown",
        map_name: str = "Unknown",
        importance: float = 0.5,
        extra_tags: Optional[List[str]] = None,
    ) -> MemoryEntry:
        """Record a game episode."""
        ts = time.time()
        key = hashlib.md5(f"{ts}_{action}_{outcome.value}".encode()).hexdigest()[:12]
        tags = [opponent_race, map_name, outcome.value]
        if extra_tags:
            tags.extend(extra_tags)

        entry = MemoryEntry(
            key=key,
            content={
                "game_state": game_state,
                "action": action,
                "outcome": outcome.value,
                "opponent_race": opponent_race,
                "map_name": map_name,
            },
            memory_type=MemoryType.EPISODIC,
            timestamp=ts,
            importance=importance,
            tags=tags,
        )
        self._episodes.append(entry)
        self._enforce_capacity()
        return entry

    # -- retrieval --

    def recall(
        self,
        opponent_race: Optional[str] = None,
        map_name: Optional[str] = None,
        outcome: Optional[Outcome] = None,
        top_k: int = 10,
    ) -> List[MemoryEntry]:
        """Retrieve episodes matching optional filters, ranked by strength."""
        now = time.time()
        results: List[MemoryEntry] = []
        for ep in self._episodes:
            c = ep.content
            if opponent_race and c.get("opponent_race") != opponent_race:
                continue
            if map_name and c.get("map_name") != map_name:
                continue
            if outcome and c.get("outcome") != outcome.value:
                continue
            results.append(ep)

        results.sort(key=lambda e: e.strength(now, self.decay_rate), reverse=True)
        for r in results[:top_k]:
            r.touch()
        return results[:top_k]

    def recall_by_tags(self, tags: List[str], top_k: int = 10) -> List[MemoryEntry]:
        """Retrieve episodes that contain **all** specified tags."""
        now = time.time()
        tag_set = set(tags)
        matched = [ep for ep in self._episodes if tag_set.issubset(set(ep.tags))]
        matched.sort(key=lambda e: e.strength(now, self.decay_rate), reverse=True)
        for m in matched[:top_k]:
            m.touch()
        return matched[:top_k]

    # -- maintenance --

    def forget(self, threshold: float = 0.01) -> int:
        """Remove episodes whose strength has decayed below *threshold*."""
        now = time.time()
        before = len(self._episodes)
        self._episodes = [
            ep
            for ep in self._episodes
            if ep.strength(now, self.decay_rate) >= threshold
        ]
        return before - len(self._episodes)

    def _enforce_capacity(self) -> None:
        if len(self._episodes) > self.capacity:
            now = time.time()
            self._episodes.sort(key=lambda e: e.strength(now, self.decay_rate))
            self._episodes = self._episodes[len(self._episodes) - self.capacity :]

    @property
    def size(self) -> int:
        return len(self._episodes)


# ---------------------------------------------------------------------------
# Semantic Memory
# ---------------------------------------------------------------------------


class SemanticMemory:
    """
    Stores learned facts and generalized knowledge derived from experience.
    Examples: matchup win-rates, counter-strategy tables, build-order effectiveness.
    """

    def __init__(self, decay_rate: float = DEFAULT_DECAY_RATE * 0.5):
        self.decay_rate = decay_rate
        self._facts: Dict[str, MemoryEntry] = {}
        self._matchup_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"wins": 0, "losses": 0, "draws": 0}
        )
        self._counter_strategies: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # -- fact storage --

    def store_fact(
        self,
        fact_key: str,
        content: Dict[str, Any],
        importance: float = 0.6,
        tags: Optional[List[str]] = None,
    ) -> MemoryEntry:
        """Store or update a semantic fact."""
        if fact_key in self._facts:
            existing = self._facts[fact_key]
            existing.content.update(content)
            existing.importance = max(existing.importance, importance)
            existing.touch()
            return existing

        entry = MemoryEntry(
            key=fact_key,
            content=content,
            memory_type=MemoryType.SEMANTIC,
            importance=importance,
            tags=tags or [],
        )
        self._facts[fact_key] = entry
        return entry

    def recall_fact(self, fact_key: str) -> Optional[MemoryEntry]:
        entry = self._facts.get(fact_key)
        if entry:
            entry.touch()
        return entry

    def search_facts(self, query_tags: List[str], top_k: int = 10) -> List[MemoryEntry]:
        """Retrieve facts containing **any** of the query tags, ranked by relevance."""
        now = time.time()
        tag_set = set(query_tags)
        scored: List[Tuple[float, MemoryEntry]] = []
        for entry in self._facts.values():
            overlap = len(tag_set & set(entry.tags))
            if overlap == 0:
                continue
            score = overlap * entry.strength(now, self.decay_rate)
            scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [e for _, e in scored[:top_k]]
        for r in results:
            r.touch()
        return results

    # -- matchup knowledge --

    def record_matchup_result(self, matchup: str, outcome: Outcome) -> None:
        """Accumulate win/loss/draw counts for a matchup string (e.g. 'ZvT')."""
        if outcome == Outcome.WIN:
            self._matchup_stats[matchup]["wins"] += 1
        elif outcome == Outcome.LOSS:
            self._matchup_stats[matchup]["losses"] += 1
        elif outcome == Outcome.DRAW:
            self._matchup_stats[matchup]["draws"] += 1

    def get_matchup_winrate(self, matchup: str) -> float:
        stats = self._matchup_stats.get(matchup)
        if not stats:
            return 0.0
        total = stats["wins"] + stats["losses"] + stats["draws"]
        if total == 0:
            return 0.0
        return stats["wins"] / total

    def get_matchup_stats(self, matchup: str) -> Dict[str, int]:
        return dict(
            self._matchup_stats.get(matchup, {"wins": 0, "losses": 0, "draws": 0})
        )

    # -- counter strategies --

    def store_counter_strategy(
        self,
        enemy_strategy: str,
        counter: str,
        success_rate: float,
        notes: str = "",
    ) -> None:
        """Record a counter-strategy for a known enemy approach."""
        self._counter_strategies[enemy_strategy].append(
            {
                "counter": counter,
                "success_rate": success_rate,
                "notes": notes,
                "timestamp": time.time(),
            }
        )

    def get_best_counter(self, enemy_strategy: str) -> Optional[Dict[str, Any]]:
        options = self._counter_strategies.get(enemy_strategy, [])
        if not options:
            return None
        return max(options, key=lambda o: o["success_rate"])

    # -- maintenance --

    def forget(self, threshold: float = 0.005) -> int:
        now = time.time()
        before = len(self._facts)
        self._facts = {
            k: v
            for k, v in self._facts.items()
            if v.strength(now, self.decay_rate) >= threshold
        }
        return before - len(self._facts)

    @property
    def size(self) -> int:
        return len(self._facts)


# ---------------------------------------------------------------------------
# Working Memory
# ---------------------------------------------------------------------------


class WorkingMemory:
    """
    Short-term buffer for the current game.
    Holds the last N observations and active goals/plans.
    """

    def __init__(self, capacity: int = DEFAULT_WORKING_MEMORY_SIZE):
        self.capacity = capacity
        self._observations: List[Dict[str, Any]] = []
        self._active_goals: List[str] = []
        self._context: Dict[str, Any] = {}

    # -- observations --

    def push_observation(self, obs: Dict[str, Any]) -> None:
        """Append an observation; evict oldest if over capacity."""
        self._observations.append(obs)
        if len(self._observations) > self.capacity:
            self._observations.pop(0)

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        return self._observations[-n:]

    def get_all_observations(self) -> List[Dict[str, Any]]:
        return list(self._observations)

    # -- goals --

    def set_goals(self, goals: List[str]) -> None:
        self._active_goals = list(goals)

    def add_goal(self, goal: str) -> None:
        if goal not in self._active_goals:
            self._active_goals.append(goal)

    def remove_goal(self, goal: str) -> None:
        if goal in self._active_goals:
            self._active_goals.remove(goal)

    def get_goals(self) -> List[str]:
        return list(self._active_goals)

    # -- context --

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def get_full_context(self) -> Dict[str, Any]:
        return dict(self._context)

    # -- reset --

    def clear(self) -> None:
        """Wipe working memory (typically at game start/end)."""
        self._observations.clear()
        self._active_goals.clear()
        self._context.clear()

    @property
    def size(self) -> int:
        return len(self._observations)


# ---------------------------------------------------------------------------
# Memory Consolidation Engine
# ---------------------------------------------------------------------------


class ConsolidationEngine:
    """
    Moves repeated episodic patterns into semantic memory.
    If a (action, opponent_race) pair appears >= threshold times
    with a consistent outcome, it becomes a semantic fact.
    """

    def __init__(
        self,
        threshold: int = DEFAULT_CONSOLIDATION_THRESHOLD,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        self.threshold = threshold
        self.similarity_threshold = similarity_threshold

    def consolidate(
        self,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
    ) -> int:
        """
        Scan episodic memory for recurring patterns and promote them
        to semantic facts. Returns number of new facts created.
        """
        pattern_counts: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"wins": 0, "losses": 0, "total": 0, "actions": [], "maps": set()}
        )

        for ep in episodic._episodes:
            c = ep.content
            pattern_key = f"{c.get('action', '')}|{c.get('opponent_race', '')}"
            bucket = pattern_counts[pattern_key]
            bucket["total"] += 1
            bucket["actions"].append(c.get("action", ""))
            bucket["maps"].add(c.get("map_name", "Unknown"))
            if c.get("outcome") == Outcome.WIN.value:
                bucket["wins"] += 1
            elif c.get("outcome") == Outcome.LOSS.value:
                bucket["losses"] += 1

        new_facts = 0
        for pattern_key, stats in pattern_counts.items():
            if stats["total"] < self.threshold:
                continue
            action, race = pattern_key.split("|", 1)
            win_rate = stats["wins"] / stats["total"] if stats["total"] else 0.0

            fact_key = f"pattern_{pattern_key}"
            semantic.store_fact(
                fact_key=fact_key,
                content={
                    "action": action,
                    "opponent_race": race,
                    "win_rate": round(win_rate, 3),
                    "sample_size": stats["total"],
                    "maps": sorted(stats["maps"]),
                    "consolidated_at": time.time(),
                },
                importance=0.4 + 0.4 * win_rate,
                tags=[race, action, "consolidated"],
            )
            new_facts += 1

        return new_facts


# ---------------------------------------------------------------------------
# Memory Manager - unified facade
# ---------------------------------------------------------------------------


class MemoryManager:
    """
    Top-level controller that owns all memory subsystems.
    Provides SC2-specific convenience methods for storing and recalling
    opponent tendencies, map strategies, and game experiences.
    """

    def __init__(
        self,
        episodic_capacity: int = 5000,
        working_capacity: int = DEFAULT_WORKING_MEMORY_SIZE,
        decay_rate: float = DEFAULT_DECAY_RATE,
        consolidation_threshold: int = DEFAULT_CONSOLIDATION_THRESHOLD,
    ):
        self.episodic = EpisodicMemory(
            capacity=episodic_capacity, decay_rate=decay_rate
        )
        self.semantic = SemanticMemory(decay_rate=decay_rate * 0.5)
        self.working = WorkingMemory(capacity=working_capacity)
        self._consolidation = ConsolidationEngine(threshold=consolidation_threshold)
        self._game_count = 0

    # -- high-level SC2 API --

    def on_game_start(self, opponent_race: str, map_name: str) -> None:
        """Reset working memory and set context for a new game."""
        self.working.clear()
        self.working.set_context("opponent_race", opponent_race)
        self.working.set_context("map_name", map_name)
        self.working.set_context("game_start_time", time.time())
        self._game_count += 1

    def on_step(self, observation: Dict[str, Any]) -> None:
        """Push a game-tick observation into working memory."""
        self.working.push_observation(observation)

    def on_game_end(
        self, outcome: Outcome, summary_action: str = "default"
    ) -> MemoryEntry:
        """
        Finalize the game: store an episode, update matchup stats,
        and periodically consolidate.
        """
        race = self.working.get_context("opponent_race", "Unknown")
        map_name = self.working.get_context("map_name", "Unknown")

        game_state = {
            "observations_count": self.working.size,
            "goals": self.working.get_goals(),
            "context": self.working.get_full_context(),
        }

        entry = self.episodic.store(
            game_state=game_state,
            action=summary_action,
            outcome=outcome,
            opponent_race=race,
            map_name=map_name,
            importance=0.7 if outcome == Outcome.WIN else 0.5,
        )

        matchup = (
            f"{self.working.get_context('my_race', 'Z')}v{race[0] if race else '?'}"
        )
        self.semantic.record_matchup_result(matchup, outcome)

        # periodic consolidation
        if self._game_count % 5 == 0:
            self.consolidate()

        return entry

    def consolidate(self) -> int:
        """Run episodic-to-semantic consolidation."""
        return self._consolidation.consolidate(self.episodic, self.semantic)

    def run_forgetting(
        self, episodic_threshold: float = 0.01, semantic_threshold: float = 0.005
    ) -> Dict[str, int]:
        """Apply forgetting curves to both long-term stores."""
        return {
            "episodic_forgotten": self.episodic.forget(episodic_threshold),
            "semantic_forgotten": self.semantic.forget(semantic_threshold),
        }

    # -- opponent tendencies --

    def remember_opponent_tendency(
        self,
        opponent_name: str,
        tendency: str,
        confidence: float = 0.5,
    ) -> MemoryEntry:
        """Store a learned tendency about a specific opponent."""
        return self.semantic.store_fact(
            fact_key=f"opponent_tendency_{opponent_name}_{tendency}",
            content={
                "opponent": opponent_name,
                "tendency": tendency,
                "confidence": confidence,
                "observed_at": time.time(),
            },
            importance=0.5 + 0.3 * confidence,
            tags=[opponent_name, "tendency", tendency],
        )

    def recall_opponent_tendencies(self, opponent_name: str) -> List[MemoryEntry]:
        return self.semantic.search_facts([opponent_name, "tendency"], top_k=20)

    # -- map strategies --

    def remember_map_strategy(
        self,
        map_name: str,
        strategy: str,
        effectiveness: float = 0.5,
    ) -> MemoryEntry:
        return self.semantic.store_fact(
            fact_key=f"map_strategy_{map_name}_{strategy}",
            content={
                "map_name": map_name,
                "strategy": strategy,
                "effectiveness": effectiveness,
            },
            importance=0.4 + 0.4 * effectiveness,
            tags=[map_name, "map_strategy", strategy],
        )

    def recall_map_strategies(self, map_name: str) -> List[MemoryEntry]:
        return self.semantic.search_facts([map_name, "map_strategy"], top_k=10)

    # -- serialization --

    def save(self, path: str) -> None:
        """Persist all long-term memories to a JSON file."""
        data = {
            "episodic": [e.to_dict() for e in self.episodic._episodes],
            "semantic": {k: v.to_dict() for k, v in self.semantic._facts.items()},
            "matchup_stats": dict(self.semantic._matchup_stats),
            "counter_strategies": dict(self.semantic._counter_strategies),
            "game_count": self._game_count,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, path: str) -> None:
        """Restore long-term memories from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.episodic._episodes = [
            MemoryEntry.from_dict(d) for d in data.get("episodic", [])
        ]
        self.semantic._facts = {
            k: MemoryEntry.from_dict(v) for k, v in data.get("semantic", {}).items()
        }
        for matchup, stats in data.get("matchup_stats", {}).items():
            self.semantic._matchup_stats[matchup] = stats
        for strat, entries in data.get("counter_strategies", {}).items():
            self.semantic._counter_strategies[strat] = entries
        self._game_count = data.get("game_count", 0)

    # -- summary --

    def summary(self) -> Dict[str, Any]:
        return {
            "episodic_count": self.episodic.size,
            "semantic_facts": self.semantic.size,
            "working_observations": self.working.size,
            "working_goals": self.working.get_goals(),
            "total_games": self._game_count,
            "matchup_stats": dict(self.semantic._matchup_stats),
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate the Long-Term Agent Memory system with a simulated SC2 session."""
    print("=" * 70)
    print("Phase 632: Long-Term Agent Memory - Demo")
    print("=" * 70)

    manager = MemoryManager(
        episodic_capacity=100,
        working_capacity=32,
        consolidation_threshold=2,
    )

    # --- Simulate several games ---
    games = [
        ("Terran", "Equilibrium", Outcome.WIN, "ling_bane_rush"),
        ("Terran", "Equilibrium", Outcome.WIN, "ling_bane_rush"),
        ("Protoss", "Golden Wall", Outcome.LOSS, "roach_hydra"),
        ("Protoss", "Golden Wall", Outcome.WIN, "nydus_swarm_host"),
        ("Terran", "Site Delta", Outcome.LOSS, "muta_ling"),
        ("Zerg", "Equilibrium", Outcome.WIN, "roach_ravager"),
    ]

    for race, map_name, outcome, action in games:
        manager.working.set_context("my_race", "Zerg")
        manager.on_game_start(race, map_name)

        # push some fake observations
        for tick in range(5):
            manager.on_step(
                {
                    "tick": tick,
                    "minerals": 400 + tick * 50,
                    "gas": 200 + tick * 25,
                    "supply": 50 + tick * 10,
                }
            )

        manager.on_game_end(outcome, summary_action=action)

    # --- Store opponent tendencies ---
    manager.remember_opponent_tendency("MarinePrince", "early_barracks_rush", 0.8)
    manager.remember_opponent_tendency("MarinePrince", "late_game_mech_transition", 0.6)

    # --- Store map strategies ---
    manager.remember_map_strategy("Equilibrium", "fast_third_expand", 0.9)
    manager.remember_map_strategy("Golden Wall", "nydus_cheese", 0.4)

    # --- Store counter strategy ---
    manager.semantic.store_counter_strategy(
        enemy_strategy="cannon_rush",
        counter="spine_crawler_wall",
        success_rate=0.75,
        notes="Place spines at natural ramp",
    )

    # --- Consolidation ---
    new_facts = manager.consolidate()
    print(f"\nConsolidation created {new_facts} semantic facts from episodic patterns.")

    # --- Recall ---
    print("\n--- Episodic: wins vs Terran ---")
    wins = manager.episodic.recall(opponent_race="Terran", outcome=Outcome.WIN, top_k=5)
    for ep in wins:
        print(
            f"  [{ep.key}] action={ep.content['action']} map={ep.content['map_name']}"
        )

    print("\n--- Semantic: opponent tendencies for MarinePrince ---")
    tendencies = manager.recall_opponent_tendencies("MarinePrince")
    for t in tendencies:
        print(f"  {t.key}: {t.content['tendency']} (conf={t.content['confidence']})")

    print("\n--- Semantic: best counter for cannon_rush ---")
    counter = manager.semantic.get_best_counter("cannon_rush")
    if counter:
        print(
            f"  {counter['counter']} (success={counter['success_rate']}) -- {counter['notes']}"
        )

    print("\n--- Matchup win-rates ---")
    for mu in ["ZvT", "ZvP", "ZvZ"]:
        wr = manager.semantic.get_matchup_winrate(mu)
        stats = manager.semantic.get_matchup_stats(mu)
        print(f"  {mu}: {wr:.0%} ({stats})")

    print("\n--- Map strategies for Equilibrium ---")
    strats = manager.recall_map_strategies("Equilibrium")
    for s in strats:
        print(f"  {s.key}: {s.content['strategy']} (eff={s.content['effectiveness']})")

    # --- Forgetting ---
    forgotten = manager.run_forgetting(episodic_threshold=0.0, semantic_threshold=0.0)
    print(f"\nForgetting pass: {forgotten}")

    # --- Summary ---
    print("\n--- Memory Summary ---")
    summary = manager.summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 70)
    print("Phase 632 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 632: Agent Memory registered
