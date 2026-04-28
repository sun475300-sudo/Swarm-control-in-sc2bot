"""
Phase 629: Vector Database for SC2 Game State Similarity
=========================================================
Custom vector database for encoding SC2 game states as dense vectors and
performing fast nearest-neighbor retrieval to find historically similar
situations.

Index backends:
    - Brute-force (exact, O(n) per query)
    - LSH  (locality-sensitive hashing, approximate, sub-linear)
    - HNSW (hierarchical navigable small-world graph, approximate, fast)

The GameStateEncoder maps raw game observations (army composition, resources,
tech progress, map control) into fixed-dimension dense vectors suitable for
similarity search.
"""

from __future__ import annotations

import hashlib
import heapq
import math
import random
import struct
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DIM = 64
MAX_CANDIDATES = 500

ZERG_UNITS = [
    "zergling",
    "baneling",
    "roach",
    "ravager",
    "hydralisk",
    "lurker",
    "mutalisk",
    "corruptor",
    "brood_lord",
    "viper",
    "infestor",
    "ultralisk",
    "queen",
    "overlord",
    "overseer",
    "swarm_host",
]

TERRAN_UNITS = [
    "marine",
    "marauder",
    "reaper",
    "ghost",
    "hellion",
    "hellbat",
    "widow_mine",
    "siege_tank",
    "cyclone",
    "thor",
    "viking",
    "medivac",
    "liberator",
    "banshee",
    "battlecruiser",
    "raven",
]

PROTOSS_UNITS = [
    "zealot",
    "stalker",
    "sentry",
    "adept",
    "high_templar",
    "dark_templar",
    "archon",
    "immortal",
    "colossus",
    "disruptor",
    "warp_prism",
    "observer",
    "phoenix",
    "void_ray",
    "oracle",
    "carrier",
    "tempest",
    "mothership",
]

ALL_UNITS = ZERG_UNITS + TERRAN_UNITS + PROTOSS_UNITS

RESOURCE_KEYS = [
    "minerals",
    "vespene",
    "supply_used",
    "supply_cap",
    "worker_count",
    "base_count",
]

TECH_KEYS = [
    "has_lair",
    "has_hive",
    "has_spire",
    "has_greater_spire",
    "has_infestation_pit",
    "has_ultra_cavern",
    "has_lurker_den",
    "has_bane_nest",
    "has_roach_warren",
    "has_hydra_den",
    "melee_upgrades",
    "ranged_upgrades",
    "armor_upgrades",
    "air_upgrades",
]

MAP_CONTROL_KEYS = [
    "creep_coverage",
    "vision_coverage",
    "enemy_bases_scouted",
    "expansions_taken",
    "watchtower_count",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IndexType(Enum):
    BRUTE_FORCE = auto()
    LSH = auto()
    HNSW = auto()


class DistanceMetric(Enum):
    EUCLIDEAN = auto()
    COSINE = auto()
    MANHATTAN = auto()


# ---------------------------------------------------------------------------
# Vector math helpers
# ---------------------------------------------------------------------------


def _vec_dot(a: List[float], b: List[float]) -> float:
    s = 0.0
    for i in range(len(a)):
        s += a[i] * b[i]
    return s


def _vec_norm(a: List[float]) -> float:
    return math.sqrt(_vec_dot(a, a))


def _vec_sub(a: List[float], b: List[float]) -> List[float]:
    return [a[i] - b[i] for i in range(len(a))]


def _vec_add(a: List[float], b: List[float]) -> List[float]:
    return [a[i] + b[i] for i in range(len(a))]


def _vec_scale(a: List[float], s: float) -> List[float]:
    return [x * s for x in a]


def _euclidean_dist(a: List[float], b: List[float]) -> float:
    d = _vec_sub(a, b)
    return math.sqrt(_vec_dot(d, d))


def _cosine_dist(a: List[float], b: List[float]) -> float:
    na = _vec_norm(a)
    nb = _vec_norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 1.0
    return 1.0 - _vec_dot(a, b) / (na * nb)


def _manhattan_dist(a: List[float], b: List[float]) -> float:
    return sum(abs(a[i] - b[i]) for i in range(len(a)))


def _get_distance_fn(
    metric: DistanceMetric,
) -> Callable[[List[float], List[float]], float]:
    if metric == DistanceMetric.EUCLIDEAN:
        return _euclidean_dist
    elif metric == DistanceMetric.COSINE:
        return _cosine_dist
    elif metric == DistanceMetric.MANHATTAN:
        return _manhattan_dist
    return _euclidean_dist


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class VectorEntry:
    """A single entry in the vector store."""

    entry_id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def dim(self) -> int:
        return len(self.vector)

    def distance_to(
        self, other: List[float], metric: DistanceMetric = DistanceMetric.EUCLIDEAN
    ) -> float:
        fn = _get_distance_fn(metric)
        return fn(self.vector, other)


@dataclass
class SearchResult:
    """One result from a nearest-neighbor search."""

    entry_id: str
    distance: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "SearchResult") -> bool:
        return self.distance < other.distance


