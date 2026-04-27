# Phase 655: Fuzz Testing for SC2 Bot Input Validation
# Fuzz testing framework for SC2 bot input validation and robustness

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import struct
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ============================================================
# Constants
# ============================================================

MAX_INPUT_SIZE = 65536
DEFAULT_SEED = 42
MUTATION_ROUNDS = 5

# SC2 game constants for structure-aware fuzzing
SC2_UNIT_IDS = list(range(1, 300))
SC2_ABILITY_IDS = list(range(1, 500))
SC2_UPGRADE_IDS = list(range(1, 150))
SC2_MAX_MAP_X = 200.0
SC2_MAX_MAP_Y = 200.0
SC2_MAX_MINERALS = 99999
SC2_MAX_VESPENE = 99999
SC2_MAX_SUPPLY = 200
SC2_MAX_GAME_LOOP = 100000
SC2_RACES = ["Zerg", "Terran", "Protoss", "Random"]


# ============================================================
# Data Classes
# ============================================================


@dataclass
class FuzzInput:
    """Represents a single fuzz test input."""

    input_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    data: bytes = b""
    structured: Optional[Dict[str, Any]] = None
    source: str = "random"  # random, mutated, dictionary, structure-aware
    parent_id: Optional[str] = None
    generation: int = 0
    coverage_hash: str = ""
    is_interesting: bool = False
    crash_detected: bool = False
    execution_time_ms: float = 0.0

    @property
    def size(self) -> int:
        return len(self.data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_id": self.input_id,
            "size": self.size,
            "source": self.source,
            "generation": self.generation,
            "is_interesting": self.is_interesting,
            "crash_detected": self.crash_detected,
            "execution_time_ms": self.execution_time_ms,
            "data_preview": self.data[:64].hex() if self.data else "",
        }

    def clone(self) -> "FuzzInput":
        return FuzzInput(
            data=bytearray(self.data),
            structured=(
                json.loads(json.dumps(self.structured)) if self.structured else None
            ),
            source=self.source,
            parent_id=self.input_id,
            generation=self.generation + 1,
        )


@dataclass
class CrashReport:
    """Represents a detected crash or error from fuzzing."""

    crash_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    input_id: str = ""
    input_data: bytes = b""
    structured_input: Optional[Dict[str, Any]] = None
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    crash_hash: str = ""
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    reproducible: bool = True
    minimized_input: Optional[bytes] = None
    target_function: str = ""
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.crash_hash:
            raw = f"{self.error_type}:{self.error_message}:{self.stack_trace[:200]}"
            self.crash_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def unique_key(self) -> str:
        return self.crash_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crash_id": self.crash_id,
            "input_id": self.input_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "severity": self.severity,
            "crash_hash": self.crash_hash,
            "reproducible": self.reproducible,
            "target_function": self.target_function,
            "input_size": len(self.input_data),
            "minimized_size": (
                len(self.minimized_input) if self.minimized_input else None
            ),
        }


# ============================================================
# Mutator: Mutation Strategies
# ============================================================


