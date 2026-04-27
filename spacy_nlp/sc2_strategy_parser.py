# Phase 590: spaCy
"""
sc2_strategy_parser.py — StarCraft II Strategy Text Parser with spaCy
Parses strategy guides, game chat, and build-order descriptions into
structured data using custom NER, rule-based matching, dependency parsing,
and sentence similarity.

Graceful fallback to regex-based parsing when spaCy is absent.
"""

from __future__ import annotations

import json
import logging
import re
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_strategy_parser")

# ---------------------------------------------------------------------------
# Optional spaCy import — graceful fallback
# ---------------------------------------------------------------------------
try:
    import spacy
    from spacy.language import Language
    from spacy.matcher import Matcher, PhraseMatcher
    from spacy.tokens import Doc, Span, Token
    from spacy.training import Example
    from spacy.util import minibatch, compounding

    SPACY_AVAILABLE = True
    log.info("spaCy %s available.", spacy.__version__)
except ImportError:
    SPACY_AVAILABLE = False
    log.warning(
        "spaCy not installed. Running regex-based fallback. "
        "Install with: pip install spacy && python -m spacy download en_core_web_sm"
    )

# ---------------------------------------------------------------------------
# SC2 unit / building / strategy knowledge base
# ---------------------------------------------------------------------------

SC2_UNITS: Dict[str, Dict[str, Any]] = {
    # Zerg
    "zergling": {
        "race": "zerg",
        "tier": 1,
        "type": "unit",
        "supply": 0.5,
        "minerals": 25,
        "gas": 0,
    },
    "baneling": {
        "race": "zerg",
        "tier": 1,
        "type": "unit",
        "supply": 0.5,
        "minerals": 25,
        "gas": 25,
    },
    "roach": {
        "race": "zerg",
        "tier": 1,
        "type": "unit",
        "supply": 2,
        "minerals": 75,
        "gas": 25,
    },
    "ravager": {
        "race": "zerg",
        "tier": 2,
        "type": "unit",
        "supply": 3,
        "minerals": 75,
        "gas": 75,
    },
    "hydralisk": {
        "race": "zerg",
        "tier": 2,
        "type": "unit",
        "supply": 2,
        "minerals": 100,
        "gas": 50,
    },
    "lurker": {
        "race": "zerg",
        "tier": 3,
        "type": "unit",
        "supply": 3,
        "minerals": 50,
        "gas": 100,
    },
    "mutalisk": {
        "race": "zerg",
        "tier": 2,
        "type": "unit",
        "supply": 2,
        "minerals": 100,
        "gas": 100,
    },
    "corruptor": {
        "race": "zerg",
        "tier": 2,
        "type": "unit",
        "supply": 2,
        "minerals": 150,
        "gas": 100,
    },
    "brood lord": {
        "race": "zerg",
        "tier": 3,
        "type": "unit",
        "supply": 4,
        "minerals": 150,
        "gas": 150,
    },
    "infestor": {
        "race": "zerg",
        "tier": 2,
        "type": "unit",
        "supply": 2,
        "minerals": 100,
        "gas": 150,
    },
    "swarm host": {
        "race": "zerg",
        "tier": 2,
        "type": "unit",
        "supply": 3,
        "minerals": 100,
        "gas": 75,
    },
    "ultralisk": {
        "race": "zerg",
        "tier": 3,
        "type": "unit",
        "supply": 6,
        "minerals": 275,
        "gas": 200,
    },
    "viper": {
        "race": "zerg",
        "tier": 3,
        "type": "unit",
        "supply": 3,
        "minerals": 100,
        "gas": 200,
    },
    "queen": {
        "race": "zerg",
        "tier": 1,
        "type": "unit",
        "supply": 2,
        "minerals": 150,
        "gas": 0,
    },
    "overlord": {
        "race": "zerg",
        "tier": 1,
        "type": "unit",
        "supply": 0,
        "minerals": 100,
        "gas": 0,
    },
    "overseer": {
        "race": "zerg",
        "tier": 2,
        "type": "unit",
        "supply": 0,
        "minerals": 50,
        "gas": 50,
    },
    "drone": {
        "race": "zerg",
        "tier": 1,
        "type": "unit",
        "supply": 1,
        "minerals": 50,
        "gas": 0,
    },
    # Terran
    "marine": {
        "race": "terran",
        "tier": 1,
        "type": "unit",
        "supply": 1,
        "minerals": 50,
        "gas": 0,
    },
    "marauder": {
        "race": "terran",
        "tier": 1,
        "type": "unit",
        "supply": 2,
        "minerals": 100,
        "gas": 25,
    },
    "medivac": {
        "race": "terran",
        "tier": 2,
        "type": "unit",
        "supply": 2,
        "minerals": 100,
        "gas": 100,
    },
    "siege tank": {
        "race": "terran",
        "tier": 2,
        "type": "unit",
        "supply": 3,
        "minerals": 150,
        "gas": 125,
    },
    "hellion": {
        "race": "terran",
        "tier": 1,
        "type": "unit",
        "supply": 2,
        "minerals": 100,
        "gas": 0,
    },
    "thor": {
        "race": "terran",
        "tier": 3,
        "type": "unit",
        "supply": 6,
        "minerals": 300,
        "gas": 200,
    },
    "banshee": {
        "race": "terran",
        "tier": 2,
        "type": "unit",
        "supply": 3,
        "minerals": 150,
        "gas": 100,
    },
    "battlecruiser": {
        "race": "terran",
        "tier": 3,
        "type": "unit",
        "supply": 6,
        "minerals": 400,
        "gas": 300,
    },
    # Protoss
    "zealot": {
        "race": "protoss",
        "tier": 1,
        "type": "unit",
        "supply": 2,
        "minerals": 100,
        "gas": 0,
    },
    "stalker": {
        "race": "protoss",
        "tier": 1,
        "type": "unit",
        "supply": 2,
        "minerals": 125,
        "gas": 50,
    },
    "adept": {
        "race": "protoss",
        "tier": 1,
        "type": "unit",
        "supply": 2,
        "minerals": 100,
        "gas": 25,
    },
    "immortal": {
        "race": "protoss",
        "tier": 2,
        "type": "unit",
        "supply": 4,
        "minerals": 275,
        "gas": 100,
    },
    "colossus": {
        "race": "protoss",
        "tier": 3,
        "type": "unit",
        "supply": 6,
        "minerals": 300,
        "gas": 200,
    },
    "void ray": {
        "race": "protoss",
        "tier": 2,
        "type": "unit",
        "supply": 4,
        "minerals": 250,
        "gas": 150,
    },
    "carrier": {
        "race": "protoss",
        "tier": 3,
        "type": "unit",
        "supply": 6,
        "minerals": 350,
        "gas": 250,
    },
    "archon": {
        "race": "protoss",
        "tier": 2,
        "type": "unit",
        "supply": 4,
        "minerals": 0,
        "gas": 0,
    },
}

