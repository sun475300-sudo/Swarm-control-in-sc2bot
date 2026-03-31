# Phase 574: Pinecone Search — SC2 Strategy Similarity Engine
# StarCraft II Commander Bot — vector search over historical strategies.
# Encodes game state as a dense feature vector and queries Pinecone for
# the most similar past strategies, enabling context-aware decision making.
# Falls back to in-memory cosine similarity when Pinecone is unavailable.

from __future__ import annotations

import os
import math
import json
import time
import random
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Optional Pinecone dependency
# ──────────────────────────────────────────────
try:
    from pinecone import Pinecone, ServerlessSpec, PineconeException
    _PINECONE_AVAILABLE = True
except ImportError:
    _PINECONE_AVAILABLE = False
    logger.warning(
        "pinecone library not installed — using in-memory cosine similarity fallback. "
        "Install with: pip install pinecone-client"
    )


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
VECTOR_DIM = 64          # Feature dimensionality
INDEX_NAME = "sc2-strategies"
METRIC = "cosine"
TOP_K_DEFAULT = 5
NAMESPACE_DEFAULT = "production"


# ──────────────────────────────────────────────
# Domain types
# ──────────────────────────────────────────────
class Race(str, Enum):
    TERRAN = "terran"
    ZERG = "zerg"
    PROTOSS = "protoss"


class GamePhase(str, Enum):
    EARLY = "early"     # 0–4 minutes
    MID = "mid"         # 4–12 minutes
    LATE = "late"       # 12+ minutes


@dataclass
class GameState:
    """
    Snapshot of the current SC2 game state used as a query input.
    All continuous fields should be normalised before encoding.
    """
    # Economy
    minerals: int = 0
    vespene: int = 0
    mineral_income: float = 0.0   # per minute
    vespene_income: float = 0.0
    worker_count: int = 12
    # Supply
    supply_used: int = 14
    supply_cap: int = 18
    army_supply: int = 0
    # Structural
    base_count: int = 1
    tech_buildings: int = 0       # e.g. tech labs, bays, forges
    production_buildings: int = 1
    # Combat
    army_value: int = 0           # supply-weighted army size
    enemy_army_value: int = 0
    # Timing
    game_time_seconds: float = 0.0
    # Context
    bot_race: Race = Race.ZERG
    opponent_race: Race = Race.TERRAN
    phase: GamePhase = GamePhase.EARLY
    # Optional scouting
    enemy_base_count: int = 1
    enemy_tech_tier: int = 0      # 0=unknown, 1=basic, 2=advanced, 3=top-tier


@dataclass
class Strategy:
    """
    A named SC2 strategy with metadata and an optional pre-computed embedding.
    """
    strategy_id: str
    name: str
    race: Race
    description: str
    build_order: List[str]
    tags: List[str]                        # e.g. ["aggressive", "all-in", "bio"]
    typical_timing_seconds: float = 300.0  # when strategy executes
    win_rate: float = 0.5
    games_played: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None  # pre-computed vector


@dataclass
class SearchResult:
    strategy: Strategy
    score: float     # cosine similarity [−1, 1]
    rank: int


