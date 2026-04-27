# Phase 622: RAG Replay Search - SC2 Replay-Based Strategy Retrieval
# Retrieval-Augmented Generation system that indexes SC2 replays and retrieves
# relevant expert strategies based on game-state similarity queries.

import hashlib
import json
import logging
import math
import os
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import faiss

    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

try:
    import chromadb

    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SC2ReplayRAG")

# ============================================================
# Constants & Enums
# ============================================================

EMBEDDING_DIM = 128
MAX_CHUNK_TOKENS = 512
OVERLAP_TOKENS = 64
TOP_K_DEFAULT = 5


class GamePhase(Enum):
    """SC2 game phases for phase-aware chunking."""

    EARLY = "early"  # 0-5 min
    MID = "mid"  # 5-12 min
    LATE = "late"  # 12-20 min
    ULTRA_LATE = "ultra_late"  # 20+ min


class Race(Enum):
    ZERG = "Zerg"
    TERRAN = "Terran"
    PROTOSS = "Protoss"
    RANDOM = "Random"


PHASE_TIME_BOUNDARIES = {
    GamePhase.EARLY: (0, 300),
    GamePhase.MID: (300, 720),
    GamePhase.LATE: (720, 1200),
    GamePhase.ULTRA_LATE: (1200, float("inf")),
}

# ============================================================
# Data Classes
# ============================================================


@dataclass
class BuildOrderEntry:
    """A single entry in a build order."""

    time_seconds: float
    supply: int
    action: str
    unit_or_structure: str
    count: int = 1

    def to_text(self) -> str:
        minutes = int(self.time_seconds) // 60
        seconds = int(self.time_seconds) % 60
        return f"[{minutes}:{seconds:02d}] ({self.supply} supply) {self.action} {self.unit_or_structure} x{self.count}"


@dataclass
class ReplayOutcome:
    """Outcome metadata for a replay."""

    winner_race: str
    loser_race: str
    duration_seconds: float
    winner_apm: float = 0.0
    loser_apm: float = 0.0
    map_name: str = "Unknown"
    game_version: str = ""

    def to_text(self) -> str:
        mins = int(self.duration_seconds) // 60
        secs = int(self.duration_seconds) % 60
        return (
            f"Outcome: {self.winner_race} defeated {self.loser_race} "
            f"on {self.map_name} in {mins}:{secs:02d}. "
            f"Winner APM: {self.winner_apm:.0f}, Loser APM: {self.loser_apm:.0f}"
        )


@dataclass
class TimingWindow:
    """A notable timing event in the replay."""

    time_seconds: float
    event_type: str  # "attack", "expand", "tech", "upgrade"
    description: str
    player: int = 1  # 1 or 2
    phase: GamePhase = GamePhase.EARLY

    def to_text(self) -> str:
        mins = int(self.time_seconds) // 60
        secs = int(self.time_seconds) % 60
        return (
            f"[{mins}:{secs:02d}] P{self.player} {self.event_type}: {self.description}"
        )


