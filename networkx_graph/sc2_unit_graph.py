# Phase 592: NetworkX
"""
sc2_unit_graph.py — StarCraft II Unit Relationship Graph Analysis with NetworkX

Provides graph-based analysis of unit counter relationships, tech trees,
optimal transitions, centrality metrics, community detection, map pathfinding,
battle simulation via adjacency matrices, and PageRank-based unit valuation.

Graceful fallback to a pure-Python implementation when NetworkX is absent.
"""

from __future__ import annotations

import heapq
import logging
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_unit_graph")

# ---------------------------------------------------------------------------
# Optional NetworkX / matplotlib import — graceful fallback
# ---------------------------------------------------------------------------
try:
    import networkx as nx
    from networkx.algorithms.community import greedy_modularity_communities

    NX_AVAILABLE = True
    log.info("NetworkX %s available.", nx.__version__)
except ImportError:
    NX_AVAILABLE = False
    nx = None  # type: ignore[assignment]
    log.warning(
        "NetworkX not installed. Running pure-Python fallback. "
        "Install with: pip install networkx"
    )

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False
    plt = None  # type: ignore[assignment]
    log.warning(
        "matplotlib not installed. Visualization disabled. "
        "Install with: pip install matplotlib"
    )


# ---------------------------------------------------------------------------
# SC2 unit taxonomy
# ---------------------------------------------------------------------------
class UnitRole(Enum):
    """High-level role classification for Zerg units."""

    WORKER = auto()
    GROUND_MELEE = auto()
    GROUND_RANGED = auto()
    AIR_UNIT = auto()
    SPELLCASTER = auto()
    SIEGE = auto()
    STRUCTURE = auto()


class Race(Enum):
    ZERG = "zerg"
    TERRAN = "terran"
    PROTOSS = "protoss"


@dataclass(frozen=True)
class UnitInfo:
    """Static metadata for one SC2 unit."""

    name: str
    race: Race
    role: UnitRole
    mineral_cost: int
    gas_cost: int
    supply: int
    build_time: float  # seconds (fastest speed)
    tech_tier: int  # 1=hatch, 2=lair, 3=hive
    hp: int
    dps: float
    armor: int = 0
    is_flying: bool = False


# ---------------------------------------------------------------------------
# Zerg unit database
# ---------------------------------------------------------------------------
ZERG_UNITS: Dict[str, UnitInfo] = {
    "drone": UnitInfo("drone", Race.ZERG, UnitRole.WORKER, 50, 0, 1, 12.0, 1, 40, 4.67),
    "zergling": UnitInfo(
        "zergling", Race.ZERG, UnitRole.GROUND_MELEE, 25, 0, 0.5, 17.0, 1, 35, 10.22
    ),
    "baneling": UnitInfo(
        "baneling", Race.ZERG, UnitRole.GROUND_MELEE, 50, 25, 0.5, 14.0, 1, 30, 80.0
    ),
    "roach": UnitInfo(
        "roach", Race.ZERG, UnitRole.GROUND_RANGED, 75, 25, 2, 19.0, 1, 145, 11.2
    ),
    "ravager": UnitInfo(
        "ravager", Race.ZERG, UnitRole.GROUND_RANGED, 100, 75, 3, 12.0, 1, 120, 14.0
    ),
    "hydralisk": UnitInfo(
        "hydralisk", Race.ZERG, UnitRole.GROUND_RANGED, 100, 50, 2, 24.0, 2, 90, 18.6
    ),
    "lurker": UnitInfo(
        "lurker", Race.ZERG, UnitRole.SIEGE, 150, 100, 3, 18.0, 2, 200, 20.0
    ),
    "queen": UnitInfo(
        "queen", Race.ZERG, UnitRole.SPELLCASTER, 150, 0, 2, 36.0, 1, 175, 11.2
    ),
    "mutalisk": UnitInfo(
        "mutalisk",
        Race.ZERG,
        UnitRole.AIR_UNIT,
        100,
        100,
        2,
        24.0,
        2,
        120,
        11.8,
        is_flying=True,
    ),
    "corruptor": UnitInfo(
        "corruptor",
        Race.ZERG,
        UnitRole.AIR_UNIT,
        150,
        100,
        2,
        28.0,
        2,
        200,
        10.1,
        is_flying=True,
    ),
    "brood_lord": UnitInfo(
        "brood_lord",
        Race.ZERG,
        UnitRole.SIEGE,
        300,
        250,
        4,
        24.0,
        3,
        225,
        11.2,
        is_flying=True,
    ),
    "viper": UnitInfo(
        "viper",
        Race.ZERG,
        UnitRole.SPELLCASTER,
        100,
        200,
        3,
        29.0,
        3,
        150,
        0.0,
        is_flying=True,
    ),
    "infestor": UnitInfo(
        "infestor", Race.ZERG, UnitRole.SPELLCASTER, 100, 150, 2, 36.0, 2, 90, 0.0
    ),
    "swarm_host": UnitInfo(
        "swarm_host", Race.ZERG, UnitRole.SIEGE, 100, 75, 3, 29.0, 2, 160, 7.0
    ),
    "ultralisk": UnitInfo(
        "ultralisk",
        Race.ZERG,
        UnitRole.GROUND_MELEE,
        300,
        200,
        6,
        39.0,
        3,
        500,
        35.0,
        armor=2,
    ),
    "overlord": UnitInfo(
        "overlord",
        Race.ZERG,
        UnitRole.AIR_UNIT,
        100,
        0,
        0,
        18.0,
        1,
        200,
        0.0,
        is_flying=True,
    ),
    "overseer": UnitInfo(
        "overseer",
        Race.ZERG,
        UnitRole.AIR_UNIT,
        150,
        50,
        0,
        12.0,
        2,
        200,
        0.0,
        is_flying=True,
    ),
}

