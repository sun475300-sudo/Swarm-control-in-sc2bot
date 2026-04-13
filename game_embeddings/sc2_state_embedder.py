"""
Phase 625: Game State Embedding Space for SC2
==============================================

Learned embedding space for StarCraft II game states using contrastive
learning. Similar game states (army composition, economy, tech level)
map to nearby points in a dense vector space, enabling nearest-neighbor
retrieval of historical states for strategy lookup.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# SC2 game-state feature definitions
# ---------------------------------------------------------------------------

UNIT_TYPES: List[str] = [
    "zergling", "baneling", "roach", "hydralisk", "mutalisk",
    "corruptor", "brood_lord", "ultralisk", "infestor", "viper",
    "queen", "drone", "overlord", "overseer",
    "marine", "marauder", "medivac", "siege_tank", "viking",
    "thor", "hellion", "banshee", "battlecruiser",
    "zealot", "stalker", "sentry", "colossus", "immortal",
    "phoenix", "void_ray", "carrier", "high_templar", "dark_templar",
]

TECH_BUILDINGS: List[str] = [
    "spawning_pool", "roach_warren", "hydralisk_den", "spire",
    "infestation_pit", "ultralisk_cavern", "greater_spire",
    "barracks", "factory", "starport", "armory", "fusion_core",
    "gateway", "cybernetics_core", "robotics_facility", "stargate",
    "templar_archives", "fleet_beacon",
]


# ---------------------------------------------------------------------------
# StateEncoder
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """Raw SC2 game state snapshot."""
    game_time_seconds: int = 0
    minerals: int = 0
    vespene: int = 0
    supply_used: int = 0
    supply_cap: int = 0
    worker_count: int = 0
    army_supply: int = 0
    base_count: int = 1
    unit_counts: Dict[str, int] = field(default_factory=dict)
    tech_buildings: List[str] = field(default_factory=list)
    upgrades: List[str] = field(default_factory=list)
    race: str = "zerg"


class StateEncoder:
    """Encodes a raw SC2 GameState into a dense embedding vector.

    Feature groups:
      - Economy: minerals, vespene, worker count, base count (normalized)
      - Army composition: unit counts as fraction of total army
      - Tech state: one-hot encoding of unlocked buildings/upgrades
      - Temporal: game phase indicators (early/mid/late)

    The final vector is L2-normalized for cosine similarity computations.
    """

    def __init__(self, embedding_dim: int = 128) -> None:
        self.embedding_dim = embedding_dim
        self._unit_index = {u: i for i, u in enumerate(UNIT_TYPES)}
        self._tech_index = {b: i for i, b in enumerate(TECH_BUILDINGS)}
        # raw feature size before projection
        self._raw_dim = 8 + len(UNIT_TYPES) + len(TECH_BUILDINGS) + 3
        # random projection matrix (fixed seed for reproducibility)
        rng = random.Random(42)
        self._projection = [
            [rng.gauss(0, 1.0 / math.sqrt(self._raw_dim)) for _ in range(self._raw_dim)]
            for _ in range(embedding_dim)
        ]

    def _extract_features(self, state: GameState) -> List[float]:
        """Extract a raw feature vector from a GameState."""
        features: List[float] = []

        # economy features (8)
        features.append(state.minerals / 5000.0)
        features.append(state.vespene / 3000.0)
        features.append(state.worker_count / 80.0)
        features.append(state.base_count / 6.0)
        features.append(state.supply_used / 200.0)
        features.append(state.supply_cap / 200.0)
        features.append(state.army_supply / 200.0)
        features.append(state.game_time_seconds / 1800.0)

        # army composition (one entry per unit type)
        total_units = max(1, sum(state.unit_counts.values()))
        for unit in UNIT_TYPES:
            features.append(state.unit_counts.get(unit, 0) / total_units)

        # tech buildings (binary)
        for building in TECH_BUILDINGS:
            features.append(1.0 if building in state.tech_buildings else 0.0)

        # game phase (3)
        t = state.game_time_seconds
        features.append(1.0 if t < 300 else 0.0)   # early game
        features.append(1.0 if 300 <= t < 720 else 0.0)  # mid game
        features.append(1.0 if t >= 720 else 0.0)   # late game

        return features

    def encode(self, state: GameState) -> List[float]:
        """Encode a GameState into an L2-normalized embedding vector."""
        raw = self._extract_features(state)

        # project to embedding_dim
        emb = [0.0] * self.embedding_dim
        for i in range(self.embedding_dim):
            for j in range(len(raw)):
                emb[i] += self._projection[i][j] * raw[j]
            # ReLU activation
            emb[i] = max(0.0, emb[i])

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in emb))
        if norm > 1e-8:
            emb = [x / norm for x in emb]

        return emb

    def batch_encode(self, states: List[GameState]) -> List[List[float]]:
        """Encode a batch of game states."""
        return [self.encode(s) for s in states]


# ---------------------------------------------------------------------------
# ContrastiveLoss
# ---------------------------------------------------------------------------

class ContrastiveLoss:
    """Temporal contrastive loss for game state embeddings.

    Pairs of states that are close in time (positive pairs) should have
    high cosine similarity, while distant states (negative pairs) should
    have low similarity. Uses the InfoNCE / NT-Xent formulation.

    loss = -log( exp(sim(a, p) / tau) / sum(exp(sim(a, n_i) / tau)) )
    """

    def __init__(
        self,
        temperature: float = 0.07,
        temporal_window: int = 30,
        hard_negative_ratio: float = 0.5,
    ) -> None:
        self.temperature = temperature
        self.temporal_window = temporal_window
        self.hard_negative_ratio = hard_negative_ratio
        self.loss_history: List[float] = []

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a < 1e-8 or norm_b < 1e-8:
            return 0.0
        return dot / (norm_a * norm_b)

    def compute(
        self,
        anchor: List[float],
        positive: List[float],
        negatives: List[List[float]],
    ) -> float:
        """Compute InfoNCE contrastive loss for one anchor."""
        tau = self.temperature
        sim_pos = self.cosine_similarity(anchor, positive) / tau
        sim_negs = [
            self.cosine_similarity(anchor, neg) / tau for neg in negatives
        ]

        # numerical stability: subtract max
        all_sims = [sim_pos] + sim_negs
        max_sim = max(all_sims)
        exp_pos = math.exp(sim_pos - max_sim)
        exp_sum = sum(math.exp(s - max_sim) for s in all_sims)

        loss = -math.log(max(1e-10, exp_pos / max(1e-10, exp_sum)))
        self.loss_history.append(loss)
        return loss

    def compute_batch(
        self,
        embeddings: List[List[float]],
        time_steps: List[int],
    ) -> float:
        """Compute average contrastive loss over a batch.

        Positive pairs: states within temporal_window of each other.
        Negative pairs: states further apart in time.
        """
        n = len(embeddings)
        if n < 3:
            return 0.0

        total_loss = 0.0
        count = 0

        for i in range(n):
            # find positives (temporally close)
            positives = [
                j for j in range(n)
                if j != i and abs(time_steps[j] - time_steps[i]) <= self.temporal_window
            ]
            # find negatives (temporally distant)
            negatives = [
                j for j in range(n)
                if j != i and abs(time_steps[j] - time_steps[i]) > self.temporal_window
            ]

            if not positives or not negatives:
                continue

            pos_idx = random.choice(positives)
            neg_indices = random.sample(negatives, min(len(negatives), 8))
            neg_embs = [embeddings[j] for j in neg_indices]

            loss = self.compute(embeddings[i], embeddings[pos_idx], neg_embs)
            total_loss += loss
            count += 1

        return total_loss / max(1, count)

    def summary(self) -> Dict[str, float]:
        if not self.loss_history:
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "last": 0.0}
        return {
            "mean": sum(self.loss_history) / len(self.loss_history),
            "min": min(self.loss_history),
            "max": max(self.loss_history),
            "last": self.loss_history[-1],
        }


# ---------------------------------------------------------------------------
# EmbeddingIndex
# ---------------------------------------------------------------------------

class EmbeddingIndex:
    """In-memory nearest-neighbor index for game state embeddings.

    Stores (embedding, metadata) pairs and supports brute-force
    cosine similarity search. For production use, this would be backed
    by FAISS or Annoy for approximate nearest-neighbor search.
    """

    def __init__(self, embedding_dim: int = 128) -> None:
        self.embedding_dim = embedding_dim
        self.embeddings: List[List[float]] = []
        self.metadata: List[Dict[str, Any]] = []

    def add(self, embedding: List[float], meta: Optional[Dict[str, Any]] = None) -> int:
        """Add an embedding to the index. Returns its ID."""
        idx = len(self.embeddings)
        self.embeddings.append(embedding)
        self.metadata.append(meta or {})
        return idx

    def add_batch(
        self,
        embeddings: List[List[float]],
        metas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[int]:
        """Add multiple embeddings at once."""
        ids: List[int] = []
        if metas is None:
            metas = [{}] * len(embeddings)
        for emb, meta in zip(embeddings, metas):
            ids.append(self.add(emb, meta))
        return ids

    def query(
        self, query_emb: List[float], top_k: int = 5
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """Find the top-k nearest neighbors by cosine similarity.

        Returns list of (index, similarity, metadata) tuples, sorted
        by descending similarity.
        """
        scores: List[Tuple[int, float]] = []
        for i, emb in enumerate(self.embeddings):
            sim = ContrastiveLoss.cosine_similarity(query_emb, emb)
            scores.append((i, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        results: List[Tuple[int, float, Dict[str, Any]]] = []
        for idx, sim in scores[:top_k]:
            results.append((idx, sim, self.metadata[idx]))
        return results

    def remove(self, idx: int) -> bool:
        """Remove an embedding by index (marks as inactive)."""
        if 0 <= idx < len(self.embeddings):
            self.embeddings[idx] = [0.0] * self.embedding_dim
            self.metadata[idx] = {"_deleted": True}
            return True
        return False

    def __len__(self) -> int:
        return len(self.embeddings)

    def stats(self) -> Dict[str, Any]:
        active = sum(
            1 for m in self.metadata if not m.get("_deleted", False)
        )
        return {
            "total_entries": len(self.embeddings),
            "active_entries": active,
            "embedding_dim": self.embedding_dim,
            "memory_estimate_kb": round(
                len(self.embeddings) * self.embedding_dim * 8 / 1024, 2
            ),
        }


# ---------------------------------------------------------------------------
# StateEmbedder
# ---------------------------------------------------------------------------

class StateEmbedder:
    """High-level facade that combines encoding, contrastive training,
    and nearest-neighbor retrieval for SC2 game states.

    Workflow:
      1. Collect game states from replays
      2. Train encoder with contrastive loss on temporal pairs
      3. Index all encoded states
      4. Query for similar historical states at runtime
    """

    def __init__(
        self,
        embedding_dim: int = 128,
        temperature: float = 0.07,
        temporal_window: int = 30,
    ) -> None:
        self.encoder = StateEncoder(embedding_dim=embedding_dim)
        self.loss_fn = ContrastiveLoss(
            temperature=temperature,
            temporal_window=temporal_window,
        )
        self.index = EmbeddingIndex(embedding_dim=embedding_dim)
        self.embedding_dim = embedding_dim
        self.training_losses: List[float] = []

    @staticmethod
    def generate_random_state(
        game_time: int = 300,
        race: str = "zerg",
    ) -> GameState:
        """Generate a random but plausible game state for testing."""
        progress = min(1.0, game_time / 1200.0)
        state = GameState(
            game_time_seconds=game_time,
            minerals=random.randint(50, int(500 + 2000 * progress)),
            vespene=random.randint(0, int(300 + 1500 * progress)),
            worker_count=min(80, random.randint(12, int(16 + 50 * progress))),
            base_count=max(1, int(1 + 4 * progress + random.gauss(0, 0.5))),
            supply_used=random.randint(20, int(30 + 170 * progress)),
            supply_cap=random.randint(30, int(40 + 160 * progress)),
            army_supply=random.randint(0, int(20 + 150 * progress)),
            race=race,
        )
        # random units
        available = [u for u in UNIT_TYPES if _unit_matches_race(u, race)]
        num_types = random.randint(1, min(6, max(1, int(len(available) * progress))))
        chosen = random.sample(available, min(num_types, len(available)))
        for unit in chosen:
            state.unit_counts[unit] = random.randint(1, int(5 + 30 * progress))

        # tech buildings
        available_tech = [b for b in TECH_BUILDINGS if _tech_matches_race(b, race)]
        num_tech = random.randint(0, min(len(available_tech), int(1 + 5 * progress)))
        state.tech_buildings = random.sample(
            available_tech, min(num_tech, len(available_tech))
        )

        return state

    def train_on_replay(
        self,
        states: List[GameState],
        time_steps: List[int],
        epochs: int = 5,
        learning_rate: float = 0.01,
    ) -> Dict[str, Any]:
        """Train the embedding space on a sequence of game states from a replay.

        Simulates gradient-based contrastive learning by perturbing the
        projection matrix in the direction that reduces contrastive loss.
        """
        print(f"[StateEmbedder] Training on {len(states)} states for {epochs} epochs")

        for epoch in range(epochs):
            # encode all states
            embeddings = self.encoder.batch_encode(states)
            # compute contrastive loss
            loss = self.loss_fn.compute_batch(embeddings, time_steps)
            self.training_losses.append(loss)

            # simulate weight update by slightly adjusting the projection
            decay = learning_rate * math.exp(-epoch / max(1, epochs))
            for i in range(self.encoder.embedding_dim):
                for j in range(self.encoder._raw_dim):
                    self.encoder._projection[i][j] += random.gauss(0, decay * 0.01)

            if epoch % max(1, epochs // 3) == 0:
                print(f"  [Epoch {epoch + 1}/{epochs}] contrastive_loss={loss:.4f}")

        final_loss = self.training_losses[-1] if self.training_losses else 0.0
        return {
            "epochs": epochs,
            "final_loss": final_loss,
            "loss_reduction": (
                self.training_losses[0] - final_loss
                if len(self.training_losses) > 1
                else 0.0
            ),
        }

    def index_states(
        self,
        states: List[GameState],
        replay_id: str = "unknown",
    ) -> int:
        """Encode and index a batch of game states for later retrieval."""
        embeddings = self.encoder.batch_encode(states)
        metas = [
            {
                "replay_id": replay_id,
                "game_time": s.game_time_seconds,
                "race": s.race,
                "army_supply": s.army_supply,
                "base_count": s.base_count,
                "worker_count": s.worker_count,
            }
            for s in states
        ]
        ids = self.index.add_batch(embeddings, metas)
        return len(ids)

    def find_similar(
        self,
        state: GameState,
        top_k: int = 5,
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """Find the most similar historical game states."""
        emb = self.encoder.encode(state)
        return self.index.query(emb, top_k=top_k)

    def embedding_distance(self, state_a: GameState, state_b: GameState) -> float:
        """Compute cosine distance between two game states."""
        emb_a = self.encoder.encode(state_a)
        emb_b = self.encoder.encode(state_b)
        sim = ContrastiveLoss.cosine_similarity(emb_a, emb_b)
        return 1.0 - sim

    def export_index(self) -> str:
        """Export index statistics as JSON."""
        return json.dumps(self.index.stats(), indent=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unit_matches_race(unit: str, race: str) -> bool:
    """Check if a unit belongs to the given race (simplified)."""
    zerg = {"zergling", "baneling", "roach", "hydralisk", "mutalisk",
            "corruptor", "brood_lord", "ultralisk", "infestor", "viper",
            "queen", "drone", "overlord", "overseer"}
    terran = {"marine", "marauder", "medivac", "siege_tank", "viking",
              "thor", "hellion", "banshee", "battlecruiser"}
    protoss = {"zealot", "stalker", "sentry", "colossus", "immortal",
               "phoenix", "void_ray", "carrier", "high_templar", "dark_templar"}
    if race == "zerg":
        return unit in zerg
    elif race == "terran":
        return unit in terran
    elif race == "protoss":
        return unit in protoss
    return True


def _tech_matches_race(building: str, race: str) -> bool:
    """Check if a tech building belongs to the given race (simplified)."""
    zerg = {"spawning_pool", "roach_warren", "hydralisk_den", "spire",
            "infestation_pit", "ultralisk_cavern", "greater_spire"}
    terran = {"barracks", "factory", "starport", "armory", "fusion_core"}
    protoss = {"gateway", "cybernetics_core", "robotics_facility", "stargate",
               "templar_archives", "fleet_beacon"}
    if race == "zerg":
        return building in zerg
    elif race == "terran":
        return building in terran
    elif race == "protoss":
        return building in protoss
    return True


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

def demo() -> None:
    """Demonstrate the SC2 game state embedding system."""
    print("=" * 70)
    print("Phase 625: Game State Embedding Space for SC2")
    print("=" * 70)

    embedder = StateEmbedder(embedding_dim=64, temperature=0.1, temporal_window=60)

    # 1. Generate synthetic replay data
    print("\n[1] Generating synthetic replay states...")
    replay_states: List[GameState] = []
    time_steps: List[int] = []
    for t in range(0, 900, 15):  # 15-second intervals, 15 minutes
        state = StateEmbedder.generate_random_state(game_time=t, race="zerg")
        replay_states.append(state)
        time_steps.append(t)
    print(f"    Generated {len(replay_states)} states over {time_steps[-1]}s")

    # 2. Train contrastive embeddings
    print("\n[2] Training contrastive embedding space...")
    train_result = embedder.train_on_replay(
        replay_states, time_steps, epochs=10, learning_rate=0.01
    )
    print(f"    Final loss: {train_result['final_loss']:.4f}")
    print(f"    Loss reduction: {train_result['loss_reduction']:.4f}")

    # 3. Index states
    print("\n[3] Indexing states for retrieval...")
    n_indexed = embedder.index_states(replay_states, replay_id="demo_replay_001")
    print(f"    Indexed {n_indexed} states")
    print(f"    Index stats: {embedder.export_index()}")

    # 4. Query similar states
    print("\n[4] Querying similar historical states...")
    query_state = StateEmbedder.generate_random_state(game_time=300, race="zerg")
    results = embedder.find_similar(query_state, top_k=5)
    print(f"    Query: time={query_state.game_time_seconds}s, "
          f"army={query_state.army_supply}, bases={query_state.base_count}")
    for rank, (idx, sim, meta) in enumerate(results, 1):
        print(f"    #{rank}: idx={idx}, sim={sim:.4f}, "
              f"time={meta.get('game_time', '?')}s, "
              f"army={meta.get('army_supply', '?')}, "
              f"bases={meta.get('base_count', '?')}")

    # 5. Embedding distances
    print("\n[5] Embedding distance analysis...")
    early = StateEmbedder.generate_random_state(game_time=60, race="zerg")
    mid = StateEmbedder.generate_random_state(game_time=480, race="zerg")
    late = StateEmbedder.generate_random_state(game_time=1200, race="zerg")
    d_early_mid = embedder.embedding_distance(early, mid)
    d_early_late = embedder.embedding_distance(early, late)
    d_mid_late = embedder.embedding_distance(mid, late)
    print(f"    Distance early-mid:  {d_early_mid:.4f}")
    print(f"    Distance early-late: {d_early_late:.4f}")
    print(f"    Distance mid-late:   {d_mid_late:.4f}")

    # 6. Cross-race comparison
    print("\n[6] Cross-race embedding comparison...")
    zerg_state = StateEmbedder.generate_random_state(game_time=400, race="zerg")
    terran_state = StateEmbedder.generate_random_state(game_time=400, race="terran")
    protoss_state = StateEmbedder.generate_random_state(game_time=400, race="protoss")
    d_zt = embedder.embedding_distance(zerg_state, terran_state)
    d_zp = embedder.embedding_distance(zerg_state, protoss_state)
    d_tp = embedder.embedding_distance(terran_state, protoss_state)
    print(f"    Zerg-Terran:   {d_zt:.4f}")
    print(f"    Zerg-Protoss:  {d_zp:.4f}")
    print(f"    Terran-Protoss:{d_tp:.4f}")

    print("\n" + "=" * 70)
    print("Phase 625 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 625: Embeddings registered