@dataclass
class ReplayDocument:
    """Parsed SC2 replay as a structured document."""

    replay_id: str
    replay_path: str
    player1_race: str
    player2_race: str
    matchup: str
    build_orders: Dict[int, List[BuildOrderEntry]] = field(default_factory=dict)
    timings: List[TimingWindow] = field(default_factory=list)
    outcome: Optional[ReplayOutcome] = None
    army_compositions: Dict[int, Dict[str, int]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_full_text(self) -> str:
        """Convert entire replay into text representation."""
        sections = []
        sections.append(f"=== Replay: {self.replay_id} ===")
        sections.append(f"Matchup: {self.matchup}")
        if self.outcome:
            sections.append(self.outcome.to_text())

        for player_id in sorted(self.build_orders.keys()):
            race = self.player1_race if player_id == 1 else self.player2_race
            sections.append(f"\n--- Player {player_id} ({race}) Build Order ---")
            for entry in self.build_orders[player_id]:
                sections.append(entry.to_text())

        if self.timings:
            sections.append("\n--- Key Timings ---")
            for tw in sorted(self.timings, key=lambda t: t.time_seconds):
                sections.append(tw.to_text())

        if self.army_compositions:
            sections.append("\n--- Army Compositions ---")
            for pid, comp in self.army_compositions.items():
                race = self.player1_race if pid == 1 else self.player2_race
                comp_str = ", ".join(f"{u}: {c}" for u, c in comp.items())
                sections.append(f"Player {pid} ({race}): {comp_str}")

        return "\n".join(sections)


@dataclass
class TextChunk:
    """A chunked piece of replay text with metadata."""

    chunk_id: str
    text: str
    source_replay_id: str
    source_replay_path: str
    phase: GamePhase
    matchup: str
    chunk_type: str  # "build_order", "timing", "outcome", "composition", "full"
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def citation(self) -> str:
        return f"[Replay: {self.source_replay_id}, Phase: {self.phase.value}, Type: {self.chunk_type}]"


@dataclass
class RetrievalResult:
    """A single retrieval result with score and citation."""

    chunk: TextChunk
    score: float
    rerank_score: float = 0.0
    combined_score: float = 0.0
    citation: str = ""

    def __post_init__(self):
        if not self.citation:
            self.citation = self.chunk.citation()


# ============================================================
# Numpy Vector Math Fallback
# ============================================================


class VectorMath:
    """Vector math operations with numpy or pure-Python fallback."""

    @staticmethod
    def zeros(dim: int) -> List[float]:
        if HAS_NUMPY:
            return np.zeros(dim).tolist()
        return [0.0] * dim

    @staticmethod
    def normalize(vec: List[float]) -> List[float]:
        if HAS_NUMPY:
            arr = np.array(vec, dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm < 1e-10:
                return arr.tolist()
            return (arr / norm).tolist()
        norm = math.sqrt(sum(x * x for x in vec))
        if norm < 1e-10:
            return vec
        return [x / norm for x in vec]

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        if HAS_NUMPY:
            a_arr = np.array(a, dtype=np.float32)
            b_arr = np.array(b, dtype=np.float32)
            dot = np.dot(a_arr, b_arr)
            na = np.linalg.norm(a_arr)
            nb = np.linalg.norm(b_arr)
            if na < 1e-10 or nb < 1e-10:
                return 0.0
            return float(dot / (na * nb))
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na < 1e-10 or nb < 1e-10:
            return 0.0
        return dot / (na * nb)

    @staticmethod
    def dot_product(a: List[float], b: List[float]) -> float:
        if HAS_NUMPY:
            return float(np.dot(np.array(a), np.array(b)))
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def add(a: List[float], b: List[float]) -> List[float]:
        if HAS_NUMPY:
            return (np.array(a) + np.array(b)).tolist()
        return [x + y for x, y in zip(a, b)]

    @staticmethod
    def scale(vec: List[float], scalar: float) -> List[float]:
        if HAS_NUMPY:
            return (np.array(vec) * scalar).tolist()
        return [x * scalar for x in vec]

    @staticmethod
    def mean_vectors(vectors: List[List[float]]) -> List[float]:
        if not vectors:
            return []
        if HAS_NUMPY:
            return np.mean(np.array(vectors), axis=0).tolist()
        dim = len(vectors[0])
        result = [0.0] * dim
        for v in vectors:
            for i in range(dim):
                result[i] += v[i]
        n = len(vectors)
        return [x / n for x in result]


# ============================================================
# Replay Document Loader
# ============================================================


class SC2ReplayLoader:
    """Parse SC2 replays into structured ReplayDocument objects.

    In production this would use sc2reader or s2protocol to parse
    .SC2Replay files. Here we provide a parser interface with
    built-in demo replays for testing.
    """

    DEMO_REPLAYS: List[ReplayDocument] = []

    @classmethod
    def _init_demos(cls):
        if cls.DEMO_REPLAYS:
            return
        # --- Demo Replay 1: ZvT Roach-Hydra Timing ---
        r1 = ReplayDocument(
            replay_id="replay_001_zvt_roachhydra",
            replay_path="replays/001_zvt_roachhydra.SC2Replay",
            player1_race="Zerg",
            player2_race="Terran",
            matchup="ZvT",
            build_orders={
                1: [
                    BuildOrderEntry(13, 13, "build", "Overlord"),
                    BuildOrderEntry(17, 17, "build", "Hatchery"),
                    BuildOrderEntry(18, 18, "build", "Extractor"),
                    BuildOrderEntry(19, 17, "build", "SpawningPool"),
                    BuildOrderEntry(24, 24, "train", "Queen", 2),
                    BuildOrderEntry(28, 28, "train", "Zergling", 4),
                    BuildOrderEntry(32, 32, "build", "RoachWarren"),
                    BuildOrderEntry(44, 44, "build", "Extractor"),
                    BuildOrderEntry(50, 50, "train", "Roach", 8),
                    BuildOrderEntry(60, 60, "build", "HydraliskDen"),
                    BuildOrderEntry(66, 66, "research", "GlialReconstitution"),
                    BuildOrderEntry(75, 75, "train", "Hydralisk", 10),
                    BuildOrderEntry(80, 80, "attack", "MoveOut"),
                ],
                2: [
                    BuildOrderEntry(15, 15, "build", "SupplyDepot"),
                    BuildOrderEntry(16, 16, "build", "Barracks"),
                    BuildOrderEntry(19, 19, "build", "Refinery"),
                    BuildOrderEntry(20, 20, "train", "Reaper"),
                    BuildOrderEntry(22, 22, "build", "OrbitalCommand"),
                    BuildOrderEntry(23, 23, "build", "CommandCenter"),
                    BuildOrderEntry(25, 25, "build", "Factory"),
                    BuildOrderEntry(30, 30, "build", "Barracks", 2),
                    BuildOrderEntry(35, 35, "build", "EngineeringBay"),
                    BuildOrderEntry(40, 40, "research", "Stim"),
                    BuildOrderEntry(50, 50, "train", "Marine", 12),
                    BuildOrderEntry(55, 55, "train", "SiegeTank", 2),
                ],
            },
            timings=[
                TimingWindow(210, "tech", "Roach Warren started", 1, GamePhase.EARLY),
                TimingWindow(360, "tech", "Hydralisk Den started", 1, GamePhase.MID),
                TimingWindow(
                    480, "attack", "Roach-Hydra push begins", 1, GamePhase.MID
                ),
                TimingWindow(300, "expand", "Natural base completed", 2, GamePhase.MID),
                TimingWindow(420, "tech", "Stim research completed", 2, GamePhase.MID),
            ],
            outcome=ReplayOutcome(
                "Zerg", "Terran", 580, 185, 160, "Oxide LE", "5.0.12"
            ),
            army_compositions={
                1: {"Roach": 12, "Hydralisk": 10, "Zergling": 8, "Queen": 3},
                2: {"Marine": 18, "Marauder": 4, "SiegeTank": 2, "Medivac": 2},
            },
        )

        # --- Demo Replay 2: ZvP Ling-Bane into Ultras ---
        r2 = ReplayDocument(
            replay_id="replay_002_zvp_lingbane_ultra",
            replay_path="replays/002_zvp_lingbane_ultra.SC2Replay",
            player1_race="Zerg",
            player2_race="Protoss",
            matchup="ZvP",
            build_orders={
                1: [
                    BuildOrderEntry(13, 13, "build", "Overlord"),
                    BuildOrderEntry(16, 16, "build", "Hatchery"),
                    BuildOrderEntry(18, 18, "build", "Extractor"),
                    BuildOrderEntry(17, 17, "build", "SpawningPool"),
                    BuildOrderEntry(22, 22, "train", "Queen", 2),
                    BuildOrderEntry(24, 24, "research", "MetabolicBoost"),
                    BuildOrderEntry(30, 30, "build", "BanelingNest"),
                    BuildOrderEntry(36, 36, "train", "Zergling", 16),
                    BuildOrderEntry(44, 44, "morph", "Baneling", 8),
                    BuildOrderEntry(50, 50, "build", "Hatchery"),
                    BuildOrderEntry(66, 66, "build", "InfestationPit"),
                    BuildOrderEntry(70, 70, "research", "Hive"),
                    BuildOrderEntry(80, 80, "build", "UltraliskCavern"),
                    BuildOrderEntry(90, 90, "train", "Ultralisk", 6),
                    BuildOrderEntry(95, 95, "attack", "FinalPush"),
                ],
                2: [
                    BuildOrderEntry(14, 14, "build", "Pylon"),
                    BuildOrderEntry(16, 16, "build", "Gateway"),
                    BuildOrderEntry(17, 17, "build", "Assimilator"),
                    BuildOrderEntry(20, 20, "build", "Nexus"),
                    BuildOrderEntry(22, 22, "build", "CyberneticsCore"),
                    BuildOrderEntry(26, 26, "build", "Gateway", 2),
                    BuildOrderEntry(30, 30, "build", "TwilightCouncil"),
                    BuildOrderEntry(35, 35, "research", "Charge"),
                    BuildOrderEntry(40, 40, "build", "RoboticsFacility"),
                    BuildOrderEntry(50, 50, "train", "Immortal", 3),
                    BuildOrderEntry(55, 55, "train", "Zealot", 8),
                    BuildOrderEntry(60, 60, "train", "Archon", 4),
                ],
            },
            timings=[
                TimingWindow(180, "tech", "Baneling Nest started", 1, GamePhase.EARLY),
                TimingWindow(
                    300, "attack", "Ling-Bane pressure at natural", 1, GamePhase.MID
                ),
                TimingWindow(480, "tech", "Hive started", 1, GamePhase.MID),
                TimingWindow(
                    600, "tech", "Ultralisk Cavern completed", 1, GamePhase.LATE
                ),
                TimingWindow(720, "attack", "Ultra push begins", 1, GamePhase.LATE),
                TimingWindow(350, "tech", "Charge completed", 2, GamePhase.MID),
                TimingWindow(500, "expand", "Third base taken", 2, GamePhase.MID),
            ],
            outcome=ReplayOutcome(
                "Zerg", "Protoss", 840, 210, 145, "Alcyone LE", "5.0.12"
            ),
            army_compositions={
                1: {"Ultralisk": 6, "Zergling": 20, "Baneling": 12, "Corruptor": 4},
                2: {"Zealot": 12, "Archon": 4, "Immortal": 3, "Stalker": 6},
            },
        )

        # --- Demo Replay 3: ZvZ Macro Roach ---
        r3 = ReplayDocument(
            replay_id="replay_003_zvz_roach_macro",
            replay_path="replays/003_zvz_roach_macro.SC2Replay",
            player1_race="Zerg",
            player2_race="Zerg",
            matchup="ZvZ",
            build_orders={
                1: [
                    BuildOrderEntry(13, 13, "build", "Overlord"),
                    BuildOrderEntry(17, 17, "build", "Hatchery"),
                    BuildOrderEntry(17, 17, "build", "SpawningPool"),
                    BuildOrderEntry(19, 19, "build", "Extractor"),
                    BuildOrderEntry(22, 22, "train", "Queen", 2),
                    BuildOrderEntry(24, 24, "train", "Zergling", 4),
                    BuildOrderEntry(28, 28, "build", "RoachWarren"),
                    BuildOrderEntry(30, 30, "build", "Extractor"),
                    BuildOrderEntry(35, 35, "train", "Roach", 6),
                    BuildOrderEntry(44, 44, "build", "Lair"),
                    BuildOrderEntry(50, 50, "research", "RoachSpeed"),
                    BuildOrderEntry(55, 55, "train", "Roach", 8),
                    BuildOrderEntry(60, 60, "build", "Hatchery"),
                    BuildOrderEntry(70, 70, "train", "Ravager", 4),
                ],
                2: [
                    BuildOrderEntry(13, 13, "build", "Overlord"),
                    BuildOrderEntry(16, 16, "build", "SpawningPool"),
                    BuildOrderEntry(17, 17, "build", "Hatchery"),
                    BuildOrderEntry(18, 18, "build", "Extractor"),
                    BuildOrderEntry(20, 20, "train", "Queen", 2),
                    BuildOrderEntry(22, 22, "research", "MetabolicBoost"),
                    BuildOrderEntry(24, 24, "train", "Zergling", 8),
                    BuildOrderEntry(30, 30, "build", "BanelingNest"),
                    BuildOrderEntry(35, 35, "morph", "Baneling", 6),
                    BuildOrderEntry(40, 40, "build", "RoachWarren"),
                    BuildOrderEntry(50, 50, "train", "Roach", 6),
                ],
            },
            timings=[
                TimingWindow(168, "tech", "Roach Warren started", 1, GamePhase.EARLY),
                TimingWindow(264, "tech", "Lair started", 1, GamePhase.EARLY),
                TimingWindow(330, "attack", "Roach push at natural", 1, GamePhase.MID),
                TimingWindow(180, "tech", "Baneling Nest started", 2, GamePhase.EARLY),
                TimingWindow(300, "attack", "Ling-Bane counter", 2, GamePhase.MID),
            ],
            outcome=ReplayOutcome(
                "Zerg", "Zerg", 510, 230, 190, "Goldenaura LE", "5.0.12"
            ),
            army_compositions={
                1: {"Roach": 14, "Ravager": 4, "Zergling": 6},
                2: {"Zergling": 16, "Baneling": 8, "Roach": 6},
            },
        )

        # --- Demo Replay 4: ZvT Mutalisk Harass ---
        r4 = ReplayDocument(
            replay_id="replay_004_zvt_muta_harass",
            replay_path="replays/004_zvt_muta_harass.SC2Replay",
            player1_race="Zerg",
            player2_race="Terran",
            matchup="ZvT",
            build_orders={
                1: [
                    BuildOrderEntry(13, 13, "build", "Overlord"),
                    BuildOrderEntry(17, 17, "build", "Hatchery"),
                    BuildOrderEntry(18, 18, "build", "Extractor"),
                    BuildOrderEntry(17, 17, "build", "SpawningPool"),
                    BuildOrderEntry(22, 22, "train", "Queen", 2),
                    BuildOrderEntry(24, 24, "research", "MetabolicBoost"),
                    BuildOrderEntry(26, 26, "build", "Extractor"),
                    BuildOrderEntry(30, 30, "train", "Zergling", 6),
                    BuildOrderEntry(33, 33, "build", "Lair"),
                    BuildOrderEntry(44, 44, "build", "Spire"),
                    BuildOrderEntry(55, 55, "train", "Mutalisk", 11),
                    BuildOrderEntry(65, 65, "attack", "MutaHarass"),
                    BuildOrderEntry(80, 80, "build", "Hatchery"),
                    BuildOrderEntry(90, 90, "train", "Mutalisk", 6),
                ],
                2: [
                    BuildOrderEntry(15, 15, "build", "SupplyDepot"),
                    BuildOrderEntry(16, 16, "build", "Barracks"),
                    BuildOrderEntry(19, 19, "build", "Refinery"),
                    BuildOrderEntry(20, 20, "build", "OrbitalCommand"),
                    BuildOrderEntry(22, 22, "build", "CommandCenter"),
                    BuildOrderEntry(28, 28, "build", "Factory"),
                    BuildOrderEntry(32, 32, "build", "Starport"),
                    BuildOrderEntry(35, 35, "build", "Barracks", 2),
                    BuildOrderEntry(40, 40, "research", "Stim"),
                    BuildOrderEntry(45, 45, "train", "Marine", 10),
                    BuildOrderEntry(50, 50, "train", "Medivac", 2),
                    BuildOrderEntry(55, 55, "build", "EngineeringBay"),
                    BuildOrderEntry(60, 60, "build", "MissileTurret", 3),
                ],
            },
            timings=[
                TimingWindow(198, "tech", "Lair started", 1, GamePhase.EARLY),
                TimingWindow(300, "tech", "Spire completed", 1, GamePhase.MID),
                TimingWindow(
                    390, "attack", "11 Mutalisk harass begins", 1, GamePhase.MID
                ),
                TimingWindow(
                    540, "attack", "Second muta wave + ling runby", 1, GamePhase.MID
                ),
                TimingWindow(400, "tech", "Missile Turrets placed", 2, GamePhase.MID),
                TimingWindow(480, "attack", "Marine-Medivac drop", 2, GamePhase.MID),
            ],
            outcome=ReplayOutcome(
                "Zerg", "Terran", 720, 245, 175, "Oxide LE", "5.0.12"
            ),
            army_compositions={
                1: {"Mutalisk": 17, "Zergling": 24, "Baneling": 6, "Queen": 4},
                2: {
                    "Marine": 22,
                    "Medivac": 4,
                    "Marauder": 6,
                    "SiegeTank": 3,
                    "Thor": 1,
                },
            },
        )

        # --- Demo Replay 5: ZvP Nydus All-In ---
        r5 = ReplayDocument(
            replay_id="replay_005_zvp_nydus",
            replay_path="replays/005_zvp_nydus.SC2Replay",
            player1_race="Zerg",
            player2_race="Protoss",
            matchup="ZvP",
            build_orders={
                1: [
                    BuildOrderEntry(13, 13, "build", "Overlord"),
                    BuildOrderEntry(16, 16, "build", "Hatchery"),
                    BuildOrderEntry(18, 18, "build", "Extractor"),
                    BuildOrderEntry(17, 17, "build", "SpawningPool"),
                    BuildOrderEntry(22, 22, "train", "Queen", 2),
                    BuildOrderEntry(25, 25, "build", "Lair"),
                    BuildOrderEntry(28, 28, "build", "RoachWarren"),
                    BuildOrderEntry(33, 33, "build", "NydusNetwork"),
                    BuildOrderEntry(38, 38, "train", "Roach", 8),
                    BuildOrderEntry(42, 42, "build", "NydusWorm"),
                    BuildOrderEntry(44, 44, "attack", "NydusAllIn"),
                    BuildOrderEntry(50, 50, "train", "Ravager", 4),
                ],
                2: [
                    BuildOrderEntry(14, 14, "build", "Pylon"),
                    BuildOrderEntry(16, 16, "build", "Gateway"),
                    BuildOrderEntry(17, 17, "build", "Assimilator"),
                    BuildOrderEntry(20, 20, "build", "Nexus"),
                    BuildOrderEntry(22, 22, "build", "CyberneticsCore"),
                    BuildOrderEntry(28, 28, "build", "Stargate"),
                    BuildOrderEntry(33, 33, "train", "Oracle"),
                    BuildOrderEntry(40, 40, "build", "Gateway", 2),
                    BuildOrderEntry(45, 45, "train", "Adept", 4),
                ],
            },
            timings=[
                TimingWindow(165, "tech", "Lair started for Nydus", 1, GamePhase.EARLY),
                TimingWindow(
                    210, "tech", "Nydus Network completed", 1, GamePhase.EARLY
                ),
                TimingWindow(
                    252, "attack", "Nydus Worm placed in main", 1, GamePhase.EARLY
                ),
                TimingWindow(270, "attack", "All-in through Nydus", 1, GamePhase.EARLY),
                TimingWindow(
                    200, "tech", "Oracle out for scouting", 2, GamePhase.EARLY
                ),
            ],
            outcome=ReplayOutcome(
                "Zerg", "Protoss", 350, 265, 130, "Equilibrium LE", "5.0.12"
            ),
            army_compositions={
                1: {"Roach": 10, "Ravager": 4, "Queen": 3, "Zergling": 8},
                2: {"Adept": 4, "Oracle": 1, "Stalker": 2, "Zealot": 3},
            },
        )

        cls.DEMO_REPLAYS = [r1, r2, r3, r4, r5]

    def load_replay_file(self, path: str) -> Optional[ReplayDocument]:
        """Load and parse a single .SC2Replay file.

        In production, use sc2reader:
            replay = sc2reader.load_replay(path)
        Here we simulate with demo data.
        """
        logger.info(f"Loading replay: {path}")
        self._init_demos()
        for demo in self.DEMO_REPLAYS:
            if Path(demo.replay_path).name in path:
                return demo
        # Return a placeholder for unknown files
        replay_id = hashlib.md5(path.encode()).hexdigest()[:12]
        return ReplayDocument(
            replay_id=f"replay_{replay_id}",
            replay_path=path,
            player1_race="Unknown",
            player2_race="Unknown",
            matchup="Unknown",
        )

    def load_directory(self, directory: str) -> List[ReplayDocument]:
        """Load all replays from a directory."""
        self._init_demos()
        replays = []
        dir_path = Path(directory)
        if dir_path.exists():
            for f in dir_path.glob("*.SC2Replay"):
                doc = self.load_replay_file(str(f))
                if doc:
                    replays.append(doc)
        if not replays:
            logger.info("No replay files found; loading demo replays.")
            replays = list(self.DEMO_REPLAYS)
        return replays

    def load_demos(self) -> List[ReplayDocument]:
        """Load built-in demo replays."""
        self._init_demos()
        return list(self.DEMO_REPLAYS)


# ============================================================
# Game-Phase-Aware Text Splitter
# ============================================================


class GamePhaseTextSplitter:
    """Split replay text into chunks aligned with game phases."""

    def __init__(
        self, max_tokens: int = MAX_CHUNK_TOKENS, overlap: int = OVERLAP_TOKENS
    ):
        self.max_tokens = max_tokens
        self.overlap = overlap

    def _classify_phase(self, time_seconds: float) -> GamePhase:
        for phase, (start, end) in PHASE_TIME_BOUNDARIES.items():
            if start <= time_seconds < end:
                return phase
        return GamePhase.ULTRA_LATE

    def _estimate_tokens(self, text: str) -> int:
        return len(text.split())

    def split_replay(self, replay: ReplayDocument) -> List[TextChunk]:
        """Split a replay into phase-aware chunks."""
        chunks: List[TextChunk] = []

        # Chunk 1: Overview/outcome chunk
        overview_lines = [
            f"Replay {replay.replay_id}: {replay.matchup}",
        ]
        if replay.outcome:
            overview_lines.append(replay.outcome.to_text())
        if replay.army_compositions:
            for pid, comp in replay.army_compositions.items():
                race = replay.player1_race if pid == 1 else replay.player2_race
                comp_str = ", ".join(f"{u}: {c}" for u, c in comp.items())
                overview_lines.append(f"Player {pid} ({race}) final army: {comp_str}")
        chunks.append(
            TextChunk(
                chunk_id=f"{replay.replay_id}_overview",
                text="\n".join(overview_lines),
                source_replay_id=replay.replay_id,
                source_replay_path=replay.replay_path,
                phase=GamePhase.EARLY,
                matchup=replay.matchup,
                chunk_type="outcome",
                metadata={
                    "player1_race": replay.player1_race,
                    "player2_race": replay.player2_race,
                },
            )
        )

        # Chunk per phase per player build order
        for player_id in sorted(replay.build_orders.keys()):
            race = replay.player1_race if player_id == 1 else replay.player2_race
            entries = replay.build_orders[player_id]
            phase_entries: Dict[GamePhase, List[BuildOrderEntry]] = {}
            for entry in entries:
                phase = self._classify_phase(entry.time_seconds)
                phase_entries.setdefault(phase, []).append(entry)

            for phase, pentries in phase_entries.items():
                lines = [f"Player {player_id} ({race}) {phase.value} game build:"]
                for e in pentries:
                    lines.append(e.to_text())
                text = "\n".join(lines)

                # If chunk too long, split further
                if self._estimate_tokens(text) > self.max_tokens:
                    sub_chunks = self._split_long_text(
                        text, phase, replay, "build_order", player_id
                    )
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(
                        TextChunk(
                            chunk_id=f"{replay.replay_id}_p{player_id}_{phase.value}_bo",
                            text=text,
                            source_replay_id=replay.replay_id,
                            source_replay_path=replay.replay_path,
                            phase=phase,
                            matchup=replay.matchup,
                            chunk_type="build_order",
                            metadata={"player_id": player_id, "race": race},
                        )
                    )

        # Chunk for timing windows
        if replay.timings:
            phase_timings: Dict[GamePhase, List[TimingWindow]] = {}
            for tw in replay.timings:
                phase_timings.setdefault(tw.phase, []).append(tw)
            for phase, tws in phase_timings.items():
                lines = [f"Key timings ({phase.value} game):"]
                for tw in sorted(tws, key=lambda t: t.time_seconds):
                    lines.append(tw.to_text())
                chunks.append(
                    TextChunk(
                        chunk_id=f"{replay.replay_id}_{phase.value}_timings",
                        text="\n".join(lines),
                        source_replay_id=replay.replay_id,
                        source_replay_path=replay.replay_path,
                        phase=phase,
                        matchup=replay.matchup,
                        chunk_type="timing",
                    )
                )

        return chunks

    def _split_long_text(
        self,
        text: str,
        phase: GamePhase,
        replay: ReplayDocument,
        chunk_type: str,
        player_id: int = 0,
    ) -> List[TextChunk]:
        """Split text that exceeds max_tokens into overlapping sub-chunks."""
        words = text.split()
        chunks = []
        idx = 0
        part = 0
        while idx < len(words):
            end = min(idx + self.max_tokens, len(words))
            chunk_text = " ".join(words[idx:end])
            chunks.append(
                TextChunk(
                    chunk_id=f"{replay.replay_id}_p{player_id}_{phase.value}_{chunk_type}_pt{part}",
                    text=chunk_text,
                    source_replay_id=replay.replay_id,
                    source_replay_path=replay.replay_path,
                    phase=phase,
                    matchup=replay.matchup,
                    chunk_type=chunk_type,
                    metadata={"player_id": player_id, "part": part},
                )
            )
            idx = end - self.overlap if end < len(words) else end
            part += 1
        return chunks


# ============================================================
# Embedding Model
# ============================================================


class SC2GameStateEncoder:
    """Encode game-state text into fixed-dimension vectors.

    Uses a deterministic hash-based embedding as a lightweight fallback.
    In production, swap in a real transformer encoder.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim
        # Keyword weight table for domain-aware embedding
        self.keyword_weights: Dict[str, List[float]] = {}
        self._init_keyword_vectors()

    def _init_keyword_vectors(self):
        """Create stable pseudo-random vectors for SC2 keywords."""
        keywords = [
            "zergling",
            "baneling",
            "roach",
            "hydralisk",
            "mutalisk",
            "ultralisk",
            "corruptor",
            "broodlord",
            "infestor",
            "queen",
            "ravager",
            "lurker",
            "viper",
            "swarmhost",
            "overlord",
            "marine",
            "marauder",
            "medivac",
            "siegetank",
            "thor",
            "hellion",
            "viking",
            "liberator",
            "ghost",
            "battlecruiser",
            "zealot",
            "stalker",
            "adept",
            "immortal",
            "colossus",
            "archon",
            "oracle",
            "phoenix",
            "voidray",
            "carrier",
            "hatchery",
            "lair",
            "hive",
            "spawningpool",
            "roachwarren",
            "hydraliskden",
            "spire",
            "banelingnest",
            "nydusnetwork",
            "attack",
            "defend",
            "expand",
            "harass",
            "timing",
            "push",
            "allin",
            "macro",
            "micro",
            "scout",
            "early",
            "mid",
            "late",
            "upgrade",
            "research",
            "zvt",
            "zvp",
            "zvz",
            "tvp",
            "tvt",
            "pvp",
        ]
        for kw in keywords:
            seed = int(hashlib.md5(kw.encode()).hexdigest(), 16) % (2**31)
            vec = self._seeded_random_vector(seed)
            self.keyword_weights[kw] = vec

    def _seeded_random_vector(self, seed: int) -> List[float]:
        """Generate a deterministic pseudo-random unit vector from a seed."""
        vec = []
        state = seed
        for _ in range(self.dim):
            # Linear congruential generator
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            val = (state / 0x7FFFFFFF) * 2.0 - 1.0
            vec.append(val)
        return VectorMath.normalize(vec)

    def encode(self, text: str) -> List[float]:
        """Encode text into a vector by aggregating keyword vectors."""
        text_lower = text.lower()
        tokens = (
            text_lower.replace(",", " ").replace(".", " ").replace(":", " ").split()
        )
        accumulator = VectorMath.zeros(self.dim)
        matches = 0

        for token in tokens:
            token_clean = token.strip("[]()_")
            if token_clean in self.keyword_weights:
                kw_vec = self.keyword_weights[token_clean]
                accumulator = VectorMath.add(accumulator, kw_vec)
                matches += 1
            # Partial match: check if any keyword is a substring
            else:
                for kw, kw_vec in self.keyword_weights.items():
                    if kw in token_clean or token_clean in kw:
                        accumulator = VectorMath.add(
                            accumulator, VectorMath.scale(kw_vec, 0.5)
                        )
                        matches += 1
                        break

        # Add a content-hash component for text not covered by keywords
        hash_vec = self._seeded_random_vector(
            int(hashlib.md5(text_lower.encode()).hexdigest(), 16) % (2**31)
        )
        weight = 0.3 if matches > 0 else 1.0
        accumulator = VectorMath.add(accumulator, VectorMath.scale(hash_vec, weight))

        return VectorMath.normalize(accumulator)

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts."""
        return [self.encode(t) for t in texts]


# ============================================================
# Vector Store (FAISS / ChromaDB / Brute-Force Numpy)
# ============================================================


class BruteForceVectorStore:
    """Pure numpy / pure-Python brute-force vector store."""

    def __init__(self):
        self.vectors: List[List[float]] = []
        self.chunks: List[TextChunk] = []

    def add(self, chunk: TextChunk, vector: List[float]):
        self.vectors.append(vector)
        self.chunks.append(chunk)

    def add_batch(self, chunks: List[TextChunk], vectors: List[List[float]]):
        for c, v in zip(chunks, vectors):
            self.add(c, v)

    def search(
        self, query_vector: List[float], top_k: int = TOP_K_DEFAULT
    ) -> List[Tuple[TextChunk, float]]:
        if not self.vectors:
            return []
        scores = []
        for i, vec in enumerate(self.vectors):
            sim = VectorMath.cosine_similarity(query_vector, vec)
            scores.append((i, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in scores[:top_k]:
            results.append((self.chunks[idx], score))
        return results

    def size(self) -> int:
        return len(self.vectors)

    def save(self, path: str):
        data = {
            "vectors": self.vectors,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "source_replay_id": c.source_replay_id,
                    "source_replay_path": c.source_replay_path,
                    "phase": c.phase.value,
                    "matchup": c.matchup,
                    "chunk_type": c.chunk_type,
                    "metadata": c.metadata,
                }
                for c in self.chunks
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved vector store to {path} ({self.size()} vectors)")

    def load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vectors = data["vectors"]
        self.chunks = []
        for cd in data["chunks"]:
            self.chunks.append(
                TextChunk(
                    chunk_id=cd["chunk_id"],
                    text=cd["text"],
                    source_replay_id=cd["source_replay_id"],
                    source_replay_path=cd["source_replay_path"],
                    phase=GamePhase(cd["phase"]),
                    matchup=cd["matchup"],
                    chunk_type=cd["chunk_type"],
                    metadata=cd.get("metadata", {}),
                )
            )
        logger.info(f"Loaded vector store from {path} ({self.size()} vectors)")


class FAISSVectorStore:
    """FAISS-backed vector store with fallback."""

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim
        self.chunks: List[TextChunk] = []
        if HAS_FAISS:
            self.index = faiss.IndexFlatIP(dim)  # Inner product (use normalized vecs)
        else:
            self.index = None
            self._fallback = BruteForceVectorStore()
            logger.warning("FAISS not available, using brute-force fallback.")

    def add(self, chunk: TextChunk, vector: List[float]):
        self.chunks.append(chunk)
        if self.index is not None:
            vec_np = np.array([vector], dtype=np.float32)
            self.index.add(vec_np)
        else:
            self._fallback.add(chunk, vector)

    def add_batch(self, chunks: List[TextChunk], vectors: List[List[float]]):
        if self.index is not None:
            self.chunks.extend(chunks)
            vecs_np = np.array(vectors, dtype=np.float32)
            self.index.add(vecs_np)
        else:
            self._fallback.add_batch(chunks, vectors)

    def search(
        self, query_vector: List[float], top_k: int = TOP_K_DEFAULT
    ) -> List[Tuple[TextChunk, float]]:
        if self.index is not None:
            q = np.array([query_vector], dtype=np.float32)
            k = min(top_k, self.index.ntotal)
            if k == 0:
                return []
            scores, indices = self.index.search(q, k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0:
                    results.append((self.chunks[idx], float(score)))
            return results
        else:
            return self._fallback.search(query_vector, top_k)

    def size(self) -> int:
        if self.index is not None:
            return self.index.ntotal
        return self._fallback.size()


class ChromaVectorStore:
    """ChromaDB-backed vector store with fallback."""

    def __init__(self, collection_name: str = "sc2_replays", dim: int = EMBEDDING_DIM):
        self.dim = dim
        self.chunks: Dict[str, TextChunk] = {}
        if HAS_CHROMA:
            self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        else:
            self.collection = None
            self._fallback = BruteForceVectorStore()
            logger.warning("ChromaDB not available, using brute-force fallback.")

    def add(self, chunk: TextChunk, vector: List[float]):
        self.chunks[chunk.chunk_id] = chunk
        if self.collection is not None:
            self.collection.add(
                ids=[chunk.chunk_id],
                embeddings=[vector],
                documents=[chunk.text],
                metadatas=[
                    {
                        "source_replay_id": chunk.source_replay_id,
                        "phase": chunk.phase.value,
                        "matchup": chunk.matchup,
                        "chunk_type": chunk.chunk_type,
                    }
                ],
            )
        else:
            self._fallback.add(chunk, vector)

    def add_batch(self, chunks: List[TextChunk], vectors: List[List[float]]):
        for c, v in zip(chunks, vectors):
            self.add(c, v)

    def search(
        self, query_vector: List[float], top_k: int = TOP_K_DEFAULT
    ) -> List[Tuple[TextChunk, float]]:
        if self.collection is not None:
            count = self.collection.count()
            if count == 0:
                return []
            k = min(top_k, count)
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=k,
            )
            output = []
            if results["ids"] and results["ids"][0]:
                distances = (
                    results["distances"][0]
                    if results.get("distances")
                    else [0.0] * len(results["ids"][0])
                )
                for cid, dist in zip(results["ids"][0], distances):
                    if cid in self.chunks:
                        score = 1.0 - dist  # cosine distance to similarity
                        output.append((self.chunks[cid], score))
            return output
        else:
            return self._fallback.search(query_vector, top_k)

    def size(self) -> int:
        if self.collection is not None:
            return self.collection.count()
        return self._fallback.size()


# ============================================================
# Re-Ranker with Game-Context Relevance Scoring
# ============================================================


class GameContextReranker:
    """Re-rank retrieval results using game-context relevance signals."""

    # Matchup compatibility matrix
    MATCHUP_COMPAT: Dict[str, List[str]] = {
        "ZvT": ["ZvT", "TvZ"],
        "ZvP": ["ZvP", "PvZ"],
        "ZvZ": ["ZvZ"],
        "TvP": ["TvP", "PvT"],
        "TvT": ["TvT"],
        "PvP": ["PvP"],
    }

    def __init__(self):
        self.phase_weight = 0.2
        self.matchup_weight = 0.3
        self.chunk_type_weight = 0.15
        self.keyword_weight = 0.35

    def rerank(
        self,
        results: List[RetrievalResult],
        query_context: Dict[str, Any],
    ) -> List[RetrievalResult]:
        """Re-rank results using game context."""
        query_matchup = query_context.get("matchup", "")
        query_phase = query_context.get("phase", "")
        query_keywords = set(query_context.get("keywords", []))
        preferred_types = set(query_context.get("chunk_types", []))

        for r in results:
            phase_score = 0.0
            matchup_score = 0.0
            type_score = 0.0
            keyword_score = 0.0

            # Phase relevance
            if query_phase:
                if r.chunk.phase.value == query_phase:
                    phase_score = 1.0
                elif self._phase_distance(r.chunk.phase.value, query_phase) == 1:
                    phase_score = 0.5

            # Matchup relevance
            if query_matchup:
                compat = self.MATCHUP_COMPAT.get(query_matchup, [query_matchup])
                if r.chunk.matchup in compat:
                    matchup_score = 1.0
                elif r.chunk.matchup == "all":
                    matchup_score = 0.5

            # Chunk type preference
            if preferred_types:
                if r.chunk.chunk_type in preferred_types:
                    type_score = 1.0

            # Keyword overlap
            if query_keywords:
                chunk_words = set(r.chunk.text.lower().split())
                overlap = len(query_keywords & chunk_words)
                keyword_score = min(overlap / max(len(query_keywords), 1), 1.0)

            r.rerank_score = (
                self.phase_weight * phase_score
                + self.matchup_weight * matchup_score
                + self.chunk_type_weight * type_score
                + self.keyword_weight * keyword_score
            )
            # Combined: weighted average of retrieval similarity and rerank
            r.combined_score = 0.5 * r.score + 0.5 * r.rerank_score

        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results

    @staticmethod
    def _phase_distance(a: str, b: str) -> int:
        order = ["early", "mid", "late", "ultra_late"]
        if a in order and b in order:
            return abs(order.index(a) - order.index(b))
        return 2


# ============================================================
# Multi-Query Retriever
# ============================================================


class MultiQueryRetriever:
    """Generate multiple sub-queries for complex strategy questions."""

    QUERY_TEMPLATES = [
        "build order for {subject}",
        "timing attack {subject}",
        "army composition {subject}",
        "counter strategy {subject}",
        "key upgrades and tech {subject}",
    ]

    def __init__(self, encoder: SC2GameStateEncoder):
        self.encoder = encoder

    def generate_sub_queries(self, query: str) -> List[str]:
        """Break a complex query into focused sub-queries."""
        sub_queries = [query]  # Always include original

        query_lower = query.lower()

        # Extract matchup context
        matchup = ""
        for mu in ["zvt", "zvp", "zvz", "tvp", "tvt", "pvp"]:
            if mu in query_lower:
                matchup = mu
                break

        # Extract key subjects
        subjects = []
        sc2_terms = [
            "roach",
            "hydra",
            "mutalisk",
            "zergling",
            "baneling",
            "ultra",
            "marine",
            "tank",
            "medivac",
            "stalker",
            "immortal",
            "colossus",
            "timing",
            "macro",
            "allin",
            "harass",
            "nydus",
            "drop",
        ]
        for term in sc2_terms:
            if term in query_lower:
                subjects.append(term)

        subject_str = " ".join(subjects) if subjects else query_lower
        if matchup:
            subject_str = f"{matchup} {subject_str}"

        # Generate sub-queries from templates
        for template in self.QUERY_TEMPLATES:
            sq = template.format(subject=subject_str)
            if sq != query:
                sub_queries.append(sq)

        return sub_queries[:5]  # Limit to 5 sub-queries

    def retrieve_multi(
        self,
        query: str,
        vector_store: Any,
        top_k: int = TOP_K_DEFAULT,
    ) -> List[Tuple[TextChunk, float]]:
        """Retrieve using multiple sub-queries and merge results."""
        sub_queries = self.generate_sub_queries(query)
        all_results: Dict[str, Tuple[TextChunk, float]] = {}

        for sq in sub_queries:
            vec = self.encoder.encode(sq)
            results = vector_store.search(vec, top_k=top_k)
            for chunk, score in results:
                if chunk.chunk_id not in all_results:
                    all_results[chunk.chunk_id] = (chunk, score)
                else:
                    # Keep best score
                    existing_score = all_results[chunk.chunk_id][1]
                    if score > existing_score:
                        all_results[chunk.chunk_id] = (chunk, score)

        merged = list(all_results.values())
        merged.sort(key=lambda x: x[1], reverse=True)
        return merged[: top_k * 2]  # Return up to 2x top_k for reranking


# ============================================================
# Query Context Extractor
# ============================================================


class QueryContextExtractor:
    """Extract structured context from natural language queries."""

    MATCHUP_PATTERNS = {
        "zvt": "ZvT",
        "zerg vs terran": "ZvT",
        "zerg versus terran": "ZvT",
        "zvp": "ZvP",
        "zerg vs protoss": "ZvP",
        "zerg versus protoss": "ZvP",
        "zvz": "ZvZ",
        "zerg vs zerg": "ZvZ",
        "zerg mirror": "ZvZ",
        "tvp": "TvP",
        "terran vs protoss": "TvP",
        "tvt": "TvT",
        "terran vs terran": "TvT",
        "terran mirror": "TvT",
        "pvp": "PvP",
        "protoss vs protoss": "PvP",
        "protoss mirror": "PvP",
    }

    PHASE_PATTERNS = {
        "early": "early",
        "opening": "early",
        "start": "early",
        "mid": "mid",
        "midgame": "mid",
        "mid game": "mid",
        "late": "late",
        "lategame": "late",
        "late game": "late",
        "ultra late": "ultra_late",
        "very late": "ultra_late",
    }

    TYPE_PATTERNS = {
        "build": "build_order",
        "build order": "build_order",
        "opener": "build_order",
        "timing": "timing",
        "attack timing": "timing",
        "push": "timing",
        "composition": "composition",
        "army": "composition",
        "comp": "composition",
        "counter": "outcome",
        "result": "outcome",
        "winner": "outcome",
    }

    def extract(self, query: str) -> Dict[str, Any]:
        """Extract context from a query string."""
        ql = query.lower()
        context: Dict[str, Any] = {"keywords": []}

        # Extract matchup
        for pattern, matchup in self.MATCHUP_PATTERNS.items():
            if pattern in ql:
                context["matchup"] = matchup
                break

        # Extract phase
        for pattern, phase in self.PHASE_PATTERNS.items():
            if pattern in ql:
                context["phase"] = phase
                break

        # Extract preferred chunk types
        chunk_types = set()
        for pattern, ctype in self.TYPE_PATTERNS.items():
            if pattern in ql:
                chunk_types.add(ctype)
        if chunk_types:
            context["chunk_types"] = list(chunk_types)

        # Extract SC2 keywords
        sc2_keywords = [
            "roach",
            "hydralisk",
            "mutalisk",
            "zergling",
            "baneling",
            "ultralisk",
            "ravager",
            "nydus",
            "lurker",
            "infestor",
            "marine",
            "marauder",
            "tank",
            "medivac",
            "thor",
            "zealot",
            "stalker",
            "immortal",
            "colossus",
            "archon",
            "macro",
            "micro",
            "timing",
            "allin",
            "harass",
        ]
        for kw in sc2_keywords:
            if kw in ql:
                context["keywords"].append(kw)

        return context


# ============================================================
# SC2 Replay RAG System
# ============================================================


class SC2ReplayRAG:
    """Complete RAG system for SC2 replay-based strategy retrieval.

    Pipeline:
        1. Load replays -> parse into ReplayDocuments
        2. Split into game-phase-aware TextChunks
        3. Encode chunks into vectors
        4. Store in vector store (FAISS/Chroma/BruteForce)
        5. Query: encode query -> retrieve similar chunks -> rerank -> cite
    """

    def __init__(
        self,
        store_type: str = "auto",
        embedding_dim: int = EMBEDDING_DIM,
    ):
        self.encoder = SC2GameStateEncoder(dim=embedding_dim)
        self.splitter = GamePhaseTextSplitter()
        self.reranker = GameContextReranker()
        self.multi_retriever = MultiQueryRetriever(self.encoder)
        self.context_extractor = QueryContextExtractor()
        self.loader = SC2ReplayLoader()
        self.embedding_dim = embedding_dim
        self.all_chunks: List[TextChunk] = []

        # Select vector store
        if store_type == "faiss" or (store_type == "auto" and HAS_FAISS):
            self.vector_store = FAISSVectorStore(dim=embedding_dim)
            logger.info("Using FAISS vector store.")
        elif store_type == "chroma" or (store_type == "auto" and HAS_CHROMA):
            self.vector_store = ChromaVectorStore(dim=embedding_dim)
            logger.info("Using ChromaDB vector store.")
        else:
            self.vector_store = BruteForceVectorStore()
            logger.info("Using brute-force numpy vector store.")

    def index_replays(self, replays: List[ReplayDocument]):
        """Index a list of replays into the vector store."""
        total_chunks = 0
        for replay in replays:
            chunks = self.splitter.split_replay(replay)
            texts = [c.text for c in chunks]
            vectors = self.encoder.encode_batch(texts)

            for chunk, vec in zip(chunks, vectors):
                chunk.embedding = vec

            self.vector_store.add_batch(chunks, vectors)
            self.all_chunks.extend(chunks)
            total_chunks += len(chunks)
            logger.info(f"Indexed replay {replay.replay_id}: {len(chunks)} chunks")

        logger.info(f"Total indexed: {total_chunks} chunks from {len(replays)} replays")

    def index_directory(self, directory: str):
        """Load and index all replays from a directory."""
        replays = self.loader.load_directory(directory)
        self.index_replays(replays)

    def index_demos(self):
        """Load and index built-in demo replays."""
        replays = self.loader.load_demos()
        self.index_replays(replays)

    def query(
        self,
        query_text: str,
        top_k: int = TOP_K_DEFAULT,
        use_multi_query: bool = True,
        use_rerank: bool = True,
    ) -> List[RetrievalResult]:
        """Query the replay database for relevant strategy information.

        Args:
            query_text: Natural language query about SC2 strategy.
            top_k: Number of results to return.
            use_multi_query: Whether to use multi-query retrieval.
            use_rerank: Whether to apply game-context reranking.

        Returns:
            List of RetrievalResult with citations.
        """
        # Extract context
        context = self.context_extractor.extract(query_text)

        # Retrieve
        if use_multi_query:
            raw_results = self.multi_retriever.retrieve_multi(
                query_text, self.vector_store, top_k=top_k
            )
        else:
            query_vec = self.encoder.encode(query_text)
            raw_results = self.vector_store.search(query_vec, top_k=top_k * 2)

        # Build RetrievalResult objects
        retrieval_results = [
            RetrievalResult(chunk=chunk, score=score) for chunk, score in raw_results
        ]

        # Re-rank
        if use_rerank and retrieval_results:
            retrieval_results = self.reranker.rerank(retrieval_results, context)

        # Trim to top_k
        retrieval_results = retrieval_results[:top_k]

        return retrieval_results

    def query_with_citations(
        self,
        query_text: str,
        top_k: int = TOP_K_DEFAULT,
    ) -> Dict[str, Any]:
        """Query and format results with full citations."""
        results = self.query(query_text, top_k=top_k)
        formatted = {
            "query": query_text,
            "num_results": len(results),
            "results": [],
        }
        for i, r in enumerate(results):
            formatted["results"].append(
                {
                    "rank": i + 1,
                    "text": r.chunk.text,
                    "citation": r.citation,
                    "similarity_score": round(r.score, 4),
                    "rerank_score": round(r.rerank_score, 4),
                    "combined_score": round(r.combined_score, 4),
                    "matchup": r.chunk.matchup,
                    "phase": r.chunk.phase.value,
                    "chunk_type": r.chunk.chunk_type,
                    "source_replay": r.chunk.source_replay_id,
                    "source_path": r.chunk.source_replay_path,
                }
            )
        return formatted

    def get_stats(self) -> Dict[str, Any]:
        """Return indexing statistics."""
        matchup_counts: Dict[str, int] = {}
        phase_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        replay_ids = set()

        for chunk in self.all_chunks:
            matchup_counts[chunk.matchup] = matchup_counts.get(chunk.matchup, 0) + 1
            phase_counts[chunk.phase.value] = phase_counts.get(chunk.phase.value, 0) + 1
            type_counts[chunk.chunk_type] = type_counts.get(chunk.chunk_type, 0) + 1
            replay_ids.add(chunk.source_replay_id)

        return {
            "total_chunks": len(self.all_chunks),
            "total_replays": len(replay_ids),
            "vector_store_size": self.vector_store.size(),
            "embedding_dim": self.embedding_dim,
            "matchup_distribution": matchup_counts,
            "phase_distribution": phase_counts,
            "chunk_type_distribution": type_counts,
        }


# ============================================================
# CLI Demo
# ============================================================


def run_cli_demo():
    """Run interactive CLI demo of SC2 Replay RAG."""
    print("=" * 70)
    print("  Phase 622: SC2 Replay RAG - Strategy Retrieval System")
    print("=" * 70)
    print()

    # Initialize
    rag = SC2ReplayRAG(store_type="auto")
    print("[*] Loading and indexing demo replays...")
    rag.index_demos()

    stats = rag.get_stats()
    print(
        f"[*] Indexed {stats['total_replays']} replays -> {stats['total_chunks']} chunks"
    )
    print(f"    Vector store size: {stats['vector_store_size']}")
    print(f"    Embedding dimension: {stats['embedding_dim']}")
    print(f"    Matchups: {stats['matchup_distribution']}")
    print(f"    Phases: {stats['phase_distribution']}")
    print(f"    Chunk types: {stats['chunk_type_distribution']}")
    print()

    # Demo queries
    demo_queries = [
        "Best ZvT roach hydra timing attack build order",
        "How to counter mass marines with Zerg in mid game",
        "Mutalisk harass strategy ZvT",
        "ZvP early game all-in with nydus worm",
        "Late game ZvP army composition with ultralisk",
    ]

    print("-" * 70)
    print("  Running demo queries")
    print("-" * 70)

    for query in demo_queries:
        print(f"\n>>> Query: {query}")
        result = rag.query_with_citations(query, top_k=3)
        print(f"    Found {result['num_results']} results:")
        for r in result["results"]:
            print(
                f"    [{r['rank']}] Score: {r['combined_score']:.3f} "
                f"(sim={r['similarity_score']:.3f}, rerank={r['rerank_score']:.3f})"
            )
            print(f"        {r['citation']}")
            # Print first 120 chars of text
            text_preview = r["text"][:120].replace("\n", " ")
            print(f'        "{text_preview}..."')
        print()

    # Interactive mode
    print("-" * 70)
    print("  Interactive Mode (type 'quit' to exit)")
    print("-" * 70)
    while True:
        try:
            query = input("\nQuery> ").strip()
            if not query or query.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            result = rag.query_with_citations(query, top_k=5)
            print(f"\nFound {result['num_results']} results:\n")
            for r in result["results"]:
                print(
                    f"  [{r['rank']}] Combined={r['combined_score']:.3f} | "
                    f"{r['citation']}"
                )
                print(
                    f"      Matchup: {r['matchup']} | Phase: {r['phase']} | "
                    f"Type: {r['chunk_type']}"
                )
                lines = r["text"].strip().split("\n")
                for line in lines[:6]:
                    print(f"      {line}")
                if len(lines) > 6:
                    print(f"      ... ({len(lines) - 6} more lines)")
                print()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    run_cli_demo()