SC2_BUILDINGS: Dict[str, Dict[str, Any]] = {
    # Zerg
    "hatchery": {"race": "zerg", "tier": 1, "minerals": 300, "gas": 0},
    "lair": {"race": "zerg", "tier": 2, "minerals": 150, "gas": 100},
    "hive": {"race": "zerg", "tier": 3, "minerals": 200, "gas": 150},
    "spawning pool": {"race": "zerg", "tier": 1, "minerals": 200, "gas": 0},
    "roach warren": {"race": "zerg", "tier": 1, "minerals": 150, "gas": 0},
    "baneling nest": {"race": "zerg", "tier": 1, "minerals": 100, "gas": 50},
    "hydralisk den": {"race": "zerg", "tier": 2, "minerals": 100, "gas": 100},
    "lurker den": {"race": "zerg", "tier": 3, "minerals": 100, "gas": 150},
    "spire": {"race": "zerg", "tier": 2, "minerals": 200, "gas": 200},
    "greater spire": {"race": "zerg", "tier": 3, "minerals": 100, "gas": 150},
    "infestation pit": {"race": "zerg", "tier": 2, "minerals": 100, "gas": 100},
    "ultralisk cavern": {"race": "zerg", "tier": 3, "minerals": 150, "gas": 200},
    "evolution chamber": {"race": "zerg", "tier": 1, "minerals": 75, "gas": 0},
    "extractor": {"race": "zerg", "tier": 1, "minerals": 25, "gas": 0},
    "spine crawler": {"race": "zerg", "tier": 1, "minerals": 100, "gas": 0},
    "spore crawler": {"race": "zerg", "tier": 1, "minerals": 75, "gas": 0},
    "nydus network": {"race": "zerg", "tier": 2, "minerals": 150, "gas": 200},
    # Terran
    "command center": {"race": "terran", "tier": 1, "minerals": 400, "gas": 0},
    "barracks": {"race": "terran", "tier": 1, "minerals": 150, "gas": 0},
    "factory": {"race": "terran", "tier": 2, "minerals": 150, "gas": 100},
    "starport": {"race": "terran", "tier": 2, "minerals": 150, "gas": 100},
    "bunker": {"race": "terran", "tier": 1, "minerals": 100, "gas": 0},
    # Protoss
    "nexus": {"race": "protoss", "tier": 1, "minerals": 400, "gas": 0},
    "gateway": {"race": "protoss", "tier": 1, "minerals": 150, "gas": 0},
    "robotics facility": {"race": "protoss", "tier": 2, "minerals": 200, "gas": 100},
    "stargate": {"race": "protoss", "tier": 2, "minerals": 150, "gas": 150},
    "forge": {"race": "protoss", "tier": 1, "minerals": 150, "gas": 0},
}

SC2_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "12 pool": {"race": "zerg", "category": "rush", "timing": "early"},
    "13 pool": {"race": "zerg", "category": "rush", "timing": "early"},
    "hatch first": {"race": "zerg", "category": "macro", "timing": "early"},
    "pool first": {"race": "zerg", "category": "aggression", "timing": "early"},
    "ling flood": {"race": "zerg", "category": "all-in", "timing": "early"},
    "roach rush": {"race": "zerg", "category": "rush", "timing": "early"},
    "roach ravager": {"race": "zerg", "category": "timing", "timing": "mid"},
    "ling bane": {"race": "zerg", "category": "composition", "timing": "mid"},
    "muta ling bane": {"race": "zerg", "category": "composition", "timing": "mid"},
    "hydra lurker": {"race": "zerg", "category": "composition", "timing": "mid"},
    "swarm host nydus": {"race": "zerg", "category": "cheese", "timing": "mid"},
    "brood lord viper": {"race": "zerg", "category": "composition", "timing": "late"},
    "ultra ling": {"race": "zerg", "category": "composition", "timing": "late"},
    "proxy hatch": {"race": "zerg", "category": "cheese", "timing": "early"},
    "two base muta": {"race": "zerg", "category": "timing", "timing": "mid"},
    "three hatch before pool": {
        "race": "zerg",
        "category": "greedy",
        "timing": "early",
    },
    "cannon rush": {"race": "protoss", "category": "cheese", "timing": "early"},
    "four gate": {"race": "protoss", "category": "all-in", "timing": "early"},
    "marine push": {"race": "terran", "category": "timing", "timing": "early"},
    "bio": {"race": "terran", "category": "composition", "timing": "mid"},
    "mech": {"race": "terran", "category": "composition", "timing": "mid"},
}