class Mutator:
    """Implements various mutation strategies for fuzz input generation."""

    def __init__(self, seed: int = DEFAULT_SEED) -> None:
        self.rng = random.Random(seed)
        self.dictionary: List[bytes] = []
        self._load_sc2_dictionary()

    def _load_sc2_dictionary(self) -> None:
        """Load SC2-specific byte patterns for dictionary-based fuzzing."""
        sc2_tokens = [
            b"SCreplay",
            b"\x00\x00\x00\x00",
            b"\xff\xff\xff\xff",
            b"\x7f\xff\xff\xff",
            b"\x80\x00\x00\x00",
            b"s2ma",  # SC2 map archive magic
            b"MPQ\x1a",  # MPQ archive header
            b"\x00" * 16,
            b"\xff" * 16,
            b"Zerg",
            b"Terran",
            b"Protoss",
            b"CommandCenter",
            b"Hatchery",
            b"Nexus",
        ]
        # Add integer boundary values as little-endian bytes
        for val in [
            0,
            1,
            -1,
            127,
            128,
            255,
            256,
            32767,
            32768,
            65535,
            65536,
            2147483647,
            -2147483648,
        ]:
            try:
                self.dictionary.append(struct.pack("<i", val))
            except struct.error:
                pass
            try:
                self.dictionary.append(struct.pack("<I", val & 0xFFFFFFFF))
            except struct.error:
                pass
        self.dictionary.extend(sc2_tokens)

    def random_bytes(self, size: int) -> bytes:
        """Generate completely random bytes."""
        return bytes(self.rng.getrandbits(8) for _ in range(size))

    def bit_flip(self, data: bytes, num_flips: int = 1) -> bytes:
        """Flip random bits in the input data."""
        if not data:
            return data
        result = bytearray(data)
        for _ in range(num_flips):
            byte_idx = self.rng.randint(0, len(result) - 1)
            bit_idx = self.rng.randint(0, 7)
            result[byte_idx] ^= 1 << bit_idx
        return bytes(result)

    def byte_flip(self, data: bytes, num_flips: int = 1) -> bytes:
        """Replace random bytes with random values."""
        if not data:
            return data
        result = bytearray(data)
        for _ in range(num_flips):
            idx = self.rng.randint(0, len(result) - 1)
            result[idx] = self.rng.randint(0, 255)
        return bytes(result)

    def boundary_values(self, data: bytes) -> bytes:
        """Insert boundary values at random positions."""
        if not data:
            return data
        result = bytearray(data)
        boundaries = [0, 1, 0x7F, 0x80, 0xFF]
        if len(result) >= 4:
            pos = self.rng.randint(0, len(result) - 4)
            boundary_int = self.rng.choice(
                [0, 1, -1, 0x7FFFFFFF, -0x80000000, 0xFFFFFFFF, 0x7FFF, 0x8000]
            )
            try:
                packed = struct.pack("<i", boundary_int)
                for i, b in enumerate(packed):
                    result[pos + i] = b
            except struct.error:
                pass
        else:
            pos = self.rng.randint(0, len(result) - 1)
            result[pos] = self.rng.choice(boundaries)
        return bytes(result)

    def dictionary_insert(self, data: bytes) -> bytes:
        """Insert a dictionary token at a random position."""
        if not self.dictionary:
            return data
        token = self.rng.choice(self.dictionary)
        if not data:
            return token
        pos = self.rng.randint(0, len(data))
        result = bytearray(data[:pos]) + bytearray(token) + bytearray(data[pos:])
        return bytes(result[:MAX_INPUT_SIZE])

    def dictionary_replace(self, data: bytes) -> bytes:
        """Replace a segment with a dictionary token."""
        if not data or not self.dictionary:
            return data
        token = self.rng.choice(self.dictionary)
        if len(data) < len(token):
            return token
        pos = self.rng.randint(0, len(data) - len(token))
        result = bytearray(data)
        for i, b in enumerate(token):
            result[pos + i] = b
        return bytes(result)

    def arithmetic(self, data: bytes) -> bytes:
        """Apply small arithmetic changes to integer-sized chunks."""
        if len(data) < 4:
            return data
        result = bytearray(data)
        pos = self.rng.randint(0, len(result) - 4)
        val = struct.unpack("<I", result[pos : pos + 4])[0]
        delta = self.rng.randint(-35, 35)
        new_val = (val + delta) & 0xFFFFFFFF
        struct.pack_into("<I", result, pos, new_val)
        return bytes(result)

    def chunk_delete(self, data: bytes) -> bytes:
        """Delete a random chunk from the input."""
        if len(data) < 4:
            return data
        start = self.rng.randint(0, len(data) - 2)
        length = self.rng.randint(1, min(32, len(data) - start))
        return data[:start] + data[start + length :]

    def chunk_duplicate(self, data: bytes) -> bytes:
        """Duplicate a random chunk within the input."""
        if len(data) < 2:
            return data
        start = self.rng.randint(0, len(data) - 1)
        length = self.rng.randint(1, min(32, len(data) - start))
        chunk = data[start : start + length]
        insert_pos = self.rng.randint(0, len(data))
        result = data[:insert_pos] + chunk + data[insert_pos:]
        return bytes(result[:MAX_INPUT_SIZE])

    def shuffle_bytes(self, data: bytes) -> bytes:
        """Shuffle a random sub-range of bytes."""
        if len(data) < 4:
            return data
        start = self.rng.randint(0, len(data) - 4)
        length = self.rng.randint(4, min(32, len(data) - start))
        result = bytearray(data)
        sub = list(result[start : start + length])
        self.rng.shuffle(sub)
        result[start : start + length] = sub
        return bytes(result)

    def structure_aware_sc2_state(self) -> Dict[str, Any]:
        """Generate a structure-aware SC2 game state for fuzzing."""
        num_units = self.rng.randint(0, 500)
        units = []
        for _ in range(num_units):
            unit = {
                "unit_id": self.rng.choice(SC2_UNIT_IDS + [-1, 0, 99999]),
                "pos_x": self.rng.uniform(-100.0, SC2_MAX_MAP_X + 100.0),
                "pos_y": self.rng.uniform(-100.0, SC2_MAX_MAP_Y + 100.0),
                "health": self.rng.uniform(-100.0, 5000.0),
                "health_max": self.rng.uniform(0.0, 5000.0),
                "shield": self.rng.uniform(-100.0, 1000.0),
                "energy": self.rng.uniform(-50.0, 300.0),
                "is_flying": self.rng.choice([True, False, None, 0, 1, "yes"]),
                "owner": self.rng.choice([1, 2, 0, -1, 3, 255]),
                "tag": self.rng.randint(-1, 2**32),
            }
            units.append(unit)

        state = {
            "game_loop": self.rng.choice(
                [
                    0,
                    -1,
                    SC2_MAX_GAME_LOOP,
                    SC2_MAX_GAME_LOOP + 1,
                    self.rng.randint(0, SC2_MAX_GAME_LOOP),
                    2**31,
                    2**32 - 1,
                ]
            ),
            "minerals": self.rng.choice(
                [
                    0,
                    -1,
                    SC2_MAX_MINERALS,
                    SC2_MAX_MINERALS + 1,
                    self.rng.randint(0, SC2_MAX_MINERALS),
                ]
            ),
            "vespene": self.rng.choice(
                [
                    0,
                    -1,
                    SC2_MAX_VESPENE,
                    self.rng.randint(0, SC2_MAX_VESPENE),
                ]
            ),
            "supply_used": self.rng.choice(
                [
                    0,
                    -1,
                    SC2_MAX_SUPPLY,
                    SC2_MAX_SUPPLY + 1,
                    999,
                    self.rng.randint(0, SC2_MAX_SUPPLY),
                ]
            ),
            "supply_cap": self.rng.choice(
                [
                    0,
                    SC2_MAX_SUPPLY,
                    -1,
                    self.rng.randint(0, SC2_MAX_SUPPLY),
                ]
            ),
            "race": self.rng.choice(SC2_RACES + ["Unknown", "", None, 42]),
            "enemy_race": self.rng.choice(SC2_RACES + ["Unknown", "", None]),
            "units": units,
            "pending_actions": [
                {
                    "ability_id": self.rng.choice(SC2_ABILITY_IDS + [0, -1, 99999]),
                    "target_unit_tag": self.rng.choice(
                        [None, 0, -1, self.rng.randint(1, 2**32)]
                    ),
                    "target_x": self.rng.uniform(-50.0, SC2_MAX_MAP_X + 50.0),
                    "target_y": self.rng.uniform(-50.0, SC2_MAX_MAP_Y + 50.0),
                }
                for _ in range(self.rng.randint(0, 50))
            ],
            "upgrades": [
                self.rng.choice(SC2_UPGRADE_IDS + [0, -1, 9999])
                for _ in range(self.rng.randint(0, 30))
            ],
            "map_name": self.rng.choice(
                [
                    "Equilibrium",
                    "",
                    None,
                    "A" * 10000,
                    "\x00" * 100,
                    "DragonScales",
                    "../../../etc/passwd",
                ]
            ),
        }
        return state

    def structure_aware_sc2_action(self) -> Dict[str, Any]:
        """Generate a structure-aware SC2 action command for fuzzing."""
        action_types = [
            "build",
            "train",
            "attack",
            "move",
            "patrol",
            "hold_position",
            "ability",
            "upgrade",
            "rally",
            "unload",
            "lift",
            "land",
            "",
            None,
            "INVALID",
            "drop_table",
        ]
        action = {
            "type": self.rng.choice(action_types),
            "ability_id": self.rng.choice(SC2_ABILITY_IDS + [0, -1, 2**31]),
            "unit_tags": [
                self.rng.randint(-1, 2**32) for _ in range(self.rng.randint(0, 100))
            ],
            "target": {
                "type": self.rng.choice(["point", "unit", "none", "", None, 42]),
                "x": self.rng.uniform(-200.0, 400.0),
                "y": self.rng.uniform(-200.0, 400.0),
                "unit_tag": self.rng.choice([None, 0, -1, self.rng.randint(1, 2**32)]),
            },
            "queue": self.rng.choice([True, False, None, 0, 1, "yes"]),
        }
        return action

    def structure_aware_replay_header(self) -> bytes:
        """Generate a fuzzed SC2 replay header."""
        header = bytearray()
        # Magic bytes (sometimes corrupted)
        if self.rng.random() < 0.7:
            header.extend(b"MPQ\x1a")
        else:
            header.extend(self.random_bytes(4))
        # Header size (sometimes invalid)
        header_size = self.rng.choice([44, 0, -1, 2**31, self.rng.randint(0, 1024)])
        header.extend(struct.pack("<i", header_size & 0xFFFFFFFF))
        # Archive size
        archive_size = self.rng.choice([0, 1024, 2**31, self.rng.randint(0, 10**7)])
        header.extend(struct.pack("<I", archive_size & 0xFFFFFFFF))
        # Version
        header.extend(struct.pack("<H", self.rng.randint(0, 65535)))
        # Padding / additional fields
        header.extend(self.random_bytes(self.rng.randint(0, 128)))
        return bytes(header)

    def mutate(self, fuzz_input: FuzzInput) -> FuzzInput:
        """Apply a random mutation strategy to a FuzzInput."""
        child = fuzz_input.clone()
        strategy = self.rng.choice(
            [
                "bit_flip",
                "byte_flip",
                "boundary",
                "dict_insert",
                "dict_replace",
                "arithmetic",
                "chunk_delete",
                "chunk_duplicate",
                "shuffle",
            ]
        )
        data = child.data
        if strategy == "bit_flip":
            child.data = self.bit_flip(data, self.rng.randint(1, 8))
            child.source = "mutated:bit_flip"
        elif strategy == "byte_flip":
            child.data = self.byte_flip(data, self.rng.randint(1, 4))
            child.source = "mutated:byte_flip"
        elif strategy == "boundary":
            child.data = self.boundary_values(data)
            child.source = "mutated:boundary"
        elif strategy == "dict_insert":
            child.data = self.dictionary_insert(data)
            child.source = "mutated:dict_insert"
        elif strategy == "dict_replace":
            child.data = self.dictionary_replace(data)
            child.source = "mutated:dict_replace"
        elif strategy == "arithmetic":
            child.data = self.arithmetic(data)
            child.source = "mutated:arithmetic"
        elif strategy == "chunk_delete":
            child.data = self.chunk_delete(data)
            child.source = "mutated:chunk_delete"
        elif strategy == "chunk_duplicate":
            child.data = self.chunk_duplicate(data)
            child.source = "mutated:chunk_duplicate"
        elif strategy == "shuffle":
            child.data = self.shuffle_bytes(data)
            child.source = "mutated:shuffle"
        return child


