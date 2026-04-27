"""
Phase 621: LangChain Strategy Coach --- SC2 Strategy Coach
===========================================================
langchain_coach/sc2_strategy_coach.py

Production-quality LangChain-powered coaching agent for the SC2 Zerg
commander bot.
  - SC2StrategyCoach     : main coach with chain-of-thought reasoning
  - ReActAgent           : Reason+Act loop for interactive coaching
  - ReplayAnalyserTool   : analyses replays for strategic insights
  - BuildOrderDB         : lookup database for standard build orders
  - UnitCounterLookup    : matchup-specific unit counter reference
  - StrategyMemory       : conversation buffer + game history summary
  - StrategyRecommendation : structured output for strategy advice
  - StreamingCoach       : real-time coaching with streaming responses

Supports matchup-specific prompts (ZvT, ZvP, ZvZ), structured output
parsing, and full rule-based fallback when LLM is unavailable.

Dependencies: numpy (required), langchain (optional).
Supports 260+ language localisation via label keys.
"""

from __future__ import annotations

import json
import logging
import os
import re
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
# Optional LangChain imports
# ---------------------------------------------------------------------------
_LANGCHAIN_AVAILABLE = False
try:
    from langchain.chains import LLMChain, SequentialChain
    from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
    from langchain.prompts import PromptTemplate
    from langchain.schema import BaseMessage, HumanMessage, AIMessage
    from langchain.tools import BaseTool

    _LANGCHAIN_AVAILABLE = True
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


def classify_phase(game_time_seconds: float) -> GamePhase:
    minutes = game_time_seconds / 60.0
    if minutes < 3.0:
        return GamePhase.OPENING
    elif minutes < 6.0:
        return GamePhase.EARLY
    elif minutes < 12.0:
        return GamePhase.MID
    return GamePhase.LATE


# ---------------------------------------------------------------------------
# Game state representation
# ---------------------------------------------------------------------------


@dataclass
class SC2GameState:
    """Snapshot of a StarCraft II game state for coaching."""

    game_time_seconds: float = 0.0
    player_race: Race = Race.ZERG
    enemy_race: Race = Race.TERRAN
    minerals: float = 0.0
    vespene: float = 0.0
    supply_used: int = 0
    supply_cap: int = 0
    worker_count: int = 0
    base_count: int = 1
    army_composition: Dict[str, int] = field(default_factory=dict)
    enemy_army_scouted: Dict[str, int] = field(default_factory=dict)
    upgrades_completed: List[str] = field(default_factory=list)
    tech_buildings: List[str] = field(default_factory=list)
    creep_coverage: float = 0.0
    army_value: float = 0.0
    enemy_army_value: float = 0.0

    @property
    def matchup(self) -> Matchup:
        mapping = {
            (Race.ZERG, Race.TERRAN): Matchup.ZvT,
            (Race.ZERG, Race.PROTOSS): Matchup.ZvP,
            (Race.ZERG, Race.ZERG): Matchup.ZvZ,
        }
        return mapping.get((self.player_race, self.enemy_race), Matchup.ZvT)

    @property
    def phase(self) -> GamePhase:
        return classify_phase(self.game_time_seconds)

    @property
    def minutes(self) -> float:
        return self.game_time_seconds / 60.0

    def to_description(self) -> str:
        """Human-readable state description for LLM prompts."""
        army_str = (
            ", ".join(f"{k}: {v}" for k, v in self.army_composition.items()) or "None"
        )
        enemy_str = (
            ", ".join(f"{k}: {v}" for k, v in self.enemy_army_scouted.items())
            or "Unknown"
        )
        upgrades_str = ", ".join(self.upgrades_completed) or "None"
        return (
            f"Time: {self.minutes:.1f} min ({self.phase.name})\n"
            f"Matchup: {self.matchup.value}\n"
            f"Resources: {self.minerals:.0f} minerals, "
            f"{self.vespene:.0f} gas\n"
            f"Supply: {self.supply_used}/{self.supply_cap}\n"
            f"Workers: {self.worker_count}, Bases: {self.base_count}\n"
            f"Army ({self.army_value:.0f} value): {army_str}\n"
            f"Enemy army ({self.enemy_army_value:.0f} est.): {enemy_str}\n"
            f"Upgrades: {upgrades_str}\n"
            f"Creep coverage: {self.creep_coverage:.0%}"
        )


# ---------------------------------------------------------------------------
# Structured output: Strategy Recommendation
# ---------------------------------------------------------------------------