# ──────────────────────────────────────────────
# Feature engineering: GameState → vector
# ──────────────────────────────────────────────
class StrategyEmbedding:
    """
    Encodes a GameState (or Strategy) into a fixed-size float32 vector.

    Feature layout (VECTOR_DIM = 64):
      [0–9]   economy features
      [10–19] supply / army features
      [20–29] structural / tech features
      [30–39] timing / phase one-hot + normalised time
      [40–49] race one-hot (bot + opponent)
      [50–59] scouting / threat features
      [60–63] derived ratios

    All values are clamped to [−1, 1] after normalisation.
    """

    MAX_MINERALS = 5000.0
    MAX_VESPENE = 3000.0
    MAX_INCOME_MIN = 2000.0
    MAX_WORKERS = 80.0
    MAX_SUPPLY = 200.0
    MAX_ARMY_VALUE = 200.0
    MAX_GAME_TIME = 1800.0   # 30 minutes
    MAX_BUILDINGS = 20.0

    def encode_game_state(self, gs: GameState) -> List[float]:
        """Convert a GameState snapshot to a 64-dim feature vector."""
        v = [0.0] * VECTOR_DIM

        # Economy [0–9]
        v[0] = self._norm(gs.minerals, self.MAX_MINERALS)
        v[1] = self._norm(gs.vespene, self.MAX_VESPENE)
        v[2] = self._norm(gs.mineral_income, self.MAX_INCOME_MIN)
        v[3] = self._norm(gs.vespene_income, self.MAX_INCOME_MIN * 0.5)
        v[4] = self._norm(gs.worker_count, self.MAX_WORKERS)
        v[5] = 1.0 if gs.minerals > 400 else 0.0   # floating minerals flag
        v[6] = 1.0 if gs.vespene > 200 else 0.0    # floating gas flag
        v[7] = self._norm(gs.mineral_income * 60, self.MAX_INCOME_MIN)  # per-second to per-min
        v[8] = float(gs.base_count) / 5.0
        v[9] = float(gs.base_count - gs.enemy_base_count + 3) / 6.0    # relative bases

        # Supply / army [10–19]
        v[10] = self._norm(gs.supply_used, self.MAX_SUPPLY)
        v[11] = self._norm(gs.supply_cap, self.MAX_SUPPLY)
        v[12] = self._norm(gs.army_supply, self.MAX_SUPPLY * 0.8)
        v[13] = self._norm(gs.army_value, self.MAX_ARMY_VALUE)
        v[14] = self._norm(gs.enemy_army_value, self.MAX_ARMY_VALUE)
        v[15] = float(gs.supply_cap - gs.supply_used) / 20.0            # supply headroom
        v[16] = float(gs.army_supply) / max(gs.supply_used, 1)          # army ratio
        v[17] = float(gs.worker_count) / max(gs.supply_used, 1)         # eco ratio
        v[18] = 1.0 if gs.supply_cap >= 200 else 0.0                    # max supply flag
        v[19] = self._norm(gs.army_value - gs.enemy_army_value + 100,
                           200.0)                                         # army advantage

        # Structural / tech [20–29]
        v[20] = self._norm(gs.tech_buildings, self.MAX_BUILDINGS)
        v[21] = self._norm(gs.production_buildings, self.MAX_BUILDINGS)
        v[22] = float(gs.enemy_tech_tier) / 3.0
        v[23] = float(gs.tech_buildings > 0)   # has tech flag
        v[24] = float(gs.tech_buildings > 2)   # advanced tech flag
        v[25] = float(gs.production_buildings > 3)  # mass production flag
        v[26] = float(gs.tech_buildings) / max(gs.production_buildings + 1, 1)
        v[27] = 0.0  # reserved
        v[28] = 0.0  # reserved
        v[29] = 0.0  # reserved

        # Timing / phase [30–39]
        v[30] = self._norm(gs.game_time_seconds, self.MAX_GAME_TIME)
        # Phase one-hot
        v[31] = 1.0 if gs.phase == GamePhase.EARLY else 0.0
        v[32] = 1.0 if gs.phase == GamePhase.MID else 0.0
        v[33] = 1.0 if gs.phase == GamePhase.LATE else 0.0
        # Early / mid / late timing sub-features
        v[34] = 1.0 if gs.game_time_seconds < 120 else 0.0   # first 2 min
        v[35] = 1.0 if 120 <= gs.game_time_seconds < 300 else 0.0
        v[36] = 1.0 if 300 <= gs.game_time_seconds < 600 else 0.0
        v[37] = 1.0 if gs.game_time_seconds >= 600 else 0.0
        v[38] = 0.0
        v[39] = 0.0

        # Race one-hot — bot [40–42] / opponent [43–45]
        races = [Race.TERRAN, Race.ZERG, Race.PROTOSS]
        for i, r in enumerate(races):
            v[40 + i] = 1.0 if gs.bot_race == r else 0.0
            v[43 + i] = 1.0 if gs.opponent_race == r else 0.0
        v[46] = 0.0
        v[47] = 0.0
        v[48] = 0.0
        v[49] = 0.0

        # Scouting / threat [50–59]
        v[50] = float(gs.enemy_base_count) / 5.0
        v[51] = float(gs.enemy_tech_tier) / 3.0
        v[52] = 1.0 if gs.enemy_army_value > gs.army_value * 1.5 else 0.0  # threat flag
        v[53] = 1.0 if gs.enemy_army_value < gs.army_value * 0.5 else 0.0  # dominating flag
        v[54] = self._norm(abs(gs.army_value - gs.enemy_army_value), 100.0)
        v[55] = 0.0
        v[56] = 0.0
        v[57] = 0.0
        v[58] = 0.0
        v[59] = 0.0

        # Derived ratios [60–63]
        eco = gs.mineral_income + gs.vespene_income
        v[60] = self._norm(eco, self.MAX_INCOME_MIN)
        v[61] = float(gs.army_supply) / max(gs.worker_count, 1) / 5.0  # aggression index
        v[62] = float(gs.base_count * 400 - gs.minerals) / 2000.0      # saturation deficit
        v[63] = float(gs.tech_buildings + gs.production_buildings) / max(gs.supply_cap, 1) * 10

        return [max(-1.0, min(1.0, x)) for x in v]

    def encode_strategy(self, strategy: Strategy) -> List[float]:
        """
        Create an embedding from a Strategy's metadata for indexing.
        Constructs a synthetic GameState that represents the strategy's context.
        """
        # Build a representative mid-game state from strategy tags and timing
        timing = strategy.typical_timing_seconds
        is_aggressive = "aggressive" in strategy.tags or "all-in" in strategy.tags
        is_eco = "macro" in strategy.tags or "economy" in strategy.tags
        is_tech = any(t in strategy.tags for t in ["tech", "mech", "bio", "psi"])

        gs = GameState(
            minerals=400 if is_eco else 150,
            vespene=300 if is_tech else 50,
            mineral_income=800.0,
            vespene_income=400.0 if is_tech else 100.0,
            worker_count=22 if is_eco else 16,
            supply_used=60 if is_aggressive else 40,
            supply_cap=66 if is_aggressive else 46,
            army_supply=40 if is_aggressive else 20,
            base_count=2 if is_eco else 1,
            tech_buildings=3 if is_tech else 0,
            production_buildings=4 if is_aggressive else 2,
            army_value=40 if is_aggressive else 20,
            enemy_army_value=30,
            game_time_seconds=timing,
            bot_race=strategy.race,
            opponent_race=Race.TERRAN,  # neutral default
            phase=(
                GamePhase.EARLY if timing < 240
                else GamePhase.MID if timing < 720
                else GamePhase.LATE
            ),
            enemy_base_count=1,
            enemy_tech_tier=1,
        )

        base_vec = self.encode_game_state(gs)

        # Blend in win-rate signal
        wr_signal = (strategy.win_rate - 0.5) * 0.2
        for i in range(len(base_vec)):
            base_vec[i] = max(-1.0, min(1.0, base_vec[i] + wr_signal))

        return base_vec

    @staticmethod
    def _norm(val: float, max_val: float) -> float:
        return float(val) / max_val if max_val != 0 else 0.0

    @staticmethod
    def l2_normalize(vec: List[float]) -> List[float]:
        norm = math.sqrt(sum(x * x for x in vec))
        if norm < 1e-9:
            return vec
        return [x / norm for x in vec]


