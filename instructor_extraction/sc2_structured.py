"""
Phase 431: Instructor - Structured SC2 Strategy Extraction
Uses Pydantic + OpenAI to extract structured strategy data from game commentary.
"""

import instructor
from openai import OpenAI, AsyncOpenAI
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import asyncio


# ── Pydantic models ───────────────────────────────────────────────────────────


class BuildOrderStep(BaseModel):
    """A single step in an SC2 build order."""

    supply: int = Field(
        ..., ge=9, le=200, description="Supply count when this step triggers"
    )
    action: str = Field(..., min_length=2, description="What to build or do")
    notes: Optional[str] = None


class ThreatAssessment(BaseModel):
    """Assessed threat level from an SC2 game state description."""

    threat_level: int = Field(..., ge=1, le=10, description="Threat level 1-10")
    threat_type: str = Field(
        ..., description="Type: harassment, all-in, timing_attack, macro"
    )
    estimated_army_size: Optional[str] = None
    recommended_response: str
    urgency: str = Field(..., pattern="^(low|medium|high|critical)$")

    @field_validator("threat_type")
    @classmethod
    def validate_threat_type(cls, v: str) -> str:
        valid = {"harassment", "all-in", "timing_attack", "macro", "unknown"}
        if v.lower() not in valid:
            return "unknown"
        return v.lower()


class BuildOrderAdvice(BaseModel):
    """Recommended build order for a given matchup."""

    race: str = Field(..., pattern="^(Zerg|Terran|Protoss)$")
    opponent_race: str = Field(..., pattern="^(Zerg|Terran|Protoss)$")
    opening_name: str
    steps: list[BuildOrderStep] = Field(..., min_length=3, max_length=20)
    win_condition: str
    counters: list[str] = Field(default_factory=list)


class StrategyRecommendation(BaseModel):
    """Complete SC2 strategy recommendation extracted from commentary."""

    summary: str = Field(..., max_length=300)
    recommended_race: str = Field(..., pattern="^(Zerg|Terran|Protoss)$")
    build_order: BuildOrderAdvice
    threat_assessment: Optional[ThreatAssessment] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    key_timings: list[str] = Field(default_factory=list)


# ── Instructor client setup ───────────────────────────────────────────────────


def get_instructor_client() -> instructor.Instructor:
    """Create an Instructor-patched OpenAI client."""
    return instructor.from_openai(OpenAI())


def get_async_instructor_client() -> instructor.AsyncInstructor:
    """Create an async Instructor-patched OpenAI client."""
    return instructor.from_openai(AsyncOpenAI())


# ── Extraction functions ──────────────────────────────────────────────────────


def extract_strategy(commentary: str, client=None) -> StrategyRecommendation:
    """Extract structured strategy from SC2 game commentary text."""
    if client is None:
        client = get_instructor_client()

    return client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=StrategyRecommendation,
        max_retries=3,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an SC2 strategy expert. Extract structured strategy "
                    "recommendations from game commentary. Be precise with build orders "
                    "and threat assessments."
                ),
            },
            {
                "role": "user",
                "content": f"Analyze this SC2 commentary and extract strategy:\n\n{commentary}",
            },
        ],
    )


def extract_threat(game_state_description: str, client=None) -> ThreatAssessment:
    """Extract threat assessment from a game state description."""
    if client is None:
        client = get_instructor_client()

    return client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=ThreatAssessment,
        max_retries=3,
        messages=[
            {"role": "system", "content": "You are an SC2 threat assessment expert."},
            {
                "role": "user",
                "content": f"Assess the threat in this game state:\n\n{game_state_description}",
            },
        ],
    )


async def batch_extract_strategies(
    commentaries: list[str],
) -> list[StrategyRecommendation]:
    """Asynchronously extract strategies from multiple commentaries."""
    client = get_async_instructor_client()
    tasks = [
        client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=StrategyRecommendation,
            max_retries=2,
            messages=[
                {"role": "system", "content": "You are an SC2 strategy expert."},
                {"role": "user", "content": f"Extract strategy from: {c}"},
            ],
        )
        for c in commentaries
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)


# ── Demo ──────────────────────────────────────────────────────────────────────

SAMPLE_COMMENTARY = """
In this ZvT game, the Zerg player opens with a standard 17 Hatch, 17 Pool build.
After getting the hatchery down at the natural, they make a queen and 2 sets of zerglings.
The Terran is doing a 1-1-1 build with a possible banshee opening - there's a threat of
cloaked air harassment around the 4-minute mark. The Zerg needs an extra queen ASAP and
should scout with an overlord. Key timing: get roach warren before 5 minutes if bio
pressure is spotted.
"""

if __name__ == "__main__":
    print("[Instructor] SC2 Structured Extraction models loaded.")
    print(f"  Models: StrategyRecommendation, BuildOrderAdvice, ThreatAssessment")
    print(f"  Features: Pydantic validation, retry on failure, async batch extraction")
    print(f"\nSample commentary (would be sent to OpenAI):")
    print(SAMPLE_COMMENTARY[:200] + "...")

# Phase 431: Instructor registered