# ============================================================
# Coverage Tracker
# ============================================================


class CoverageTracker:
    """Track code coverage to guide fuzzing toward new paths."""

    def __init__(self) -> None:
        self.coverage_map: Dict[str, int] = {}  # hash -> hit count
        self.total_inputs: int = 0
        self.interesting_inputs: int = 0
        self.unique_paths: int = 0
        self.path_history: List[Tuple[str, str]] = []  # (input_id, coverage_hash)
        self._edge_counts: Dict[int, int] = {}

    def compute_coverage_hash(self, execution_trace: List[str]) -> str:
        """Compute a hash of the execution trace to identify unique paths."""
        if not execution_trace:
            return hashlib.md5(b"empty").hexdigest()[:16]
        trace_str = "|".join(execution_trace)
        return hashlib.md5(trace_str.encode()).hexdigest()[:16]

    def record_execution(
        self, fuzz_input: FuzzInput, execution_trace: List[str]
    ) -> bool:
        """Record an execution. Returns True if new coverage was discovered."""
        self.total_inputs += 1
        cov_hash = self.compute_coverage_hash(execution_trace)
        fuzz_input.coverage_hash = cov_hash

        is_new = cov_hash not in self.coverage_map
        if is_new:
            self.coverage_map[cov_hash] = 1
            self.unique_paths += 1
            self.interesting_inputs += 1
            fuzz_input.is_interesting = True
        else:
            self.coverage_map[cov_hash] += 1

        self.path_history.append((fuzz_input.input_id, cov_hash))

        # Track edge coverage (simulated)
        for i, item in enumerate(execution_trace):
            edge_id = hash(f"{i}:{item}") & 0xFFFF
            prev = self._edge_counts.get(edge_id, 0)
            self._edge_counts[edge_id] = prev + 1

        return is_new

    def record_edge(self, edge_id: int) -> bool:
        """Record a single edge hit. Returns True if first time seen."""
        is_new = edge_id not in self._edge_counts
        self._edge_counts[edge_id] = self._edge_counts.get(edge_id, 0) + 1
        return is_new

    @property
    def total_edges(self) -> int:
        return len(self._edge_counts)

    def coverage_percentage(self, estimated_total_edges: int = 1000) -> float:
        """Estimate coverage as a percentage of total possible edges."""
        if estimated_total_edges <= 0:
            return 0.0
        return min(100.0, (len(self._edge_counts) / estimated_total_edges) * 100.0)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_inputs": self.total_inputs,
            "unique_paths": self.unique_paths,
            "interesting_inputs": self.interesting_inputs,
            "total_edges_hit": self.total_edges,
            "coverage_map_size": len(self.coverage_map),
        }


