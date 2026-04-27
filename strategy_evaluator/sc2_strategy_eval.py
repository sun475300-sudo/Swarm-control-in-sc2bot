"""
Phase 635: LLM-Based Strategy Evaluator for SC2

Evaluate and score StarCraft II strategies across multiple dimensions:
economy, army strength, timing windows, risk, and matchup viability.
Supports head-to-head comparison, Elo ranking, and improvement suggestions.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# ── Constants ───────────────────────────────────────────────────────────────────

DEFAULT_ELO = 1500.0
ELO_K_FACTOR = 32.0

MATCHUP_TYPES: list[str] = ["ZvT", "ZvP", "ZvZ", "TvP", "TvT", "PvP"]

RACE_NAMES: dict[str, str] = {
    "Z": "Zerg",
    "T": "Terran",
    "P": "Protoss",
}

# Baseline benchmark values for scoring normalization
BENCHMARK_VALUES: dict[str, dict[str, float]] = {
    "economy": {
        "worker_count_5min": 40.0,
        "worker_count_8min": 60.0,
        "expansion_count_8min": 3.0,
        "gas_timing_sec": 90.0,
    },
    "army": {
        "supply_at_timing": 80.0,
        "unit_diversity": 3.0,
        "upgrade_count": 2.0,
        "anti_air_ratio": 0.2,
    },
    "timing": {
        "first_attack_sec": 300.0,
        "tech_completion_sec": 360.0,
        "max_army_supply_sec": 480.0,
    },
    "risk": {
        "greed_index": 0.5,
        "cheese_factor": 0.1,
        "all_in_factor": 0.2,
    },
}

# Known build order archetypes with baseline scores
ARCHETYPE_SCORES: dict[str, dict[str, float]] = {
    "hatch_first": {
        "economy": 0.9,
        "army": 0.5,
        "timing": 0.4,
        "risk": 0.3,
        "versatility": 0.8,
    },
    "pool_first": {
        "economy": 0.5,
        "army": 0.7,
        "timing": 0.8,
        "risk": 0.5,
        "versatility": 0.6,
    },
    "roach_ravager_timing": {
        "economy": 0.6,
        "army": 0.8,
        "timing": 0.9,
        "risk": 0.6,
        "versatility": 0.5,
    },
    "ling_bane_muta": {
        "economy": 0.7,
        "army": 0.7,
        "timing": 0.6,
        "risk": 0.5,
        "versatility": 0.7,
    },
    "hydra_lurker": {
        "economy": 0.6,
        "army": 0.85,
        "timing": 0.5,
        "risk": 0.4,
        "versatility": 0.6,
    },
    "12_pool": {
        "economy": 0.2,
        "army": 0.6,
        "timing": 1.0,
        "risk": 0.9,
        "versatility": 0.2,
    },
    "macro_hive": {
        "economy": 1.0,
        "army": 0.9,
        "timing": 0.3,
        "risk": 0.3,
        "versatility": 0.9,
    },
    "nydus_swarm_host": {
        "economy": 0.4,
        "army": 0.6,
        "timing": 0.7,
        "risk": 0.8,
        "versatility": 0.3,
    },
}


# ── Enums ───────────────────────────────────────────────────────────────────────


class EvalDimension(Enum):
    ECONOMY = "economy"
    ARMY = "army"
    TIMING = "timing"
    RISK = "risk"
    VERSATILITY = "versatility"
    MICRO_DEMAND = "micro_demand"
    MACRO_DEMAND = "macro_demand"


class MatchupType(Enum):
    ZVT = "ZvT"
    ZVP = "ZvP"
    ZVZ = "ZvZ"
    TVP = "TvP"
    TVT = "TvT"
    PVP = "PvP"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


# ── Data Classes ────────────────────────────────────────────────────────────────


@dataclass
class StrategyProfile:
    """Represents a complete SC2 strategy with its attributes."""

    name: str
    race: str
    matchup: str
    archetype: str = "custom"
    description: str = ""
    build_order: list[tuple[int, str]] = field(default_factory=list)
    key_units: list[str] = field(default_factory=list)
    key_upgrades: list[str] = field(default_factory=list)
    timing_window_sec: tuple[int, int] = (0, 600)
    worker_target: int = 66
    expansion_target: int = 3
    supply_peak: int = 120
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """One-line summary of the strategy."""
        units = ", ".join(self.key_units[:4]) if self.key_units else "mixed"
        return (
            f"{self.name} ({self.race} {self.matchup}) "
            f"arch={self.archetype} units=[{units}] "
            f"timing={self.timing_window_sec[0]}-{self.timing_window_sec[1]}s"
        )


@dataclass
class EvalCriteria:
    """Evaluation criteria weights and thresholds."""

    dimension: EvalDimension
    weight: float = 1.0
    min_threshold: float = 0.0
    max_threshold: float = 1.0
    description: str = ""

    def normalize_score(self, raw: float) -> float:
        """Normalize a raw score to 0-1 range based on thresholds."""
        if self.max_threshold == self.min_threshold:
            return 1.0 if raw >= self.max_threshold else 0.0
        clamped = max(self.min_threshold, min(raw, self.max_threshold))
        return (clamped - self.min_threshold) / (
            self.max_threshold - self.min_threshold
        )


@dataclass
class EvalScore:
    """Score for a single evaluation dimension."""

    dimension: EvalDimension
    score: float  # 0.0 to 1.0
    weight: float = 1.0
    notes: list[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    def grade(self) -> str:
        """Letter grade from score."""
        if self.score >= 0.9:
            return "S"
        elif self.score >= 0.8:
            return "A"
        elif self.score >= 0.65:
            return "B"
        elif self.score >= 0.5:
            return "C"
        elif self.score >= 0.35:
            return "D"
        else:
            return "F"


@dataclass
class EvalReport:
    """Full evaluation report for a strategy."""

    strategy_name: str
    matchup: str
    scores: list[EvalScore] = field(default_factory=list)
    overall_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    eval_time_ms: float = 0.0

    def summary(self) -> str:
        lines: list[str] = [
            f"=== Evaluation: {self.strategy_name} ({self.matchup}) ===",
            f"Overall Score: {self.overall_score:.2f} / 1.00  |  Risk: {self.risk_level.value}",
            "",
        ]
        for s in self.scores:
            bar_len = int(s.score * 20)
            bar = "#" * bar_len + "-" * (20 - bar_len)
            lines.append(
                f"  {s.dimension.value:15s} [{bar}] {s.score:.2f} ({s.grade()})"
            )

        if self.strengths:
            lines.append("\n  Strengths:")
            for item in self.strengths:
                lines.append(f"    + {item}")

        if self.weaknesses:
            lines.append("\n  Weaknesses:")
            for item in self.weaknesses:
                lines.append(f"    - {item}")

        if self.suggestions:
            lines.append("\n  Suggestions:")
            for item in self.suggestions:
                lines.append(f"    > {item}")

        return "\n".join(lines)


@dataclass
class ComparisonResult:
    """Head-to-head comparison between two strategies."""

    strategy_a: str
    strategy_b: str
    matchup: str
    winner: str
    dimension_winners: dict[str, str] = field(default_factory=dict)
    score_a: float = 0.0
    score_b: float = 0.0
    analysis: str = ""
    advantages_a: list[str] = field(default_factory=list)
    advantages_b: list[str] = field(default_factory=list)


# ── Matchup Evaluator ──────────────────────────────────────────────────────────


class MatchupEvaluator:
    """Evaluate strategies within the context of specific SC2 matchups."""

    # Matchup-specific dimension weights
    MATCHUP_WEIGHTS: dict[str, dict[str, float]] = {
        "ZvT": {
            "economy": 1.2,
            "army": 1.0,
            "timing": 0.9,
            "risk": 0.8,
            "versatility": 1.0,
            "micro_demand": 0.7,
            "macro_demand": 1.3,
        },
        "ZvP": {
            "economy": 1.0,
            "army": 1.1,
            "timing": 1.1,
            "risk": 0.9,
            "versatility": 0.8,
            "micro_demand": 0.9,
            "macro_demand": 1.1,
        },
        "ZvZ": {
            "economy": 0.8,
            "army": 0.9,
            "timing": 1.3,
            "risk": 1.1,
            "versatility": 0.6,
            "micro_demand": 1.2,
            "macro_demand": 0.8,
        },
    }

    # Matchup-specific counter relationships
    COUNTERS: dict[str, dict[str, list[str]]] = {
        "ZvT": {
            "bio": ["ling_bane_muta", "lurker_contain"],
            "mech": ["roach_ravager_timing", "swarm_host_nydus"],
            "bc_rush": ["hydra_corruptor", "queen_walk"],
        },
        "ZvP": {
            "gateway_all_in": ["roach_ravager_timing", "spine_rush"],
            "skytoss": ["hydra_corruptor", "viper_abduct"],
            "dt_rush": ["spore_crawlers", "overseer_detection"],
        },
        "ZvZ": {
            "12_pool": ["15_pool_speed", "spine_rush"],
            "roach_all_in": ["ling_flood", "roach_ravager_timing"],
            "macro_play": ["early_aggression", "nydus_timing"],
        },
    }

    def get_matchup_weights(self, matchup: str) -> dict[str, float]:
        """Get dimension weights for a matchup."""
        return dict(
            self.MATCHUP_WEIGHTS.get(
                matchup,
                {
                    dim: 1.0
                    for dim in [
                        "economy",
                        "army",
                        "timing",
                        "risk",
                        "versatility",
                        "micro_demand",
                        "macro_demand",
                    ]
                },
            )
        )

    def suggest_counters(self, matchup: str, opponent_style: str) -> list[str]:
        """Suggest counter-strategies for a given opponent style."""
        matchup_counters = self.COUNTERS.get(matchup, {})
        return list(matchup_counters.get(opponent_style, []))

    def evaluate_matchup_fitness(self, profile: StrategyProfile) -> dict[str, float]:
        """Score how well a strategy fits its intended matchup."""
        archetype_scores = ARCHETYPE_SCORES.get(profile.archetype, {})
        weights = self.get_matchup_weights(profile.matchup)

        fitness: dict[str, float] = {}
        for dim_name, weight in weights.items():
            base_score = archetype_scores.get(dim_name, 0.5)
            fitness[dim_name] = min(1.0, base_score * weight)

        return fitness

    def rate_build_order(
        self, build_order: list[tuple[int, str]], matchup: str
    ) -> dict[str, Any]:
        """Rate a build order for efficiency and safety."""
        result: dict[str, Any] = {
            "total_steps": len(build_order),
            "economy_score": 0.0,
            "safety_score": 0.0,
            "timing_score": 0.0,
            "notes": [],
        }

        if not build_order:
            result["notes"].append("Empty build order")
            return result

        # Economy: check for early expansion
        expansion_supply = None
        pool_supply = None
        gas_supply = None
        for supply, action in build_order:
            action_low = action.lower()
            if "hatch" in action_low or "expand" in action_low:
                if expansion_supply is None:
                    expansion_supply = supply
            if "pool" in action_low:
                pool_supply = supply
            if "gas" in action_low or "extractor" in action_low:
                gas_supply = supply

        # Score economy (hatch before pool = economic)
        if expansion_supply is not None and pool_supply is not None:
            if expansion_supply <= pool_supply:
                result["economy_score"] = 0.85
                result["notes"].append("Economic opener: hatch before pool")
            else:
                result["economy_score"] = 0.6
                result["notes"].append("Aggressive opener: pool before hatch")
        elif expansion_supply is not None:
            result["economy_score"] = 0.7
        else:
            result["economy_score"] = 0.4
            result["notes"].append("No early expansion detected")

        # Safety: pool timing
        if pool_supply is not None:
            if pool_supply <= 14:
                result["safety_score"] = 0.9
                result["notes"].append("Early pool provides scouting and safety")
            elif pool_supply <= 17:
                result["safety_score"] = 0.7
            else:
                result["safety_score"] = 0.5
                result["notes"].append(
                    "Late pool may be vulnerable to early aggression"
                )
        else:
            result["safety_score"] = 0.3

        # Timing: gas determines tech speed
        if gas_supply is not None:
            if gas_supply <= 18:
                result["timing_score"] = 0.8
                result["notes"].append("Early gas enables fast tech")
            elif gas_supply <= 24:
                result["timing_score"] = 0.6
            else:
                result["timing_score"] = 0.4
        else:
            result["timing_score"] = 0.3

        return result


# ── Strategy Evaluator (main) ──────────────────────────────────────────────────


class StrategyEvaluator:
    """Full strategy evaluation engine with scoring, comparison, and ranking."""

    def __init__(self) -> None:
        self.matchup_evaluator = MatchupEvaluator()
        self.elo_ratings: dict[str, float] = {}
        self.eval_history: list[EvalReport] = []
        self._criteria = self._default_criteria()

    def _default_criteria(self) -> list[EvalCriteria]:
        """Create the default set of evaluation criteria."""
        return [
            EvalCriteria(
                dimension=EvalDimension.ECONOMY,
                weight=1.2,
                description="Worker production, expansion timing, income",
            ),
            EvalCriteria(
                dimension=EvalDimension.ARMY,
                weight=1.0,
                description="Army composition, supply efficiency, upgrades",
            ),
            EvalCriteria(
                dimension=EvalDimension.TIMING,
                weight=1.1,
                description="Attack timing, tech progression speed",
            ),
            EvalCriteria(
                dimension=EvalDimension.RISK,
                weight=0.8,
                description="Vulnerability to cheese, greediness level",
            ),
            EvalCriteria(
                dimension=EvalDimension.VERSATILITY,
                weight=0.9,
                description="Adaptability, transition options",
            ),
            EvalCriteria(
                dimension=EvalDimension.MICRO_DEMAND,
                weight=0.7,
                description="APM and micro skill required",
            ),
            EvalCriteria(
                dimension=EvalDimension.MACRO_DEMAND,
                weight=0.7,
                description="Macro cycle and multitasking demand",
            ),
        ]

    def evaluate(self, profile: StrategyProfile) -> EvalReport:
        """Evaluate a strategy and produce a full report."""
        t0 = time.time()

        matchup_fitness = self.matchup_evaluator.evaluate_matchup_fitness(profile)
        archetype_base = ARCHETYPE_SCORES.get(profile.archetype, {})
        matchup_weights = self.matchup_evaluator.get_matchup_weights(profile.matchup)

        scores: list[EvalScore] = []
        total_weighted = 0.0
        total_weight = 0.0

        for criteria in self._criteria:
            dim_name = criteria.dimension.value
            base = archetype_base.get(dim_name, 0.5)
            fitness_mod = matchup_fitness.get(dim_name, base)

            # Blend base archetype score with matchup fitness
            raw_score = base * 0.6 + fitness_mod * 0.4

            # Apply adjustments based on profile specifics
            raw_score = self._apply_profile_adjustments(
                raw_score, criteria.dimension, profile
            )

            clamped = max(0.0, min(1.0, raw_score))
            notes = self._generate_score_notes(criteria.dimension, clamped, profile)

            mw = matchup_weights.get(dim_name, 1.0)
            effective_weight = criteria.weight * mw

            eval_score = EvalScore(
                dimension=criteria.dimension,
                score=clamped,
                weight=effective_weight,
                notes=notes,
            )
            scores.append(eval_score)
            total_weighted += eval_score.weighted_score
            total_weight += effective_weight

        overall = total_weighted / total_weight if total_weight > 0 else 0.0

        # Determine risk level
        risk_score = next(
            (s.score for s in scores if s.dimension == EvalDimension.RISK), 0.5
        )
        risk_level = self._classify_risk(risk_score)

        # Generate strengths, weaknesses, suggestions
        strengths = self._identify_strengths(scores, profile)
        weaknesses = self._identify_weaknesses(scores, profile)
        suggestions = self._generate_suggestions(scores, profile, weaknesses)

        elapsed = (time.time() - t0) * 1000

        report = EvalReport(
            strategy_name=profile.name,
            matchup=profile.matchup,
            scores=scores,
            overall_score=round(overall, 4),
            risk_level=risk_level,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            eval_time_ms=elapsed,
        )
        self.eval_history.append(report)

        # Update Elo
        if profile.name not in self.elo_ratings:
            self.elo_ratings[profile.name] = DEFAULT_ELO

        return report

    def _apply_profile_adjustments(
        self,
        score: float,
        dimension: EvalDimension,
        profile: StrategyProfile,
    ) -> float:
        """Adjust score based on specific strategy profile attributes."""
        if dimension == EvalDimension.ECONOMY:
            # More workers = better economy score
            worker_ratio = min(1.0, profile.worker_target / 66.0)
            score = score * 0.7 + worker_ratio * 0.3

            # Expansion target bonus
            if profile.expansion_target >= 4:
                score += 0.05
            elif profile.expansion_target <= 1:
                score -= 0.15

        elif dimension == EvalDimension.ARMY:
            # Unit diversity bonus
            if len(profile.key_units) >= 3:
                score += 0.05
            # Upgrade bonus
            if len(profile.key_upgrades) >= 2:
                score += 0.05

        elif dimension == EvalDimension.TIMING:
            # Narrow timing window = more timing focused
            window_start, window_end = profile.timing_window_sec
            window_size = window_end - window_start
            if window_size < 120:
                score += 0.1  # Tight timing = high timing score
            elif window_size > 300:
                score -= 0.05

        elif dimension == EvalDimension.RISK:
            # Higher risk for all-in style
            if profile.expansion_target <= 1 and profile.supply_peak <= 80:
                score += 0.2
            if profile.archetype in ("12_pool", "nydus_swarm_host"):
                score += 0.15

        elif dimension == EvalDimension.VERSATILITY:
            # More units + expansions = more versatile
            if len(profile.key_units) >= 4 and profile.expansion_target >= 3:
                score += 0.1

        elif dimension == EvalDimension.MICRO_DEMAND:
            # Certain units require more micro
            micro_heavy = {"Mutalisk", "Baneling", "Viper", "Infestor", "Lurker"}
            micro_units = [u for u in profile.key_units if u in micro_heavy]
            if len(micro_units) >= 2:
                score += 0.15
            elif len(micro_units) == 1:
                score += 0.05

        elif dimension == EvalDimension.MACRO_DEMAND:
            if profile.worker_target >= 70 and profile.expansion_target >= 4:
                score += 0.15

        return score

    def _classify_risk(self, risk_score: float) -> RiskLevel:
        """Classify risk level from risk dimension score."""
        if risk_score >= 0.8:
            return RiskLevel.EXTREME
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.35:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _generate_score_notes(
        self,
        dimension: EvalDimension,
        score: float,
        profile: StrategyProfile,
    ) -> list[str]:
        """Generate explanatory notes for a dimension score."""
        notes: list[str] = []

        if dimension == EvalDimension.ECONOMY:
            if score >= 0.8:
                notes.append("Strong economy; high worker saturation expected")
            elif score < 0.5:
                notes.append("Sacrifices economy for early pressure")

        elif dimension == EvalDimension.ARMY:
            if score >= 0.8:
                notes.append("Powerful army composition with good synergy")
            elif score < 0.5:
                notes.append("Limited army strength; relies on timing/cheese")

        elif dimension == EvalDimension.TIMING:
            w_start, w_end = profile.timing_window_sec
            if w_end - w_start < 120:
                notes.append(f"Tight timing window: {w_start}-{w_end}s")
            else:
                notes.append(f"Flexible timing: {w_start}-{w_end}s")

        elif dimension == EvalDimension.RISK:
            if score >= 0.7:
                notes.append("High risk: vulnerable if initial plan fails")
            elif score < 0.3:
                notes.append("Conservative: safe against most openers")

        return notes

    def _identify_strengths(
        self, scores: list[EvalScore], profile: StrategyProfile
    ) -> list[str]:
        """Identify strategy strengths from scores."""
        strengths: list[str] = []
        for s in scores:
            if s.score >= 0.75:
                dim = s.dimension.value.replace("_", " ").title()
                strengths.append(f"Strong {dim} ({s.grade()})")

        if profile.expansion_target >= 4:
            strengths.append("Excellent long-game scaling")
        if len(profile.key_units) >= 4:
            strengths.append("Diverse army composition")

        return strengths

    def _identify_weaknesses(
        self, scores: list[EvalScore], profile: StrategyProfile
    ) -> list[str]:
        """Identify strategy weaknesses from scores."""
        weaknesses: list[str] = []
        for s in scores:
            if s.score < 0.45:
                dim = s.dimension.value.replace("_", " ").title()
                weaknesses.append(f"Weak {dim} ({s.grade()})")

        if profile.expansion_target <= 1:
            weaknesses.append("No expansion plan; fragile in longer games")
        if not profile.key_upgrades:
            weaknesses.append("No upgrades planned")

        return weaknesses

    def _generate_suggestions(
        self,
        scores: list[EvalScore],
        profile: StrategyProfile,
        weaknesses: list[str],
    ) -> list[str]:
        """Generate improvement suggestions."""
        suggestions: list[str] = []

        for s in scores:
            if s.dimension == EvalDimension.ECONOMY and s.score < 0.5:
                suggestions.append(
                    "Consider adding a third base earlier to improve economy"
                )
            elif s.dimension == EvalDimension.ARMY and s.score < 0.5:
                suggestions.append(
                    "Diversify army composition; add splash or anti-air units"
                )
            elif s.dimension == EvalDimension.TIMING and s.score < 0.4:
                suggestions.append(
                    "Tighten timing window or add pressure before main push"
                )
            elif s.dimension == EvalDimension.VERSATILITY and s.score < 0.4:
                suggestions.append(
                    "Plan transition options in case primary attack fails"
                )

        if not profile.key_upgrades:
            suggestions.append("Add attack/armor upgrades to improve mid-game power")

        # Matchup-specific suggestions
        counters = self.matchup_evaluator.suggest_counters(
            profile.matchup, profile.archetype
        )
        if counters:
            suggestions.append(f"Be aware of counter-styles: {', '.join(counters)}")

        return suggestions

    def compare(
        self, profile_a: StrategyProfile, profile_b: StrategyProfile
    ) -> ComparisonResult:
        """Head-to-head comparison of two strategies."""
        report_a = self.evaluate(profile_a)
        report_b = self.evaluate(profile_b)

        dimension_winners: dict[str, str] = {}
        advantages_a: list[str] = []
        advantages_b: list[str] = []

        for sa, sb in zip(report_a.scores, report_b.scores):
            dim_name = sa.dimension.value
            if sa.score > sb.score + 0.05:
                dimension_winners[dim_name] = profile_a.name
                advantages_a.append(f"{dim_name}: {sa.score:.2f} vs {sb.score:.2f}")
            elif sb.score > sa.score + 0.05:
                dimension_winners[dim_name] = profile_b.name
                advantages_b.append(f"{dim_name}: {sb.score:.2f} vs {sa.score:.2f}")
            else:
                dimension_winners[dim_name] = "tie"

        if report_a.overall_score > report_b.overall_score:
            winner = profile_a.name
        elif report_b.overall_score > report_a.overall_score:
            winner = profile_b.name
        else:
            winner = "tie"

        analysis_parts: list[str] = [
            f"{profile_a.name} ({report_a.overall_score:.2f}) vs "
            f"{profile_b.name} ({report_b.overall_score:.2f})",
        ]
        if advantages_a:
            analysis_parts.append(
                f"{profile_a.name} excels in: "
                + ", ".join(d.split(":")[0] for d in advantages_a)
            )
        if advantages_b:
            analysis_parts.append(
                f"{profile_b.name} excels in: "
                + ", ".join(d.split(":")[0] for d in advantages_b)
            )

        # Update Elo ratings
        self._update_elo(
            profile_a.name,
            profile_b.name,
            report_a.overall_score,
            report_b.overall_score,
        )

        return ComparisonResult(
            strategy_a=profile_a.name,
            strategy_b=profile_b.name,
            matchup=profile_a.matchup,
            winner=winner,
            dimension_winners=dimension_winners,
            score_a=report_a.overall_score,
            score_b=report_b.overall_score,
            analysis=" | ".join(analysis_parts),
            advantages_a=advantages_a,
            advantages_b=advantages_b,
        )

    def _update_elo(
        self,
        name_a: str,
        name_b: str,
        score_a: float,
        score_b: float,
    ) -> None:
        """Update Elo ratings based on evaluation scores."""
        ra = self.elo_ratings.get(name_a, DEFAULT_ELO)
        rb = self.elo_ratings.get(name_b, DEFAULT_ELO)

        expected_a = 1.0 / (1.0 + math.pow(10.0, (rb - ra) / 400.0))
        expected_b = 1.0 - expected_a

        # Convert scores to win probability
        total = score_a + score_b
        if total > 0:
            actual_a = score_a / total
            actual_b = score_b / total
        else:
            actual_a = 0.5
            actual_b = 0.5

        self.elo_ratings[name_a] = ra + ELO_K_FACTOR * (actual_a - expected_a)
        self.elo_ratings[name_b] = rb + ELO_K_FACTOR * (actual_b - expected_b)

    def get_rankings(self) -> list[tuple[str, float]]:
        """Return strategies sorted by Elo rating (descending)."""
        ranked = sorted(self.elo_ratings.items(), key=lambda x: x[1], reverse=True)
        return ranked

    def evaluate_build_order(
        self, build_order: list[tuple[int, str]], matchup: str
    ) -> dict[str, Any]:
        """Quick evaluation of a raw build order."""
        return self.matchup_evaluator.rate_build_order(build_order, matchup)

    def stats(self) -> dict[str, Any]:
        """Return evaluator statistics."""
        total = len(self.eval_history)
        if total == 0:
            avg_score = 0.0
        else:
            avg_score = sum(r.overall_score for r in self.eval_history) / total

        return {
            "total_evaluations": total,
            "strategies_ranked": len(self.elo_ratings),
            "avg_overall_score": round(avg_score, 4),
            "criteria_count": len(self._criteria),
        }


# ── Demo ────────────────────────────────────────────────────────────────────────


def demo() -> None:
    """Demonstrate the Strategy Evaluator capabilities."""
    print("=" * 72)
    print("Phase 635: LLM-Based Strategy Evaluator for SC2")
    print("=" * 72)

    evaluator = StrategyEvaluator()

    # 1. Create strategy profiles
    roach_timing = StrategyProfile(
        name="Roach-Ravager Timing",
        race="Zerg",
        matchup="ZvT",
        archetype="roach_ravager_timing",
        description="2-base roach-ravager push at 5:30",
        build_order=[
            (14, "overlord"),
            (17, "hatch"),
            (18, "gas"),
            (17, "pool"),
            (20, "queen"),
            (24, "roach_warren"),
            (30, "roach"),
            (36, "ravager"),
        ],
        key_units=["Roach", "Ravager", "Queen"],
        key_upgrades=["Glial Reconstitution"],
        timing_window_sec=(300, 420),
        worker_target=44,
        expansion_target=2,
        supply_peak=90,
    )

    ling_bane_muta = StrategyProfile(
        name="Ling-Bane-Muta",
        race="Zerg",
        matchup="ZvT",
        archetype="ling_bane_muta",
        description="Standard ZvT with ling-bane-muta mid-game",
        build_order=[
            (14, "overlord"),
            (17, "hatch"),
            (18, "gas"),
            (17, "pool"),
            (19, "overlord"),
            (22, "queen"),
            (26, "lair"),
            (30, "spire"),
            (36, "bane_nest"),
        ],
        key_units=["Zergling", "Baneling", "Mutalisk"],
        key_upgrades=["Metabolic Boost", "Centrifugal Hooks", "Flyer Attacks 1"],
        timing_window_sec=(300, 600),
        worker_target=66,
        expansion_target=3,
        supply_peak=150,
    )

    twelve_pool = StrategyProfile(
        name="12-Pool Rush",
        race="Zerg",
        matchup="ZvZ",
        archetype="12_pool",
        description="Early pool aggression in ZvZ",
        build_order=[
            (12, "pool"),
            (13, "overlord"),
            (14, "zergling"),
            (16, "zergling"),
            (18, "queen"),
        ],
        key_units=["Zergling"],
        key_upgrades=["Metabolic Boost"],
        timing_window_sec=(90, 210),
        worker_target=20,
        expansion_target=1,
        supply_peak=50,
    )

    macro_hive = StrategyProfile(
        name="Macro Hive Tech",
        race="Zerg",
        matchup="ZvP",
        archetype="macro_hive",
        description="Greedy 4-base hive tech with broodlords",
        build_order=[
            (14, "overlord"),
            (17, "hatch"),
            (18, "gas"),
            (17, "pool"),
            (20, "queen"),
            (30, "third_hatch"),
            (44, "lair"),
            (50, "infestation_pit"),
            (60, "hive"),
        ],
        key_units=["Hydralisk", "Lurker", "BroodLord", "Viper"],
        key_upgrades=["Grooved Spines", "Muscular Augments", "Lurker Range"],
        timing_window_sec=(480, 900),
        worker_target=80,
        expansion_target=4,
        supply_peak=200,
    )

    # 2. Evaluate individual strategies
    print("\n--- Individual Evaluations ---\n")
    for profile in [roach_timing, ling_bane_muta, twelve_pool, macro_hive]:
        report = evaluator.evaluate(profile)
        print(report.summary())
        print()

    # 3. Head-to-head comparison
    print("\n--- Head-to-Head: Roach Timing vs Ling-Bane-Muta ---\n")
    comparison = evaluator.compare(roach_timing, ling_bane_muta)
    print(f"  Winner: {comparison.winner}")
    print(f"  Score: {comparison.score_a:.3f} vs {comparison.score_b:.3f}")
    print(f"  Analysis: {comparison.analysis}")
    if comparison.advantages_a:
        print(f"  {comparison.strategy_a} advantages:")
        for adv in comparison.advantages_a:
            print(f"    + {adv}")
    if comparison.advantages_b:
        print(f"  {comparison.strategy_b} advantages:")
        for adv in comparison.advantages_b:
            print(f"    + {adv}")

    # 4. Build order evaluation
    print("\n--- Build Order Quick Eval ---")
    bo_eval = evaluator.evaluate_build_order(
        [(14, "overlord"), (17, "hatch"), (18, "gas"), (17, "pool")],
        matchup="ZvT",
    )
    for key, val in bo_eval.items():
        print(f"  {key}: {val}")

    # 5. Elo rankings
    print("\n--- Elo Rankings ---")
    rankings = evaluator.get_rankings()
    for rank, (name, elo) in enumerate(rankings, start=1):
        print(f"  #{rank} {name:30s} Elo={elo:.1f}")

    # 6. Evaluator stats
    print("\n--- Evaluator Stats ---")
    stats = evaluator.stats()
    for key, val in stats.items():
        print(f"  {key}: {val}")

    print("\n" + "=" * 72)
    print("Phase 635 demo complete.")
    print("=" * 72)


if __name__ == "__main__":
    demo()


# Phase 635: Strategy Evaluator registered