# ---------------------------------------------------------------------------
# LSHIndex
# ---------------------------------------------------------------------------


class LSHIndex:
    """
    Locality-Sensitive Hashing index for approximate nearest neighbors.

    Uses random hyperplane partitioning: each hash function projects the
    vector onto a random direction and takes the sign.  Vectors that hash
    to the same bucket are likely close in cosine distance.
    """

    def __init__(
        self,
        dim: int = DEFAULT_DIM,
        num_tables: int = 8,
        num_bits: int = 12,
        seed: int = 42,
    ) -> None:
        self.dim = dim
        self.num_tables = num_tables
        self.num_bits = num_bits
        self._rng = random.Random(seed)
        self._planes: List[List[List[float]]] = []
        self._tables: List[Dict[int, List[str]]] = []
        self._vectors: Dict[str, List[float]] = {}

        # Generate random hyperplanes for each table
        for _ in range(num_tables):
            planes = []
            for _ in range(num_bits):
                plane = [self._rng.gauss(0, 1) for _ in range(dim)]
                norm = math.sqrt(sum(x * x for x in plane))
                if norm > 1e-12:
                    plane = [x / norm for x in plane]
                planes.append(plane)
            self._planes.append(planes)
            self._tables.append(defaultdict(list))

    # ------------------------------------------------------------------
    def _hash_vector(self, vec: List[float], table_idx: int) -> int:
        """Compute the LSH bucket hash for one table."""
        h = 0
        for bit_idx, plane in enumerate(self._planes[table_idx]):
            if _vec_dot(vec, plane) >= 0:
                h |= 1 << bit_idx
        return h

    def insert(self, entry_id: str, vector: List[float]) -> None:
        self._vectors[entry_id] = vector
        for t in range(self.num_tables):
            bucket = self._hash_vector(vector, t)
            self._tables[t][bucket].append(entry_id)

    def query(
        self,
        vector: List[float],
        k: int = 10,
        metric: DistanceMetric = DistanceMetric.COSINE,
    ) -> List[Tuple[str, float]]:
        """Find approximate k nearest neighbors."""
        candidates: Set[str] = set()
        for t in range(self.num_tables):
            bucket = self._hash_vector(vector, t)
            for eid in self._tables[t].get(bucket, []):
                candidates.add(eid)

        dist_fn = _get_distance_fn(metric)
        scored: List[Tuple[float, str]] = []
        for eid in candidates:
            d = dist_fn(self._vectors[eid], vector)
            scored.append((d, eid))

        scored.sort()
        return [(eid, d) for d, eid in scored[:k]]

    def remove(self, entry_id: str) -> bool:
        if entry_id not in self._vectors:
            return False
        vec = self._vectors.pop(entry_id)
        for t in range(self.num_tables):
            bucket = self._hash_vector(vec, t)
            bucket_list = self._tables[t].get(bucket, [])
            if entry_id in bucket_list:
                bucket_list.remove(entry_id)
        return True

    @property
    def size(self) -> int:
        return len(self._vectors)

    def stats(self) -> Dict[str, Any]:
        bucket_sizes = []
        for t in range(self.num_tables):
            for bucket_list in self._tables[t].values():
                bucket_sizes.append(len(bucket_list))
        avg_bucket = sum(bucket_sizes) / max(len(bucket_sizes), 1)
        return {
            "type": "LSH",
            "num_tables": self.num_tables,
            "num_bits": self.num_bits,
            "total_vectors": self.size,
            "total_buckets": sum(len(t) for t in self._tables),
            "avg_bucket_size": round(avg_bucket, 2),
        }