# ============================================================
# Crash Analyzer & Minimizer
# ============================================================


class CrashAnalyzer:
    """Analyze, deduplicate, and minimize crash-inducing inputs."""

    def __init__(self) -> None:
        self.crashes: Dict[str, CrashReport] = {}  # crash_hash -> report
        self.crash_history: List[CrashReport] = []

    @property
    def unique_crash_count(self) -> int:
        return len(self.crashes)

    @property
    def total_crash_count(self) -> int:
        return len(self.crash_history)

    def record_crash(
        self, fuzz_input: FuzzInput, error: Exception, target_name: str = ""
    ) -> CrashReport:
        """Record a crash, deduplicating by crash hash."""
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        stack_str = "".join(tb)

        report = CrashReport(
            input_id=fuzz_input.input_id,
            input_data=fuzz_input.data,
            structured_input=fuzz_input.structured,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=stack_str,
            target_function=target_name,
            severity=self._classify_severity(error),
        )

        self.crash_history.append(report)

        if report.crash_hash not in self.crashes:
            self.crashes[report.crash_hash] = report
            return report

        return self.crashes[report.crash_hash]

    def _classify_severity(self, error: Exception) -> str:
        """Classify crash severity based on error type."""
        critical_types = (MemoryError, SystemError, RecursionError)
        high_types = (OverflowError, BufferError, UnicodeError)
        medium_types = (ValueError, TypeError, KeyError, IndexError, AttributeError)

        if isinstance(error, critical_types):
            return "CRITICAL"
        elif isinstance(error, high_types):
            return "HIGH"
        elif isinstance(error, medium_types):
            return "MEDIUM"
        return "LOW"

    def minimize_input(
        self,
        fuzz_input: FuzzInput,
        target_fn: Callable[[bytes], Any],
        max_rounds: int = 50,
    ) -> bytes:
        """
        Minimize a crash-inducing input by binary search and delta debugging.
        Returns the smallest input that still triggers the crash.
        """
        data = bytearray(fuzz_input.data)
        if not data:
            return bytes(data)

        # Verify original crash
        if not self._triggers_crash(bytes(data), target_fn):
            return bytes(data)

        # Phase 1: Binary reduction
        chunk_size = len(data) // 2
        while chunk_size >= 1:
            i = 0
            while i < len(data):
                candidate = bytes(data[:i] + data[i + chunk_size :])
                if candidate and self._triggers_crash(candidate, target_fn):
                    data = bytearray(candidate)
                else:
                    i += chunk_size
            chunk_size //= 2

        # Phase 2: Single-byte removal
        i = 0
        rounds = 0
        while i < len(data) and rounds < max_rounds:
            candidate = bytes(data[:i] + data[i + 1 :])
            if candidate and self._triggers_crash(candidate, target_fn):
                data = bytearray(candidate)
            else:
                i += 1
            rounds += 1

        return bytes(data)

    @staticmethod
    def _triggers_crash(data: bytes, target_fn: Callable[[bytes], Any]) -> bool:
        """Check if given data triggers a crash in the target function."""
        try:
            target_fn(data)
            return False
        except Exception:
            return True

    def get_report_summary(self) -> Dict[str, Any]:
        severity_counts: Dict[str, int] = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }
        for cr in self.crashes.values():
            sev = cr.severity
            if sev in severity_counts:
                severity_counts[sev] += 1
        return {
            "unique_crashes": self.unique_crash_count,
            "total_crashes": self.total_crash_count,
            "by_severity": severity_counts,
            "crash_hashes": list(self.crashes.keys()),
        }


# ============================================================
# SC2 Fuzzer (Main Orchestrator)
# ============================================================