# Counter relationships: (unit_a, unit_b, weight) means unit_a counters unit_b
# weight in [0, 1] represents how strong the counter is
COUNTER_RELATIONSHIPS: List[Tuple[str, str, float]] = [
    ("zergling", "drone", 0.95),
    ("baneling", "zergling", 0.90),
    ("baneling", "hydralisk", 0.70),
    ("roach", "zergling", 0.85),
    ("roach", "baneling", 0.75),
    ("hydralisk", "roach", 0.65),
    ("hydralisk", "mutalisk", 0.80),
    ("hydralisk", "corruptor", 0.70),
    ("lurker", "zergling", 0.95),
    ("lurker", "roach", 0.70),
    ("lurker", "hydralisk", 0.60),
    ("mutalisk", "drone", 0.90),
    ("mutalisk", "queen", 0.30),
    ("corruptor", "mutalisk", 0.85),
    ("corruptor", "brood_lord", 0.75),
    ("brood_lord", "lurker", 0.80),
    ("brood_lord", "ultralisk", 0.55),
    ("viper", "ultralisk", 0.65),
    ("viper", "brood_lord", 0.70),
    ("infestor", "ultralisk", 0.75),
    ("infestor", "hydralisk", 0.60),
    ("ultralisk", "zergling", 0.95),
    ("ultralisk", "roach", 0.80),
    ("ultralisk", "hydralisk", 0.60),
    ("queen", "zergling", 0.55),
    ("queen", "baneling", 0.45),
    ("ravager", "lurker", 0.70),
    ("ravager", "roach", 0.55),
    ("swarm_host", "lurker", 0.50),
]

# Tech tree edges: (prerequisite, unlocked_unit)
TECH_TREE_EDGES: List[Tuple[str, str]] = [
    ("drone", "zergling"),
    ("drone", "queen"),
    ("drone", "overlord"),
    ("zergling", "baneling"),
    ("drone", "roach"),
    ("roach", "ravager"),
    ("overlord", "overseer"),
    ("drone", "hydralisk"),
    ("hydralisk", "lurker"),
    ("drone", "mutalisk"),
    ("mutalisk", "corruptor"),
    ("corruptor", "brood_lord"),
    ("drone", "infestor"),
    ("drone", "swarm_host"),
    ("drone", "viper"),
    ("drone", "ultralisk"),
]