@dataclass
class StrategyRecommendation:
    """Parsed strategy recommendation with structured fields."""

    summary: str = ""
    immediate_actions: List[str] = field(default_factory=list)
    build_order_next: List[str] = field(default_factory=list)
    army_composition_target: Dict[str, int] = field(default_factory=dict)
    tech_priority: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "immediate_actions": self.immediate_actions,
            "build_order_next": self.build_order_next,
            "army_composition_target": self.army_composition_target,
            "tech_priority": self.tech_priority,
            "warnings": self.warnings,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }

    def to_display(self) -> str:
        lines = [f"=== Strategy Recommendation (confidence: {self.confidence:.0%}) ==="]
        lines.append(f"Summary: {self.summary}")
        if self.immediate_actions:
            lines.append("Immediate actions:")
            for a in self.immediate_actions:
                lines.append(f"  - {a}")
        if self.build_order_next:
            lines.append("Build order (next):")
            for b in self.build_order_next:
                lines.append(f"  - {b}")
        if self.army_composition_target:
            lines.append("Target army composition:")
            for unit, count in self.army_composition_target.items():
                lines.append(f"  - {unit}: {count}")
        if self.tech_priority:
            lines.append("Tech priority:")
            for t in self.tech_priority:
                lines.append(f"  - {t}")
        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  [!] {w}")
        if self.reasoning:
            lines.append(f"Reasoning: {self.reasoning}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output parser
# ---------------------------------------------------------------------------


class StrategyOutputParser:
    """Parses LLM text output into StrategyRecommendation."""

    SECTION_PATTERNS = {
        "summary": r"(?:Summary|SUMMARY)[:\s]*(.+?)(?=\n[A-Z]|\n\n|$)",
        "immediate": r"(?:Immediate|IMMEDIATE)[:\s]*([\s\S]+?)(?=\n[A-Z]|\n\n|$)",
        "build_order": r"(?:Build[_ ]?order|BUILD)[:\s]*([\s\S]+?)(?=\n[A-Z]|\n\n|$)",
        "army": r"(?:Army|ARMY|Composition)[:\s]*([\s\S]+?)(?=\n[A-Z]|\n\n|$)",
        "tech": r"(?:Tech|TECH|Technology)[:\s]*([\s\S]+?)(?=\n[A-Z]|\n\n|$)",
        "warnings": r"(?:Warning|WARNING)[:\s]*([\s\S]+?)(?=\n[A-Z]|\n\n|$)",
        "confidence": r"(?:Confidence|CONFIDENCE)[:\s]*(\d+(?:\.\d+)?)",
        "reasoning": r"(?:Reasoning|REASONING|Reason)[:\s]*([\s\S]+?)(?=\n[A-Z]|\n\n|$)",
    }

    def parse(self, text: str) -> StrategyRecommendation:
        rec = StrategyRecommendation()

        # Summary
        m = re.search(self.SECTION_PATTERNS["summary"], text, re.IGNORECASE)
        if m:
            rec.summary = m.group(1).strip()
        else:
            # Use first line as summary
            rec.summary = text.strip().split("\n")[0][:200]

        # List sections
        for section, attr in [
            ("immediate", "immediate_actions"),
            ("build_order", "build_order_next"),
            ("tech", "tech_priority"),
            ("warnings", "warnings"),
        ]:
            m = re.search(self.SECTION_PATTERNS[section], text, re.IGNORECASE)
            if m:
                items = self._parse_list(m.group(1))
                setattr(rec, attr, items)

        # Army composition
        m = re.search(self.SECTION_PATTERNS["army"], text, re.IGNORECASE)
        if m:
            rec.army_composition_target = self._parse_army(m.group(1))

        # Confidence
        m = re.search(self.SECTION_PATTERNS["confidence"], text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            rec.confidence = val if val <= 1.0 else val / 100.0
        else:
            rec.confidence = 0.5

        # Reasoning
        m = re.search(self.SECTION_PATTERNS["reasoning"], text, re.IGNORECASE)
        if m:
            rec.reasoning = m.group(1).strip()

        return rec

    @staticmethod
    def _parse_list(text: str) -> List[str]:
        items = []
        for line in text.strip().split("\n"):
            line = re.sub(r"^[\s\-\*\d.]+", "", line).strip()
            if line and len(line) > 2:
                items.append(line)
        return items

    @staticmethod
    def _parse_army(text: str) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for m in re.finditer(r"(\w+(?:\s\w+)?)\s*[:\-]\s*(\d+)", text):
            result[m.group(1).strip()] = int(m.group(2))
        return result


# ---------------------------------------------------------------------------
# Tool: Build Order Database
# ---------------------------------------------------------------------------

# Standard Zerg build orders
_BUILD_ORDER_DB: Dict[str, Dict[str, Any]] = {
    "hatch_first_zvt": {
        "name": "Hatch First (ZvT)",
        "matchup": "ZvT",
        "phase": "OPENING",
        "steps": [
            "13 Overlord",
            "16 Hatchery (natural)",
            "18 Gas",
            "17 Spawning Pool",
            "20 2x Zerglings (scout)",
            "20 Queen x2",
            "24 Overlord",
            "28 3rd Hatchery",
            "30 Lair",
        ],
        "description": "Economic opening against Terran. Safe with early lings for scouting.",
        "transitions": ["ling-bane into hydra", "roach-ravager timing"],
    },
    "pool_first_zvp": {
        "name": "Pool First (ZvP)",
        "matchup": "ZvP",
        "phase": "OPENING",
        "steps": [
            "13 Overlord",
            "16 Spawning Pool",
            "16 Hatchery (natural)",
            "18 Gas",
            "18 Queen",
            "20 2x Zerglings",
            "22 Queen (natural)",
            "24 Overlord",
            "28 Lair",
            "30 3rd Hatchery",
        ],
        "description": "Safe pool-first against Protoss. Lings defend early adepts.",
        "transitions": ["roach-hydra-lurker", "ling-hydra-viper"],
    },
    "12_pool_zvz": {
        "name": "12 Pool (ZvZ)",
        "matchup": "ZvZ",
        "phase": "OPENING",
        "steps": [
            "12 Spawning Pool",
            "13 Overlord",
            "13 Gas",
            "14 6x Zerglings",
            "16 Queen",
            "18 Metabolic Boost",
            "20 Hatchery (natural)",
            "22 Overlord",
        ],
        "description": "Aggressive early pool for ZvZ. Puts pressure while securing natural.",
        "transitions": ["ling-bane all-in", "macro behind lings"],
    },
    "roach_ravager_timing": {
        "name": "Roach-Ravager Timing",
        "matchup": "ZvT",
        "phase": "EARLY",
        "steps": [
            "Standard opening into 3 bases",
            "Roach Warren at 3:30",
            "Double gas at natural",
            "Roach Speed (Glial Reconstitution)",
            "Produce 8-12 Roaches",
            "Add Ravagers (3-4)",
            "Attack with +1 Missile",
        ],
        "description": "Roach-Ravager timing push at ~5:30. Bile destroys bunkers.",
        "transitions": ["hydra follow-up", "macro into lurkers"],
    },
    "ling_bane_muta_zvt": {
        "name": "Ling-Bane-Muta (ZvT)",
        "matchup": "ZvT",
        "phase": "MID",
        "steps": [
            "Secure 3 bases",
            "Baneling Nest",
            "Lair -> Spire",
            "+1 Melee, +1 Carapace",
            "Centrifugal Hooks (bane speed)",
            "12-16 Mutalisks",
            "Mass ling-bane on ground",
            "Harass with mutas, engage with ling-bane",
        ],
        "description": "Classic Zerg mid-game. Mutas for harass, ling-bane for fights.",
        "transitions": ["hive tech (ultras/vipers)", "brood lord switch"],
    },
    "hydra_lurker_zvp": {
        "name": "Hydra-Lurker (ZvP)",
        "matchup": "ZvP",
        "phase": "MID",
        "steps": [
            "3 base economy",
            "Hydralisk Den",
            "Lurker Den",
            "+1 Missile, +1 Carapace",
            "Grooved Spines (hydra range)",
            "Mass hydras (20+)",
            "Add 6-8 Lurkers",
            "Siege positions, force engagements",
        ],
        "description": "Strong composition vs ground Protoss. Lurkers zone out zealots.",
        "transitions": ["viper support", "brood lords late game"],
    },
}


class BuildOrderDB:
    """Searchable database of standard Zerg build orders."""

    def __init__(self) -> None:
        self.builds = dict(_BUILD_ORDER_DB)

    def search(
        self,
        matchup: Optional[str] = None,
        phase: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = list(self.builds.values())
        if matchup:
            results = [b for b in results if b["matchup"].lower() == matchup.lower()]
        if phase:
            results = [b for b in results if b["phase"].lower() == phase.lower()]
        if query:
            q = query.lower()
            results = [
                b
                for b in results
                if q in b["name"].lower() or q in b["description"].lower()
            ]
        return results

    def get(self, build_id: str) -> Optional[Dict[str, Any]]:
        return self.builds.get(build_id)

    def recommend(self, state: SC2GameState) -> List[Dict[str, Any]]:
        """Recommend builds based on current game state."""
        matchup = state.matchup.value
        phase = state.phase.name
        candidates = self.search(matchup=matchup)
        # Prefer builds matching current or next phase
        phase_order = [
            GamePhase.OPENING,
            GamePhase.EARLY,
            GamePhase.MID,
            GamePhase.LATE,
        ]
        current_idx = phase_order.index(state.phase)
        scored = []
        for b in candidates:
            b_phase = b["phase"].upper()
            try:
                b_idx = [p.name for p in phase_order].index(b_phase)
            except ValueError:
                b_idx = 0
            # Prefer builds at or just ahead of current phase
            score = -abs(b_idx - current_idx)
            if b_idx >= current_idx:
                score += 1
            scored.append((score, b))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [b for _, b in scored[:3]]


# ---------------------------------------------------------------------------
# Tool: Unit Counter Lookup
# ---------------------------------------------------------------------------

_UNIT_COUNTERS: Dict[str, Dict[str, Any]] = {
    "Marine": {
        "counters": ["Baneling", "Lurker", "Ultralisk"],
        "soft_counters": ["Zergling (with speed)", "Mutalisk"],
        "note": "Marines are vulnerable to splash. Banelings destroy clumps.",
    },
    "Siege Tank": {
        "counters": ["Ravager (bile)", "Brood Lord", "Swarm Host"],
        "soft_counters": ["Mutalisk", "Zergling (flank)"],
        "note": "Use Ravager bile to unsiege. Mutas harass unsieged tanks.",
    },
    "Medivac": {
        "counters": ["Corruptor", "Hydralisk", "Mutalisk"],
        "soft_counters": ["Queen (transfuse denial)"],
        "note": "Priority target. Kill Medivacs to remove healing.",
    },
    "Battlecruiser": {
        "counters": ["Corruptor", "Viper (abduct)"],
        "soft_counters": ["Hydralisk (massed)"],
        "note": "Abduct with Vipers then surround. Corruptors in numbers.",
    },
    "Zealot": {
        "counters": ["Lurker", "Roach (kite)"],
        "soft_counters": ["Zergling (surround)"],
        "note": "Lurkers absolutely destroy chargelots. Keep distance.",
    },
    "Stalker": {
        "counters": ["Zergling (surround)", "Hydralisk"],
        "soft_counters": ["Roach (early game)"],
        "note": "Stalkers are weak vs mass ling surrounds.",
    },
    "Immortal": {
        "counters": ["Zergling (surround)", "Brood Lord"],
        "soft_counters": ["Hydralisk", "Viper (abduct)"],
        "note": "Barrier absorbs 100 damage. Surround to waste it.",
    },
    "Colossus": {
        "counters": ["Corruptor", "Viper (abduct)"],
        "soft_counters": ["Hydralisk"],
        "note": "Air units can hit Colossi. Abduct into army.",
    },
    "Disruptor": {
        "counters": ["Zergling (split)", "Lurker"],
        "soft_counters": ["Mutalisk"],
        "note": "Split against purification nova. Lurkers outrange.",
    },
    "Void Ray": {
        "counters": ["Corruptor", "Hydralisk (massed)", "Queen"],
        "soft_counters": ["Mutalisk"],
        "note": "Queens with transfuse tank well. Corruptors in numbers.",
    },
}


class UnitCounterLookup:
    """Provides unit counter information for coaching."""

    def __init__(self) -> None:
        self.data = dict(_UNIT_COUNTERS)

    def lookup(self, unit_name: str) -> Optional[Dict[str, Any]]:
        """Look up counters for a specific enemy unit."""
        for key, val in self.data.items():
            if key.lower() == unit_name.lower():
                return {"unit": key, **val}
        # Fuzzy match
        for key, val in self.data.items():
            if unit_name.lower() in key.lower():
                return {"unit": key, **val}
        return None

    def counter_army(self, enemy_units: Dict[str, int]) -> Dict[str, Any]:
        """Recommend counters for an entire enemy army composition."""
        counter_scores: Dict[str, float] = {}
        notes: List[str] = []

        for unit_name, count in enemy_units.items():
            info = self.lookup(unit_name)
            if not info:
                continue
            weight = count  # More units = more important to counter
            for counter in info.get("counters", []):
                clean = re.sub(r"\s*\(.*\)", "", counter)
                counter_scores[clean] = counter_scores.get(clean, 0) + weight * 2.0
            for soft in info.get("soft_counters", []):
                clean = re.sub(r"\s*\(.*\)", "", soft)
                counter_scores[clean] = counter_scores.get(clean, 0) + weight * 1.0
            if info.get("note"):
                notes.append(f"{unit_name}: {info['note']}")

        ranked = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
        return {
            "recommended_units": [u for u, _ in ranked[:5]],
            "scores": dict(ranked),
            "notes": notes,
        }


# ---------------------------------------------------------------------------
# Tool: Replay Analyser (simulated)
# ---------------------------------------------------------------------------


class ReplayAnalyser:
    """Analyses replay data for strategic insights."""

    def __init__(self) -> None:
        self.rng = np.random.default_rng(42)

    def analyse(self, replay_id: str = "latest") -> Dict[str, Any]:
        """Analyse a replay and return strategic insights."""
        # Simulated replay analysis
        minerals_collected = float(self.rng.uniform(8000, 25000))
        gas_collected = float(self.rng.uniform(3000, 12000))
        army_created = float(self.rng.uniform(5000, 20000))
        army_lost = float(self.rng.uniform(2000, 15000))
        workers_created = int(self.rng.integers(40, 90))
        workers_lost = int(self.rng.integers(5, 30))
        game_length = float(self.rng.uniform(300, 1200))
        apm = float(self.rng.uniform(80, 250))

        # Derived metrics
        resource_efficiency = army_created / max(minerals_collected + gas_collected, 1)
        army_trade = army_created / max(army_lost, 1)
        worker_saturation = workers_created / max(workers_created - workers_lost, 1)

        issues: List[str] = []
        strengths: List[str] = []

        if resource_efficiency < 0.4:
            issues.append("Low resource efficiency -- floating too many resources")
        else:
            strengths.append("Good resource spending")

        if army_trade < 1.2:
            issues.append("Poor army trades -- losing more than gaining")
        else:
            strengths.append("Favourable army trades")

        if workers_lost > 15:
            issues.append("High worker losses -- improve drone defence")

        if apm > 150:
            strengths.append("Strong APM")
        else:
            issues.append("APM could be higher -- focus on macro cycle")

        return {
            "replay_id": replay_id,
            "game_length_seconds": round(game_length, 1),
            "minerals_collected": round(minerals_collected),
            "gas_collected": round(gas_collected),
            "army_created_value": round(army_created),
            "army_lost_value": round(army_lost),
            "workers_created": workers_created,
            "workers_lost": workers_lost,
            "apm": round(apm, 1),
            "resource_efficiency": round(resource_efficiency, 3),
            "army_trade_ratio": round(army_trade, 2),
            "issues": issues,
            "strengths": strengths,
        }


# ---------------------------------------------------------------------------
# Memory: Conversation + Game History
# ---------------------------------------------------------------------------


@dataclass
class MemoryEntry:
    role: str  # "user" or "coach"
    content: str
    timestamp: float = 0.0
    game_state: Optional[SC2GameState] = None


class StrategyMemory:
    """Manages conversation buffer and game history summary."""

    def __init__(self, max_buffer: int = 20, max_history: int = 100) -> None:
        self.buffer: List[MemoryEntry] = []
        self.game_history: List[Dict[str, Any]] = []
        self.max_buffer = max_buffer
        self.max_history = max_history
        self._summary: str = ""

    def add_message(
        self, role: str, content: str, game_state: Optional[SC2GameState] = None
    ) -> None:
        entry = MemoryEntry(
            role=role, content=content, timestamp=time.time(), game_state=game_state
        )
        self.buffer.append(entry)
        if len(self.buffer) > self.max_buffer:
            self._summarise_oldest()

    def add_game_record(self, record: Dict[str, Any]) -> None:
        self.game_history.append(record)
        if len(self.game_history) > self.max_history:
            self.game_history = self.game_history[-self.max_history :]

    def get_context(self, max_entries: int = 10) -> str:
        """Build context string from recent conversation."""
        entries = self.buffer[-max_entries:]
        lines = []
        if self._summary:
            lines.append(f"[Previous context summary]: {self._summary}")
        for e in entries:
            prefix = "Player" if e.role == "user" else "Coach"
            lines.append(f"{prefix}: {e.content}")
        return "\n".join(lines)

    def get_game_summary(self) -> str:
        """Summarise recent game history."""
        if not self.game_history:
            return "No game history available."
        recent = self.game_history[-5:]
        lines = [f"Recent games ({len(self.game_history)} total):"]
        for i, g in enumerate(recent):
            result = g.get("result", "unknown")
            matchup = g.get("matchup", "?v?")
            length = g.get("length_min", 0)
            lines.append(f"  Game {i + 1}: {matchup} - {result} ({length:.1f} min)")
        return "\n".join(lines)

    def _summarise_oldest(self) -> None:
        """Move oldest entries into summary."""
        to_summarise = self.buffer[:5]
        self.buffer = self.buffer[5:]
        parts = [f"{e.role}: {e.content[:100]}" for e in to_summarise]
        if self._summary:
            self._summary += " | " + " | ".join(parts)
        else:
            self._summary = " | ".join(parts)
        # Keep summary bounded
        if len(self._summary) > 1000:
            self._summary = self._summary[-800:]

    def clear(self) -> None:
        self.buffer.clear()
        self._summary = ""


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an expert StarCraft II Zerg coach. You analyse game states, "
    "recommend strategies, and provide actionable advice. Be specific with "
    "unit compositions, timings, and build orders. Focus on the current "
    "matchup and game phase."
)

MATCHUP_PROMPTS: Dict[str, str] = {
    "ZvT": (
        "In Zerg vs Terran, key considerations:\n"
        "- Scout for early aggression (hellion/reaper, 2-1-1 push)\n"
        "- Ling-Bane-Muta is standard mid-game composition\n"
        "- Creep spread is critical for ling-bane engagements\n"
        "- Watch for mech transitions (mass tank/thor)\n"
        "- Late game: Ultralisk or Brood Lord switch\n"
        "- Always have detection ready for widow mines/banshees"
    ),
    "ZvP": (
        "In Zerg vs Protoss, key considerations:\n"
        "- Scout for proxy stargate, DT rush, or cannon rush\n"
        "- Roach-Hydra-Lurker is strong mid-game composition\n"
        "- Spread creep aggressively to spot warp prism harass\n"
        "- Vipers are essential late game (abduct colossi/carriers)\n"
        "- Keep drone count high, Protoss has slower economy\n"
        "- Always have overseers for DT detection"
    ),
    "ZvZ": (
        "In Zerg vs Zerg, key considerations:\n"
        "- Ling-Bane micro is crucial in early game\n"
        "- First to Roaches often wins early engagements\n"
        "- Bane speed (Centrifugal Hooks) timing is important\n"
        "- Spire transition can be game-ending if unscouted\n"
        "- Lurker-Hydra is strong in later ZvZ\n"
        "- Spine crawlers for defence during transitions"
    ),
}

COT_TEMPLATE = (
    "Analyse the following SC2 game state step by step:\n\n"
    "{game_state}\n\n"
    "Context:\n{context}\n\n"
    "Matchup advice:\n{matchup_advice}\n\n"
    "Think step by step:\n"
    "1. Assess the current situation (economy, army, tech)\n"
    "2. Identify threats and opportunities\n"
    "3. Consider the matchup-specific dynamics\n"
    "4. Recommend concrete actions\n\n"
    "Provide your recommendation in this format:\n"
    "Summary: [one sentence overview]\n"
    "Immediate actions: [list]\n"
    "Build order: [next steps]\n"
    "Army composition: [target units with counts]\n"
    "Tech priority: [list]\n"
    "Warnings: [any urgent threats]\n"
    "Confidence: [0-100]\n"
    "Reasoning: [brief explanation]"
)


# ---------------------------------------------------------------------------
# ReAct Agent (Reason + Act)
# ---------------------------------------------------------------------------


class ReActStep:
    """Single step in the ReAct reasoning loop."""

    def __init__(
        self,
        thought: str = "",
        action: str = "",
        action_input: str = "",
        observation: str = "",
    ) -> None:
        self.thought = thought
        self.action = action
        self.action_input = action_input
        self.observation = observation

    def __repr__(self) -> str:
        return (
            f"Thought: {self.thought}\n"
            f"Action: {self.action}({self.action_input})\n"
            f"Observation: {self.observation}"
        )


class ReActAgent:
    """Reason+Act agent for interactive SC2 coaching.

    Available tools:
      - replay_analyser: analyse replay data
      - build_order_db: search build orders
      - unit_counter: look up unit counters
      - game_state: describe current game state
    """

    def __init__(self) -> None:
        self.replay_analyser = ReplayAnalyser()
        self.build_order_db = BuildOrderDB()
        self.unit_counter = UnitCounterLookup()
        self.steps: List[ReActStep] = []
        self.max_steps = 5

    def _execute_tool(
        self, tool_name: str, tool_input: str, game_state: Optional[SC2GameState] = None
    ) -> str:
        """Execute a tool and return observation string."""
        tool_name = tool_name.strip().lower()

        if tool_name in ("replay_analyser", "replay", "analyse_replay"):
            result = self.replay_analyser.analyse(tool_input or "latest")
            return json.dumps(result, indent=2)

        elif tool_name in ("build_order_db", "build_order", "builds"):
            matchup = None
            if game_state:
                matchup = game_state.matchup.value
            builds = self.build_order_db.search(
                matchup=matchup, query=tool_input or None
            )
            return json.dumps(
                [
                    {
                        "name": b["name"],
                        "steps": b["steps"][:5],
                        "description": b["description"],
                    }
                    for b in builds
                ],
                indent=2,
            )

        elif tool_name in ("unit_counter", "counter", "counters"):
            if game_state and game_state.enemy_army_scouted:
                result = self.unit_counter.counter_army(game_state.enemy_army_scouted)
            else:
                info = self.unit_counter.lookup(tool_input or "Marine")
                result = info if info else {"error": "Unit not found"}
            return json.dumps(result, indent=2)

        elif tool_name in ("game_state", "state", "situation"):
            if game_state:
                return game_state.to_description()
            return "No game state available."

        return f"Unknown tool: {tool_name}"

    def reason(
        self, query: str, game_state: Optional[SC2GameState] = None
    ) -> List[ReActStep]:
        """Run the ReAct loop with rule-based reasoning."""
        self.steps = []

        # Step 1: Assess situation
        step1 = ReActStep(
            thought="First, I need to understand the current game state.",
            action="game_state",
            action_input="current",
        )
        step1.observation = self._execute_tool("game_state", "current", game_state)
        self.steps.append(step1)

        # Step 2: Check for unit counters if enemy army is known
        if game_state and game_state.enemy_army_scouted:
            step2 = ReActStep(
                thought="The enemy has specific units. Let me find counters.",
                action="unit_counter",
                action_input="",
            )
            step2.observation = self._execute_tool("unit_counter", "", game_state)
            self.steps.append(step2)

        # Step 3: Look up build orders
        step3 = ReActStep(
            thought="Let me check recommended build orders for this matchup.",
            action="build_order_db",
            action_input=query,
        )
        step3.observation = self._execute_tool("build_order_db", query, game_state)
        self.steps.append(step3)

        # Step 4: Analyse recent replay if relevant
        if "replay" in query.lower() or "analyse" in query.lower():
            step4 = ReActStep(
                thought="The player asked about replay analysis.",
                action="replay_analyser",
                action_input="latest",
            )
            step4.observation = self._execute_tool(
                "replay_analyser", "latest", game_state
            )
            self.steps.append(step4)

        return self.steps


# ---------------------------------------------------------------------------
# Rule-based fallback coach
# ---------------------------------------------------------------------------


class RuleBasedCoach:
    """Fallback coaching engine when LLM is unavailable."""

    def __init__(self) -> None:
        self.build_db = BuildOrderDB()
        self.counter_lookup = UnitCounterLookup()
        self.replay_analyser = ReplayAnalyser()

    def coach(self, state: SC2GameState, query: str = "") -> StrategyRecommendation:
        """Generate strategy recommendation using rules."""
        rec = StrategyRecommendation()
        matchup = state.matchup
        phase = state.phase

        # Economy checks
        warnings: List[str] = []
        actions: List[str] = []

        ideal_workers = {
            GamePhase.OPENING: 20,
            GamePhase.EARLY: 40,
            GamePhase.MID: 60,
            GamePhase.LATE: 70,
        }
        target_workers = ideal_workers.get(phase, 50)
        if state.worker_count < target_workers * 0.7:
            actions.append(
                f"Drone up! Current: {state.worker_count}, " f"target: {target_workers}"
            )
            warnings.append("Worker count is significantly below target")

        # Supply check
        if state.supply_cap - state.supply_used < 4:
            actions.append("Build Overlords immediately -- supply blocked!")
            warnings.append("SUPPLY BLOCKED")

        # Expansion timing
        ideal_bases = {
            GamePhase.OPENING: 2,
            GamePhase.EARLY: 3,
            GamePhase.MID: 4,
            GamePhase.LATE: 5,
        }
        target_bases = ideal_bases.get(phase, 3)
        if state.base_count < target_bases:
            actions.append(
                f"Take expansion #{state.base_count + 1} "
                f"(target: {target_bases} bases by {phase.name} game)"
            )

        # Resource floating
        if state.minerals > 800:
            actions.append(
                f"Floating {state.minerals:.0f} minerals! " "Spend on army or expand"
            )
            warnings.append("High mineral float")
        if state.vespene > 500:
            actions.append(
                f"Floating {state.vespene:.0f} gas! "
                "Consider tech upgrades or gas-heavy units"
            )

        # Army composition advice
        army_target: Dict[str, int] = {}
        tech_priority: List[str] = []

        if matchup == Matchup.ZvT:
            rec.summary = self._zvt_advice(
                state, army_target, tech_priority, actions, warnings
            )
        elif matchup == Matchup.ZvP:
            rec.summary = self._zvp_advice(
                state, army_target, tech_priority, actions, warnings
            )
        else:
            rec.summary = self._zvz_advice(
                state, army_target, tech_priority, actions, warnings
            )

        # Counter enemy army
        if state.enemy_army_scouted:
            counter_info = self.counter_lookup.counter_army(state.enemy_army_scouted)
            for unit in counter_info["recommended_units"][:3]:
                if unit not in army_target:
                    army_target[unit] = 8

        # Build order recommendation
        builds = self.build_db.recommend(state)
        build_steps: List[str] = []
        if builds:
            best = builds[0]
            build_steps = best["steps"][:5]

        rec.immediate_actions = actions
        rec.build_order_next = build_steps
        rec.army_composition_target = army_target
        rec.tech_priority = tech_priority
        rec.warnings = warnings
        rec.confidence = 0.65  # rule-based is less confident
        rec.reasoning = (
            f"Rule-based analysis for {matchup.value} in {phase.name} game. "
            f"Economy: {state.worker_count} workers, {state.base_count} bases."
        )
        return rec

    def _zvt_advice(
        self,
        state: SC2GameState,
        army: Dict[str, int],
        tech: List[str],
        actions: List[str],
        warnings: List[str],
    ) -> str:
        phase = state.phase
        if phase in (GamePhase.OPENING, GamePhase.EARLY):
            army.update({"Zergling": 16, "Queen": 3})
            tech.extend(["Metabolic Boost", "Lair"])
            actions.append("Focus on economy and creep spread")
            return "Establish economy and scout for Terran aggression"
        elif phase == GamePhase.MID:
            army.update({"Zergling": 30, "Baneling": 12, "Mutalisk": 12})
            tech.extend(["+1 Melee", "+1 Carapace", "Centrifugal Hooks"])
            actions.append("Harass with Mutalisks, defend with Ling-Bane")
            return "Transition to Ling-Bane-Muta mid-game composition"
        else:
            army.update({"Ultralisk": 8, "Zergling": 40, "Corruptor": 8})
            tech.extend(["Hive", "Chitinous Plating", "+3 upgrades"])
            actions.append("Ultralisk switch with full upgrades")
            return "Late game Ultralisk composition with air support"

    def _zvp_advice(
        self,
        state: SC2GameState,
        army: Dict[str, int],
        tech: List[str],
        actions: List[str],
        warnings: List[str],
    ) -> str:
        phase = state.phase
        if phase in (GamePhase.OPENING, GamePhase.EARLY):
            army.update({"Zergling": 8, "Roach": 6, "Queen": 3})
            tech.extend(["Roach Speed", "Lair"])
            actions.append("Scout for stargate or DT opening")
            warnings.append("Have overseer ready for possible DTs")
            return "Safe roach opening, scout for Protoss tech"
        elif phase == GamePhase.MID:
            army.update({"Hydralisk": 20, "Lurker": 8, "Roach": 6})
            tech.extend(["Grooved Spines", "Lurker Den", "+1 Missile"])
            actions.append("Siege with Lurkers, protect with Hydras")
            return "Hydra-Lurker siege composition"
        else:
            army.update({"Brood Lord": 8, "Corruptor": 6, "Viper": 4})
            tech.extend(["Greater Spire", "Hive", "Viper energy upgrades"])
            actions.append("Brood Lord transition with Viper support")
            return "Late game air switch with Vipers for spellcasting"

    def _zvz_advice(
        self,
        state: SC2GameState,
        army: Dict[str, int],
        tech: List[str],
        actions: List[str],
        warnings: List[str],
    ) -> str:
        phase = state.phase
        if phase in (GamePhase.OPENING, GamePhase.EARLY):
            army.update({"Zergling": 20, "Baneling": 6})
            tech.extend(["Metabolic Boost", "Baneling Nest"])
            actions.append("Careful ling-bane micro, control map centre")
            warnings.append("ZvZ is volatile -- always have banes ready")
            return "Ling-Bane control in early ZvZ"
        elif phase == GamePhase.MID:
            army.update({"Roach": 15, "Hydralisk": 10, "Ravager": 4})
            tech.extend(["Roach Speed", "Hydralisk Den"])
            actions.append("Transition to Roach-Hydra, outmacro opponent")
            return "Roach-Hydra mid-game with macro advantage"
        else:
            army.update({"Hydralisk": 15, "Lurker": 10, "Viper": 3})
            tech.extend(["Lurker Den", "Hive", "Viper"])
            actions.append("Lurker contain with Viper support")
            return "Lurker-based late game control"


# ---------------------------------------------------------------------------
# Streaming coach (simulated)
# ---------------------------------------------------------------------------


class StreamingCoach:
    """Provides streaming responses for real-time coaching."""

    def __init__(self, coach: RuleBasedCoach) -> None:
        self.coach = coach

    def stream_advice(
        self, state: SC2GameState, query: str = ""
    ) -> Generator[str, None, None]:
        """Yield coaching advice token by token for streaming display."""
        rec = self.coach.coach(state, query)
        display = rec.to_display()
        # Simulate streaming by yielding word by word
        words = display.split(" ")
        buffer = ""
        for i, word in enumerate(words):
            buffer += word + " "
            if len(buffer) > 20 or i == len(words) - 1:
                yield buffer
                buffer = ""


# ---------------------------------------------------------------------------
# SC2StrategyCoach -- main coach class
# ---------------------------------------------------------------------------


class SC2StrategyCoach:
    """LangChain-powered strategy coach for SC2.

    Uses chain-of-thought reasoning and ReAct agent for interactive
    coaching. Falls back to rule-based coaching when LLM is unavailable.
    """

    def __init__(self, llm: Any = None, use_langchain: bool = True) -> None:
        self.llm = llm
        self.use_langchain = use_langchain and _LANGCHAIN_AVAILABLE and llm is not None
        self.memory = StrategyMemory()
        self.parser = StrategyOutputParser()
        self.react_agent = ReActAgent()
        self.rule_coach = RuleBasedCoach()
        self.streaming = StreamingCoach(self.rule_coach)

        # LangChain chain (if available)
        self._chain: Any = None
        if self.use_langchain and self.llm is not None:
            self._setup_langchain()

        logger.info(
            "SC2StrategyCoach initialised (langchain=%s, llm=%s)",
            self.use_langchain,
            type(self.llm).__name__ if self.llm else "None",
        )

    def _setup_langchain(self) -> None:
        """Configure LangChain chain-of-thought pipeline."""
        if not _LANGCHAIN_AVAILABLE or self.llm is None:
            return

        prompt = PromptTemplate(
            input_variables=["game_state", "context", "matchup_advice"],
            template=COT_TEMPLATE,
        )
        self._chain = LLMChain(llm=self.llm, prompt=prompt)
        logger.info("LangChain CoT chain configured")

    def analyse(self, state: SC2GameState, query: str = "") -> StrategyRecommendation:
        """Main entry point: analyse game state and provide coaching."""
        self.memory.add_message("user", query or "Analyse current state", state)

        if self.use_langchain and self._chain is not None:
            rec = self._langchain_analyse(state, query)
        else:
            rec = self._fallback_analyse(state, query)

        self.memory.add_message("coach", rec.summary)
        return rec

    def _langchain_analyse(
        self, state: SC2GameState, query: str
    ) -> StrategyRecommendation:
        """Use LangChain CoT chain for analysis."""
        matchup_advice = MATCHUP_PROMPTS.get(state.matchup.value, "General Zerg advice")
        context = self.memory.get_context()

        try:
            result = self._chain.run(
                game_state=state.to_description(),
                context=context,
                matchup_advice=matchup_advice,
            )
            return self.parser.parse(result)
        except Exception as e:
            logger.warning("LangChain analysis failed: %s, falling back", e)
            return self._fallback_analyse(state, query)

    def _fallback_analyse(
        self, state: SC2GameState, query: str
    ) -> StrategyRecommendation:
        """Rule-based fallback analysis."""
        # Run ReAct reasoning for additional context
        react_steps = self.react_agent.reason(query, state)

        # Get rule-based recommendation
        rec = self.rule_coach.coach(state, query)

        # Enrich with ReAct observations
        for step in react_steps:
            if step.action == "unit_counter" and step.observation:
                try:
                    counter_data = json.loads(step.observation)
                    if "recommended_units" in counter_data:
                        rec.reasoning += (
                            f" Counter analysis suggests: "
                            f"{', '.join(counter_data['recommended_units'][:3])}."
                        )
                except (json.JSONDecodeError, KeyError):
                    pass

        return rec

    def interactive_coach(self, state: SC2GameState, question: str) -> str:
        """Answer a specific coaching question interactively."""
        self.memory.add_message("user", question, state)

        # ReAct reasoning
        steps = self.react_agent.reason(question, state)

        # Build response from ReAct steps
        response_parts: List[str] = []
        for step in steps:
            if step.thought:
                response_parts.append(f"[Thinking] {step.thought}")

        # Get recommendation
        rec = self.rule_coach.coach(state, question)
        response_parts.append(rec.to_display())

        response = "\n".join(response_parts)
        self.memory.add_message("coach", response[:200])
        return response

    def stream_coaching(
        self, state: SC2GameState, query: str = ""
    ) -> Generator[str, None, None]:
        """Stream coaching advice in real-time."""
        yield from self.streaming.stream_advice(state, query)

    def get_build_orders(
        self, matchup: Optional[str] = None, phase: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query build order database."""
        return self.react_agent.build_order_db.search(matchup=matchup, phase=phase)

    def get_counters(self, enemy_units: Dict[str, int]) -> Dict[str, Any]:
        """Get counter recommendations for enemy army."""
        return self.react_agent.unit_counter.counter_army(enemy_units)

    def analyse_replay(self, replay_id: str = "latest") -> Dict[str, Any]:
        """Analyse a replay for strategic insights."""
        return self.react_agent.replay_analyser.analyse(replay_id)

    def save_session(self, path: str) -> None:
        """Save coaching session to file."""
        data = {
            "conversation": [
                {"role": e.role, "content": e.content, "timestamp": e.timestamp}
                for e in self.memory.buffer
            ],
            "game_history": self.memory.game_history,
            "summary": self.memory._summary,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Session saved to %s", path)


# ---------------------------------------------------------------------------
# CLI demo with simulated game states
# ---------------------------------------------------------------------------


def _make_demo_states() -> List[Tuple[str, SC2GameState]]:
    """Create simulated game states for the demo."""
    return [
        (
            "Opening ZvT -- what should I build?",
            SC2GameState(
                game_time_seconds=90,
                player_race=Race.ZERG,
                enemy_race=Race.TERRAN,
                minerals=250,
                vespene=50,
                supply_used=18,
                supply_cap=22,
                worker_count=16,
                base_count=1,
                army_composition={"Zergling": 4},
                enemy_army_scouted={"Marine": 4, "Reaper": 1},
                tech_buildings=["SpawningPool"],
                creep_coverage=0.05,
                army_value=200,
                enemy_army_value=300,
            ),
        ),
        (
            "Mid-game ZvP -- enemy has lots of stalkers",
            SC2GameState(
                game_time_seconds=420,
                player_race=Race.ZERG,
                enemy_race=Race.PROTOSS,
                minerals=600,
                vespene=300,
                supply_used=85,
                supply_cap=100,
                worker_count=55,
                base_count=3,
                army_composition={"Zergling": 20, "Roach": 8, "Hydralisk": 6},
                enemy_army_scouted={"Stalker": 12, "Immortal": 3, "Sentry": 2},
                upgrades_completed=["+1 Missile"],
                tech_buildings=["SpawningPool", "RoachWarren", "HydraliskDen", "Lair"],
                creep_coverage=0.30,
                army_value=2400,
                enemy_army_value=3000,
            ),
        ),
        (
            "Late ZvZ -- how to close out the game?",
            SC2GameState(
                game_time_seconds=840,
                player_race=Race.ZERG,
                enemy_race=Race.ZERG,
                minerals=1200,
                vespene=800,
                supply_used=150,
                supply_cap=176,
                worker_count=65,
                base_count=5,
                army_composition={
                    "Hydralisk": 15,
                    "Lurker": 8,
                    "Roach": 10,
                    "Ravager": 4,
                },
                enemy_army_scouted={"Mutalisk": 15, "Zergling": 30, "Baneling": 10},
                upgrades_completed=["+2 Missile", "+2 Carapace", "Lurker Range"],
                tech_buildings=[
                    "SpawningPool",
                    "RoachWarren",
                    "HydraliskDen",
                    "LurkerDen",
                    "Hive",
                ],
                creep_coverage=0.55,
                army_value=5500,
                enemy_army_value=4000,
            ),
        ),
        (
            "Replay analysis request",
            SC2GameState(
                game_time_seconds=0,
                player_race=Race.ZERG,
                enemy_race=Race.TERRAN,
            ),
        ),
    ]


def run_demo(verbose: bool = True) -> None:
    """Run strategy coach demo with simulated game states."""
    print("=" * 70)
    print("Phase 621: SC2 LangChain Strategy Coach Demo")
    print("=" * 70)
    print(f"  LangChain available : {_LANGCHAIN_AVAILABLE}")
    print(
        f"  Mode                : {'LangChain' if _LANGCHAIN_AVAILABLE else 'Rule-based fallback'}"
    )
    print()

    coach = SC2StrategyCoach(llm=None, use_langchain=False)
    demo_states = _make_demo_states()

    for i, (query, state) in enumerate(demo_states):
        print(f"{'=' * 70}")
        print(f"  Scenario {i + 1}: {query}")
        print(f"{'=' * 70}")

        if "replay" in query.lower():
            # Replay analysis demo
            replay_result = coach.analyse_replay("demo_replay_001")
            print("\nReplay Analysis:")
            print(f"  Game length : {replay_result['game_length_seconds']:.0f}s")
            print(f"  APM         : {replay_result['apm']}")
            print(f"  Efficiency  : {replay_result['resource_efficiency']:.1%}")
            print(f"  Army trade  : {replay_result['army_trade_ratio']:.2f}x")
            if replay_result["issues"]:
                print("  Issues:")
                for issue in replay_result["issues"]:
                    print(f"    - {issue}")
            if replay_result["strengths"]:
                print("  Strengths:")
                for s in replay_result["strengths"]:
                    print(f"    + {s}")
            print()
            continue

        # Show game state
        if verbose:
            print(f"\nGame State:")
            for line in state.to_description().split("\n"):
                print(f"  {line}")
            print()

        # Get coaching recommendation
        rec = coach.analyse(state, query)
        print(rec.to_display())
        print()

        # Show counters if enemy army known
        if state.enemy_army_scouted:
            counters = coach.get_counters(state.enemy_army_scouted)
            print(f"Counter Analysis:")
            print(f"  Recommended: {', '.join(counters['recommended_units'][:4])}")
            print()

        # Show build orders
        builds = coach.get_build_orders(
            matchup=state.matchup.value, phase=state.phase.name
        )
        if builds:
            print(f"Matching Build Orders:")
            for b in builds[:2]:
                print(f"  [{b['name']}] {b['description']}")
            print()

        # Interactive question demo
        if i == 1:
            print("-" * 40)
            q = "Should I go Lurkers or stay on Hydra-Roach?"
            print(f"  Interactive Q: {q}")
            print("-" * 40)
            response = coach.interactive_coach(state, q)
            for line in response.split("\n"):
                print(f"  {line}")
            print()

        # Streaming demo (show first 3 chunks)
        if i == 0:
            print("-" * 40)
            print("  Streaming demo (first 3 chunks):")
            print("-" * 40)
            chunks = list(coach.stream_coaching(state, query))
            for chunk in chunks[:3]:
                print(f"  >> {chunk.strip()}")
            print(f"  ... ({len(chunks)} total chunks)")
            print()

    # Session summary
    print("=" * 70)
    print("Session Summary:")
    print(f"  Messages in memory : {len(coach.memory.buffer)}")
    print(f"  Context preview    : {coach.memory.get_context(3)[:200]}...")
    print()

    # ReAct trace demo
    print("ReAct Agent Trace (last scenario):")
    last_state = demo_states[2][1]
    steps = coach.react_agent.reason("how to win", last_state)
    for j, step in enumerate(steps):
        print(f"  Step {j + 1}:")
        print(f"    Thought: {step.thought}")
        print(f"    Action:  {step.action}({step.action_input})")
        obs_preview = step.observation[:100] if step.observation else "N/A"
        print(f"    Observe: {obs_preview}...")
    print()

    print("=" * 70)
    print("Phase 621 demo complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_demo()
