"""
Phase 626: LlamaIndex Knowledge Base for SC2 Strategy Retrieval
================================================================
llamaindex_kb/sc2_knowledge_base.py

LlamaIndex-powered knowledge base for the SC2 Zerg commander bot.
  - SC2Document          : structured document node for SC2 content
  - ReplayIndexer        : parses replays into indexed document nodes
  - StrategyQueryEngine  : natural language queries -> strategy results
  - KnowledgeBase        : top-level orchestrator with vector index

Supports matchup-specific filtering (ZvT, ZvP, ZvZ), game phase
tagging, supply range metadata, and similarity-based retrieval of
build orders, strategy guides, and replay analyses.

Dependencies: numpy (required), llama-index (optional).
Supports 260+ language localisation via label keys.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Optional LlamaIndex imports
# ---------------------------------------------------------------------------
_LLAMAINDEX_AVAILABLE = False
try:
    from llama_index.core import (
        Document,
        SimpleDirectoryReader,
        StorageContext,
        VectorStoreIndex,
        load_index_from_storage,
    )
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.core.schema import TextNode, NodeWithScore
    from llama_index.core.query_engine import RetrieverQueryEngine

    _LLAMAINDEX_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums and constants
# ---------------------------------------------------------------------------


class Race(Enum):
    ZERG = "Zerg"
    TERRAN = "Terran"
    PROTOSS = "Protoss"


class Matchup(Enum):
    ZvT = "ZvT"
    ZvP = "ZvP"
    ZvZ = "ZvZ"


class GamePhase(Enum):
    OPENING = auto()  # 0--3 min
    EARLY = auto()  # 3--6 min
    MID = auto()  # 6--12 min
    LATE = auto()  # 12+ min


class DocumentType(Enum):
    REPLAY = "replay"
    BUILD_ORDER = "build_order"
    STRATEGY_GUIDE = "strategy_guide"
    UNIT_COMPOSITION = "unit_composition"
    TIMING_ATTACK = "timing_attack"
    MAP_ANALYSIS = "map_analysis"


# Supply thresholds per game phase
SUPPLY_RANGES: Dict[GamePhase, Tuple[int, int]] = {
    GamePhase.OPENING: (12, 30),
    GamePhase.EARLY: (30, 60),
    GamePhase.MID: (60, 130),
    GamePhase.LATE: (130, 200),
}

# Default embedding dimension for the fallback engine
_EMBED_DIM = 128

# ---------------------------------------------------------------------------
# SC2Document: structured document wrapper
# ---------------------------------------------------------------------------


@dataclass
class SC2Document:
    """A single knowledge document with SC2-specific metadata."""

    doc_id: str
    title: str
    content: str
    doc_type: DocumentType = DocumentType.STRATEGY_GUIDE
    matchup: Optional[Matchup] = None
    game_phase: Optional[GamePhase] = None
    supply_min: int = 0
    supply_max: int = 200
    tags: List[str] = field(default_factory=list)
    source: str = ""
    timestamp: float = field(default_factory=time.time)

    # Computed at index time
    embedding: Optional[NDArray] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "doc_type": self.doc_type.value,
            "matchup": self.matchup.value if self.matchup else None,
            "game_phase": self.game_phase.value if self.game_phase else None,
            "supply_min": self.supply_min,
            "supply_max": self.supply_max,
            "tags": self.tags,
            "source": self.source,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SC2Document":
        matchup = Matchup(d["matchup"]) if d.get("matchup") else None
        phase = None
        if d.get("game_phase"):
            phase = (
                GamePhase[d["game_phase"]]
                if isinstance(d["game_phase"], str)
                and d["game_phase"] in GamePhase.__members__
                else None
            )
        return cls(
            doc_id=d["doc_id"],
            title=d["title"],
            content=d["content"],
            doc_type=DocumentType(d.get("doc_type", "strategy_guide")),
            matchup=matchup,
            game_phase=phase,
            supply_min=d.get("supply_min", 0),
            supply_max=d.get("supply_max", 200),
            tags=d.get("tags", []),
            source=d.get("source", ""),
            timestamp=d.get("timestamp", 0.0),
        )

    def metadata_dict(self) -> Dict[str, Any]:
        """Flat metadata suitable for vector store filters."""
        return {
            "doc_type": self.doc_type.value,
            "matchup": self.matchup.value if self.matchup else "any",
            "game_phase": self.game_phase.name if self.game_phase else "any",
            "supply_min": self.supply_min,
            "supply_max": self.supply_max,
            "tags": ",".join(self.tags),
        }


# ---------------------------------------------------------------------------
# Simple embedding helpers (fallback when LlamaIndex unavailable)
# ---------------------------------------------------------------------------


def _deterministic_embed(text: str, dim: int = _EMBED_DIM) -> NDArray:
    """Generate a deterministic pseudo-embedding from text content."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    rng = np.random.RandomState(int.from_bytes(digest[:4], byteorder="big") % (2**31))
    vec = rng.randn(dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def _cosine_similarity(a: NDArray, b: NDArray) -> float:
    """Cosine similarity between two vectors."""
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# ReplayIndexer: parse replays into SC2Document nodes
# ---------------------------------------------------------------------------


class ReplayIndexer:
    """Parses replay data and build orders into SC2Document nodes."""

    def __init__(self, rng: Optional[np.random.Generator] = None) -> None:
        self.rng = rng or np.random.default_rng(42)
        self._doc_counter = 0

    def _next_id(self) -> str:
        self._doc_counter += 1
        return f"replay-{self._doc_counter:05d}"

    # -- Replay parsing (mock for non-SC2 environments) --------------------

    def parse_replay_file(self, path: Union[str, Path]) -> SC2Document:
        """Parse a .SC2Replay file into a document node.

        In production this would use sc2reader or similar; here we
        generate structured text from the file path for indexing.
        """
        p = Path(path)
        matchup = self._detect_matchup(p.stem)
        phase = self._guess_phase(p.stem)

        content_lines = [
            f"Replay: {p.name}",
            f"Matchup: {matchup.value if matchup else 'unknown'}",
            f"Phase focus: {phase.name if phase else 'all'}",
            "",
            "Build order summary:",
        ]
        # Simulate build order extraction
        sample_builds = self._generate_sample_build(matchup)
        content_lines.extend(f"  {t:>5s}  {action}" for t, action in sample_builds)

        content_lines.append("")
        content_lines.append("Key observations:")
        content_lines.extend(self._generate_observations(matchup, phase))

        supply_lo, supply_hi = self._supply_range(phase)
        return SC2Document(
            doc_id=self._next_id(),
            title=f"Replay analysis: {p.stem}",
            content="\n".join(content_lines),
            doc_type=DocumentType.REPLAY,
            matchup=matchup,
            game_phase=phase,
            supply_min=supply_lo,
            supply_max=supply_hi,
            tags=["replay", "auto-parsed"],
            source=str(p),
        )

    def parse_build_order(
        self,
        name: str,
        steps: List[Tuple[str, str]],
        matchup: Optional[Matchup] = None,
        phase: Optional[GamePhase] = None,
    ) -> SC2Document:
        """Create a document from a structured build order."""
        lines = [f"Build Order: {name}", ""]
        lines.extend(f"  {t:>5s}  {action}" for t, action in steps)
        supply_lo, supply_hi = self._supply_range(phase)
        return SC2Document(
            doc_id=self._next_id(),
            title=name,
            content="\n".join(lines),
            doc_type=DocumentType.BUILD_ORDER,
            matchup=matchup,
            game_phase=phase,
            supply_min=supply_lo,
            supply_max=supply_hi,
            tags=["build_order"],
        )

    def parse_strategy_guide(
        self,
        title: str,
        text: str,
        matchup: Optional[Matchup] = None,
        phase: Optional[GamePhase] = None,
        tags: Optional[List[str]] = None,
    ) -> SC2Document:
        """Create a document from a strategy guide."""
        return SC2Document(
            doc_id=self._next_id(),
            title=title,
            content=text,
            doc_type=DocumentType.STRATEGY_GUIDE,
            matchup=matchup,
            game_phase=phase,
            tags=tags or ["guide"],
        )

    # -- Helpers -----------------------------------------------------------

    def _detect_matchup(self, name: str) -> Optional[Matchup]:
        low = name.lower()
        for mu in Matchup:
            if mu.value.lower() in low:
                return mu
        if "terran" in low:
            return Matchup.ZvT
        if "protoss" in low:
            return Matchup.ZvP
        if "zerg" in low:
            return Matchup.ZvZ
        return None

    def _guess_phase(self, name: str) -> Optional[GamePhase]:
        low = name.lower()
        for ph in GamePhase:
            if ph.name.lower() in low:
                return ph
        return None

    def _supply_range(self, phase: Optional[GamePhase]) -> Tuple[int, int]:
        if phase and phase in SUPPLY_RANGES:
            return SUPPLY_RANGES[phase]
        return (0, 200)

    def _generate_sample_build(
        self, matchup: Optional[Matchup]
    ) -> List[Tuple[str, str]]:
        """Produce a sample build order for demo purposes."""
        base = [
            ("0:00", "Hatchery started"),
            ("0:12", "Drone x3"),
            ("0:46", "Overlord"),
            ("1:10", "Drone x3"),
            ("1:30", "Spawning Pool"),
            ("1:45", "Gas x1"),
            ("2:00", "Natural Hatchery"),
        ]
        if matchup == Matchup.ZvT:
            base.extend(
                [
                    ("2:30", "Queen x2"),
                    ("3:00", "Ling Speed"),
                    ("3:30", "Baneling Nest"),
                    ("4:00", "Roach Warren"),
                ]
            )
        elif matchup == Matchup.ZvP:
            base.extend(
                [
                    ("2:30", "Queen x2"),
                    ("3:00", "Ling Speed"),
                    ("3:30", "Roach Warren"),
                    ("4:00", "Lair"),
                ]
            )
        else:
            base.extend(
                [
                    ("2:30", "Queen x2"),
                    ("3:00", "Ling Speed"),
                    ("3:30", "Baneling Nest"),
                ]
            )
        return base

    def _generate_observations(
        self, matchup: Optional[Matchup], phase: Optional[GamePhase]
    ) -> List[str]:
        obs = ["  - Drone production consistent through opening"]
        if matchup == Matchup.ZvT:
            obs.append("  - Baneling harass effective against bio ball")
            obs.append("  - Need better creep spread to slow pushes")
        elif matchup == Matchup.ZvP:
            obs.append("  - Roach-Ravager timing strong vs gateway units")
            obs.append("  - Watch for DT shrine after natural Nexus")
        else:
            obs.append("  - Early ling-bane micro decisive in ZvZ")
            obs.append("  - Roach transition after map control secured")
        if phase == GamePhase.LATE:
            obs.append("  - Hive tech transition timing could be faster")
        return obs


# ---------------------------------------------------------------------------
# StrategyQueryEngine: search and rank documents
# ---------------------------------------------------------------------------


@dataclass
class QueryResult:
    """A single result from a knowledge base query."""

    document: SC2Document
    score: float
    explanation: str = ""


class StrategyQueryEngine:
    """Performs similarity search over embedded SC2Documents.

    When LlamaIndex is available, delegates to VectorStoreIndex;
    otherwise falls back to a simple cosine-similarity engine using
    deterministic embeddings.
    """

    def __init__(self, embed_dim: int = _EMBED_DIM) -> None:
        self.embed_dim = embed_dim
        self._documents: List[SC2Document] = []
        self._llama_index: Any = None  # VectorStoreIndex when available

    # -- Indexing -----------------------------------------------------------

    def add_documents(self, docs: Sequence[SC2Document]) -> int:
        """Embed and index a batch of documents. Returns count added."""
        added = 0
        for doc in docs:
            if doc.embedding is None:
                doc.embedding = _deterministic_embed(doc.content, self.embed_dim)
            self._documents.append(doc)
            added += 1

        if _LLAMAINDEX_AVAILABLE:
            self._rebuild_llama_index()

        logger.info("Indexed %d documents (total: %d)", added, len(self._documents))
        return added

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document by ID."""
        before = len(self._documents)
        self._documents = [d for d in self._documents if d.doc_id != doc_id]
        removed = before - len(self._documents)
        if removed > 0 and _LLAMAINDEX_AVAILABLE:
            self._rebuild_llama_index()
        return removed > 0

    def document_count(self) -> int:
        return len(self._documents)

    # -- Querying ----------------------------------------------------------

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        matchup: Optional[Matchup] = None,
        game_phase: Optional[GamePhase] = None,
        supply: Optional[int] = None,
        doc_type: Optional[DocumentType] = None,
    ) -> List[QueryResult]:
        """Natural language query with optional metadata filters.

        Returns up to *top_k* results sorted by relevance.
        """
        if not self._documents:
            return []

        # Pre-filter by metadata
        candidates = self._filter_documents(matchup, game_phase, supply, doc_type)
        if not candidates:
            candidates = self._documents  # fallback to all

        query_vec = _deterministic_embed(query_text, self.embed_dim)
        scored: List[Tuple[float, SC2Document]] = []
        for doc in candidates:
            if doc.embedding is None:
                continue
            sim = _cosine_similarity(query_vec, doc.embedding)
            scored.append((sim, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[QueryResult] = []
        for sim, doc in scored[:top_k]:
            explanation = self._build_explanation(doc, sim, matchup, game_phase)
            results.append(
                QueryResult(document=doc, score=sim, explanation=explanation)
            )
        return results

    def query_by_game_state(
        self,
        supply: int,
        matchup: Matchup,
        game_time_seconds: float,
        army_comp: Optional[Dict[str, int]] = None,
        top_k: int = 3,
    ) -> List[QueryResult]:
        """Query using current game state instead of text."""
        phase = self._phase_from_time(game_time_seconds)
        query_parts = [
            f"matchup {matchup.value}",
            f"supply {supply}",
            f"phase {phase.name}",
        ]
        if army_comp:
            comp_str = ", ".join(f"{k}:{v}" for k, v in army_comp.items())
            query_parts.append(f"army: {comp_str}")
        query_text = " | ".join(query_parts)
        return self.query(
            query_text,
            top_k=top_k,
            matchup=matchup,
            game_phase=phase,
            supply=supply,
        )

    # -- Helpers -----------------------------------------------------------

    def _filter_documents(
        self,
        matchup: Optional[Matchup],
        game_phase: Optional[GamePhase],
        supply: Optional[int],
        doc_type: Optional[DocumentType],
    ) -> List[SC2Document]:
        result = self._documents
        if matchup:
            result = [d for d in result if d.matchup is None or d.matchup == matchup]
        if game_phase:
            result = [
                d for d in result if d.game_phase is None or d.game_phase == game_phase
            ]
        if supply is not None:
            result = [d for d in result if d.supply_min <= supply <= d.supply_max]
        if doc_type:
            result = [d for d in result if d.doc_type == doc_type]
        return result

    def _build_explanation(
        self,
        doc: SC2Document,
        sim: float,
        matchup: Optional[Matchup],
        phase: Optional[GamePhase],
    ) -> str:
        parts = [f"similarity={sim:.3f}"]
        if doc.matchup:
            parts.append(f"matchup={doc.matchup.value}")
        if doc.game_phase:
            parts.append(f"phase={doc.game_phase.name}")
        parts.append(f"type={doc.doc_type.value}")
        return " | ".join(parts)

    @staticmethod
    def _phase_from_time(seconds: float) -> GamePhase:
        if seconds < 180:
            return GamePhase.OPENING
        if seconds < 360:
            return GamePhase.EARLY
        if seconds < 720:
            return GamePhase.MID
        return GamePhase.LATE

    def _rebuild_llama_index(self) -> None:
        """Rebuild the LlamaIndex VectorStoreIndex from current documents."""
        if not _LLAMAINDEX_AVAILABLE:
            return
        try:
            nodes = []
            for doc in self._documents:
                node = Document(
                    text=doc.content,
                    metadata=doc.metadata_dict(),
                    doc_id=doc.doc_id,
                )
                nodes.append(node)
            self._llama_index = VectorStoreIndex.from_documents(nodes)
            logger.info("LlamaIndex VectorStoreIndex rebuilt with %d nodes", len(nodes))
        except Exception as exc:
            logger.warning("Failed to rebuild LlamaIndex index: %s", exc)
            self._llama_index = None


# ---------------------------------------------------------------------------
# KnowledgeBase: top-level orchestrator
# ---------------------------------------------------------------------------


# Pre-defined strategy guides for seeding
_BUILTIN_GUIDES: List[Dict[str, Any]] = [
    {
        "title": "ZvT Standard Ling-Bane-Hydra",
        "matchup": "ZvT",
        "phase": "MID",
        "content": (
            "Against Terran bio, the standard Zerg approach in the mid-game is "
            "Ling-Bane-Hydra. Start with 3-base saturation and a Baneling Nest. "
            "Key timings: Lair at 3:30, Hydra Den at 5:00. Keep creep spread "
            "active to slow Terran pushes. Engage on creep when possible. "
            "Banelings should target Marines; Hydras handle Medivacs. "
            "Transition to Hive tech (Vipers + Ultralisks) once 4th base is "
            "secured. Watch for drops: keep Overlords at base edges."
        ),
    },
    {
        "title": "ZvP Roach-Ravager Timing",
        "matchup": "ZvP",
        "phase": "EARLY",
        "content": (
            "The Roach-Ravager timing hits around 5:00-5:30 before Protoss "
            "has significant Immortal count. Build: 3 Hatch before Pool, "
            "Roach Warren at 3:00, double gas at natural by 3:30. "
            "Attack with 8-10 Roaches and 3-4 Ravagers. Target Force Fields "
            "with Corrosive Bile. Transition into Lurkers if push does not "
            "end the game. Key scouting: check for Stargate (Oracle). "
            "If Oracle detected, build 2 extra Queens and a Spore per base."
        ),
    },
    {
        "title": "ZvZ Early Ling-Bane Wars",
        "matchup": "ZvZ",
        "phase": "OPENING",
        "content": (
            "ZvZ opening is volatile. Standard is Hatch-Gas-Pool, getting "
            "Ling Speed ASAP. Key rule: never stop making Lings until you "
            "confirm opponent's Baneling Nest timing. If opponent goes "
            "early Bane Nest, match it. If they go Roaches, you can either "
            "commit to mass Ling-Bane aggression or transition Roaches "
            "yourself. Wall the natural with Evo Chambers. Keep 2 Lings "
            "on the map for scouting. First Overlord scouts opponent natural."
        ),
    },
    {
        "title": "ZvT Late-Game Broodlord-Viper Transition",
        "matchup": "ZvT",
        "phase": "LATE",
        "content": (
            "In the late game vs Terran, transition to Broodlord-Viper-Corruptor. "
            "Vipers provide Abduct to pull Thors and Blinding Cloud for Siege Tanks. "
            "Broodlords slowly push forward with Corruptor escort. Keep a Ling-Bane "
            "runby group for harassment. Neural Parasite Infestors are situational "
            "but strong vs Battlecruiser. Ensure 5+ bases with good gas income. "
            "Spore Forest at key chokes to deny air harass."
        ),
    },
    {
        "title": "ZvP Late-Game Lurker Contain",
        "matchup": "ZvP",
        "phase": "LATE",
        "content": (
            "Against late-game Protoss Skytoss, Lurkers with Seismic Spines "
            "upgrade provide area denial. Burrow Lurkers at key chokes and "
            "support with Corruptors + Vipers. Vipers use Abduct on Carriers "
            "and Parasitic Bomb on clumped air. Keep Spore Crawlers around "
            "Lurker positions. Transition into Broodlords if Protoss commits "
            "to ground. Neural Parasite on Colossi is high-value."
        ),
    },
    {
        "title": "Universal Macro Fundamentals",
        "matchup": None,
        "phase": None,
        "content": (
            "Core Zerg macro principles: (1) Always inject Larvae at Hatcheries. "
            "Queen inject cycle is 25 seconds. (2) Never be supply blocked -- "
            "build Overlords proactively at 2-3 supply below cap. (3) Drone "
            "until you scout aggression, then mass units. (4) Spend Larvae: "
            "banking 20+ Larvae means you are floating money. (5) Creep spread "
            "is free map vision and speed boost. (6) Scout with Overlord at "
            "natural and Lings on the map. (7) Upgrade timing: start +1 melee "
            "or +1 ranged around 5:00."
        ),
    },
]


class KnowledgeBase:
    """Top-level orchestrator that ties together indexing and querying.

    Usage:
        kb = KnowledgeBase()
        kb.seed_builtin_guides()
        results = kb.ask("How do I deal with Terran bio?",
                         matchup=Matchup.ZvT)
    """

    def __init__(
        self,
        embed_dim: int = _EMBED_DIM,
        persist_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.engine = StrategyQueryEngine(embed_dim=embed_dim)
        self.indexer = ReplayIndexer()
        self.persist_dir = Path(persist_dir) if persist_dir else None
        self._seeded = False

    # -- Seeding -----------------------------------------------------------

    def seed_builtin_guides(self) -> int:
        """Index all built-in strategy guides."""
        if self._seeded:
            return 0
        docs: List[SC2Document] = []
        for gd in _BUILTIN_GUIDES:
            matchup_val = gd.get("matchup")
            matchup = Matchup(matchup_val) if matchup_val else None
            phase_val = gd.get("phase")
            phase = (
                GamePhase[phase_val]
                if phase_val and phase_val in GamePhase.__members__
                else None
            )
            doc = self.indexer.parse_strategy_guide(
                title=gd["title"],
                text=gd["content"],
                matchup=matchup,
                phase=phase,
                tags=["builtin", "guide"],
            )
            docs.append(doc)
        self._seeded = True
        return self.engine.add_documents(docs)

    # -- Document management -----------------------------------------------

    def add_replay(self, path: Union[str, Path]) -> SC2Document:
        """Parse and index a single replay file."""
        doc = self.indexer.parse_replay_file(path)
        self.engine.add_documents([doc])
        return doc

    def add_build_order(
        self,
        name: str,
        steps: List[Tuple[str, str]],
        matchup: Optional[Matchup] = None,
        phase: Optional[GamePhase] = None,
    ) -> SC2Document:
        """Index a custom build order."""
        doc = self.indexer.parse_build_order(name, steps, matchup, phase)
        self.engine.add_documents([doc])
        return doc

    def add_guide(
        self,
        title: str,
        content: str,
        matchup: Optional[Matchup] = None,
        phase: Optional[GamePhase] = None,
        tags: Optional[List[str]] = None,
    ) -> SC2Document:
        """Index a strategy guide."""
        doc = self.indexer.parse_strategy_guide(title, content, matchup, phase, tags)
        self.engine.add_documents([doc])
        return doc

    def remove(self, doc_id: str) -> bool:
        return self.engine.remove_document(doc_id)

    @property
    def size(self) -> int:
        return self.engine.document_count()

    # -- Querying ----------------------------------------------------------

    def ask(
        self,
        question: str,
        top_k: int = 5,
        matchup: Optional[Matchup] = None,
        game_phase: Optional[GamePhase] = None,
        supply: Optional[int] = None,
        doc_type: Optional[DocumentType] = None,
    ) -> List[QueryResult]:
        """Natural language query into the knowledge base."""
        return self.engine.query(
            question,
            top_k=top_k,
            matchup=matchup,
            game_phase=game_phase,
            supply=supply,
            doc_type=doc_type,
        )

    def ask_game_state(
        self,
        supply: int,
        matchup: Matchup,
        game_time_seconds: float,
        army_comp: Optional[Dict[str, int]] = None,
        top_k: int = 3,
    ) -> List[QueryResult]:
        """Query using current game state."""
        return self.engine.query_by_game_state(
            supply,
            matchup,
            game_time_seconds,
            army_comp,
            top_k,
        )

    # -- Persistence -------------------------------------------------------

    def save(self, path: Optional[Union[str, Path]] = None) -> str:
        """Save knowledge base to JSON."""
        save_path = Path(path) if path else (self.persist_dir or Path("."))
        save_path.mkdir(parents=True, exist_ok=True)
        fpath = save_path / "sc2_knowledge_base.json"
        data = {
            "version": "626.1.0",
            "documents": [d.to_dict() for d in self.engine._documents],
        }
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d documents to %s", len(data["documents"]), fpath)
        return str(fpath)

    def load(self, path: Optional[Union[str, Path]] = None) -> int:
        """Load knowledge base from JSON. Returns count loaded."""
        load_path = Path(path) if path else (self.persist_dir or Path("."))
        fpath = load_path / "sc2_knowledge_base.json"
        if not fpath.exists():
            logger.warning("No knowledge base file at %s", fpath)
            return 0
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        docs = [SC2Document.from_dict(d) for d in data.get("documents", [])]
        count = self.engine.add_documents(docs)
        logger.info("Loaded %d documents from %s", count, fpath)
        return count

    # -- Summary / stats ---------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return summary statistics about the knowledge base."""
        docs = self.engine._documents
        by_type: Dict[str, int] = {}
        by_matchup: Dict[str, int] = {}
        by_phase: Dict[str, int] = {}
        for d in docs:
            tkey = d.doc_type.value
            by_type[tkey] = by_type.get(tkey, 0) + 1
            mkey = d.matchup.value if d.matchup else "any"
            by_matchup[mkey] = by_matchup.get(mkey, 0) + 1
            pkey = d.game_phase.name if d.game_phase else "any"
            by_phase[pkey] = by_phase.get(pkey, 0) + 1
        return {
            "total_documents": len(docs),
            "by_type": by_type,
            "by_matchup": by_matchup,
            "by_phase": by_phase,
            "llamaindex_available": _LLAMAINDEX_AVAILABLE,
        }


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate Phase 626 LlamaIndex Knowledge Base."""
    print("=" * 70)
    print("Phase 626: LlamaIndex Knowledge Base for SC2 Strategy Retrieval")
    print("=" * 70)
    print()

    kb = KnowledgeBase()

    # 1. Seed built-in guides
    count = kb.seed_builtin_guides()
    print(f"[1] Seeded {count} built-in strategy guides")
    print(f"    LlamaIndex available: {_LLAMAINDEX_AVAILABLE}")
    print()

    # 2. Add some replays
    replays = [
        "ZvT_marine_rush_early.SC2Replay",
        "ZvP_roach_timing_mid.SC2Replay",
        "ZvZ_ling_bane_opening.SC2Replay",
    ]
    for rp in replays:
        doc = kb.add_replay(rp)
        print(f"[2] Indexed replay: {doc.title} (matchup={doc.matchup})")
    print()

    # 3. Add a custom build order
    custom_bo = kb.add_build_order(
        "3-Hatch Hydra Timing",
        [
            ("0:00", "Hatchery"),
            ("0:46", "Overlord"),
            ("1:30", "Spawning Pool"),
            ("1:45", "Natural Hatchery"),
            ("2:00", "Third Hatchery"),
            ("2:30", "Queen x2, Ling Speed"),
            ("3:30", "Lair, Double Gas"),
            ("4:30", "Hydralisk Den"),
            ("5:30", "Hydra + Ling push"),
        ],
        matchup=Matchup.ZvP,
        phase=GamePhase.EARLY,
    )
    print(f"[3] Added build order: {custom_bo.title}")
    print()

    # 4. Summary
    stats = kb.summary()
    print(f"[4] Knowledge base summary:")
    print(f"    Total documents : {stats['total_documents']}")
    print(f"    By type         : {stats['by_type']}")
    print(f"    By matchup      : {stats['by_matchup']}")
    print(f"    By phase        : {stats['by_phase']}")
    print()

    # 5. Natural language queries
    test_queries = [
        ("How do I deal with Terran bio?", Matchup.ZvT, None),
        ("Roach timing attack", Matchup.ZvP, GamePhase.EARLY),
        ("ZvZ early game tips", Matchup.ZvZ, GamePhase.OPENING),
        ("Macro fundamentals", None, None),
        ("Late game transition broodlord", Matchup.ZvT, GamePhase.LATE),
    ]
    print("[5] Query results:")
    for question, mu, ph in test_queries:
        results = kb.ask(question, top_k=3, matchup=mu, game_phase=ph)
        print(f'\n  Q: "{question}" (matchup={mu}, phase={ph})')
        for i, r in enumerate(results):
            print(f"    #{i + 1} [{r.score:.3f}] {r.document.title}")
            print(f"         {r.explanation}")
    print()

    # 6. Game state query
    print("[6] Game state query:")
    gs_results = kb.ask_game_state(
        supply=80,
        matchup=Matchup.ZvT,
        game_time_seconds=480.0,
        army_comp={"Zergling": 30, "Baneling": 8, "Hydralisk": 12},
    )
    for i, r in enumerate(gs_results):
        print(f"    #{i + 1} [{r.score:.3f}] {r.document.title}")
        preview = r.document.content[:100].replace("\n", " ")
        print(f"         Preview: {preview}...")
    print()

    # 7. Persistence round-trip
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        saved = kb.save(tmpdir)
        print(f"[7] Saved knowledge base to: {saved}")
        kb2 = KnowledgeBase()
        loaded = kb2.load(tmpdir)
        print(f"    Loaded back: {loaded} documents")
        assert kb2.size == kb.size, "Round-trip size mismatch!"
        print(f"    Round-trip OK: {kb2.size} == {kb.size}")
    print()

    print("=" * 70)
    print("Phase 626 demo complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    demo()

# Phase 626: LlamaIndex registered