# ---------------------------------------------------------------------------
# HNSWIndex
# ---------------------------------------------------------------------------


class HNSWIndex:
    """
    Simplified Hierarchical Navigable Small World graph index.

    Each node is connected to its nearest neighbors at multiple layers.
    Search starts at the top layer and greedily descends, broadening the
    candidate set at the bottom layer.
    """

    def __init__(
        self,
        dim: int = DEFAULT_DIM,
        m: int = 16,
        ef_construction: int = 100,
        max_layers: int = 4,
        seed: int = 42,
    ) -> None:
        self.dim = dim
        self.m = m  # max connections per node per layer
        self.ef_construction = ef_construction
        self.max_layers = max_layers
        self._rng = random.Random(seed)

        # node_id -> vector
        self._vectors: Dict[str, List[float]] = {}
        # layer -> { node_id -> set of neighbor ids }
        self._graph: List[Dict[str, Set[str]]] = [
            defaultdict(set) for _ in range(max_layers)
        ]
        self._entry_point: Optional[str] = None
        self._node_layer: Dict[str, int] = {}  # max layer per node

    # ------------------------------------------------------------------
    def _random_layer(self) -> int:
        """Assign a random layer level (geometric distribution)."""
        level = 0
        while level < self.max_layers - 1 and self._rng.random() < 0.3:
            level += 1
        return level

    def _select_neighbors(
        self,
        query: List[float],
        candidates: Set[str],
        m: int,
    ) -> List[str]:
        """Pick the m closest candidates."""
        scored = []
        for c in candidates:
            d = _euclidean_dist(self._vectors[c], query)
            scored.append((d, c))
        scored.sort()
        return [c for _, c in scored[:m]]

    def _search_layer(
        self,
        query: List[float],
        entry_points: Set[str],
        layer: int,
        ef: int,
    ) -> List[Tuple[float, str]]:
        """Greedy BFS on one layer, returning ef closest nodes."""
        visited: Set[str] = set(entry_points)
        # max-heap of candidates (negate distance for max-heap)
        candidates: List[Tuple[float, str]] = []
        results: List[Tuple[float, str]] = []

        for ep in entry_points:
            d = _euclidean_dist(self._vectors[ep], query)
            heapq.heappush(candidates, (d, ep))
            heapq.heappush(results, (-d, ep))
            if len(results) > ef:
                heapq.heappop(results)

        while candidates:
            cd, cnode = heapq.heappop(candidates)
            # Furthest in results
            if results:
                worst_d = -results[0][0]
            else:
                worst_d = float("inf")
            if cd > worst_d:
                break

            neighbors = self._graph[layer].get(cnode, set())
            for nb in neighbors:
                if nb in visited:
                    continue
                visited.add(nb)
                nd = _euclidean_dist(self._vectors[nb], query)
                if len(results) < ef or nd < worst_d:
                    heapq.heappush(candidates, (nd, nb))
                    heapq.heappush(results, (-nd, nb))
                    if len(results) > ef:
                        heapq.heappop(results)
                    if results:
                        worst_d = -results[0][0]

        return [(abs(d), nid) for d, nid in results]

    # ------------------------------------------------------------------
    def insert(self, entry_id: str, vector: List[float]) -> None:
        self._vectors[entry_id] = vector
        node_layer = self._random_layer()
        self._node_layer[entry_id] = node_layer

        if self._entry_point is None:
            self._entry_point = entry_id
            return

        ep = {self._entry_point}

        # Descend from top to node_layer + 1, narrowing entry point
        for layer in range(self.max_layers - 1, node_layer, -1):
            results = self._search_layer(vector, ep, layer, ef=1)
            if results:
                ep = {results[0][1]}

        # Insert at layers node_layer down to 0
        for layer in range(min(node_layer, self.max_layers - 1), -1, -1):
            results = self._search_layer(vector, ep, layer, ef=self.ef_construction)
            neighbors = self._select_neighbors(
                vector,
                {nid for _, nid in results},
                self.m,
            )
            for nb in neighbors:
                self._graph[layer][entry_id].add(nb)
                self._graph[layer][nb].add(entry_id)
                # Trim if over budget
                if len(self._graph[layer][nb]) > self.m * 2:
                    keep = self._select_neighbors(
                        self._vectors[nb],
                        self._graph[layer][nb],
                        self.m,
                    )
                    self._graph[layer][nb] = set(keep)
            if results:
                ep = {results[0][1]}

        # Update entry point if new node has higher layer
        if node_layer > self._node_layer.get(self._entry_point, 0):
            self._entry_point = entry_id

    def query(
        self,
        vector: List[float],
        k: int = 10,
        ef_search: int = 50,
    ) -> List[Tuple[str, float]]:
        """Find k approximate nearest neighbors."""
        if self._entry_point is None:
            return []

        ep = {self._entry_point}
        for layer in range(self.max_layers - 1, 0, -1):
            results = self._search_layer(vector, ep, layer, ef=1)
            if results:
                ep = {results[0][1]}

        results = self._search_layer(vector, ep, 0, ef=max(ef_search, k))
        results.sort()
        return [(nid, d) for d, nid in results[:k]]

    def remove(self, entry_id: str) -> bool:
        if entry_id not in self._vectors:
            return False
        self._vectors.pop(entry_id)
        node_layer = self._node_layer.pop(entry_id, 0)
        for layer in range(node_layer + 1):
            neighbors = self._graph[layer].pop(entry_id, set())
            for nb in neighbors:
                self._graph[layer][nb].discard(entry_id)
        if self._entry_point == entry_id:
            self._entry_point = next(iter(self._vectors), None)
        return True

    @property
    def size(self) -> int:
        return len(self._vectors)

    def stats(self) -> Dict[str, Any]:
        edge_counts = []
        for layer in range(self.max_layers):
            total_edges = sum(len(nb) for nb in self._graph[layer].values())
            edge_counts.append(total_edges)
        return {
            "type": "HNSW",
            "m": self.m,
            "max_layers": self.max_layers,
            "total_vectors": self.size,
            "edges_per_layer": edge_counts,
            "entry_point": self._entry_point,
        }