TIMING_MARKERS = [
    "early game",
    "mid game",
    "late game",
    "before",
    "after",
    "then",
    "first",
    "next",
    "when",
    "at",
    "once",
    "as soon as",
    "immediately",
    "@",
    "supply",
    "timing",
    "push",
    "all-in",
]

ACTION_VERBS = [
    "build",
    "make",
    "train",
    "produce",
    "morph",
    "attack",
    "push",
    "rush",
    "harass",
    "defend",
    "expand",
    "scout",
    "research",
    "upgrade",
    "tech",
    "transition",
    "rally",
    "retreat",
    "flank",
    "contain",
    "drop",
    "nydus",
    "creep",
    "inject",
    "spread",
    "mass",
    "spam",
    "stack",
    "split",
    "surround",
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SC2Entity:
    """A recognized SC2 entity in text."""

    text: str
    label: str  # UNIT, BUILDING, STRATEGY, TIMING, ACTION, QUANTITY
    start_char: int
    end_char: int
    linked_id: Optional[str] = None  # key into SC2_UNITS / SC2_BUILDINGS
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "label": self.label,
            "start": self.start_char,
            "end": self.end_char,
            "linked_id": self.linked_id,
            "metadata": self.metadata,
        }


@dataclass
class ParsedCommand:
    """A single extracted command from strategy text."""

    action: str
    target: Optional[str] = None
    quantity: Optional[int] = None
    timing: Optional[str] = None
    condition: Optional[str] = None
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "quantity": self.quantity,
            "timing": self.timing,
            "condition": self.condition,
            "priority": self.priority,
        }