# ──────────────────────────────────────────────
# In-memory cosine similarity fallback
# ──────────────────────────────────────────────
class _InMemoryIndex:
    """Simple brute-force cosine similarity store for fallback use."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def upsert(self, vectors: List[Tuple[str, List[float], Dict]]) -> None:
        for vec_id, embedding, metadata in vectors:
            self._store[vec_id] = {
                "embedding": embedding,
                "metadata": metadata,
            }

    def query(self, vector: List[float], top_k: int = 5,
              namespace: str = "") -> List[Dict]:
        def cosine(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a < 1e-9 or norm_b < 1e-9:
                return 0.0
            return dot / (norm_a * norm_b)

        scored = [
            (vec_id, cosine(vector, entry["embedding"]), entry["metadata"])
            for vec_id, entry in self._store.items()
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {"id": vid, "score": score, "metadata": meta}
            for vid, score, meta in scored[:top_k]
        ]

    def delete(self, ids: List[str]) -> None:
        for vid in ids:
            self._store.pop(vid, None)

    @property
    def vector_count(self) -> int:
        return len(self._store)


# ──────────────────────────────────────────────
# Pinecone-backed (or fallback) strategy index
# ──────────────────────────────────────────────
class StrategyIndex:
    """
    Manages strategy embeddings in Pinecone (or in-memory fallback).

    Usage
    -----
    >>> idx = StrategyIndex.from_env()
    >>> idx.upsert_strategy(strategy)
    >>> results = idx.query_by_game_state(current_game_state, top_k=3)
    """

    def __init__(
        self,
        api_key: str = "",
        index_name: str = INDEX_NAME,
        environment: str = "us-east-1-aws",
        namespace: str = NAMESPACE_DEFAULT,
        create_if_missing: bool = True,
    ) -> None:
        self._index_name = index_name
        self._namespace = namespace
        self._embedder = StrategyEmbedding()
        self._strategy_cache: Dict[str, Strategy] = {}

        if _PINECONE_AVAILABLE and api_key:
            try:
                pc = Pinecone(api_key=api_key)
                existing = [idx.name for idx in pc.list_indexes()]
                if index_name not in existing:
                    if create_if_missing:
                        logger.info("Creating Pinecone index '%s' ...", index_name)
                        pc.create_index(
                            name=index_name,
                            dimension=VECTOR_DIM,
                            metric=METRIC,
                            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                        )
                        # Wait for index to be ready
                        for _ in range(30):
                            desc = pc.describe_index(index_name)
                            if desc.status.get("ready", False):
                                break
                            time.sleep(1)
                    else:
                        raise RuntimeError(
                            f"Index '{index_name}' not found. Pass create_if_missing=True."
                        )
                self._index = pc.Index(index_name)
                self._fallback = None
                logger.info("Connected to Pinecone index '%s'.", index_name)
            except Exception as exc:
                logger.warning("Pinecone init failed (%s) — using in-memory fallback.", exc)
                self._index = None
                self._fallback = _InMemoryIndex()
        else:
            if _PINECONE_AVAILABLE and not api_key:
                logger.info("No Pinecone API key — using in-memory cosine similarity.")
            self._index = None
            self._fallback = _InMemoryIndex()

    @classmethod
    def from_env(cls) -> "StrategyIndex":
        return cls(
            api_key=os.environ.get("PINECONE_API_KEY", ""),
            index_name=os.environ.get("PINECONE_INDEX", INDEX_NAME),
            environment=os.environ.get("PINECONE_ENV", "us-east-1-aws"),
            namespace=os.environ.get("PINECONE_NAMESPACE", NAMESPACE_DEFAULT),
        )

    # ── Core operations ────────────────────────

    def upsert_strategy(self, strategy: Strategy) -> None:
        """Encode and index a single strategy."""
        embedding = (
            strategy.embedding
            if strategy.embedding is not None
            else self._embedder.encode_strategy(strategy)
        )
        embedding = StrategyEmbedding.l2_normalize(embedding)

        meta = {
            "name": strategy.name,
            "race": strategy.race.value,
            "description": strategy.description[:200],
            "tags": ",".join(strategy.tags),
            "win_rate": strategy.win_rate,
            "games_played": strategy.games_played,
            "typical_timing_seconds": strategy.typical_timing_seconds,
        }

        if self._index is not None:
            self._index.upsert(
                vectors=[(strategy.strategy_id, embedding, meta)],
                namespace=self._namespace,
            )
        else:
            self._fallback.upsert([(strategy.strategy_id, embedding, meta)])

        self._strategy_cache[strategy.strategy_id] = strategy
        logger.debug("Upserted strategy '%s'.", strategy.name)

    def upsert_many(self, strategies: List[Strategy], batch_size: int = 50) -> None:
        """Batch upsert a list of strategies."""
        for i in range(0, len(strategies), batch_size):
            batch = strategies[i : i + batch_size]
            for s in batch:
                self.upsert_strategy(s)
        logger.info("Upserted %d strategies.", len(strategies))

    def query_by_game_state(
        self,
        game_state: GameState,
        top_k: int = TOP_K_DEFAULT,
        filter_race: Optional[Race] = None,
        min_win_rate: float = 0.0,
    ) -> List[SearchResult]:
        """
        Find the most similar historical strategies for the given game state.

        Parameters
        ----------
        game_state:    Current in-game observation.
        top_k:         Number of results to return.
        filter_race:   If set, restrict results to this bot race.
        min_win_rate:  Only return strategies with win_rate >= this value.
        """
        query_vec = self._embedder.encode_game_state(game_state)
        query_vec = StrategyEmbedding.l2_normalize(query_vec)

        pinecone_filter: Optional[Dict] = None
        if filter_race is not None or min_win_rate > 0.0:
            pinecone_filter = {}
            if filter_race is not None:
                pinecone_filter["race"] = {"$eq": filter_race.value}
            if min_win_rate > 0.0:
                pinecone_filter["win_rate"] = {"$gte": min_win_rate}

        if self._index is not None:
            kwargs: Dict[str, Any] = {
                "vector": query_vec,
                "top_k": top_k,
                "namespace": self._namespace,
                "include_metadata": True,
            }
            if pinecone_filter:
                kwargs["filter"] = pinecone_filter
            raw = self._index.query(**kwargs)
            matches = raw.get("matches", [])
        else:
            matches = self._fallback.query(query_vec, top_k=top_k * 3)
            # Apply post-filtering for in-memory fallback
            if filter_race is not None:
                matches = [m for m in matches
                           if m["metadata"].get("race") == filter_race.value]
            if min_win_rate > 0.0:
                matches = [m for m in matches
                           if m["metadata"].get("win_rate", 0) >= min_win_rate]
            matches = matches[:top_k]

        return self._parse_results(matches)

    def query_by_strategy(
        self,
        strategy: Strategy,
        top_k: int = TOP_K_DEFAULT,
        exclude_self: bool = True,
    ) -> List[SearchResult]:
        """Find strategies similar to a given strategy (used for counter-picking)."""
        embedding = (
            strategy.embedding
            if strategy.embedding is not None
            else self._embedder.encode_strategy(strategy)
        )
        embedding = StrategyEmbedding.l2_normalize(embedding)

        if self._index is not None:
            raw = self._index.query(
                vector=embedding,
                top_k=top_k + (1 if exclude_self else 0),
                namespace=self._namespace,
                include_metadata=True,
            )
            matches = raw.get("matches", [])
        else:
            matches = self._fallback.query(embedding, top_k=top_k + 1)

        if exclude_self:
            matches = [m for m in matches if m["id"] != strategy.strategy_id]

        return self._parse_results(matches[:top_k])

    def delete(self, strategy_ids: List[str]) -> None:
        """Remove strategies from the index."""
        if self._index is not None:
            self._index.delete(ids=strategy_ids, namespace=self._namespace)
        else:
            self._fallback.delete(strategy_ids)
        for sid in strategy_ids:
            self._strategy_cache.pop(sid, None)

    @property
    def vector_count(self) -> int:
        if self._index is not None:
            stats = self._index.describe_index_stats()
            return stats.get("total_vector_count", 0)
        return self._fallback.vector_count

    # ── Helpers ───────────────────────────────

    def _parse_results(self, matches: List[Dict]) -> List[SearchResult]:
        results = []
        for rank, match in enumerate(matches, start=1):
            sid = match["id"]
            score = float(match.get("score", 0.0))
            meta = match.get("metadata", {})

            # Rebuild Strategy from cache or metadata
            if sid in self._strategy_cache:
                strat = self._strategy_cache[sid]
            else:
                strat = Strategy(
                    strategy_id=sid,
                    name=meta.get("name", sid),
                    race=Race(meta.get("race", "terran")),
                    description=meta.get("description", ""),
                    build_order=[],
                    tags=meta.get("tags", "").split(","),
                    typical_timing_seconds=float(meta.get("typical_timing_seconds", 300)),
                    win_rate=float(meta.get("win_rate", 0.5)),
                    games_played=int(meta.get("games_played", 0)),
                )

            results.append(SearchResult(strategy=strat, score=score, rank=rank))
        return results


# ──────────────────────────────────────────────
# Sample strategy library
# ──────────────────────────────────────────────
def build_sample_strategy_library() -> List[Strategy]:
    """Returns a curated set of common SC2 strategies for seeding the index."""
    return [
        # ── Zerg strategies ──────────────────
        Strategy(
            strategy_id="z_roach_rush",
            name="Roach Rush",
            race=Race.ZERG,
            description="Mass roach aggression at ~5 minutes. Use 4 gas, lair timing, and mass roaches to overwhelm before opponent tech kicks in.",
            build_order=["14 hatch", "14 pool", "16 hatch", "17 gas x2", "lair", "roach warren", "mass roaches"],
            tags=["aggressive", "roach", "early", "all-in"],
            typical_timing_seconds=300,
            win_rate=0.54,
            games_played=1200,
        ),
        Strategy(
            strategy_id="z_ling_bane",
            name="Ling-Bane Aggression",
            race=Race.ZERG,
            description="Speed-ling with banelings for worker line harassment and mid-game army fights. Excellent vs Terran bio.",
            build_order=["12 pool", "17 hatch", "metabolic boost", "bane nest", "queen inject spam", "ling-bane flood"],
            tags=["aggressive", "ling", "bane", "bio-counter", "mid"],
            typical_timing_seconds=360,
            win_rate=0.58,
            games_played=2300,
        ),
        Strategy(
            strategy_id="z_hydra_lurker",
            name="Hydra-Lurker",
            race=Race.ZERG,
            description="Establish macro with fast lair, transition into hydralisk-lurker for map control and siege positions.",
            build_order=["hatch first", "lair", "hydralisk den", "lurker aspect", "third base"],
            tags=["tech", "macro", "lurker", "hydra", "siege", "mid"],
            typical_timing_seconds=480,
            win_rate=0.61,
            games_played=1800,
        ),
        Strategy(
            strategy_id="z_macro_hatch",
            name="Fast Third Hatch Economy",
            race=Race.ZERG,
            description="Greed-first hatchery spam to reach 80+ workers before committing to army. Reactive defence with queens and spine crawlers.",
            build_order=["12 hatch", "12 pool", "16 hatch", "third hatch", "66 worker saturation", "mass units"],
            tags=["macro", "economy", "greedy", "safe"],
            typical_timing_seconds=600,
            win_rate=0.55,
            games_played=3100,
        ),
        Strategy(
            strategy_id="z_12_pool_all_in",
            name="12 Pool All-In",
            race=Race.ZERG,
            description="Super early pool into zergling flood. All-in with little economic backup. Very map-dependent.",
            build_order=["9 overlord", "12 pool", "13 gas", "speedlings x16"],
            tags=["all-in", "aggressive", "early", "ling", "cheese"],
            typical_timing_seconds=120,
            win_rate=0.47,
            games_played=800,
        ),
        Strategy(
            strategy_id="z_muta_switch",
            name="Muta Harass → Ling-Bane",
            race=Race.ZERG,
            description="Open with ling-bane, then surprise muta transition for worker harassment. Pivot back to ground army if mutas die.",
            build_order=["hatch first", "lair", "spire", "12 mutas", "ling-bane ground support"],
            tags=["harassment", "muta", "ling", "bane", "mid", "flexible"],
            typical_timing_seconds=420,
            win_rate=0.52,
            games_played=1400,
        ),

        # ── Terran strategies ────────────────
        Strategy(
            strategy_id="t_bio_push",
            name="Bio Marine-Marauder-Medivac",
            race=Race.TERRAN,
            description="Classic MMM composition. Fast stim, combat shield, then 2-1-1 timing push. Strong vs Zerg and Protoss gateway armies.",
            build_order=["rax rax", "factory", "starport", "stim + combat shield", "2-1-1 push"],
            tags=["bio", "aggressive", "mid", "mmm", "stim"],
            typical_timing_seconds=390,
            win_rate=0.59,
            games_played=4200,
        ),
        Strategy(
            strategy_id="t_mech",
            name="Mech Tank-Thor",
            race=Race.TERRAN,
            description="Siege tank and Thor-based mech army with widow mine support. Turtles to 3 bases then deploys.",
            build_order=["barracks", "factory x3", "armory", "ebay upgrades", "siege tank production"],
            tags=["mech", "siege", "tank", "late", "defensive"],
            typical_timing_seconds=720,
            win_rate=0.56,
            games_played=1600,
        ),
        Strategy(
            strategy_id="t_proxy_2rax",
            name="Proxy 2-Rax All-In",
            race=Race.TERRAN,
            description="Build two barracks near the opponent's natural. Flood marines before they can stabilise. True all-in.",
            build_order=["12 rax proxy", "14 rax proxy", "supply depot", "marine flood"],
            tags=["all-in", "proxy", "cheese", "early", "aggressive"],
            typical_timing_seconds=150,
            win_rate=0.44,
            games_played=600,
        ),

        # ── Protoss strategies ───────────────
        Strategy(
            strategy_id="p_stalker_blink",
            name="Blink Stalker Aggression",
            race=Race.PROTOSS,
            description="Fast blink research and stalker production for early aggression and poke. Transitions to colossus or chargelot.",
            build_order=["gate expand", "cybernetics core", "blink research", "4-gate stalker push"],
            tags=["stalker", "blink", "aggressive", "gateway", "mid"],
            typical_timing_seconds=330,
            win_rate=0.53,
            games_played=2100,
        ),
        Strategy(
            strategy_id="p_colossus_push",
            name="Robo Colossus Push",
            race=Race.PROTOSS,
            description="Standard robo-based play into colossus with thermal lance. Strong AoE vs bio and ling-heavy armies.",
            build_order=["gate expand", "robo bay", "extended thermal lance", "3 colossus push"],
            tags=["tech", "robo", "colossus", "aoe", "mid", "macro"],
            typical_timing_seconds=540,
            win_rate=0.60,
            games_played=2800,
        ),
        Strategy(
            strategy_id="p_skytoss",
            name="Skytoss Fleet",
            race=Race.PROTOSS,
            description="Transition to carrier and void ray fleet with mothership support. Dominant in late game but requires economic lead.",
            build_order=["expand x3", "fleet beacon", "carriers + void rays", "mothership"],
            tags=["skytoss", "late", "air", "carrier", "macro", "economy"],
            typical_timing_seconds=900,
            win_rate=0.57,
            games_played=900,
        ),
        Strategy(
            strategy_id="p_chargelot_archon",
            name="Chargelot-Archon Push",
            race=Race.PROTOSS,
            description="Zealot charge + archon combo for a timing attack. Very supply-efficient and deadly vs clumped bio.",
            build_order=["expand", "twilight council", "charge", "archon production", "timing attack"],
            tags=["chargelot", "archon", "gateway", "timing", "mid", "aggressive"],
            typical_timing_seconds=420,
            win_rate=0.55,
            games_played=1700,
        ),
    ]


# ──────────────────────────────────────────────
# Demo / standalone entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SC2 Strategy Vector Search Demo")
    parser.add_argument("--api-key", default=os.environ.get("PINECONE_API_KEY", ""))
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=== SC2 Strategy Vector Search Demo ===")
    if not args.api_key:
        print("NOTE: No Pinecone API key — running with in-memory fallback.\n")

    # Build and seed the index
    idx = StrategyIndex(api_key=args.api_key)
    strategies = build_sample_strategy_library()
    print(f"Indexing {len(strategies)} strategies ...")
    idx.upsert_many(strategies)
    print(f"Index contains {idx.vector_count} vectors.\n")

    # Define several representative game states for querying
    query_scenarios = [
        {
            "label": "Zerg early aggression (4:30, many lings, small eco)",
            "state": GameState(
                minerals=200, vespene=50, mineral_income=600.0, vespene_income=80.0,
                worker_count=18, supply_used=40, supply_cap=44, army_supply=22,
                base_count=2, tech_buildings=1, production_buildings=1,
                army_value=22, enemy_army_value=15,
                game_time_seconds=270, bot_race=Race.ZERG, opponent_race=Race.TERRAN,
                phase=GamePhase.EARLY,
            ),
        },
        {
            "label": "Terran mid-game with MMM army (6:30)",
            "state": GameState(
                minerals=300, vespene=150, mineral_income=900.0, vespene_income=250.0,
                worker_count=26, supply_used=80, supply_cap=90, army_supply=50,
                base_count=2, tech_buildings=3, production_buildings=4,
                army_value=50, enemy_army_value=45,
                game_time_seconds=390, bot_race=Race.TERRAN, opponent_race=Race.ZERG,
                phase=GamePhase.MID,
            ),
        },
        {
            "label": "Protoss late-game economic dominance (15:00)",
            "state": GameState(
                minerals=600, vespene=400, mineral_income=1400.0, vespene_income=600.0,
                worker_count=66, supply_used=160, supply_cap=180, army_supply=90,
                base_count=4, tech_buildings=5, production_buildings=6,
                army_value=90, enemy_army_value=70,
                game_time_seconds=900, bot_race=Race.PROTOSS, opponent_race=Race.ZERG,
                phase=GamePhase.LATE,
            ),
        },
    ]

    for scenario in query_scenarios:
        print(f"Query: {scenario['label']}")
        results = idx.query_by_game_state(
            scenario["state"], top_k=args.top_k,
            filter_race=scenario["state"].bot_race,
        )
        for r in results:
            print(f"  #{r.rank}  [{r.score:.4f}]  {r.strategy.name!r:<35} "
                  f"(race={r.strategy.race.value}, wr={r.strategy.win_rate:.0%}, "
                  f"tags={r.strategy.tags[:3]})")
        print()

    # Counter-strategy demo
    roach_rush = next(s for s in strategies if s.strategy_id == "z_roach_rush")
    print(f"Strategies similar to '{roach_rush.name}' (for counter research):")
    similar = idx.query_by_strategy(roach_rush, top_k=3, exclude_self=True)
    for r in similar:
        print(f"  #{r.rank}  [{r.score:.4f}]  {r.strategy.name!r}")

    print("\nDone.")
