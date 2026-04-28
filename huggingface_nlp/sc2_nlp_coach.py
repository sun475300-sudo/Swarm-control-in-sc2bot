# Phase 582: HuggingFace NLP
"""
sc2_nlp_coach.py — StarCraft II NLP Coaching System
Analyzes SC2 game logs using HuggingFace Transformers and provides
strategic advice in Korean and English.

Graceful fallback to keyword-based analysis when `transformers` is not installed.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_nlp_coach")

# ---------------------------------------------------------------------------
# Optional HuggingFace import — graceful fallback
# ---------------------------------------------------------------------------
try:
    import torch
    from transformers import AutoModel, AutoTokenizer, pipeline

    HF_AVAILABLE = True
    log.info("HuggingFace Transformers available — using neural models.")
except ImportError:
    HF_AVAILABLE = False
    log.warning(
        "HuggingFace Transformers not installed. "
        "Falling back to keyword-based analysis. "
        "Install with: pip install transformers torch"
    )

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

STRATEGY_LABELS = [
    "early_aggression",
    "macro_economy",
    "tech_rush",
    "defensive_turtle",
    "timing_attack",
    "all_in",
    "harassment",
    "late_game_deathball",
]

RACE_LABELS = ["Terran", "Zerg", "Protoss", "Unknown"]

BUILD_ORDER_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "Zerg": {
        "early_aggression": [
            "12 Hatchery",
            "13 Pool",
            "15 Drones",
            "16 Queen",
            "Zergling speed",
            "20 Zerglings — attack!",
        ],
        "macro_economy": [
            "17 Hatchery (natural)",
            "18 Pool",
            "19 Queen ×2",
            "Lair @ 65 supply",
            "Roach Warren",
            "Third hatch @ 65",
            "Hydra Den / Spire when needed",
        ],
        "tech_rush": [
            "15 Hatchery",
            "16 Pool",
            "17 Gas ×2",
            "Lair ASAP",
            "Spire/Hydra Den",
            "Mass Mutalisk / Lurker",
        ],
    },
    "Terran": {
        "early_aggression": [
            "14 Supply Depot",
            "15 Barracks",
            "16 Refinery",
            "Reaper — scout + pressure",
            "Orbital Command",
            "Factory + Tech Lab → Hellion/Hellbat push",
        ],
        "macro_economy": [
            "14 Supply",
            "15 Barracks",
            "16 CC (2nd)",
            "3 CC economy",
            "Bio + Medivac mid-game push",
        ],
        "tech_rush": [
            "14 Supply",
            "15 Barracks",
            "16 Factory",
            "Starport — Banshee/Viking",
            "Cloaked Banshee harass",
        ],
    },
    "Protoss": {
        "early_aggression": [
            "14 Pylon",
            "15 Gateway",
            "16 Assimilator",
            "Adept — shade pressure",
            "2-Gate Stalker push",
        ],
        "macro_economy": [
            "14 Pylon",
            "15 Nexus (2nd)",
            "16 Cybernetics Core",
            "Blink Stalkers / Colossus",
            "Third base @ 65",
        ],
        "tech_rush": [
            "14 Pylon",
            "15 Gateway",
            "Dark Shrine — DT rush",
            "Or: Stargate — Oracle into Void Ray",
        ],
    },
}

STRATEGY_ADVICE: Dict[str, Dict[str, str]] = {
    "early_aggression": {
        "en": (
            "Focus on early pressure. Prioritise production buildings "
            "and attack before the opponent stabilises. "
            "Scout at supply 14-16 to confirm counter-strategy."
        ),
        "ko": (
            "초반 압박을 극대화하세요. 상대가 안정되기 전에 공격하세요. "
            "14~16 서플 타이밍에 정찰하여 상대의 대응 전략을 파악하세요."
        ),
    },
    "macro_economy": {
        "en": (
            "Expand safely and maintain high worker saturation. "
            "Control the map to deny the opponent's expansions. "
            "Move out when you have a decisive army advantage."
        ),
        "ko": (
            "안전하게 멀티를 확보하고 일꾼 포화도를 높게 유지하세요. "
            "맵 컨트롤로 상대의 확장을 방해하세요. "
            "병력 우위가 확실해졌을 때 공격하세요."
        ),
    },
    "tech_rush": {
        "en": (
            "Invest in technology ahead of the curve. "
            "Use harassment units to buy time while tech completes. "
            "Strike decisively before the opponent adapts."
        ),
        "ko": (
            "빠른 테크 전환으로 상대를 앞서세요. "
            "테크 완성 전까지 견제 유닛으로 시간을 버세요. "
            "상대가 대응하기 전에 결정타를 날리세요."
        ),
    },
    "defensive_turtle": {
        "en": (
            "Secure a strong defensive perimeter early. "
            "Use static defenses wisely; do not over-invest. "
            "Transition to aggression once your tech advantage is overwhelming."
        ),
        "ko": (
            "초반 강력한 방어선을 구축하세요. "
            "정적 방어물에 과잉 투자하지 마세요. "
            "기술 우위가 충분할 때 공세로 전환하세요."
        ),
    },
    "timing_attack": {
        "en": (
            "Time your attack to the exact moment before the opponent "
            "completes a key tech or expansion. Hit the vulnerability window."
        ),
        "ko": (
            "상대의 핵심 테크나 확장이 완성되기 직전을 노리세요. "
            "그 취약한 순간을 정확히 공략하세요."
        ),
    },
    "all_in": {
        "en": (
            "Commit fully — do not take expansions or hold workers back. "
            "Win or lose on this push. "
            "Ensure supply and production are maxed before moving out."
        ),
        "ko": (
            "올인 — 확장하지 말고 모든 자원을 병력에 쏟으세요. "
            "이 타이밍 공격으로 승패를 결정지으세요. "
            "출전 전 서플과 생산을 최대화하세요."
        ),
    },
    "harassment": {
        "en": (
            "Continuously harass worker lines and tech structures. "
            "Use multi-pronged attacks to split the opponent's attention. "
            "Never let the opponent mine freely."
        ),
        "ko": (
            "일꾼 라인과 테크 건물을 꾸준히 견제하세요. "
            "다방면 공격으로 상대의 집중을 분산시키세요. "
            "상대가 자유롭게 채광하지 못하게 하세요."
        ),
    },
    "late_game_deathball": {
        "en": (
            "Accumulate an overwhelming force before engaging. "
            "Max out supply, then split push or engage head-on. "
            "Position AoE units to maximise splash damage."
        ),
        "ko": (
            "교전 전에 압도적인 병력을 집결시키세요. "
            "서플을 가득 채운 뒤 분산 공격이나 정면 돌파를 선택하세요. "
            "광역 딜 유닛의 포지션을 최적화하세요."
        ),
    },
}

IMPROVEMENT_TIPS: List[str] = [
    "Maintain consistent worker production throughout the game.",
    "Check the minimap every 5-10 seconds to anticipate enemy movements.",
    "Inject/Chrono/MULE on cooldown — never let them sit idle.",
    "Build production structures proactively before you need the units.",
    "Scout after your early build to confirm enemy tech path.",
    "Spread creep (Zerg) / place pylons forward (Protoss) for map vision.",
    "Use control groups and hotkeys to reduce reaction time.",
    "Watch your own replays focusing on supply blocks and idle production.",
    "일꾼 생산을 게임 내내 꾸준히 유지하세요.",
    "미니맵을 5~10초마다 확인하여 적의 움직임을 미리 파악하세요.",
    "주입/크로노/뮬은 쿨타임마다 사용하세요. 절대 낭비하지 마세요.",
    "필요하기 전에 생산 건물을 미리 지으세요.",
    "리플레이를 보며 서플 블록과 놀고 있는 생산 건물을 분석하세요.",
]


@dataclass
class GameEvent:
    """Represents a single parsed event from a SC2 game log."""

    timestamp: float  # game time in seconds
    event_type: str  # e.g. "unit_created", "building_started", "attack"
    subject: str  # unit / building name
    value: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        base = f"[{self.timestamp:.1f}s] {self.event_type}: {self.subject}"
        if self.value is not None:
            base += f" (value={self.value})"
        return base


@dataclass
class GameAnalysis:
    """Result of analysing a complete game log."""

    strategy: str
    confidence: float
    race: str
    win_probability: float
    events_parsed: int
    suggestions: List[str]
    build_order: List[str]
    sentiment: str  # "positive" | "neutral" | "negative"
    raw_text_preview: str


# ---------------------------------------------------------------------------
# SC2TextEncoder
# ---------------------------------------------------------------------------


class SC2TextEncoder:
    """
    Converts raw SC2 game log text / event lists into a normalised string
    suitable for NLP models, and provides simple tokenisation.
    """

    # Canonical unit/building name normalisation map
    UNIT_ALIASES: Dict[str, str] = {
        "lair": "lair_structure",
        "hive": "hive_structure",
        "spawning pool": "spawning_pool",
        "roach warren": "roach_warren",
        "baneling nest": "baneling_nest",
        "hydralisk den": "hydralisk_den",
        "barracks": "barracks_structure",
        "factory": "factory_structure",
        "starport": "starport_structure",
        "gateway": "gateway_structure",
        "cybernetics core": "cybernetics_core",
        "dark shrine": "dark_shrine",
        "fleet beacon": "fleet_beacon",
        "robo bay": "robotics_bay",
        "robo facility": "robotics_facility",
        "zergling": "zergling_unit",
        "marine": "marine_unit",
        "zealot": "zealot_unit",
        "stalker": "stalker_unit",
        "mutalisk": "mutalisk_unit",
        "banshee": "banshee_unit",
        "reaper": "reaper_unit",
    }

    SC2_VOCAB: List[str] = [
        "<PAD>",
        "<UNK>",
        "<SOS>",
        "<EOS>",
        # Events
        "unit_created",
        "building_started",
        "building_complete",
        "attack_started",
        "attack_complete",
        "expansion_taken",
        "worker_killed",
        "army_killed",
        "game_won",
        "game_lost",
        # Units & structures (abbreviated)
        "drone",
        "scv",
        "probe",
        "queen",
        "orbital_command",
        "nexus",
        "command_center",
        "hatchery",
        "zergling_unit",
        "marine_unit",
        "zealot_unit",
        "stalker_unit",
        "mutalisk_unit",
        "banshee_unit",
        "reaper_unit",
        "spawning_pool",
        "barracks_structure",
        "gateway_structure",
        "lair_structure",
        "hive_structure",
        "cybernetics_core",
        "dark_shrine",
        "fleet_beacon",
        "robotics_facility",
        "robotics_bay",
        "hydralisk_den",
        "roach_warren",
        "baneling_nest",
        # Resources
        "minerals",
        "gas",
        "supply",
        "worker_count",
        "army_supply",
        # Strategy tokens
        "rush",
        "expand",
        "tech",
        "harass",
        "defend",
        "all_in",
        "timing",
        "deathball",
        "macro",
        "micro",
    ]

    def __init__(self) -> None:
        self.token2id: Dict[str, int] = {
            tok: idx for idx, tok in enumerate(self.SC2_VOCAB)
        }
        self.id2token: Dict[int, str] = {v: k for k, v in self.token2id.items()}
        self.pad_id = self.token2id["<PAD>"]
        self.unk_id = self.token2id["<UNK>"]

    def normalise(self, text: str) -> str:
        """Lower-case and normalise unit/building aliases."""
        text = text.lower()
        for alias, canonical in self.UNIT_ALIASES.items():
            text = text.replace(alias, canonical)
        # Remove timestamps like [123.4s] or (1:23)
        text = re.sub(r"\[\d+\.?\d*s\]", "", text)
        text = re.sub(r"\(\d+:\d+\)", "", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def tokenize(self, text: str) -> List[str]:
        """Split normalised text into tokens."""
        normalised = self.normalise(text)
        tokens = re.findall(r"[a-z0-9_]+", normalised)
        return tokens

    def encode(self, text: str, max_length: int = 128) -> List[int]:
        """Convert text to integer token IDs, padded to max_length."""
        tokens = self.tokenize(text)[:max_length]
        ids = [self.token2id.get(t, self.unk_id) for t in tokens]
        ids += [self.pad_id] * (max_length - len(ids))
        return ids

    def events_to_text(self, events: List[GameEvent]) -> str:
        """Serialise a list of GameEvents to a single readable string."""
        parts = [str(e) for e in events]
        return " | ".join(parts)

    def parse_log_line(self, line: str) -> Optional[GameEvent]:
        """
        Parse one line of a structured SC2 log into a GameEvent.
        Expected format:
          [<seconds>s] <event_type>: <subject> [value=<float>]
        """
        m = re.match(
            r"\[(\d+\.?\d*)s\]\s+(\w+):\s+([^(]+?)(?:\s+\(value=([\d.]+)\))?$",
            line.strip(),
        )
        if not m:
            return None
        return GameEvent(
            timestamp=float(m.group(1)),
            event_type=m.group(2),
            subject=m.group(3).strip(),
            value=float(m.group(4)) if m.group(4) else None,
        )


# ---------------------------------------------------------------------------
# StrategyClassifier
# ---------------------------------------------------------------------------


class StrategyClassifier:
    """
    Classifies a game log text into one of STRATEGY_LABELS.

    Uses HuggingFace zero-shot classification when available,
    otherwise falls back to keyword-based scoring.
    """

    KEYWORD_WEIGHTS: Dict[str, Dict[str, float]] = {
        "early_aggression": {
            "zergling": 2.0,
            "reaper": 2.0,
            "zealot": 1.5,
            "rush": 3.0,
            "early": 1.5,
            "pool": 1.0,
            "6pool": 4.0,
            "proxy": 2.5,
        },
        "macro_economy": {
            "expand": 2.5,
            "hatchery": 2.0,
            "nexus": 2.0,
            "command_center": 2.0,
            "drone": 1.5,
            "worker": 1.5,
            "saturation": 2.0,
            "macro": 3.0,
        },
        "tech_rush": {
            "lair": 2.0,
            "spire": 3.0,
            "dark_shrine": 3.5,
            "tech": 2.0,
            "mutalisk": 2.5,
            "banshee": 3.0,
            "void_ray": 3.0,
            "lurker": 2.5,
        },
        "defensive_turtle": {
            "bunker": 3.0,
            "spine": 3.0,
            "shield_battery": 3.0,
            "cannon": 2.5,
            "defend": 2.0,
            "wall": 2.0,
            "turtle": 3.5,
        },
        "timing_attack": {
            "timing": 3.0,
            "push": 2.0,
            "window": 2.5,
            "before": 1.5,
            "attack": 1.5,
            "3rax": 3.5,
            "2base": 2.0,
        },
        "all_in": {
            "all_in": 4.0,
            "no_expand": 3.0,
            "cheese": 3.0,
            "proxy": 2.5,
            "cannon_rush": 4.0,
            "4gate": 3.5,
            "mass": 1.5,
        },
        "harassment": {
            "harass": 3.0,
            "worker_kill": 2.5,
            "multi": 2.0,
            "drop": 2.5,
            "banshee": 2.0,
            "hellion": 2.0,
            "oracle": 2.5,
            "adept": 2.0,
        },
        "late_game_deathball": {
            "max": 2.5,
            "200_200": 3.5,
            "deathball": 4.0,
            "siege": 2.5,
            "carrier": 3.0,
            "brood_lord": 3.0,
            "thor": 2.5,
            "late": 1.5,
        },
    }

    def __init__(self) -> None:
        self._pipeline = None
        if HF_AVAILABLE:
            try:
                self._pipeline = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                    device=-1,  # CPU; set to 0 for GPU
                )
                log.info("Zero-shot classification pipeline loaded.")
            except Exception as exc:
                log.warning("Could not load zero-shot pipeline: %s", exc)

    def classify(self, text: str) -> Tuple[str, float]:
        """
        Returns (strategy_label, confidence_score).
        confidence is in [0, 1].
        """
        if self._pipeline is not None:
            return self._classify_neural(text)
        return self._classify_keywords(text)

    def _classify_neural(self, text: str) -> Tuple[str, float]:
        # Truncate to avoid model token limits
        truncated = text[:1024]
        result = self._pipeline(
            truncated,
            candidate_labels=[label.replace("_", " ") for label in STRATEGY_LABELS],
        )
        label_str: str = result["labels"][0].replace(" ", "_")
        score: float = float(result["scores"][0])
        return label_str, score

    def _classify_keywords(self, text: str) -> Tuple[str, float]:
        text_lower = text.lower()
        scores: Dict[str, float] = {label: 0.0 for label in STRATEGY_LABELS}
        for label, kw_map in self.KEYWORD_WEIGHTS.items():
            for keyword, weight in kw_map.items():
                count = text_lower.count(keyword.replace("_", " "))
                count += text_lower.count(keyword)
                scores[label] += count * weight
        total = sum(scores.values()) or 1.0
        best_label = max(scores, key=lambda k: scores[k])
        confidence = scores[best_label] / total
        return best_label, min(confidence * 2.0, 1.0)  # normalise

    def detect_race(self, text: str) -> str:
        """Heuristic race detection from log text."""
        text_lower = text.lower()
        race_keywords = {
            "Zerg": ["zerg", "hatchery", "drone", "zergling", "queen", "lair", "hive"],
            "Terran": [
                "terran",
                "barracks",
                "scv",
                "marine",
                "factory",
                "command center",
            ],
            "Protoss": [
                "protoss",
                "nexus",
                "probe",
                "zealot",
                "gateway",
                "cybernetics",
            ],
        }
        race_scores = {race: 0 for race in race_keywords}
        for race, keywords in race_keywords.items():
            for kw in keywords:
                race_scores[race] += text_lower.count(kw)
        best_race = max(race_scores, key=lambda r: race_scores[r])
        return best_race if race_scores[best_race] > 0 else "Unknown"


# ---------------------------------------------------------------------------
# SC2Coach
# ---------------------------------------------------------------------------


class SC2Coach:
    """
    High-level coaching interface.

    Methods
    -------
    analyze_game(log_text) -> GameAnalysis
    suggest_improvement(analysis) -> List[str]
    generate_build_order_description(race, strategy) -> str
    """

    def __init__(self) -> None:
        self.encoder = SC2TextEncoder()
        self.classifier = StrategyClassifier()
        self._sentiment_pipe = None
        if HF_AVAILABLE:
            try:
                self._sentiment_pipe = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english",
                    device=-1,
                )
                log.info("Sentiment analysis pipeline loaded.")
            except Exception as exc:
                log.warning("Could not load sentiment pipeline: %s", exc)

    # ------------------------------------------------------------------
    def analyze_game(
        self,
        log_text: str,
        *,
        player_name: str = "Player",
        lang: str = "en",
    ) -> GameAnalysis:
        """
        Full analysis pipeline:
        1. Normalise & tokenise the log.
        2. Classify strategy and detect race.
        3. Estimate win probability.
        4. Detect sentiment.
        5. Build suggestions and build order.
        """
        normalised = self.encoder.normalise(log_text)
        tokens = self.encoder.tokenize(log_text)
        event_count = log_text.count("[")  # rough proxy for event lines

        strategy, confidence = self.classifier.classify(normalised)
        race = self.classifier.detect_race(normalised)

        win_prob = self._estimate_win_probability(log_text, strategy)
        sentiment = self._analyze_sentiment(log_text)
        suggestions = self.suggest_improvement(
            strategy=strategy,
            race=race,
            win_prob=win_prob,
            lang=lang,
        )
        build_order = self._get_build_order(race, strategy)

        return GameAnalysis(
            strategy=strategy,
            confidence=confidence,
            race=race,
            win_probability=win_prob,
            events_parsed=event_count,
            suggestions=suggestions,
            build_order=build_order,
            sentiment=sentiment,
            raw_text_preview=log_text[:200] + ("..." if len(log_text) > 200 else ""),
        )

    # ------------------------------------------------------------------
    def suggest_improvement(
        self,
        *,
        strategy: str = "macro_economy",
        race: str = "Unknown",
        win_prob: float = 0.5,
        lang: str = "en",
    ) -> List[str]:
        """Return a list of actionable improvement suggestions."""
        suggestions: List[str] = []

        # Strategy-specific advice
        advice = STRATEGY_ADVICE.get(strategy, {})
        if advice:
            suggestions.append(advice.get(lang, advice.get("en", "")))

        # Win-probability-based tips
        if win_prob < 0.35:
            if lang == "ko":
                suggestions.append(
                    "승률이 낮습니다. 경제 효율성과 초반 실수를 집중적으로 검토하세요."
                )
            else:
                suggestions.append(
                    "Win probability is low. Review economy efficiency and early-game mistakes."
                )
        elif win_prob > 0.65:
            if lang == "ko":
                suggestions.append(
                    "좋은 위치입니다! 우위를 유지하고 상대가 따라잡지 못하게 압박하세요."
                )
            else:
                suggestions.append(
                    "Strong position! Maintain pressure and don't let the opponent equalise."
                )

        # Generic rotating tip
        import random

        tip = random.choice(IMPROVEMENT_TIPS)
        if tip not in suggestions:
            suggestions.append(tip)

        return suggestions

    # ------------------------------------------------------------------
    def generate_build_order_description(self, race: str, strategy: str) -> str:
        """
        Return a human-readable description of a build order
        for the given race + strategy combination.
        """
        steps = self._get_build_order(race, strategy)
        if not steps:
            return f"No build order template available for {race} {strategy}."

        lines = [f"--- {race} / {strategy.replace('_', ' ').title()} ---"]
        for i, step in enumerate(steps, 1):
            lines.append(f"  {i:>2}. {step}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_win_probability(self, log_text: str, strategy: str) -> float:
        """Heuristic win probability estimation from log content."""
        text_lower = log_text.lower()
        score = 0.5

        # Positive indicators
        positive_kw = [
            ("game_won", +0.30),
            ("win", +0.15),
            ("victory", +0.20),
            ("opponent killed", +0.10),
            ("승리", +0.20),
        ]
        # Negative indicators
        negative_kw = [
            ("game_lost", -0.30),
            ("defeat", -0.20),
            ("loss", -0.10),
            ("gg", -0.05),
            ("패배", -0.20),
        ]

        for kw, delta in positive_kw + negative_kw:
            if kw in text_lower:
                score += delta

        # Strategy coherence bonus
        strategy_coherence = {
            "early_aggression": 0.02,
            "macro_economy": 0.05,
            "tech_rush": 0.01,
        }
        score += strategy_coherence.get(strategy, 0.0)

        return max(0.0, min(1.0, score))

    def _analyze_sentiment(self, log_text: str) -> str:
        if self._sentiment_pipe is not None:
            try:
                result = self._sentiment_pipe(log_text[:512])[0]
                label = result["label"].upper()
                if label == "POSITIVE":
                    return "positive"
                elif label == "NEGATIVE":
                    return "negative"
                return "neutral"
            except Exception:
                pass
        # Keyword fallback
        text_lower = log_text.lower()
        pos = sum(
            text_lower.count(w) for w in ["win", "victory", "승리", "good", "great"]
        )
        neg = sum(
            text_lower.count(w) for w in ["loss", "defeat", "패배", "bad", "mistake"]
        )
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

    def _get_build_order(self, race: str, strategy: str) -> List[str]:
        race_builds = BUILD_ORDER_TEMPLATES.get(race, {})
        if not race_builds:
            # Try the closest-matching race
            for r in BUILD_ORDER_TEMPLATES:
                if r.lower() in race.lower():
                    race_builds = BUILD_ORDER_TEMPLATES[r]
                    break
        steps = race_builds.get(strategy, [])
        if not steps:
            # Fall back to macro_economy for that race
            steps = race_builds.get("macro_economy", [])
        return steps

    # ------------------------------------------------------------------
    def print_analysis_report(self, analysis: GameAnalysis, lang: str = "en") -> None:
        """Pretty-print a GameAnalysis to stdout."""
        sep = "=" * 60
        print(sep)
        print("  SC2 NLP Coach — Game Analysis Report")
        print(sep)
        print(f"  Race detected    : {analysis.race}")
        print(f"  Strategy         : {analysis.strategy.replace('_', ' ').title()}")
        print(f"  Confidence       : {analysis.confidence:.1%}")
        print(f"  Win probability  : {analysis.win_probability:.1%}")
        print(f"  Sentiment        : {analysis.sentiment}")
        print(f"  Events parsed    : {analysis.events_parsed}")
        print()
        print("  Log preview:")
        print(f"    {analysis.raw_text_preview}")
        print()
        print("  Build Order:")
        for i, step in enumerate(analysis.build_order, 1):
            print(f"    {i:>2}. {step}")
        print()
        print("  Suggestions:")
        for i, tip in enumerate(analysis.suggestions, 1):
            print(f"    {i}. {tip}")
        print(sep)


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

SAMPLE_GAME_LOG = """
[0.0s] game_start: ZvT_Ladder_Match
[12.0s] unit_created: Drone (value=13)
[15.5s] building_started: Spawning Pool
[16.0s] unit_created: Drone (value=14)
[21.0s] building_complete: Spawning Pool
[22.0s] unit_created: Zergling (value=2)
[22.0s] unit_created: Zergling (value=2)
[24.0s] attack_started: Zergling rush towards enemy base
[35.0s] unit_created: Zergling (value=4)
[40.0s] attack_complete: Worker killed opponent_worker (value=3)
[45.0s] unit_created: Queen
[50.0s] building_started: Hatchery (natural expansion)
[65.0s] game_won: Victory against Terran opponent
"""

SAMPLE_GAME_LOG_KO = """
[0.0s] game_start: ZvP_래더_경기
[13.0s] unit_created: 드론 (value=13)
[17.0s] building_started: 산란못
[20.0s] unit_created: 저글링 (value=4)
[25.0s] attack_started: 저글링 러시 — 상대 본진 공격
[38.0s] attack_complete: 일꾼 3마리 처치 (value=3)
[50.0s] unit_created: 여왕 (value=1)
[60.0s] building_started: 부화장 (앞마당)
[80.0s] game_won: 승리 — 프로토스 상대 조기 러시 성공
"""


def main() -> None:
    print("\n[SC2 NLP Coach — Phase 582]\n")

    coach = SC2Coach()
    encoder = SC2TextEncoder()

    # ---- English log analysis ----
    print("Encoding sample English log...")
    ids = encoder.encode(SAMPLE_GAME_LOG)
    print(f"  Token IDs (first 20): {ids[:20]}")
    print()

    analysis_en = coach.analyze_game(
        SAMPLE_GAME_LOG,
        player_name="ZergPlayer",
        lang="en",
    )
    coach.print_analysis_report(analysis_en, lang="en")

    # ---- Korean log analysis ----
    print("\nKorean log analysis (한국어 로그 분석)...")
    analysis_ko = coach.analyze_game(
        SAMPLE_GAME_LOG_KO,
        player_name="저그플레이어",
        lang="ko",
    )
    coach.print_analysis_report(analysis_ko, lang="ko")

    # ---- Build order description ----
    print("\nBuild Order Description:")
    bo_desc = coach.generate_build_order_description("Zerg", "early_aggression")
    print(bo_desc)

    bo_desc_p = coach.generate_build_order_description("Protoss", "tech_rush")
    print(bo_desc_p)

    # ---- Serialise analysis to JSON ----
    result_dict = {
        "strategy": analysis_en.strategy,
        "confidence": round(analysis_en.confidence, 4),
        "race": analysis_en.race,
        "win_probability": round(analysis_en.win_probability, 4),
        "sentiment": analysis_en.sentiment,
        "suggestions": analysis_en.suggestions,
        "build_order": analysis_en.build_order,
    }
    print("\nJSON output:")
    print(json.dumps(result_dict, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