@dataclass
class ParsedStrategy:
    """Full parsed strategy document."""

    raw_text: str
    entities: List[SC2Entity] = field(default_factory=list)
    commands: List[ParsedCommand] = field(default_factory=list)
    classification: Optional[str] = None
    race: Optional[str] = None
    timing: Optional[str] = None
    confidence: float = 0.0
    text_hash: str = ""

    def __post_init__(self):
        self.text_hash = hashlib.md5(self.raw_text.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "text_hash": self.text_hash,
            "entities": [e.to_dict() for e in self.entities],
            "commands": [c.to_dict() for c in self.commands],
            "classification": self.classification,
            "race": self.race,
            "timing": self.timing,
            "confidence": self.confidence,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Text preprocessor
# ---------------------------------------------------------------------------


class SC2TextPreprocessor:
    """Clean and normalise SC2 game chat / strategy guide text."""

    # Common abbreviations in SC2 community
    ABBREVIATIONS: Dict[str, str] = {
        "lings": "zerglings",
        "ling": "zergling",
        "banes": "banelings",
        "bane": "baneling",
        "hydras": "hydralisks",
        "hydra": "hydralisk",
        "mutas": "mutalisks",
        "muta": "mutalisk",
        "ultras": "ultralisks",
        "ultra": "ultralisk",
        "rax": "barracks",
        "cc": "command center",
        "nat": "natural expansion",
        "3rd": "third base",
        "4th": "fourth base",
        "SH": "swarm host",
        "BL": "brood lord",
        "robo": "robotics facility",
        "immo": "immortal",
        "dt": "dark templar",
        "HT": "high templar",
        "BC": "battlecruiser",
        "evo": "evolution chamber",
        "evo chamber": "evolution chamber",
        "RW": "roach warren",
        "SP": "spawning pool",
        "infestation pit": "infestation pit",
    }

    # Regex patterns for cleaning
    _RE_MULTI_SPACE = re.compile(r"\s+")
    _RE_GAME_TIME = re.compile(r"(\d{1,2}):(\d{2})")
    _RE_SUPPLY_COUNT = re.compile(r"@(\d+)\s*supply")
    _RE_AT_NOTATION = re.compile(r"@(\d+)")

    @classmethod
    def preprocess(cls, text: str) -> str:
        """Full preprocessing pipeline."""
        text = text.lower().strip()
        text = cls._normalize_unicode(text)
        text = cls._expand_abbreviations(text)
        text = cls._normalize_game_times(text)
        text = cls._normalize_supply_notations(text)
        text = cls._clean_whitespace(text)
        return text

    @classmethod
    def _normalize_unicode(cls, text: str) -> str:
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        return text

    @classmethod
    def _expand_abbreviations(cls, text: str) -> str:
        for abbr, full in cls.ABBREVIATIONS.items():
            pattern = re.compile(r"\b" + re.escape(abbr) + r"\b", re.IGNORECASE)
            text = pattern.sub(full, text)
        return text

    @classmethod
    def _normalize_game_times(cls, text: str) -> str:
        def _replace(m):
            minutes, seconds = int(m.group(1)), int(m.group(2))
            total = minutes * 60 + seconds
            return f"[time:{total}s]"

        return cls._RE_GAME_TIME.sub(_replace, text)

    @classmethod
    def _normalize_supply_notations(cls, text: str) -> str:
        text = cls._RE_SUPPLY_COUNT.sub(r"[supply:\1]", text)
        text = cls._RE_AT_NOTATION.sub(r"[supply:\1]", text)
        return text

    @classmethod
    def _clean_whitespace(cls, text: str) -> str:
        return cls._RE_MULTI_SPACE.sub(" ", text).strip()


# ---------------------------------------------------------------------------
# Custom spaCy pipeline component: SC2 strategy classifier
# ---------------------------------------------------------------------------

if SPACY_AVAILABLE:

    @Language.factory("sc2_strategy_classifier")
    def create_strategy_classifier(nlp: Language, name: str):
        return SC2StrategyClassifierComponent(nlp)

    class SC2StrategyClassifierComponent:
        """Custom spaCy pipeline component that classifies strategy category."""

        def __init__(self, nlp: Language):
            self.nlp = nlp
            self._categories = [
                "rush",
                "timing",
                "all-in",
                "macro",
                "cheese",
                "composition",
                "greedy",
                "aggression",
            ]
            # Register custom Doc extension
            if not Doc.has_extension("sc2_strategy_category"):
                Doc.set_extension("sc2_strategy_category", default=None)
            if not Doc.has_extension("sc2_strategy_confidence"):
                Doc.set_extension("sc2_strategy_confidence", default=0.0)
            if not Doc.has_extension("sc2_race"):
                Doc.set_extension("sc2_race", default=None)
            if not Doc.has_extension("sc2_timing"):
                Doc.set_extension("sc2_timing", default=None)

        def __call__(self, doc: Doc) -> Doc:
            text_lower = doc.text.lower()
            scores: Dict[str, float] = {c: 0.0 for c in self._categories}

            # Keyword-based scoring
            rush_words = {
                "rush",
                "pool first",
                "12 pool",
                "13 pool",
                "early aggression",
            }
            allin_words = {"all-in", "all in", "flood", "commit", "one base"}
            cheese_words = {"cheese", "proxy", "cannon rush", "nydus", "bunker rush"}
            macro_words = {
                "macro",
                "expand",
                "greedy",
                "economic",
                "hatch first",
                "three base",
            }
            timing_words = {"timing", "push", "attack at", "hit at", "before"}

            for w in rush_words:
                if w in text_lower:
                    scores["rush"] += 2.0
            for w in allin_words:
                if w in text_lower:
                    scores["all-in"] += 2.0
            for w in cheese_words:
                if w in text_lower:
                    scores["cheese"] += 2.0
            for w in macro_words:
                if w in text_lower:
                    scores["macro"] += 2.0
            for w in timing_words:
                if w in text_lower:
                    scores["timing"] += 1.5

            # Race detection
            race = None
            zerg_score = sum(
                1
                for ent_name in SC2_UNITS
                if SC2_UNITS[ent_name]["race"] == "zerg" and ent_name in text_lower
            )
            terran_score = sum(
                1
                for ent_name in SC2_UNITS
                if SC2_UNITS[ent_name]["race"] == "terran" and ent_name in text_lower
            )
            protoss_score = sum(
                1
                for ent_name in SC2_UNITS
                if SC2_UNITS[ent_name]["race"] == "protoss" and ent_name in text_lower
            )
            race_scores = {
                "zerg": zerg_score,
                "terran": terran_score,
                "protoss": protoss_score,
            }
            if max(race_scores.values()) > 0:
                race = max(race_scores, key=race_scores.get)

            # Timing detection
            timing = None
            if any(w in text_lower for w in ["early", "rush", "pool first", "12 pool"]):
                timing = "early"
            elif any(w in text_lower for w in ["mid game", "mid-game", "transition"]):
                timing = "mid"
            elif any(
                w in text_lower
                for w in ["late game", "late-game", "brood lord", "ultralisk"]
            ):
                timing = "late"

            best_cat = max(scores, key=scores.get)
            best_score = scores[best_cat]
            total = sum(scores.values())
            confidence = best_score / total if total > 0 else 0.0

            doc._.sc2_strategy_category = best_cat if best_score > 0 else None
            doc._.sc2_strategy_confidence = round(confidence, 4)
            doc._.sc2_race = race
            doc._.sc2_timing = timing

            return doc


# ---------------------------------------------------------------------------
# NER training data generator
# ---------------------------------------------------------------------------


class SC2TrainingDataGenerator:
    """Generate spaCy-format training data for custom NER on SC2 text."""

    TEMPLATES = [
        "build {quantity} {unit} and attack",
        "open with {building} then make {unit}",
        "go {strategy} into {unit} timing",
        "at {timing} supply start {unit} production",
        "defend with {quantity} {unit} then counter attack",
        "transition to {unit} {unit2} composition",
        "{strategy} is strong against {unit}",
        "after {building} get {quantity} {unit}",
        "use {unit} to harass while building {building}",
        "mass {unit} and push at {timing} supply",
    ]

    @classmethod
    def generate(cls, n_samples: int = 200) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate n_samples training examples with entity annotations."""
        import random

        training_data = []
        unit_names = list(SC2_UNITS.keys())
        building_names = list(SC2_BUILDINGS.keys())
        strategy_names = list(SC2_STRATEGIES.keys())

        for _ in range(n_samples):
            template = random.choice(cls.TEMPLATES)
            entities = []
            text = template

            # Replace placeholders
            if "{quantity}" in text:
                qty = random.randint(2, 20)
                qty_str = str(qty)
                text = text.replace("{quantity}", qty_str, 1)

            if "{unit}" in text:
                unit = random.choice(unit_names)
                text = text.replace("{unit}", unit, 1)

            if "{unit2}" in text:
                unit2 = random.choice(unit_names)
                text = text.replace("{unit2}", unit2, 1)

            if "{building}" in text:
                building = random.choice(building_names)
                text = text.replace("{building}", building, 1)

            if "{strategy}" in text:
                strategy = random.choice(strategy_names)
                text = text.replace("{strategy}", strategy, 1)

            if "{timing}" in text:
                timing = str(random.choice([44, 66, 80, 100, 130, 150, 170, 200]))
                text = text.replace("{timing}", timing, 1)

            # Find entity spans in the generated text
            for unit_name in unit_names:
                for m in re.finditer(re.escape(unit_name), text):
                    entities.append((m.start(), m.end(), "SC2_UNIT"))

            for bld_name in building_names:
                for m in re.finditer(re.escape(bld_name), text):
                    entities.append((m.start(), m.end(), "SC2_BUILDING"))

            for strat_name in strategy_names:
                for m in re.finditer(re.escape(strat_name), text):
                    entities.append((m.start(), m.end(), "SC2_STRATEGY"))

            # Remove overlapping entities (keep longest)
            entities = cls._resolve_overlaps(entities)

            training_data.append((text, {"entities": entities}))

        log.info("Generated %d training samples.", len(training_data))
        return training_data

    @staticmethod
    def _resolve_overlaps(
        entities: List[Tuple[int, int, str]],
    ) -> List[Tuple[int, int, str]]:
        """Remove overlapping entity spans, keeping the longest."""
        if not entities:
            return entities
        sorted_ents = sorted(entities, key=lambda e: (e[0], -(e[1] - e[0])))
        result = [sorted_ents[0]]
        for ent in sorted_ents[1:]:
            prev = result[-1]
            if ent[0] >= prev[1]:
                result.append(ent)
        return result


# ---------------------------------------------------------------------------
# Main parser — StrategyParser
# ---------------------------------------------------------------------------


class StrategyParser:
    """
    Parse SC2 strategy text into structured data using spaCy NLP.

    Features:
     - Custom NER pipeline for SC2 entities
     - Rule-based matching with Matcher / PhraseMatcher
     - Dependency parsing for command extraction
     - Strategy classification pipeline component
     - Sentence similarity for strategy comparison
     - Entity linking to SC2 unit database
     - Export as structured JSON

    Falls back to regex-based parsing when spaCy is unavailable.
    """

    def __init__(self, model_name: str = "en_core_web_sm", use_gpu: bool = False):
        self.preprocessor = SC2TextPreprocessor()
        self._nlp = None
        self._matcher = None
        self._phrase_matcher = None
        self._model_name = model_name
        self._parse_cache: Dict[str, ParsedStrategy] = {}

        if SPACY_AVAILABLE:
            if use_gpu:
                spacy.prefer_gpu()
                log.info("GPU enabled for spaCy.")
            self._init_spacy_pipeline(model_name)
        else:
            log.info("Using regex fallback parser.")

    # ------------------------------------------------------------------ init
    def _init_spacy_pipeline(self, model_name: str) -> None:
        """Initialise the full spaCy pipeline with custom components."""
        try:
            self._nlp = spacy.load(model_name)
            log.info("Loaded spaCy model: %s", model_name)
        except OSError:
            log.warning(
                "Model '%s' not found. Creating blank English model.", model_name
            )
            self._nlp = spacy.blank("en")

        # Add custom pipeline component
        if "sc2_strategy_classifier" not in self._nlp.pipe_names:
            self._nlp.add_pipe("sc2_strategy_classifier", last=True)

        # Initialise rule-based matchers
        self._init_matchers()

        log.info("Pipeline components: %s", self._nlp.pipe_names)

    def _init_matchers(self) -> None:
        """Set up Matcher and PhraseMatcher for SC2 entities."""
        vocab = self._nlp.vocab
        self._matcher = Matcher(vocab)
        self._phrase_matcher = PhraseMatcher(vocab, attr="LOWER")

        # ------ PhraseMatcher: unit names, building names, strategies ------
        unit_patterns = [self._nlp.make_doc(name) for name in SC2_UNITS]
        self._phrase_matcher.add("SC2_UNIT", unit_patterns)

        building_patterns = [self._nlp.make_doc(name) for name in SC2_BUILDINGS]
        self._phrase_matcher.add("SC2_BUILDING", building_patterns)

        strategy_patterns = [self._nlp.make_doc(name) for name in SC2_STRATEGIES]
        self._phrase_matcher.add("SC2_STRATEGY", strategy_patterns)

        # ------ Matcher: structural patterns ------
        # Pattern: NUMBER + UNIT_NAME (e.g., "10 roaches")
        self._matcher.add(
            "QUANTITY_UNIT",
            [
                [{"LIKE_NUM": True}, {"LOWER": {"IN": list(SC2_UNITS.keys())}}],
            ],
        )

        # Pattern: ACTION_VERB + ...
        self._matcher.add(
            "ACTION_COMMAND",
            [
                [
                    {"LOWER": {"IN": ACTION_VERBS}},
                    {"OP": "*"},
                    {"LOWER": {"IN": list(SC2_UNITS.keys())}},
                ],
            ],
        )

        # Pattern: timing "@X supply"
        self._matcher.add(
            "TIMING_SUPPLY",
            [
                [{"TEXT": "@"}, {"LIKE_NUM": True}, {"LOWER": "supply"}],
            ],
        )

        log.info(
            "Matchers initialised with %d unit + %d building + %d strategy phrases.",
            len(SC2_UNITS),
            len(SC2_BUILDINGS),
            len(SC2_STRATEGIES),
        )

    # --------------------------------------------------------------- parsing
    def parse(self, text: str, use_cache: bool = True) -> ParsedStrategy:
        """Parse strategy text into structured ParsedStrategy."""
        preprocessed = self.preprocessor.preprocess(text)
        cache_key = hashlib.md5(preprocessed.encode()).hexdigest()[:16]

        if use_cache and cache_key in self._parse_cache:
            log.debug("Cache hit for text hash %s", cache_key)
            return self._parse_cache[cache_key]

        if SPACY_AVAILABLE and self._nlp is not None:
            result = self._parse_spacy(preprocessed, text)
        else:
            result = self._parse_regex(preprocessed, text)

        if use_cache:
            self._parse_cache[cache_key] = result

        return result

    def _parse_spacy(self, preprocessed: str, raw_text: str) -> ParsedStrategy:
        """Full spaCy-based parsing pipeline."""
        doc = self._nlp(preprocessed)

        # 1) Entity extraction: NER + rule-based matchers
        entities = self._extract_entities(doc)

        # 2) Command extraction via dependency parsing
        commands = self._extract_commands(doc)

        # 3) Strategy classification from custom component
        classification = doc._.sc2_strategy_category
        confidence = doc._.sc2_strategy_confidence
        race = doc._.sc2_race
        timing = doc._.sc2_timing

        result = ParsedStrategy(
            raw_text=raw_text,
            entities=entities,
            commands=commands,
            classification=classification,
            race=race,
            timing=timing,
            confidence=confidence,
        )
        log.info(
            "Parsed strategy: classification=%s, race=%s, timing=%s, "
            "%d entities, %d commands",
            classification,
            race,
            timing,
            len(entities),
            len(commands),
        )
        return result

    def _extract_entities(self, doc: Doc) -> List[SC2Entity]:
        """Extract entities using both NER and rule-based matchers."""
        entities: List[SC2Entity] = []
        seen_spans: set = set()

        # Built-in NER entities
        for ent in doc.ents:
            span_key = (ent.start_char, ent.end_char)
            if span_key not in seen_spans:
                entities.append(
                    SC2Entity(
                        text=ent.text,
                        label=ent.label_,
                        start_char=ent.start_char,
                        end_char=ent.end_char,
                    )
                )
                seen_spans.add(span_key)

        # PhraseMatcher results
        phrase_matches = self._phrase_matcher(doc)
        for match_id, start, end in phrase_matches:
            span = doc[start:end]
            span_key = (span.start_char, span.end_char)
            if span_key in seen_spans:
                continue
            label = self._nlp.vocab.strings[match_id]
            linked_id = span.text.lower()

            metadata = {}
            if label == "SC2_UNIT" and linked_id in SC2_UNITS:
                metadata = SC2_UNITS[linked_id]
            elif label == "SC2_BUILDING" and linked_id in SC2_BUILDINGS:
                metadata = SC2_BUILDINGS[linked_id]
            elif label == "SC2_STRATEGY" and linked_id in SC2_STRATEGIES:
                metadata = SC2_STRATEGIES[linked_id]

            entities.append(
                SC2Entity(
                    text=span.text,
                    label=label,
                    start_char=span.start_char,
                    end_char=span.end_char,
                    linked_id=linked_id,
                    metadata=metadata,
                )
            )
            seen_spans.add(span_key)

        # Matcher results (structural patterns)
        token_matches = self._matcher(doc)
        for match_id, start, end in token_matches:
            span = doc[start:end]
            span_key = (span.start_char, span.end_char)
            if span_key in seen_spans:
                continue
            rule_name = self._nlp.vocab.strings[match_id]
            entities.append(
                SC2Entity(
                    text=span.text,
                    label=rule_name,
                    start_char=span.start_char,
                    end_char=span.end_char,
                )
            )
            seen_spans.add(span_key)

        entities.sort(key=lambda e: e.start_char)
        return entities

    def _extract_commands(self, doc: Doc) -> List[ParsedCommand]:
        """Extract commands using dependency parsing."""
        commands: List[ParsedCommand] = []
        priority = 0

        for sent in doc.sents:
            for token in sent:
                # Look for action verbs as roots or heads
                if token.lemma_.lower() in ACTION_VERBS and token.dep_ in (
                    "ROOT",
                    "conj",
                    "advcl",
                    "xcomp",
                ):
                    action = token.lemma_.lower()
                    target = None
                    quantity = None
                    timing_str = None
                    condition = None

                    # Find direct object (target)
                    for child in token.children:
                        if child.dep_ in ("dobj", "attr", "oprd"):
                            target = child.text.lower()
                            # Check for numeric modifier on the target
                            for sub_child in child.children:
                                if sub_child.dep_ == "nummod" or sub_child.like_num:
                                    try:
                                        quantity = int(sub_child.text)
                                    except ValueError:
                                        pass
                            # If the target itself is a number, look further
                            if child.like_num:
                                try:
                                    quantity = int(child.text)
                                except ValueError:
                                    pass
                                # The actual target is likely the next token
                                for sibling in child.rights:
                                    target = sibling.text.lower()
                                    break

                        # Temporal / conditional modifiers
                        elif child.dep_ in ("advmod", "prep"):
                            subtree_text = " ".join(t.text for t in child.subtree)
                            if any(tw in subtree_text.lower() for tw in TIMING_MARKERS):
                                timing_str = subtree_text
                            else:
                                condition = subtree_text

                    # Entity-link the target
                    if target and target in SC2_UNITS:
                        pass  # already good
                    elif target:
                        # Fuzzy match attempt
                        for unit_name in SC2_UNITS:
                            if target in unit_name or unit_name in target:
                                target = unit_name
                                break

                    commands.append(
                        ParsedCommand(
                            action=action,
                            target=target,
                            quantity=quantity,
                            timing=timing_str,
                            condition=condition,
                            priority=priority,
                        )
                    )
                    priority += 1

        return commands

    # --------------------------------------------------------- regex fallback
    def _parse_regex(self, preprocessed: str, raw_text: str) -> ParsedStrategy:
        """Regex-based fallback when spaCy is unavailable."""
        entities: List[SC2Entity] = []
        commands: List[ParsedCommand] = []

        text_lower = preprocessed.lower()

        # Entity extraction via regex
        for unit_name, info in SC2_UNITS.items():
            for m in re.finditer(r"\b" + re.escape(unit_name) + r"s?\b", text_lower):
                entities.append(
                    SC2Entity(
                        text=m.group(),
                        label="SC2_UNIT",
                        start_char=m.start(),
                        end_char=m.end(),
                        linked_id=unit_name,
                        metadata=info,
                    )
                )

        for bld_name, info in SC2_BUILDINGS.items():
            for m in re.finditer(r"\b" + re.escape(bld_name) + r"s?\b", text_lower):
                entities.append(
                    SC2Entity(
                        text=m.group(),
                        label="SC2_BUILDING",
                        start_char=m.start(),
                        end_char=m.end(),
                        linked_id=bld_name,
                        metadata=info,
                    )
                )

        for strat_name, info in SC2_STRATEGIES.items():
            for m in re.finditer(r"\b" + re.escape(strat_name) + r"\b", text_lower):
                entities.append(
                    SC2Entity(
                        text=m.group(),
                        label="SC2_STRATEGY",
                        start_char=m.start(),
                        end_char=m.end(),
                        linked_id=strat_name,
                        metadata=info,
                    )
                )

        # Command extraction via regex
        cmd_pattern = re.compile(
            r"\b(" + "|".join(re.escape(v) for v in ACTION_VERBS) + r")\b"
            r"\s+(?:(\d+)\s+)?(\w[\w\s]*?)(?:\s+(?:then|and|,)|$)",
            re.IGNORECASE,
        )
        priority = 0
        for m in cmd_pattern.finditer(text_lower):
            action = m.group(1)
            quantity_str = m.group(2)
            target_raw = m.group(3).strip()

            quantity = int(quantity_str) if quantity_str else None
            target = None
            for unit_name in SC2_UNITS:
                if unit_name in target_raw:
                    target = unit_name
                    break
            if target is None:
                for bld_name in SC2_BUILDINGS:
                    if bld_name in target_raw:
                        target = bld_name
                        break
            if target is None:
                target = target_raw

            commands.append(
                ParsedCommand(
                    action=action,
                    target=target,
                    quantity=quantity,
                    priority=priority,
                )
            )
            priority += 1

        # Simple classification
        classification = None
        confidence = 0.0
        if any(w in text_lower for w in ["rush", "12 pool", "13 pool"]):
            classification = "rush"
            confidence = 0.7
        elif any(w in text_lower for w in ["all-in", "all in", "flood"]):
            classification = "all-in"
            confidence = 0.7
        elif any(w in text_lower for w in ["macro", "expand", "greedy"]):
            classification = "macro"
            confidence = 0.6
        elif any(w in text_lower for w in ["cheese", "proxy", "cannon"]):
            classification = "cheese"
            confidence = 0.7

        # Race detection
        race = None
        for entity in entities:
            if entity.metadata and "race" in entity.metadata:
                race = entity.metadata["race"]
                break

        # Timing
        timing = None
        if any(w in text_lower for w in ["early", "rush"]):
            timing = "early"
        elif any(w in text_lower for w in ["mid game", "transition"]):
            timing = "mid"
        elif any(w in text_lower for w in ["late game", "brood lord", "ultralisk"]):
            timing = "late"

        return ParsedStrategy(
            raw_text=raw_text,
            entities=entities,
            commands=commands,
            classification=classification,
            race=race,
            timing=timing,
            confidence=confidence,
        )

    # ---------------------------------------------------- sentence similarity
    def compare_strategies(self, text_a: str, text_b: str) -> Dict[str, Any]:
        """
        Compare two strategy texts using sentence similarity.
        Returns a similarity score and shared entities.
        """
        parsed_a = self.parse(text_a)
        parsed_b = self.parse(text_b)

        if SPACY_AVAILABLE and self._nlp is not None:
            doc_a = self._nlp(self.preprocessor.preprocess(text_a))
            doc_b = self._nlp(self.preprocessor.preprocess(text_b))
            similarity = doc_a.similarity(doc_b)
        else:
            # Jaccard similarity fallback
            tokens_a = set(self.preprocessor.preprocess(text_a).split())
            tokens_b = set(self.preprocessor.preprocess(text_b).split())
            intersection = tokens_a & tokens_b
            union = tokens_a | tokens_b
            similarity = len(intersection) / len(union) if union else 0.0

        # Shared entities
        entities_a = {e.linked_id for e in parsed_a.entities if e.linked_id}
        entities_b = {e.linked_id for e in parsed_b.entities if e.linked_id}
        shared = entities_a & entities_b

        return {
            "similarity": round(similarity, 4),
            "shared_entities": sorted(shared),
            "unique_to_a": sorted(entities_a - entities_b),
            "unique_to_b": sorted(entities_b - entities_a),
            "classification_a": parsed_a.classification,
            "classification_b": parsed_b.classification,
            "same_classification": parsed_a.classification == parsed_b.classification,
        }

    # --------------------------------------------------- NER model training
    def train_custom_ner(
        self,
        training_data: Optional[List[Tuple[str, Dict]]] = None,
        n_iter: int = 30,
        drop: float = 0.35,
        batch_size_range: Tuple[float, float, float] = (4.0, 32.0, 1.001),
    ) -> Optional[Any]:
        """
        Train a custom NER model for SC2 entity recognition.
        Returns the trained nlp object, or None if spaCy is unavailable.
        """
        if not SPACY_AVAILABLE:
            log.warning("Cannot train NER: spaCy not available.")
            return None

        if training_data is None:
            training_data = SC2TrainingDataGenerator.generate(300)

        nlp = spacy.blank("en")

        if "ner" not in nlp.pipe_names:
            ner = nlp.add_pipe("ner", last=True)
        else:
            ner = nlp.get_pipe("ner")

        # Add entity labels
        labels = set()
        for _, annotations in training_data:
            for ent in annotations.get("entities", []):
                labels.add(ent[2])
        for label in labels:
            ner.add_label(label)

        log.info(
            "Training NER with %d samples, %d labels: %s",
            len(training_data),
            len(labels),
            sorted(labels),
        )

        # Training loop
        other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
        with nlp.disable_pipes(*other_pipes):
            optimizer = nlp.begin_training()
            for iteration in range(n_iter):
                losses = {}
                import random as _rng

                _rng.shuffle(training_data)
                batches = minibatch(training_data, size=compounding(*batch_size_range))
                for batch in batches:
                    examples = []
                    for text, annots in batch:
                        doc = nlp.make_doc(text)
                        try:
                            example = Example.from_dict(doc, annots)
                            examples.append(example)
                        except Exception:
                            continue
                    if examples:
                        nlp.update(examples, drop=drop, sgd=optimizer, losses=losses)

                ner_loss = losses.get("ner", 0.0)
                if (iteration + 1) % 5 == 0 or iteration == 0:
                    log.info(
                        "  Iter %3d/%d — NER loss: %.4f",
                        iteration + 1,
                        n_iter,
                        ner_loss,
                    )

        log.info("NER training complete.")
        return nlp

    # ------------------------------------------------------------ entity link
    def link_entity(self, entity_text: str) -> Optional[Dict[str, Any]]:
        """Link raw entity text to SC2 unit database."""
        text = entity_text.lower().strip()

        # Direct match
        if text in SC2_UNITS:
            return {"type": "unit", "id": text, **SC2_UNITS[text]}
        if text in SC2_BUILDINGS:
            return {"type": "building", "id": text, **SC2_BUILDINGS[text]}
        if text in SC2_STRATEGIES:
            return {"type": "strategy", "id": text, **SC2_STRATEGIES[text]}

        # Plural / partial match
        for name, info in SC2_UNITS.items():
            if text.rstrip("s") == name or name in text or text in name:
                return {"type": "unit", "id": name, **info}
        for name, info in SC2_BUILDINGS.items():
            if text.rstrip("s") == name or name in text or text in name:
                return {"type": "building", "id": name, **info}

        return None

    # -------------------------------------------------------- batch parsing
    def parse_batch(self, texts: Sequence[str]) -> List[ParsedStrategy]:
        """Parse multiple strategy texts."""
        return [self.parse(t) for t in texts]

    # ----------------------------------------------------------- export JSON
    def export_strategies(
        self, strategies: Sequence[ParsedStrategy], filepath: Optional[str] = None
    ) -> str:
        """Export parsed strategies as JSON. Optionally write to file."""
        data = [s.to_dict() for s in strategies]
        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
            log.info("Exported %d strategies to %s", len(data), filepath)

        return json_str

    # ----------------------------------------------------------- cache mgmt
    def clear_cache(self) -> int:
        """Clear the parse cache. Returns number of entries removed."""
        count = len(self._parse_cache)
        self._parse_cache.clear()
        log.info("Cleared %d cached parse results.", count)
        return count

    @property
    def cache_size(self) -> int:
        return len(self._parse_cache)


# ---------------------------------------------------------------------------
# Convenience — module-level quick parse
# ---------------------------------------------------------------------------

_default_parser: Optional[StrategyParser] = None


def quick_parse(text: str) -> ParsedStrategy:
    """Parse strategy text with a module-level default parser instance."""
    global _default_parser
    if _default_parser is None:
        _default_parser = StrategyParser()
    return _default_parser.parse(text)


# ---------------------------------------------------------------------------
# CLI / demo
# ---------------------------------------------------------------------------


def _demo() -> None:
    """Run a demonstration of the strategy parser."""
    parser = StrategyParser()

    examples = [
        "Build 10 roaches then attack the natural",
        "Open with hatch first, get ling speed, then transition to muta ling bane",
        "12 pool into ling flood all-in, rally everything across the map",
        "Go roach ravager, push at 66 supply before they get colossus",
        "Defend early marine push with queens and spine crawlers, then counter with hydra lurker",
        "Mass mutas and harass mineral lines while expanding to a 4th base",
        "3:30 pool, @44 supply start zergling production, rally lings to opponent natural",
    ]

    parsed = parser.parse_batch(examples)

    for strategy in parsed:
        print("=" * 72)
        print(f"TEXT: {strategy.raw_text}")
        print(f"CLASS: {strategy.classification} (conf={strategy.confidence:.2f})")
        print(f"RACE: {strategy.race}  TIMING: {strategy.timing}")
        print(f"ENTITIES ({len(strategy.entities)}):")
        for ent in strategy.entities:
            linked = f" -> {ent.linked_id}" if ent.linked_id else ""
            print(f"  [{ent.label}] '{ent.text}'{linked}")
        print(f"COMMANDS ({len(strategy.commands)}):")
        for cmd in strategy.commands:
            qty = f" x{cmd.quantity}" if cmd.quantity else ""
            print(f"  {cmd.priority}: {cmd.action} {cmd.target or ''}{qty}")
        print()

    # Strategy comparison
    print("=" * 72)
    print("STRATEGY COMPARISON:")
    comparison = parser.compare_strategies(examples[0], examples[3])
    for key, val in comparison.items():
        print(f"  {key}: {val}")

    # JSON export
    print("\n" + "=" * 72)
    print("JSON EXPORT (first strategy):")
    print(parsed[0].to_json())

    # Entity linking demo
    print("\n" + "=" * 72)
    print("ENTITY LINKING:")
    for name in ["roaches", "hydra", "spawning pool", "12 pool"]:
        linked = parser.link_entity(name)
        print(f"  '{name}' -> {linked}")


if __name__ == "__main__":
    _demo()