# ---------------------------------------------------------------------------
# Pure-Python fallback graph (when NetworkX is not available)
# ---------------------------------------------------------------------------
class _FallbackGraph:
    """Minimal directed weighted graph for use without NetworkX."""

    def __init__(self, directed: bool = False):
        self.directed = directed
        self._adj: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self._node_attrs: Dict[str, Dict[str, Any]] = {}

    # -- basic graph ops ---------------------------------------------------
    def add_node(self, node: str, **attrs: Any) -> None:
        self._node_attrs.setdefault(node, {}).update(attrs)
        self._adj.setdefault(node, {})

    def add_edge(self, u: str, v: str, **attrs: Any) -> None:
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = attrs
        if not self.directed:
            self._adj[v][u] = attrs

    def nodes(self) -> List[str]:
        return list(self._node_attrs.keys())

    def edges(self, data: bool = False):
        seen: set = set()
        result = []
        for u, nbrs in self._adj.items():
            for v, d in nbrs.items():
                key = (u, v) if self.directed else tuple(sorted((u, v)))
                if key not in seen:
                    seen.add(key)
                    result.append((u, v, d) if data else (u, v))
        return result

    def neighbors(self, node: str) -> List[str]:
        return list(self._adj.get(node, {}).keys())

    def has_node(self, n: str) -> bool:
        return n in self._node_attrs

    def number_of_nodes(self) -> int:
        return len(self._node_attrs)

    def number_of_edges(self) -> int:
        return len(self.edges())

    def __getitem__(self, node: str) -> Dict[str, Dict[str, Any]]:
        return self._adj.get(node, {})

    # -- algorithms --------------------------------------------------------
    def dijkstra(self, source: str, target: str) -> Tuple[float, List[str]]:
        """Shortest path with Dijkstra. Edge weight key = 'weight', default 1."""
        dist: Dict[str, float] = {source: 0.0}
        prev: Dict[str, Optional[str]] = {source: None}
        pq = [(0.0, source)]
        visited: Set[str] = set()
        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            if u == target:
                break
            for v, attrs in self._adj.get(u, {}).items():
                w = attrs.get("weight", 1.0)
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        if target not in dist:
            return math.inf, []
        path: List[str] = []
        cur: Optional[str] = target
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        return dist[target], path

    def pagerank(
        self, alpha: float = 0.85, max_iter: int = 100, tol: float = 1e-6
    ) -> Dict[str, float]:
        nodes = self.nodes()
        n = len(nodes)
        if n == 0:
            return {}
        idx = {nd: i for i, nd in enumerate(nodes)}
        pr = np.ones(n) / n
        for _ in range(max_iter):
            new_pr = np.ones(n) * (1 - alpha) / n
            for u in nodes:
                nbrs = list(self._adj.get(u, {}).keys())
                if not nbrs:
                    new_pr += alpha * pr[idx[u]] / n
                else:
                    share = alpha * pr[idx[u]] / len(nbrs)
                    for v in nbrs:
                        new_pr[idx[v]] += share
            if np.abs(new_pr - pr).sum() < tol:
                pr = new_pr
                break
            pr = new_pr
        return {nd: float(pr[idx[nd]]) for nd in nodes}

    def degree_centrality(self) -> Dict[str, float]:
        n = self.number_of_nodes()
        if n <= 1:
            return {nd: 0.0 for nd in self.nodes()}
        return {nd: len(self._adj.get(nd, {})) / (n - 1) for nd in self.nodes()}

    def betweenness_centrality(self) -> Dict[str, float]:
        """Brandes' algorithm for betweenness centrality."""
        nodes = self.nodes()
        bc: Dict[str, float] = {n: 0.0 for n in nodes}
        for s in nodes:
            stack: List[str] = []
            pred: Dict[str, List[str]] = {w: [] for w in nodes}
            sigma: Dict[str, float] = {w: 0.0 for w in nodes}
            sigma[s] = 1.0
            dist_map: Dict[str, float] = {s: 0.0}
            queue = [s]
            qi = 0
            while qi < len(queue):
                v = queue[qi]
                qi += 1
                stack.append(v)
                dv = dist_map[v]
                for w in self._adj.get(v, {}):
                    if w not in dist_map:
                        dist_map[w] = dv + 1
                        queue.append(w)
                    if dist_map.get(w, math.inf) == dv + 1:
                        sigma[w] += sigma[v]
                        pred[w].append(v)
            delta: Dict[str, float] = {w: 0.0 for w in nodes}
            while stack:
                w = stack.pop()
                for v in pred[w]:
                    delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
                if w != s:
                    bc[w] += delta[w]
        n = len(nodes)
        if n > 2:
            norm = 1.0 / ((n - 1) * (n - 2))
            if not self.directed:
                norm *= 2.0
            bc = {k: v * norm for k, v in bc.items()}
        return bc

    def adjacency_matrix(
        self, node_order: Optional[List[str]] = None
    ) -> Tuple[np.ndarray, List[str]]:
        nodes = node_order or sorted(self.nodes())
        idx = {n: i for i, n in enumerate(nodes)}
        mat = np.zeros((len(nodes), len(nodes)))
        for u, nbrs in self._adj.items():
            if u not in idx:
                continue
            for v, attrs in nbrs.items():
                if v not in idx:
                    continue
                mat[idx[u], idx[v]] = attrs.get("weight", 1.0)
        return mat, nodes

    def topological_sort(self) -> List[str]:
        if not self.directed:
            raise ValueError("Topological sort requires a directed graph.")
        in_deg: Dict[str, int] = {n: 0 for n in self.nodes()}
        for u, nbrs in self._adj.items():
            for v in nbrs:
                in_deg[v] = in_deg.get(v, 0) + 1
        queue = [n for n in self.nodes() if in_deg[n] == 0]
        order: List[str] = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for v in self._adj.get(n, {}):
                in_deg[v] -= 1
                if in_deg[v] == 0:
                    queue.append(v)
        return order

    def minimum_spanning_tree(self) -> "_FallbackGraph":
        """Kruskal's algorithm. Only for undirected graphs."""
        if self.directed:
            raise ValueError("MST requires an undirected graph.")
        parent: Dict[str, str] = {n: n for n in self.nodes()}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> bool:
            ra, rb = find(a), find(b)
            if ra == rb:
                return False
            parent[ra] = rb
            return True

        edges = sorted(self.edges(data=True), key=lambda e: e[2].get("weight", 1.0))
        mst = _FallbackGraph(directed=False)
        for n in self.nodes():
            mst.add_node(n, **self._node_attrs.get(n, {}))
        for u, v, d in edges:
            if union(u, v):
                mst.add_edge(u, v, **d)
        return mst

    def greedy_communities(self, resolution: float = 1.0) -> List[Set[str]]:
        """Simple greedy modularity-based community detection."""
        communities: List[Set[str]] = [{n} for n in self.nodes()]
        node_to_comm: Dict[str, int] = {n: i for i, n in enumerate(self.nodes())}
        improved = True
        while improved:
            improved = False
            for n in self.nodes():
                ci = node_to_comm[n]
                best_comm = ci
                best_gain = 0.0
                for nbr in self._adj.get(n, {}):
                    cj = node_to_comm[nbr]
                    if cj == ci:
                        continue
                    gain = self._adj[n].get(nbr, {}).get("weight", 1.0)
                    if gain > best_gain:
                        best_gain = gain
                        best_comm = cj
                if best_comm != ci and best_gain > 0:
                    communities[ci].discard(n)
                    communities[best_comm].add(n)
                    node_to_comm[n] = best_comm
                    improved = True
        return [c for c in communities if c]