class SC2Fuzzer:
    """
    Main fuzz testing framework for SC2 bot input validation.
    Orchestrates mutation, coverage tracking, crash analysis,
    and SC2-specific input generation.
    """

    def __init__(
        self,
        seed: int = DEFAULT_SEED,
        max_iterations: int = 1000,
        max_input_size: int = MAX_INPUT_SIZE,
    ) -> None:
        self.seed = seed
        self.max_iterations = max_iterations
        self.max_input_size = max_input_size
        self.mutator = Mutator(seed)
        self.coverage = CoverageTracker()
        self.crash_analyzer = CrashAnalyzer()
        self.corpus: List[FuzzInput] = []
        self.interesting_corpus: List[FuzzInput] = []
        self._targets: Dict[str, Callable] = {}
        self._stats: Dict[str, Any] = {
            "iterations": 0,
            "start_time": 0.0,
            "end_time": 0.0,
            "crashes_found": 0,
        }
        self._register_default_targets()

    def _register_default_targets(self) -> None:
        """Register SC2-specific fuzz targets."""
        self._targets["game_state_parser"] = self._target_game_state_parser
        self._targets["action_validator"] = self._target_action_validator
        self._targets["replay_header_parser"] = self._target_replay_header_parser
        self._targets["unit_command_handler"] = self._target_unit_command_handler
        self._targets["resource_validator"] = self._target_resource_validator

    # ---- SC2 Fuzz Targets ----

    @staticmethod
    def _target_game_state_parser(data: bytes) -> Dict[str, Any]:
        """Simulated SC2 game state parser that may crash on bad input."""
        if len(data) < 4:
            raise ValueError("Game state data too short")
        header = struct.unpack("<I", data[:4])[0]
        if header == 0xDEADBEEF:
            raise MemoryError("Simulated heap corruption on magic header")
        if header > 2**30:
            raise OverflowError(f"Game state header overflow: {header}")
        if len(data) > 10000:
            raise ValueError("Game state data exceeds maximum size")
        # Parse unit count
        if len(data) >= 8:
            unit_count = struct.unpack("<I", data[4:8])[0]
            if unit_count > 10000:
                raise ValueError(f"Invalid unit count: {unit_count}")
            if unit_count * 20 > len(data) - 8:
                raise BufferError("Unit data extends beyond buffer")
        return {"parsed": True, "header": header, "size": len(data)}

    @staticmethod
    def _target_action_validator(data: bytes) -> Dict[str, Any]:
        """Simulated SC2 action validator."""
        if not data:
            raise ValueError("Empty action data")
        action_type = data[0]
        if action_type == 0xFF:
            raise TypeError("Invalid action type 0xFF")
        if len(data) >= 2 and data[1] == 0x00 and action_type > 200:
            raise KeyError(f"Unknown action type {action_type} with null modifier")
        if len(data) >= 4:
            target_id = struct.unpack("<H", data[2:4])[0]
            if target_id == 0xFFFF:
                raise IndexError("Target unit does not exist (0xFFFF)")
        return {"valid": True, "action_type": action_type}

    @staticmethod
    def _target_replay_header_parser(data: bytes) -> Dict[str, Any]:
        """Simulated SC2 replay header parser."""
        if len(data) < 4:
            raise ValueError("Replay data too short for header")
        magic = data[:4]
        if magic == b"\x00\x00\x00\x00":
            raise ValueError("Null magic bytes in replay header")
        if magic not in (b"MPQ\x1a", b"SCreplay", b"s2ma"):
            raise ValueError(f"Unknown replay magic: {magic.hex()}")
        if len(data) >= 8:
            declared_size = struct.unpack("<I", data[4:8])[0]
            if declared_size == 0:
                raise ValueError("Zero-length replay archive")
            if declared_size > 100 * 1024 * 1024:
                raise OverflowError(f"Declared size too large: {declared_size}")
        return {"magic": magic.hex(), "valid": True}

    @staticmethod
    def _target_unit_command_handler(data: bytes) -> Dict[str, Any]:
        """Simulated unit command handler."""
        if len(data) < 6:
            raise ValueError("Command too short")
        cmd_id = struct.unpack("<H", data[0:2])[0]
        unit_tag = struct.unpack("<I", data[2:6])[0]
        if cmd_id == 0:
            raise ValueError("Null command ID")
        if unit_tag == 0:
            raise AttributeError("Command targets null unit")
        if cmd_id > 500:
            raise ValueError(f"Command ID out of range: {cmd_id}")
        if unit_tag == 0xDEADBEEF:
            raise SystemError("Simulated: corrupted unit tag")
        return {"cmd_id": cmd_id, "unit_tag": unit_tag, "valid": True}

    @staticmethod
    def _target_resource_validator(data: bytes) -> Dict[str, Any]:
        """Simulated resource amount validator."""
        if len(data) < 8:
            raise ValueError("Resource data too short")
        minerals = struct.unpack("<i", data[0:4])[0]
        vespene = struct.unpack("<i", data[4:8])[0]
        if minerals < 0:
            raise ValueError(f"Negative minerals: {minerals}")
        if vespene < 0:
            raise ValueError(f"Negative vespene: {vespene}")
        if minerals > SC2_MAX_MINERALS:
            raise OverflowError(f"Minerals overflow: {minerals}")
        if vespene > SC2_MAX_VESPENE:
            raise OverflowError(f"Vespene overflow: {vespene}")
        return {"minerals": minerals, "vespene": vespene, "valid": True}

    # ---- Corpus Management ----

    def seed_corpus(self, inputs: Optional[List[bytes]] = None) -> None:
        """Initialize the corpus with seed inputs."""
        if inputs:
            for data in inputs:
                fi = FuzzInput(data=data, source="seed")
                self.corpus.append(fi)
        # Add SC2-specific seeds
        sc2_seeds = [
            struct.pack("<II", 1, 10),  # valid game state stub
            bytes([0x01, 0x01, 0x00, 0x01]),  # valid action stub
            b"MPQ\x1a" + struct.pack("<I", 1024),  # valid replay header
            struct.pack("<HI", 1, 1),  # valid command stub
            struct.pack("<ii", 100, 50),  # valid resource data
            b"\x00" * 32,  # null seed
            b"\xff" * 32,  # max seed
        ]
        for seed_data in sc2_seeds:
            fi = FuzzInput(data=seed_data, source="sc2_seed")
            self.corpus.append(fi)

    def _select_input(self) -> FuzzInput:
        """Select an input for mutation, favoring interesting inputs."""
        if self.interesting_corpus and self.mutator.rng.random() < 0.7:
            return self.mutator.rng.choice(self.interesting_corpus)
        if self.corpus:
            return self.mutator.rng.choice(self.corpus)
        # Fallback: generate new random input
        size = self.mutator.rng.randint(4, 128)
        return FuzzInput(data=self.mutator.random_bytes(size), source="random")

    def _simulate_trace(self, target_name: str, data: bytes) -> List[str]:
        """Simulate an execution trace for coverage tracking."""
        trace: List[str] = [f"entry:{target_name}"]
        if len(data) >= 4:
            header = struct.unpack("<I", data[:4])[0]
            if header < 1000:
                trace.append("path:small_header")
            elif header < 1000000:
                trace.append("path:medium_header")
            else:
                trace.append("path:large_header")
        if len(data) >= 8:
            trace.append("path:has_body")
        if len(data) > 100:
            trace.append("path:large_input")
        # Byte distribution path
        if data:
            zero_ratio = data.count(0) / len(data)
            if zero_ratio > 0.5:
                trace.append("path:mostly_zeros")
            elif zero_ratio < 0.1:
                trace.append("path:dense_data")
        trace.append(f"exit:{target_name}")
        return trace

    def fuzz_target(
        self, target_name: str, iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run fuzzing against a specific target."""
        if target_name not in self._targets:
            return {"error": f"Unknown target: {target_name}"}

        target_fn = self._targets[target_name]
        num_iters = iterations or self.max_iterations
        results: Dict[str, Any] = {
            "target": target_name,
            "iterations": num_iters,
            "crashes": 0,
            "new_coverage": 0,
            "unique_crashes": 0,
        }

        if not self.corpus:
            self.seed_corpus()

        for i in range(num_iters):
            # Select and mutate
            parent = self._select_input()
            fuzz_input = self.mutator.mutate(parent)

            # Execute
            start_t = time.time()
            trace = self._simulate_trace(target_name, fuzz_input.data)
            try:
                target_fn(fuzz_input.data)
            except Exception as e:
                fuzz_input.crash_detected = True
                self.crash_analyzer.record_crash(fuzz_input, e, target_name)
                results["crashes"] += 1
            finally:
                fuzz_input.execution_time_ms = (time.time() - start_t) * 1000.0

            # Track coverage
            is_new = self.coverage.record_execution(fuzz_input, trace)
            if is_new:
                results["new_coverage"] += 1
                self.interesting_corpus.append(fuzz_input)

            self.corpus.append(fuzz_input)

        results["unique_crashes"] = self.crash_analyzer.unique_crash_count
        results["coverage"] = self.coverage.get_stats()
        return results

    def fuzz_structured_game_state(self, iterations: int = 100) -> Dict[str, Any]:
        """Fuzz using structure-aware SC2 game state inputs."""
        crashes: List[Dict[str, Any]] = []
        validations_passed = 0
        validations_failed = 0

        for _ in range(iterations):
            state = self.mutator.structure_aware_sc2_state()
            try:
                self._validate_game_state(state)
                validations_passed += 1
            except Exception as e:
                validations_failed += 1
                fi = FuzzInput(
                    data=json.dumps(state, default=str).encode(),
                    structured=state,
                    source="structure-aware:game_state",
                )
                fi.crash_detected = True
                report = self.crash_analyzer.record_crash(fi, e, "game_state_validator")
                crashes.append(report.to_dict())

        return {
            "target": "structured_game_state",
            "iterations": iterations,
            "passed": validations_passed,
            "failed": validations_failed,
            "unique_crashes": len({c["crash_hash"] for c in crashes}),
            "crash_details": crashes[:10],
        }

    def fuzz_structured_actions(self, iterations: int = 100) -> Dict[str, Any]:
        """Fuzz using structure-aware SC2 action inputs."""
        crashes: List[Dict[str, Any]] = []
        valid_count = 0
        invalid_count = 0

        for _ in range(iterations):
            action = self.mutator.structure_aware_sc2_action()
            try:
                self._validate_action(action)
                valid_count += 1
            except Exception as e:
                invalid_count += 1
                fi = FuzzInput(
                    data=json.dumps(action, default=str).encode(),
                    structured=action,
                    source="structure-aware:action",
                )
                fi.crash_detected = True
                report = self.crash_analyzer.record_crash(fi, e, "action_validator")
                crashes.append(report.to_dict())

        return {
            "target": "structured_actions",
            "iterations": iterations,
            "valid": valid_count,
            "invalid": invalid_count,
            "unique_crashes": len({c["crash_hash"] for c in crashes}),
        }

    def fuzz_replay_parsing(self, iterations: int = 100) -> Dict[str, Any]:
        """Fuzz SC2 replay header parsing."""
        target_fn = self._targets["replay_header_parser"]
        crashes = 0
        parsed = 0

        for _ in range(iterations):
            header_data = self.mutator.structure_aware_replay_header()
            fi = FuzzInput(data=header_data, source="structure-aware:replay")
            try:
                target_fn(header_data)
                parsed += 1
            except Exception as e:
                crashes += 1
                fi.crash_detected = True
                self.crash_analyzer.record_crash(fi, e, "replay_header_parser")

        return {
            "target": "replay_parsing",
            "iterations": iterations,
            "parsed_ok": parsed,
            "crashes": crashes,
            "unique_crashes": self.crash_analyzer.unique_crash_count,
        }

    @staticmethod
    def _validate_game_state(state: Dict[str, Any]) -> None:
        """Validate a game state dict, raising on invalid data."""
        game_loop = state.get("game_loop")
        if not isinstance(game_loop, int) or game_loop < 0:
            raise ValueError(f"Invalid game_loop: {game_loop}")
        minerals = state.get("minerals")
        if not isinstance(minerals, int) or minerals < 0:
            raise ValueError(f"Invalid minerals: {minerals}")
        vespene = state.get("vespene")
        if not isinstance(vespene, int) or vespene < 0:
            raise ValueError(f"Invalid vespene: {vespene}")
        supply_used = state.get("supply_used")
        supply_cap = state.get("supply_cap")
        if not isinstance(supply_used, int) or supply_used < 0:
            raise ValueError(f"Invalid supply_used: {supply_used}")
        if not isinstance(supply_cap, int) or supply_cap < 0:
            raise ValueError(f"Invalid supply_cap: {supply_cap}")
        if isinstance(supply_used, int) and isinstance(supply_cap, int):
            if supply_used > supply_cap + 10:  # allow small overflow
                raise OverflowError(f"Supply overflow: {supply_used}/{supply_cap}")
        race = state.get("race")
        if race not in SC2_RACES:
            raise ValueError(f"Invalid race: {race}")
        units = state.get("units", [])
        if not isinstance(units, list):
            raise TypeError(f"Units must be list, got {type(units)}")
        for u in units:
            if not isinstance(u, dict):
                raise TypeError(f"Unit must be dict, got {type(u)}")
            pos_x = u.get("pos_x", 0)
            pos_y = u.get("pos_y", 0)
            if not isinstance(pos_x, (int, float)):
                raise TypeError(f"pos_x must be numeric: {pos_x}")
            if not isinstance(pos_y, (int, float)):
                raise TypeError(f"pos_y must be numeric: {pos_y}")
            if pos_x < 0 or pos_x > SC2_MAX_MAP_X:
                raise ValueError(f"pos_x out of bounds: {pos_x}")
            if pos_y < 0 or pos_y > SC2_MAX_MAP_Y:
                raise ValueError(f"pos_y out of bounds: {pos_y}")
            health = u.get("health", 0)
            if not isinstance(health, (int, float)) or health < 0:
                raise ValueError(f"Invalid health: {health}")

    @staticmethod
    def _validate_action(action: Dict[str, Any]) -> None:
        """Validate an SC2 action dict."""
        action_type = action.get("type")
        valid_types = {
            "build",
            "train",
            "attack",
            "move",
            "patrol",
            "hold_position",
            "ability",
            "upgrade",
            "rally",
            "unload",
            "lift",
            "land",
        }
        if action_type not in valid_types:
            raise ValueError(f"Invalid action type: {action_type}")
        ability_id = action.get("ability_id")
        if not isinstance(ability_id, int) or ability_id <= 0:
            raise ValueError(f"Invalid ability_id: {ability_id}")
        if ability_id > max(SC2_ABILITY_IDS):
            raise OverflowError(f"ability_id out of range: {ability_id}")
        unit_tags = action.get("unit_tags", [])
        if not isinstance(unit_tags, list):
            raise TypeError(f"unit_tags must be list: {type(unit_tags)}")
        for tag in unit_tags:
            if not isinstance(tag, int) or tag < 0:
                raise ValueError(f"Invalid unit tag: {tag}")
        target = action.get("target", {})
        if isinstance(target, dict):
            target_type = target.get("type")
            if target_type not in ("point", "unit", "none"):
                raise ValueError(f"Invalid target type: {target_type}")
        queue = action.get("queue")
        if not isinstance(queue, bool):
            raise TypeError(f"queue must be bool, got {type(queue)}")

    def run_full_campaign(self, iterations_per_target: int = 200) -> Dict[str, Any]:
        """Run a full fuzzing campaign across all targets."""
        self._stats["start_time"] = time.time()
        self.seed_corpus()

        results: Dict[str, Any] = {"targets": {}}

        # Fuzz each binary target
        for target_name in self._targets:
            result = self.fuzz_target(target_name, iterations_per_target)
            results["targets"][target_name] = result

        # Structured fuzzing
        results["targets"]["structured_game_state"] = self.fuzz_structured_game_state(
            iterations_per_target // 2
        )
        results["targets"]["structured_actions"] = self.fuzz_structured_actions(
            iterations_per_target // 2
        )
        results["targets"]["structured_replay"] = self.fuzz_replay_parsing(
            iterations_per_target // 2
        )

        self._stats["end_time"] = time.time()
        self._stats["iterations"] = sum(
            r.get("iterations", 0) for r in results["targets"].values()
        )
        self._stats["crashes_found"] = self.crash_analyzer.total_crash_count

        results["summary"] = {
            "total_iterations": self._stats["iterations"],
            "total_time_sec": round(
                self._stats["end_time"] - self._stats["start_time"], 3
            ),
            "total_crashes": self.crash_analyzer.total_crash_count,
            "unique_crashes": self.crash_analyzer.unique_crash_count,
            "coverage": self.coverage.get_stats(),
            "crash_report": self.crash_analyzer.get_report_summary(),
        }
        return results


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate fuzz testing for SC2 bot input validation."""
    print("=" * 70)
    print("Phase 655: Fuzz Testing for SC2 Bot Input Validation")
    print("=" * 70)

    fuzzer = SC2Fuzzer(seed=42, max_iterations=200)

    # --- Seed Corpus ---
    print("\n[1] Initializing seed corpus...")
    fuzzer.seed_corpus()
    print(f"    Corpus size: {len(fuzzer.corpus)} seed inputs")

    # --- Mutation Demo ---
    print("\n[2] Mutation Strategy Demonstration")
    sample_data = struct.pack("<II", 1, 10) + b"\x00" * 24
    sample_input = FuzzInput(data=sample_data, source="demo_seed")
    strategies_seen: Set[str] = set()
    for _ in range(20):
        mutated = fuzzer.mutator.mutate(sample_input)
        strategy = (
            mutated.source.split(":")[1] if ":" in mutated.source else mutated.source
        )
        strategies_seen.add(strategy)
    print(f"    Strategies exercised: {', '.join(sorted(strategies_seen))}")

    # --- Binary Target Fuzzing ---
    print("\n[3] Fuzzing Binary Targets")
    for target_name in [
        "game_state_parser",
        "action_validator",
        "replay_header_parser",
        "unit_command_handler",
        "resource_validator",
    ]:
        result = fuzzer.fuzz_target(target_name, iterations=150)
        crashes = result.get("crashes", 0)
        new_cov = result.get("new_coverage", 0)
        print(f"    {target_name:30s} crashes={crashes:4d}  new_coverage={new_cov:3d}")

    # --- Structured Game State Fuzzing ---
    print("\n[4] Structure-Aware Game State Fuzzing")
    gs_result = fuzzer.fuzz_structured_game_state(iterations=100)
    print(f"    Passed: {gs_result['passed']}, Failed: {gs_result['failed']}")
    print(f"    Unique crash signatures: {gs_result['unique_crashes']}")

    # --- Structured Action Fuzzing ---
    print("\n[5] Structure-Aware Action Fuzzing")
    act_result = fuzzer.fuzz_structured_actions(iterations=100)
    print(f"    Valid: {act_result['valid']}, Invalid: {act_result['invalid']}")
    print(f"    Unique crash signatures: {act_result['unique_crashes']}")

    # --- Replay Parsing Fuzzing ---
    print("\n[6] Replay Header Parsing Fuzzing")
    rp_result = fuzzer.fuzz_replay_parsing(iterations=100)
    print(f"    Parsed OK: {rp_result['parsed_ok']}, Crashes: {rp_result['crashes']}")

    # --- Coverage Stats ---
    print("\n[7] Coverage Statistics")
    cov_stats = fuzzer.coverage.get_stats()
    print(f"    Total inputs processed:  {cov_stats['total_inputs']}")
    print(f"    Unique execution paths:  {cov_stats['unique_paths']}")
    print(f"    Interesting inputs:      {cov_stats['interesting_inputs']}")
    print(f"    Total edges hit:         {cov_stats['total_edges_hit']}")
    est_coverage = fuzzer.coverage.coverage_percentage(estimated_total_edges=500)
    print(f"    Estimated coverage:      {est_coverage:.1f}%")

    # --- Crash Analysis ---
    print("\n[8] Crash Analysis Summary")
    crash_summary = fuzzer.crash_analyzer.get_report_summary()
    print(f"    Total crashes:  {crash_summary['total_crashes']}")
    print(f"    Unique crashes: {crash_summary['unique_crashes']}")
    sev = crash_summary["by_severity"]
    print(
        f"    By severity: CRITICAL={sev['CRITICAL']} HIGH={sev['HIGH']} "
        f"MEDIUM={sev['MEDIUM']} LOW={sev['LOW']}"
    )

    # --- Minimization Demo ---
    print("\n[9] Input Minimization Demo")
    crash_data = struct.pack("<I", 0xDEADBEEF) + b"\x00" * 100
    crash_input = FuzzInput(data=crash_data, source="minimization_test")
    minimized = fuzzer.crash_analyzer.minimize_input(
        crash_input,
        SC2Fuzzer._target_game_state_parser,
        max_rounds=30,
    )
    print(f"    Original size:  {len(crash_data)} bytes")
    print(f"    Minimized size: {len(minimized)} bytes")
    print(f"    Reduction:      {(1 - len(minimized) / len(crash_data)) * 100:.1f}%")

    # --- Corpus Statistics ---
    print("\n[10] Final Corpus Statistics")
    print(f"    Total corpus:       {len(fuzzer.corpus)}")
    print(f"    Interesting inputs: {len(fuzzer.interesting_corpus)}")
    source_counts: Dict[str, int] = {}
    for fi in fuzzer.corpus:
        src = fi.source.split(":")[0] if ":" in fi.source else fi.source
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1])[:8]:
        print(f"      {src:20s}: {count}")

    print("\n" + "=" * 70)
    print("Phase 655 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 655: Fuzz Testing registered