# ---------------------------------------------------------------------------
# GameStateEncoder
# ---------------------------------------------------------------------------


class GameStateEncoder:
    """
    Encode a raw SC2 game state dictionary into a fixed-dimension dense vector.

    The vector layout (for dim=64):
        [0..49]  army composition (unit counts, normalized)
        [50..55] resources / economy
        [56..59] tech flags
        [60..63] map control metrics

    When dim differs, sections scale proportionally.
    """

    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        self.dim = dim
        self._unit_index: Dict[str, int] = {u: i for i, u in enumerate(ALL_UNITS)}
        self._army_dim = len(ALL_UNITS)

    # ------------------------------------------------------------------
    def encode(self, state: Dict[str, Any]) -> List[float]:
        """Convert a game state dict into a dense vector of length *dim*."""
        raw: List[float] = []

        # --- Army section ---
        army: Dict[str, int] = state.get("army", {})
        army_vec = [0.0] * self._army_dim
        for unit, count in army.items():
            idx = self._unit_index.get(unit)
            if idx is not None:
                army_vec[idx] = float(count)
        # Normalize by total supply-ish
        total = sum(army_vec) + 1e-6
        army_vec = [x / total for x in army_vec]
        raw.extend(army_vec)

        # --- Resources section ---
        minerals = state.get("minerals", 0) / 5000.0
        vespene = state.get("vespene", 0) / 3000.0
        supply_used = state.get("supply_used", 0) / 200.0
        supply_cap = state.get("supply_cap", 0) / 200.0
        workers = state.get("worker_count", 0) / 80.0
        bases = state.get("base_count", 0) / 6.0
        raw.extend([minerals, vespene, supply_used, supply_cap, workers, bases])

        # --- Tech section ---
        for tk in TECH_KEYS:
            val = state.get(tk, 0)
            if isinstance(val, bool):
                val = 1.0 if val else 0.0
            else:
                val = float(val) / 3.0  # upgrades 0-3
            raw.append(val)

        # --- Map control section ---
        for mk in MAP_CONTROL_KEYS:
            val = state.get(mk, 0.0)
            raw.append(float(val))

        # --- Project or pad to target dim ---
        if len(raw) >= self.dim:
            return raw[: self.dim]
        else:
            # Pad with zeros
            return raw + [0.0] * (self.dim - len(raw))

    def encode_batch(self, states: List[Dict[str, Any]]) -> List[List[float]]:
        return [self.encode(s) for s in states]

    def army_distance(
        self,
        state_a: Dict[str, Any],
        state_b: Dict[str, Any],
    ) -> float:
        """Compute army-composition-only distance (ignoring economy/map)."""
        va = self.encode(state_a)
        vb = self.encode(state_b)
        # Only compare first army_dim elements
        n = min(self._army_dim, self.dim)
        d = sum((va[i] - vb[i]) ** 2 for i in range(n))
        return math.sqrt(d)

    def matchup_phase_vector(
        self,
        matchup: str,
        phase: str,
    ) -> List[float]:
        """
        Create a reference vector representing a canonical matchup+phase.
        Useful as a query anchor for similarity search.
        """
        # Simple synthetic encoding
        matchup_map = {
            "ZvT": 0.1,
            "ZvP": 0.2,
            "ZvZ": 0.3,
            "TvZ": 0.4,
            "TvT": 0.5,
            "TvP": 0.6,
            "PvZ": 0.7,
            "PvT": 0.8,
            "PvP": 0.9,
        }
        phase_map = {"early": 0.2, "mid": 0.5, "late": 0.9}

        base_val = matchup_map.get(matchup, 0.5)
        phase_val = phase_map.get(phase, 0.5)

        vec = [0.0] * self.dim
        # Spread the matchup/phase signal across dimensions
        for i in range(self.dim):
            vec[i] = math.sin(base_val * (i + 1)) * phase_val * 0.5
        return vec


