"""
Phase 432: Outlines - Structured SC2 Strategy Generation
Constrained text generation for build orders, strategy JSON, and unit compositions.
"""

import outlines
import outlines.models as models
import outlines.text.generate as generate
from pydantic import BaseModel, Field
from typing import Literal
import json
import re


# ── Pydantic schemas for structured output ────────────────────────────────────

class BuildOrderStep(BaseModel):
    supply: int = Field(..., ge=9, le=200)
    action: str
    unit_or_building: str


class SC2Strategy(BaseModel):
    race: Literal["Zerg", "Terran", "Protoss"]
    opening: str
    win_condition: str
    key_units: list[str]
    build_steps: list[BuildOrderStep]
    timing_attack_at: int = Field(..., ge=60, le=1800, description="Seconds")


class UnitComposition(BaseModel):
    race: Literal["Zerg", "Terran", "Protoss"]
    army_supply: int = Field(..., ge=10, le=200)
    units: dict[str, int]
    role: Literal["aggressive", "defensive", "harassment"]


# ── FSM-constrained build order generation ───────────────────────────────────

BUILD_ORDER_REGEX = r"\d{1,3}\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)*(?:\s*,\s*\d{1,3}\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)*)*"

ZERG_OPENINGS = [
    "17 Hatch, 17 Pool, 19 Gas",
    "Pool First, 16 Hatch, 18 Gas",
    "3 Hatch Before Pool",
]

STRATEGY_CHOICES = ["aggressive_timing", "macro_play", "cheese", "defensive_turtle"]


def generate_with_json_schema(model_name: str = "gpt2") -> SC2Strategy:
    """Generate a structured SC2 strategy using JSON schema constraints."""
    lm = models.transformers(model_name)
    generator = generate.json(lm, SC2Strategy)

    prompt = (
        "Generate a complete StarCraft 2 Zerg strategy for a ZvT matchup "
        "with a Roach-Ravager timing attack."
    )
    result = generator(prompt)
    return result


def generate_strategy_choice(model_name: str = "gpt2") -> str:
    """Generate a strategy type using choice constraints."""
    lm = models.transformers(model_name)
    generator = generate.choice(lm, STRATEGY_CHOICES)
    prompt = "For a Zerg vs Terran macro game, the best approach is:"
    return generator(prompt)


def generate_unit_composition_json(model_name: str = "gpt2") -> UnitComposition:
    """Generate a constrained army composition as structured JSON."""
    lm = models.transformers(model_name)
    generator = generate.json(lm, UnitComposition)
    prompt = "Generate a standard Zerg mid-game army composition for aggressive play."
    return generator(prompt)


def generate_regex_build_order(model_name: str = "gpt2") -> str:
    """Generate a build order string constrained by regex pattern."""
    lm = models.transformers(model_name)
    pattern = re.compile(r"(1[2-9]|[2-9]\d)\s+(Drone|Overlord|Zergling|Roach|Queen|Hatchery|Spawning Pool|Extractor)")
    generator = generate.regex(lm, pattern)
    prompt = "17 "
    return generator(prompt)


# ── Template-based generation (no LLM needed) ─────────────────────────────────

def template_sc2_strategy(
    race: str = "Zerg",
    opponent: str = "Terran",
    style: str = "macro",
) -> dict:
    """Generate a strategy dict using Outlines text templates."""
    templates = {
        ("Zerg", "Terran", "macro"): {
            "race": "Zerg",
            "opening": "17 Hatch, 17 Pool",
            "win_condition": "Drone to 70 workers, then mass Roach-Hydra",
            "key_units": ["Drone", "Queen", "Roach", "Hydralisk", "Viper"],
            "build_steps": [
                {"supply": 9, "action": "send scout", "unit_or_building": "Overlord"},
                {"supply": 13, "action": "build", "unit_or_building": "Overlord"},
                {"supply": 17, "action": "build", "unit_or_building": "Hatchery"},
                {"supply": 17, "action": "build", "unit_or_building": "Spawning Pool"},
                {"supply": 19, "action": "build", "unit_or_building": "Extractor"},
            ],
            "timing_attack_at": 480,
        },
        ("Zerg", "Protoss", "aggressive"): {
            "race": "Zerg",
            "opening": "Pool First, early Zergling pressure",
            "win_condition": "Economic damage with Zerglings, transition to Bane-Ling",
            "key_units": ["Zergling", "Baneling", "Roach"],
            "build_steps": [
                {"supply": 9, "action": "build", "unit_or_building": "Overlord"},
                {"supply": 12, "action": "build", "unit_or_building": "Spawning Pool"},
                {"supply": 14, "action": "build", "unit_or_building": "Extractor"},
                {"supply": 16, "action": "produce", "unit_or_building": "Zergling x6"},
            ],
            "timing_attack_at": 240,
        },
    }

    key = (race, opponent, style)
    return templates.get(key, templates[("Zerg", "Terran", "macro")])


# ── Main demo ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[Outlines] SC2 Strategy Generation")
    print("\n[Template-based strategy: ZvT Macro]")
    strategy = template_sc2_strategy("Zerg", "Terran", "macro")
    print(json.dumps(strategy, indent=2))

    print("\n[Outlines] Generation modes available:")
    print("  - generate.json(model, SC2Strategy)  → Structured JSON output")
    print("  - generate.choice(model, CHOICES)    → Constrained choice selection")
    print("  - generate.regex(model, pattern)     → Regex-constrained text")
    print("  - generate.json(model, UnitComposition) → Army composition JSON")