# ---------------------------------------------------------------------------
# A* pathfinding on a 2D game map grid
# ---------------------------------------------------------------------------
@dataclass
class MapGrid:
    """2D grid map for pathfinding with obstacles."""

    width: int
    height: int
    obstacles: Set[Tuple[int, int]] = field(default_factory=set)
    terrain_cost: Dict[Tuple[int, int], float] = field(default_factory=dict)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def passable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and (x, y) not in self.obstacles

    def cost(self, x: int, y: int) -> float:
        return self.terrain_cost.get((x, y), 1.0)

    def neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """8-directional neighbors."""
        result = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx_, ny_ = x + dx, y + dy
                if self.passable(nx_, ny_):
                    result.append((nx_, ny_))
        return result


def astar_pathfind(
    grid: MapGrid,
    start: Tuple[int, int],
    goal: Tuple[int, int],
) -> Tuple[float, List[Tuple[int, int]]]:
    """
    A* pathfinding on the 2D map grid.
    Returns (total_cost, path) where path is a list of (x, y) coordinates.
    """

    def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    open_set: List[Tuple[float, Tuple[int, int]]] = [(0.0, start)]
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    g_score: Dict[Tuple[int, int], float] = {start: 0.0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path: List[Tuple[int, int]] = []
            node: Optional[Tuple[int, int]] = current
            while node is not None:
                path.append(node)
                node = came_from.get(node)
            path.reverse()
            return g_score[goal], path

        for nx_, ny_ in grid.neighbors(*current):
            nbr = (nx_, ny_)
            diag = abs(nx_ - current[0]) + abs(ny_ - current[1]) == 2
            move_cost = grid.cost(nx_, ny_) * (1.414 if diag else 1.0)
            tentative = g_score[current] + move_cost
            if tentative < g_score.get(nbr, math.inf):
                g_score[nbr] = tentative
                f = tentative + heuristic(nbr, goal)
                came_from[nbr] = current
                heapq.heappush(open_set, (f, nbr))

    return math.inf, []


# ---------------------------------------------------------------------------
# Main SC2UnitGraph class
# ---------------------------------------------------------------------------
class SC2UnitGraph:
    """
    Comprehensive graph-based analysis of SC2 unit relationships.

    Features
    --------
    * Counter-relationship graph (directed, weighted)
    * Tech tree as a DAG
    * Shortest path for optimal tech transitions
    * Centrality analysis (degree, betweenness, closeness)
    * Community detection for unit composition clusters
    * A* pathfinding on the game map
    * Adjacency matrix for battle simulation
    * PageRank for unit value assessment
    * Minimum spanning tree for base connection optimization
    * Visualization with matplotlib
    """

    def __init__(self) -> None:
        self._use_nx = NX_AVAILABLE
        self.counter_graph = self._make_graph(directed=True)
        self.tech_tree = self._make_graph(directed=True)
        self._build_counter_graph()
        self._build_tech_tree()
        log.info(
            "SC2UnitGraph initialised — counter graph: %d nodes / %d edges, "
            "tech tree: %d nodes / %d edges (backend=%s)",
            self._num_nodes(self.counter_graph),
            self._num_edges(self.counter_graph),
            self._num_nodes(self.tech_tree),
            self._num_edges(self.tech_tree),
            "networkx" if self._use_nx else "fallback",
        )

    # -- helper: abstract graph construction --------------------------------
    def _make_graph(self, directed: bool = False) -> Any:
        if self._use_nx:
            return nx.DiGraph() if directed else nx.Graph()
        return _FallbackGraph(directed=directed)

    def _num_nodes(self, g: Any) -> int:
        return g.number_of_nodes()

    def _num_edges(self, g: Any) -> int:
        return g.number_of_edges()

    # -- build graphs -------------------------------------------------------
    def _build_counter_graph(self) -> None:
        g = self.counter_graph
        for name, info in ZERG_UNITS.items():
            if self._use_nx:
                g.add_node(
                    name,
                    **{
                        "role": info.role.name,
                        "tier": info.tech_tier,
                        "supply": info.supply,
                        "mineral": info.mineral_cost,
                        "gas": info.gas_cost,
                        "hp": info.hp,
                        "dps": info.dps,
                    },
                )
            else:
                g.add_node(
                    name,
                    role=info.role.name,
                    tier=info.tech_tier,
                    supply=info.supply,
                    mineral=info.mineral_cost,
                    gas=info.gas_cost,
                    hp=info.hp,
                    dps=info.dps,
                )
        for counter, countered, weight in COUNTER_RELATIONSHIPS:
            g.add_edge(counter, countered, weight=weight)

    def _build_tech_tree(self) -> None:
        g = self.tech_tree
        for name, info in ZERG_UNITS.items():
            if self._use_nx:
                g.add_node(
                    name, **{"tier": info.tech_tier, "build_time": info.build_time}
                )
            else:
                g.add_node(name, tier=info.tech_tier, build_time=info.build_time)
        for prereq, unlocked in TECH_TREE_EDGES:
            build_t = ZERG_UNITS[unlocked].build_time
            g.add_edge(prereq, unlocked, weight=build_t)

    # -- shortest path for optimal tech transitions -------------------------
    def optimal_tech_path(self, start: str, target: str) -> Tuple[float, List[str]]:
        """
        Find the fastest tech transition path from *start* unit to *target* unit.
        Returns (total_build_time, path_list).
        """
        if start not in ZERG_UNITS or target not in ZERG_UNITS:
            log.warning("Unknown unit in path query: %s -> %s", start, target)
            return math.inf, []
        if self._use_nx:
            try:
                path = nx.shortest_path(self.tech_tree, start, target, weight="weight")
                cost = nx.shortest_path_length(
                    self.tech_tree, start, target, weight="weight"
                )
                return float(cost), path
            except nx.NetworkXNoPath:
                return math.inf, []
        else:
            return self.tech_tree.dijkstra(start, target)

    # -- centrality analysis ------------------------------------------------
    def centrality_analysis(self) -> Dict[str, Dict[str, float]]:
        """
        Compute degree, betweenness, and closeness centrality for the counter graph.
        Returns {unit_name: {metric: value}}.
        """
        if self._use_nx:
            deg = nx.degree_centrality(self.counter_graph)
            betw = nx.betweenness_centrality(self.counter_graph, weight="weight")
            close = nx.closeness_centrality(self.counter_graph, distance="weight")
        else:
            deg = self.counter_graph.degree_centrality()
            betw = self.counter_graph.betweenness_centrality()
            # closeness via dijkstra
            close = {}
            nodes = self.counter_graph.nodes()
            n = len(nodes)
            for nd in nodes:
                total = 0.0
                reachable = 0
                for other in nodes:
                    if other == nd:
                        continue
                    d, _ = self.counter_graph.dijkstra(nd, other)
                    if d < math.inf:
                        total += d
                        reachable += 1
                close[nd] = (reachable / total) if total > 0 else 0.0

        result: Dict[str, Dict[str, float]] = {}
        for unit in (
            self.counter_graph.nodes() if self._use_nx else self.counter_graph.nodes()
        ):
            result[unit] = {
                "degree": deg.get(unit, 0.0),
                "betweenness": betw.get(unit, 0.0),
                "closeness": close.get(unit, 0.0),
            }
        log.info("Centrality analysis complete for %d units.", len(result))
        return result

    def most_critical_units(self, top_k: int = 5) -> List[Tuple[str, float]]:
        """Return the top-k most critical units by combined centrality score."""
        ca = self.centrality_analysis()
        combined = {
            u: (m["degree"] + m["betweenness"] + m["closeness"]) / 3.0
            for u, m in ca.items()
        }
        ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    # -- community detection ------------------------------------------------
    def detect_composition_clusters(self, resolution: float = 1.0) -> List[Set[str]]:
        """
        Detect unit composition clusters via community detection.
        Uses greedy modularity optimisation.
        """
        if self._use_nx:
            undirected = self.counter_graph.to_undirected()
            communities = list(
                greedy_modularity_communities(undirected, resolution=resolution)
            )
            communities = [set(c) for c in communities]
        else:
            communities = self.counter_graph.greedy_communities(resolution)

        log.info("Detected %d composition clusters.", len(communities))
        for i, comm in enumerate(communities):
            log.info("  Cluster %d: %s", i, sorted(comm))
        return communities

    # -- adjacency matrix for battle simulation -----------------------------
    def counter_adjacency_matrix(
        self,
        unit_order: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Build an adjacency matrix from the counter graph.
        Entry (i, j) = counter strength of unit i against unit j (0 if none).
        Useful for vectorised battle simulation.
        """
        if self._use_nx:
            nodes = unit_order or sorted(self.counter_graph.nodes())
            idx = {n: i for i, n in enumerate(nodes)}
            mat = np.zeros((len(nodes), len(nodes)))
            for u, v, d in self.counter_graph.edges(data=True):
                if u in idx and v in idx:
                    mat[idx[u], idx[v]] = d.get("weight", 1.0)
            return mat, nodes
        else:
            return self.counter_graph.adjacency_matrix(unit_order)

    def simulate_battle(
        self,
        army_a: Dict[str, int],
        army_b: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Simplified battle simulation using the counter adjacency matrix.
        Each unit's effective strength = base_dps * (1 + sum of counter bonuses).
        Returns dict with scores and predicted winner.
        """
        all_units = sorted(set(list(army_a.keys()) + list(army_b.keys())))
        mat, order = self.counter_adjacency_matrix(all_units)
        idx = {n: i for i, n in enumerate(order)}

        def army_score(army: Dict[str, int], opponent: Dict[str, int]) -> float:
            total = 0.0
            for unit, count in army.items():
                if unit not in ZERG_UNITS:
                    continue
                base_dps = ZERG_UNITS[unit].dps
                counter_bonus = 0.0
                for opp_unit in opponent:
                    if unit in idx and opp_unit in idx:
                        counter_bonus += mat[idx[unit], idx[opp_unit]]
                effective = base_dps * (1.0 + counter_bonus) * count
                hp_factor = ZERG_UNITS[unit].hp / 100.0
                total += effective * hp_factor
            return total

        score_a = army_score(army_a, army_b)
        score_b = army_score(army_b, army_a)
        total = score_a + score_b
        win_prob_a = score_a / total if total > 0 else 0.5

        return {
            "score_a": round(score_a, 2),
            "score_b": round(score_b, 2),
            "win_probability_a": round(win_prob_a, 4),
            "win_probability_b": round(1.0 - win_prob_a, 4),
            "predicted_winner": "army_a" if score_a > score_b else "army_b",
        }

    # -- PageRank for unit value assessment ---------------------------------
    def unit_pagerank(self, alpha: float = 0.85) -> Dict[str, float]:
        """
        Compute PageRank on the counter graph.
        Units that counter many important units get higher rank.
        """
        if self._use_nx:
            pr = nx.pagerank(self.counter_graph, alpha=alpha, weight="weight")
        else:
            pr = self.counter_graph.pagerank(alpha=alpha)
        ranked = sorted(pr.items(), key=lambda x: x[1], reverse=True)
        log.info("PageRank top 5: %s", ranked[:5])
        return pr

    # -- minimum spanning tree for base connections -------------------------
    def base_connection_mst(
        self,
        base_positions: Dict[str, Tuple[float, float]],
    ) -> Tuple[Any, float]:
        """
        Given base positions {name: (x, y)}, build a complete weighted graph
        using Euclidean distance and compute the MST for optimal base connections.
        Returns (mst_graph, total_weight).
        """
        g = self._make_graph(directed=False)
        names = list(base_positions.keys())
        for name in names:
            pos = base_positions[name]
            if self._use_nx:
                g.add_node(name, pos=pos)
            else:
                g.add_node(name, pos=pos)

        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                dx = base_positions[a][0] - base_positions[b][0]
                dy = base_positions[a][1] - base_positions[b][1]
                dist = math.sqrt(dx * dx + dy * dy)
                g.add_edge(a, b, weight=dist)

        if self._use_nx:
            mst = nx.minimum_spanning_tree(g, weight="weight")
            total = sum(d["weight"] for _, _, d in mst.edges(data=True))
        else:
            mst = g.minimum_spanning_tree()
            total = sum(d.get("weight", 0) for _, _, d in mst.edges(data=True))

        log.info("MST for %d bases — total distance: %.2f", len(names), total)
        return mst, total

    # -- A* pathfinding on game map -----------------------------------------
    def find_map_path(
        self,
        grid: MapGrid,
        start: Tuple[int, int],
        goal: Tuple[int, int],
    ) -> Tuple[float, List[Tuple[int, int]]]:
        """
        Run A* pathfinding on a 2D game map grid.
        Returns (cost, path).
        """
        cost, path = astar_pathfind(grid, start, goal)
        if path:
            log.info("A* path found: %d steps, cost=%.2f", len(path), cost)
        else:
            log.warning("A* path not found from %s to %s", start, goal)
        return cost, path

    # -- tech tree topological order ----------------------------------------
    def tech_order(self) -> List[str]:
        """Return units in valid tech-tree build order (topological sort)."""
        if self._use_nx:
            return list(nx.topological_sort(self.tech_tree))
        return self.tech_tree.topological_sort()

    # -- visualization ------------------------------------------------------
    def visualize_counter_graph(
        self, output_path: str = "sc2_counter_graph.png"
    ) -> str:
        """
        Render the counter-relationship graph with matplotlib.
        Nodes coloured by unit role, edge width by counter strength.
        Returns the output file path.
        """
        if not MPL_AVAILABLE:
            log.warning("matplotlib not available — skipping visualisation.")
            return ""
        if not self._use_nx:
            log.warning("Visualization requires NetworkX. Skipping.")
            return ""

        role_colors = {
            UnitRole.WORKER.name: "#8BC34A",
            UnitRole.GROUND_MELEE.name: "#F44336",
            UnitRole.GROUND_RANGED.name: "#FF9800",
            UnitRole.AIR_UNIT.name: "#2196F3",
            UnitRole.SPELLCASTER.name: "#9C27B0",
            UnitRole.SIEGE.name: "#795548",
            UnitRole.STRUCTURE.name: "#607D8B",
        }

        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        pos = nx.spring_layout(self.counter_graph, seed=42, k=2.5)

        node_colors = []
        for node in self.counter_graph.nodes():
            role = self.counter_graph.nodes[node].get("role", "WORKER")
            node_colors.append(role_colors.get(role, "#9E9E9E"))

        edge_weights = [
            self.counter_graph[u][v].get("weight", 0.5) * 3
            for u, v in self.counter_graph.edges()
        ]

        nx.draw_networkx_nodes(
            self.counter_graph,
            pos,
            ax=ax,
            node_color=node_colors,
            node_size=800,
            alpha=0.9,
            edgecolors="black",
        )
        nx.draw_networkx_labels(
            self.counter_graph,
            pos,
            ax=ax,
            font_size=8,
            font_weight="bold",
        )
        nx.draw_networkx_edges(
            self.counter_graph,
            pos,
            ax=ax,
            width=edge_weights,
            alpha=0.5,
            edge_color="#555555",
            arrows=True,
            arrowsize=15,
            connectionstyle="arc3,rad=0.1",
        )

        patches = [
            mpatches.Patch(color=c, label=name.replace("_", " ").title())
            for name, c in role_colors.items()
        ]
        ax.legend(handles=patches, loc="upper left", fontsize=9)
        ax.set_title(
            "SC2 Zerg Unit Counter Relationships", fontsize=14, fontweight="bold"
        )
        ax.axis("off")

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        log.info("Counter graph saved to %s", output_path)
        return output_path

    def visualize_tech_tree(self, output_path: str = "sc2_tech_tree.png") -> str:
        """Render the tech tree DAG with matplotlib."""
        if not MPL_AVAILABLE or not self._use_nx:
            log.warning("Visualization requires NetworkX + matplotlib.")
            return ""

        fig, ax = plt.subplots(1, 1, figsize=(14, 10))

        # Layered layout based on tech tier
        pos: Dict[str, Tuple[float, float]] = {}
        tier_groups: Dict[int, List[str]] = defaultdict(list)
        for node in self.tech_tree.nodes():
            tier = self.tech_tree.nodes[node].get("tier", 1)
            tier_groups[tier].append(node)
        for tier, units in tier_groups.items():
            for i, u in enumerate(sorted(units)):
                pos[u] = (i - len(units) / 2.0, -tier)

        tier_colors = {1: "#4CAF50", 2: "#FF9800", 3: "#F44336"}
        node_colors = [
            tier_colors.get(self.tech_tree.nodes[n].get("tier", 1), "#9E9E9E")
            for n in self.tech_tree.nodes()
        ]

        nx.draw_networkx_nodes(
            self.tech_tree,
            pos,
            ax=ax,
            node_color=node_colors,
            node_size=700,
            alpha=0.9,
            edgecolors="black",
        )
        nx.draw_networkx_labels(
            self.tech_tree, pos, ax=ax, font_size=7, font_weight="bold"
        )
        nx.draw_networkx_edges(
            self.tech_tree,
            pos,
            ax=ax,
            arrows=True,
            arrowsize=12,
            edge_color="#666666",
            alpha=0.7,
        )

        patches = [
            mpatches.Patch(color=c, label=f"Tier {t}") for t, c in tier_colors.items()
        ]
        ax.legend(handles=patches, loc="upper right", fontsize=10)
        ax.set_title("Zerg Tech Tree DAG", fontsize=14, fontweight="bold")
        ax.axis("off")

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        log.info("Tech tree saved to %s", output_path)
        return output_path

    # -- summary report -----------------------------------------------------
    def full_report(self) -> Dict[str, Any]:
        """Generate a comprehensive graph analysis report."""
        centrality = self.centrality_analysis()
        critical = self.most_critical_units(top_k=5)
        clusters = self.detect_composition_clusters()
        pagerank = self.unit_pagerank()
        tech_path_example = self.optimal_tech_path("drone", "brood_lord")

        return {
            "counter_graph_stats": {
                "nodes": self._num_nodes(self.counter_graph),
                "edges": self._num_edges(self.counter_graph),
            },
            "tech_tree_stats": {
                "nodes": self._num_nodes(self.tech_tree),
                "edges": self._num_edges(self.tech_tree),
            },
            "most_critical_units": critical,
            "composition_clusters": [sorted(c) for c in clusters],
            "pagerank_top5": sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[
                :5
            ],
            "example_tech_path": {
                "from": "drone",
                "to": "brood_lord",
                "build_time": tech_path_example[0],
                "path": tech_path_example[1],
            },
            "tech_build_order": self.tech_order(),
        }


# ---------------------------------------------------------------------------
# CLI / demo entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Demonstrate SC2UnitGraph capabilities."""
    graph = SC2UnitGraph()

    print("=" * 70)
    print("SC2 Unit Graph Analysis — Phase 592: NetworkX")
    print("=" * 70)

    # 1. Critical units
    print("\n--- Most Critical Units (combined centrality) ---")
    for unit, score in graph.most_critical_units(top_k=5):
        print(f"  {unit:15s}  score={score:.4f}")

    # 2. PageRank
    print("\n--- PageRank (top 5) ---")
    pr = graph.unit_pagerank()
    for unit, rank in sorted(pr.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {unit:15s}  rank={rank:.4f}")

    # 3. Composition clusters
    print("\n--- Composition Clusters ---")
    clusters = graph.detect_composition_clusters()
    for i, cl in enumerate(clusters):
        print(f"  Cluster {i}: {sorted(cl)}")

    # 4. Optimal tech path
    print("\n--- Optimal Tech Paths ---")
    for target in ["brood_lord", "ultralisk", "lurker"]:
        cost, path = graph.optimal_tech_path("drone", target)
        print(f"  drone -> {target}: {' -> '.join(path)} (build time: {cost:.1f}s)")

    # 5. Tech build order
    print("\n--- Tech Build Order (topological) ---")
    print(f"  {' -> '.join(graph.tech_order())}")

    # 6. Battle simulation
    print("\n--- Battle Simulation ---")
    result = graph.simulate_battle(
        army_a={"zergling": 20, "baneling": 8, "hydralisk": 5},
        army_b={"roach": 10, "ravager": 4, "lurker": 3},
    )
    print(f"  Army A: 20 lings, 8 banes, 5 hydras")
    print(f"  Army B: 10 roaches, 4 ravagers, 3 lurkers")
    print(f"  Score A: {result['score_a']}  |  Score B: {result['score_b']}")
    print(f"  Win Prob A: {result['win_probability_a']:.1%}")
    print(f"  Predicted Winner: {result['predicted_winner']}")

    # 7. Base connection MST
    print("\n--- Base Connection MST ---")
    bases = {
        "main": (30.0, 130.0),
        "natural": (45.0, 110.0),
        "third": (70.0, 100.0),
        "fourth": (90.0, 80.0),
        "gold": (50.0, 50.0),
    }
    mst, total_dist = graph.base_connection_mst(bases)
    print(f"  Bases: {list(bases.keys())}")
    print(f"  MST total distance: {total_dist:.2f}")

    # 8. A* pathfinding demo
    print("\n--- A* Pathfinding Demo ---")
    grid = MapGrid(width=50, height=50)
    # Add some obstacles
    for x in range(15, 35):
        grid.obstacles.add((x, 25))
    for y in range(10, 25):
        grid.obstacles.add((25, y))
    cost, path = graph.find_map_path(grid, (5, 5), (45, 45))
    print(f"  Grid: 50x50, obstacle wall at x=15..34/y=25 and x=25/y=10..24")
    print(f"  Path from (5,5) to (45,45): {len(path)} steps, cost={cost:.2f}")

    # 9. Adjacency matrix
    print("\n--- Counter Adjacency Matrix (sample) ---")
    sample_units = ["zergling", "roach", "hydralisk", "mutalisk", "ultralisk"]
    mat, order = graph.counter_adjacency_matrix(sample_units)
    print(f"  Units: {order}")
    print(f"  Matrix shape: {mat.shape}")
    for i, u in enumerate(order):
        row = "  ".join(f"{mat[i, j]:.2f}" for j in range(len(order)))
        print(f"  {u:12s} | {row}")

    # 10. Visualization
    graph.visualize_counter_graph()
    graph.visualize_tech_tree()

    print("\n" + "=" * 70)
    print("Phase 592 complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