# ---------------------------------------------------------------------------
# VectorStore
# ---------------------------------------------------------------------------


class VectorStore:
    """
    Unified vector database facade supporting multiple index backends.

    Usage::

        store = VectorStore(dim=64, index_type=IndexType.LSH)
        store.add("game_001", vector, metadata={"matchup": "ZvT"})
        results = store.search(query_vector, k=5)
    """

    def __init__(
        self,
        dim: int = DEFAULT_DIM,
        index_type: IndexType = IndexType.BRUTE_FORCE,
        metric: DistanceMetric = DistanceMetric.EUCLIDEAN,
        **kwargs: Any,
    ) -> None:
        self.dim = dim
        self.index_type = index_type
        self.metric = metric
        self._entries: Dict[str, VectorEntry] = {}
        self._metadata_index: Dict[str, Dict[str, List[str]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Initialize the chosen index
        self._lsh: Optional[LSHIndex] = None
        self._hnsw: Optional[HNSWIndex] = None

        if index_type == IndexType.LSH:
            self._lsh = LSHIndex(
                dim=dim,
                num_tables=kwargs.get("num_tables", 8),
                num_bits=kwargs.get("num_bits", 12),
                seed=kwargs.get("seed", 42),
            )
        elif index_type == IndexType.HNSW:
            self._hnsw = HNSWIndex(
                dim=dim,
                m=kwargs.get("m", 16),
                ef_construction=kwargs.get("ef_construction", 100),
                max_layers=kwargs.get("max_layers", 4),
                seed=kwargs.get("seed", 42),
            )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(
        self,
        entry_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert or update a vector entry."""
        if len(vector) != self.dim:
            raise ValueError(f"Vector dim {len(vector)} != store dim {self.dim}")
        entry = VectorEntry(entry_id=entry_id, vector=vector, metadata=metadata or {})
        self._entries[entry_id] = entry

        # Update metadata index
        for k, v in entry.metadata.items():
            self._metadata_index[k][str(v)].append(entry_id)

        # Update ANN index
        if self._lsh is not None:
            self._lsh.insert(entry_id, vector)
        if self._hnsw is not None:
            self._hnsw.insert(entry_id, vector)

    def get(self, entry_id: str) -> Optional[VectorEntry]:
        return self._entries.get(entry_id)

    def remove(self, entry_id: str) -> bool:
        entry = self._entries.pop(entry_id, None)
        if entry is None:
            return False
        if self._lsh:
            self._lsh.remove(entry_id)
        if self._hnsw:
            self._hnsw.remove(entry_id)
        return True

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: List[float],
        k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Find k nearest neighbors, optionally filtered by metadata."""
        if len(query) != self.dim:
            raise ValueError(f"Query dim {len(query)} != store dim {self.dim}")

        if self.index_type == IndexType.BRUTE_FORCE:
            return self._brute_search(query, k, filter_metadata)
        elif self.index_type == IndexType.LSH and self._lsh is not None:
            return self._lsh_search(query, k, filter_metadata)
        elif self.index_type == IndexType.HNSW and self._hnsw is not None:
            return self._hnsw_search(query, k, filter_metadata)
        return []

    def _brute_search(
        self,
        query: List[float],
        k: int,
        filter_metadata: Optional[Dict[str, Any]],
    ) -> List[SearchResult]:
        dist_fn = _get_distance_fn(self.metric)
        candidates = self._filter_entries(filter_metadata)
        scored: List[Tuple[float, str]] = []
        for eid in candidates:
            entry = self._entries[eid]
            d = dist_fn(entry.vector, query)
            scored.append((d, eid))
        scored.sort()
        results = []
        for d, eid in scored[:k]:
            results.append(
                SearchResult(
                    entry_id=eid,
                    distance=d,
                    metadata=self._entries[eid].metadata,
                )
            )
        return results

    def _lsh_search(
        self,
        query: List[float],
        k: int,
        filter_metadata: Optional[Dict[str, Any]],
    ) -> List[SearchResult]:
        assert self._lsh is not None
        raw = self._lsh.query(query, k=k * 3, metric=self.metric)
        if filter_metadata:
            allowed = self._filter_entries(filter_metadata)
            raw = [(eid, d) for eid, d in raw if eid in allowed]
        results = []
        for eid, d in raw[:k]:
            results.append(
                SearchResult(
                    entry_id=eid,
                    distance=d,
                    metadata=self._entries[eid].metadata,
                )
            )
        return results

    def _hnsw_search(
        self,
        query: List[float],
        k: int,
        filter_metadata: Optional[Dict[str, Any]],
    ) -> List[SearchResult]:
        assert self._hnsw is not None
        raw = self._hnsw.query(query, k=k * 3)
        if filter_metadata:
            allowed = self._filter_entries(filter_metadata)
            raw = [(eid, d) for eid, d in raw if eid in allowed]
        results = []
        for eid, d in raw[:k]:
            results.append(
                SearchResult(
                    entry_id=eid,
                    distance=d,
                    metadata=self._entries[eid].metadata,
                )
            )
        return results

    def _filter_entries(
        self,
        filter_metadata: Optional[Dict[str, Any]],
    ) -> Set[str]:
        if not filter_metadata:
            return set(self._entries.keys())
        result_sets: List[Set[str]] = []
        for key, val in filter_metadata.items():
            ids = self._metadata_index.get(key, {}).get(str(val), [])
            result_sets.append(set(ids))
        if not result_sets:
            return set(self._entries.keys())
        return set.intersection(*result_sets)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._entries)

    def stats(self) -> Dict[str, Any]:
        base = {
            "total_entries": self.size,
            "dim": self.dim,
            "index_type": self.index_type.name,
            "metric": self.metric.name,
        }
        if self._lsh:
            base["lsh_stats"] = self._lsh.stats()
        if self._hnsw:
            base["hnsw_stats"] = self._hnsw.stats()
        return base

    def all_ids(self) -> List[str]:
        return list(self._entries.keys())

    def clear(self) -> None:
        self._entries.clear()
        self._metadata_index.clear()
        if self._lsh:
            self._lsh = LSHIndex(dim=self.dim)
        if self._hnsw:
            self._hnsw = HNSWIndex(dim=self.dim)


# ---------------------------------------------------------------------------
# Helper: generate synthetic game states for testing
# ---------------------------------------------------------------------------


def _make_random_state(rng: random.Random, race: str = "Zerg") -> Dict[str, Any]:
    """Generate a plausible random game state for benchmarking."""
    if race == "Zerg":
        units = ZERG_UNITS
    elif race == "Terran":
        units = TERRAN_UNITS
    else:
        units = PROTOSS_UNITS

    army: Dict[str, int] = {}
    for u in units:
        c = rng.randint(0, 30)
        if c > 0:
            army[u] = c

    return {
        "army": army,
        "minerals": rng.randint(0, 5000),
        "vespene": rng.randint(0, 3000),
        "supply_used": rng.randint(20, 200),
        "supply_cap": rng.randint(40, 200),
        "worker_count": rng.randint(16, 80),
        "base_count": rng.randint(1, 6),
        "has_lair": rng.random() > 0.3,
        "has_hive": rng.random() > 0.6,
        "has_spire": rng.random() > 0.5,
        "has_greater_spire": rng.random() > 0.8,
        "has_infestation_pit": rng.random() > 0.6,
        "has_ultra_cavern": rng.random() > 0.7,
        "has_lurker_den": rng.random() > 0.6,
        "has_bane_nest": rng.random() > 0.4,
        "has_roach_warren": rng.random() > 0.4,
        "has_hydra_den": rng.random() > 0.5,
        "melee_upgrades": rng.randint(0, 3),
        "ranged_upgrades": rng.randint(0, 3),
        "armor_upgrades": rng.randint(0, 3),
        "air_upgrades": rng.randint(0, 3),
        "creep_coverage": rng.random(),
        "vision_coverage": rng.random(),
        "enemy_bases_scouted": rng.randint(0, 5),
        "expansions_taken": rng.randint(1, 5),
        "watchtower_count": rng.randint(0, 3),
    }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate Phase 629 Vector Database with benchmarks."""
    print("=" * 70)
    print("Phase 629: Vector Database for SC2 Game State Similarity  -  Demo")
    print("=" * 70)

    encoder = GameStateEncoder(dim=DEFAULT_DIM)
    rng = random.Random(12345)
    num_states = 500

    # --- Generate synthetic game states ---
    print(f"\n[1] Generating {num_states} random game states...")
    states: List[Dict[str, Any]] = []
    for _ in range(num_states):
        race = rng.choice(["Zerg", "Terran", "Protoss"])
        s = _make_random_state(rng, race)
        s["race"] = race
        states.append(s)

    vectors = encoder.encode_batch(states)
    print(f"    Encoded to {len(vectors)} vectors of dim {DEFAULT_DIM}")

    # --- Benchmark each index type ---
    for idx_type in (IndexType.BRUTE_FORCE, IndexType.LSH, IndexType.HNSW):
        print(f"\n[2-{idx_type.name}] Building {idx_type.name} index...")
        store = VectorStore(dim=DEFAULT_DIM, index_type=idx_type)

        t0 = time.perf_counter()
        for i, vec in enumerate(vectors):
            matchup_label = "ZvT" if states[i]["race"] == "Zerg" else "TvP"
            store.add(
                entry_id=f"game_{i:04d}",
                vector=vec,
                metadata={"race": states[i]["race"], "matchup": matchup_label},
            )
        build_ms = (time.perf_counter() - t0) * 1000
        print(f"    Insert time: {build_ms:.1f} ms  ({num_states} entries)")

        # Query
        query_state = _make_random_state(rng, "Zerg")
        query_vec = encoder.encode(query_state)

        t0 = time.perf_counter()
        num_queries = 50
        for _ in range(num_queries):
            results = store.search(query_vec, k=5)
        query_ms = (time.perf_counter() - t0) * 1000
        avg_query_ms = query_ms / num_queries

        print(f"    Query time: {avg_query_ms:.2f} ms avg ({num_queries} queries)")
        print(f"    Top-5 results:")
        for r in results:
            print(
                f"      {r.entry_id}  dist={r.distance:.4f}  race={r.metadata.get('race')}"
            )

        print(f"    Stats: {store.stats()}")

    # --- Army composition distance ---
    print("\n[3] Army composition distance:")
    state_a = {"army": {"zergling": 40, "baneling": 12, "queen": 4}}
    state_b = {"army": {"zergling": 35, "baneling": 15, "roach": 8}}
    state_c = {"army": {"marine": 30, "medivac": 4, "siege_tank": 6}}

    d_ab = encoder.army_distance(state_a, state_b)
    d_ac = encoder.army_distance(state_a, state_c)
    print(f"    ZergA vs ZergB: {d_ab:.4f}")
    print(f"    ZergA vs Terran: {d_ac:.4f}")
    print(f"    (lower = more similar)")

    # --- Matchup phase reference vectors ---
    print("\n[4] Matchup+phase reference vectors:")
    for matchup in ("ZvT", "ZvP", "ZvZ"):
        for phase in ("early", "mid", "late"):
            ref = encoder.matchup_phase_vector(matchup, phase)
            norm = _vec_norm(ref)
            print(
                f"    {matchup}/{phase}: norm={norm:.3f}, first3={[round(x,3) for x in ref[:3]]}"
            )

    # --- Metadata-filtered search ---
    print("\n[5] Metadata-filtered search (Zerg only):")
    store_bf = VectorStore(dim=DEFAULT_DIM, index_type=IndexType.BRUTE_FORCE)
    for i, vec in enumerate(vectors):
        store_bf.add(
            f"game_{i:04d}",
            vec,
            metadata={"race": states[i]["race"]},
        )
    filtered = store_bf.search(
        encoder.encode(_make_random_state(rng, "Zerg")),
        k=5,
        filter_metadata={"race": "Zerg"},
    )
    for r in filtered:
        print(f"    {r.entry_id}  dist={r.distance:.4f}  race={r.metadata.get('race')}")

    print("\n" + "=" * 70)
    print("Phase 629 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 629: Vector DB registered
