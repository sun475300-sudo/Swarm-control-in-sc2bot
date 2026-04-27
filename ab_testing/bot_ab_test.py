"""
SC2 Bot - A/B Testing Framework
Phase 397: Statistical strategy evaluation for SC2 bot variants

Supports chi-squared test for win rate comparison,
t-test for APM comparison, and automated winner selection.
"""

from __future__ import annotations

import logging
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Statistical Helpers
# ---------------------------------------------------------------------------


def chi_squared_test(
    wins_a: int,
    total_a: int,
    wins_b: int,
    total_b: int,
) -> tuple[float, float]:
    """
    Chi-squared test for comparing win rates between two variants.
    Returns: (chi2_statistic, p_value)
    """
    if total_a == 0 or total_b == 0:
        return 0.0, 1.0

    losses_a = total_a - wins_a
    losses_b = total_b - wins_b
    total = total_a + total_b
    total_wins = wins_a + wins_b
    total_losses = losses_a + losses_b

    if total_wins == 0 or total_losses == 0:
        return 0.0, 1.0

    expected_wa = total_a * total_wins / total
    expected_la = total_a * total_losses / total
    expected_wb = total_b * total_wins / total
    expected_lb = total_b * total_losses / total

    cells = [
        (wins_a, expected_wa),
        (losses_a, expected_la),
        (wins_b, expected_wb),
        (losses_b, expected_lb),
    ]

    chi2 = sum(
        (observed - expected) ** 2 / expected
        for observed, expected in cells
        if expected > 0
    )

    # Approximate p-value for chi2 with 1 degree of freedom
    p_value = _chi2_p_value(chi2, df=1)
    return chi2, p_value


def welch_t_test(
    mean_a: float,
    std_a: float,
    n_a: int,
    mean_b: float,
    std_b: float,
    n_b: int,
) -> tuple[float, float]:
    """
    Welch's t-test for comparing means (e.g. APM) between two variants.
    Returns: (t_statistic, p_value)
    """
    if n_a < 2 or n_b < 2:
        return 0.0, 1.0

    se_a = (std_a**2) / n_a
    se_b = (std_b**2) / n_b
    se = math.sqrt(se_a + se_b)

    if se == 0:
        return 0.0, 1.0

    t = (mean_a - mean_b) / se
    df = (se_a + se_b) ** 2 / (se_a**2 / (n_a - 1) + se_b**2 / (n_b - 1))
    p_value = _t_p_value(abs(t), df)
    return t, p_value


def _chi2_p_value(chi2: float, df: int = 1) -> float:
    """Approximate chi-squared p-value (two-tailed)."""
    # Using Wilson–Hilferty approximation for chi2 CDF
    if chi2 <= 0:
        return 1.0
    x = chi2 / df
    p = math.exp(-0.5 * chi2)
    if df == 1:
        return min(1.0, 2 * p)
    return min(1.0, p)


def _t_p_value(t: float, df: float) -> float:
    """Approximate two-tailed p-value for t-distribution."""
    # Simple approximation using normal distribution for large df
    if df > 30:
        z = t
        p = 2 * (1 - _normal_cdf(z))
        return min(1.0, max(0.0, p))
    return min(1.0, 2 * math.exp(-0.5 * t))


def _normal_cdf(z: float) -> float:
    """Standard normal CDF approximation."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class GameResult:
    """Result of a single game in an A/B test."""

    game_id: str
    variant_name: str
    won: bool
    apm: float
    game_length_s: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VariantStats:
    """Accumulated statistics for a single variant."""

    name: str
    total_games: int = 0
    wins: int = 0
    apm_values: list[float] = field(default_factory=list)
    game_lengths: list[float] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        return self.wins / self.total_games if self.total_games > 0 else 0.0

    @property
    def avg_apm(self) -> float:
        return sum(self.apm_values) / len(self.apm_values) if self.apm_values else 0.0

    @property
    def std_apm(self) -> float:
        if len(self.apm_values) < 2:
            return 0.0
        mean = self.avg_apm
        variance = sum((x - mean) ** 2 for x in self.apm_values) / (
            len(self.apm_values) - 1
        )
        return math.sqrt(variance)

    @property
    def avg_game_length(self) -> float:
        return (
            sum(self.game_lengths) / len(self.game_lengths)
            if self.game_lengths
            else 0.0
        )

    def record(self, result: GameResult) -> None:
        self.total_games += 1
        if result.won:
            self.wins += 1
        self.apm_values.append(result.apm)
        self.game_lengths.append(result.game_length_s)

    def summary(self) -> dict:
        return {
            "name": self.name,
            "total_games": self.total_games,
            "wins": self.wins,
            "win_rate": round(self.win_rate, 4),
            "avg_apm": round(self.avg_apm, 1),
            "std_apm": round(self.std_apm, 1),
            "avg_game_length_s": round(self.avg_game_length, 1),
        }


@dataclass
class Variant:
    """
    Represents one A/B test variant (bot strategy configuration).
    """

    name: str
    description: str
    config: dict[str, Any]
    traffic_weight: float = 1.0

    def __post_init__(self):
        self._stats = VariantStats(name=self.name)

    @property
    def stats(self) -> VariantStats:
        return self._stats


@dataclass
class ExperimentResult:
    """Final result of an A/B experiment."""

    experiment_id: str
    winner: str | None
    control_stats: dict
    treatment_stats: dict
    win_rate_chi2: float
    win_rate_p_value: float
    apm_t_stat: float
    apm_p_value: float
    is_significant: bool
    confidence_level: float
    concluded_at: datetime = field(default_factory=datetime.utcnow)
    conclusion: str = ""


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------


class Experiment:
    """
    A single A/B experiment comparing two bot strategy variants.
    """

    def __init__(
        self,
        name: str,
        control: Variant,
        treatment: Variant,
        min_games: int = 100,
        significance_level: float = 0.05,
    ):
        self.experiment_id = str(uuid.uuid4())[:8]
        self.name = name
        self.control = control
        self.treatment = treatment
        self.min_games = min_games
        self.significance_level = significance_level
        self.started_at = datetime.utcnow()
        self.results: list[GameResult] = []
        self._concluded = False

        logger.info(
            f"Experiment '{name}' created (id={self.experiment_id}): "
            f"{control.name} vs {treatment.name}"
        )

    def assign_variant(self, game_id: str) -> Variant:
        """
        Assign a game to a variant using weighted random assignment.
        Assignment is deterministic per game_id for reproducibility.
        """
        total_weight = self.control.traffic_weight + self.treatment.traffic_weight
        rng = random.Random(hash(game_id + self.experiment_id))
        roll = rng.random() * total_weight
        if roll < self.control.traffic_weight:
            return self.control
        return self.treatment

    def record_result(self, result: GameResult) -> None:
        """Record a game result for the appropriate variant."""
        if result.variant_name == self.control.name:
            self.control.stats.record(result)
        elif result.variant_name == self.treatment.name:
            self.treatment.stats.record(result)
        else:
            logger.warning(f"Unknown variant: {result.variant_name}")
        self.results.append(result)

    def calculate_significance(self) -> ExperimentResult:
        """Run statistical tests and return experiment result."""
        ctrl = self.control.stats
        trt = self.treatment.stats

        # Chi-squared test for win rate
        chi2, p_win = chi_squared_test(
            ctrl.wins,
            ctrl.total_games,
            trt.wins,
            trt.total_games,
        )

        # Welch's t-test for APM
        t_stat, p_apm = welch_t_test(
            ctrl.avg_apm,
            ctrl.std_apm,
            ctrl.total_games,
            trt.avg_apm,
            trt.std_apm,
            trt.total_games,
        )

        is_significant = p_win < self.significance_level
        winner = self.get_winner() if is_significant else None

        conclusion = self._build_conclusion(winner, chi2, p_win, t_stat, p_apm)

        return ExperimentResult(
            experiment_id=self.experiment_id,
            winner=winner,
            control_stats=ctrl.summary(),
            treatment_stats=trt.summary(),
            win_rate_chi2=round(chi2, 4),
            win_rate_p_value=round(p_win, 4),
            apm_t_stat=round(t_stat, 4),
            apm_p_value=round(p_apm, 4),
            is_significant=is_significant,
            confidence_level=1 - self.significance_level,
            conclusion=conclusion,
        )

    def get_winner(self) -> str | None:
        """Determine the winning variant by win rate."""
        ctrl = self.control.stats
        trt = self.treatment.stats

        total_games = ctrl.total_games + trt.total_games
        if total_games < self.min_games:
            return None

        if ctrl.win_rate > trt.win_rate:
            return self.control.name
        elif trt.win_rate > ctrl.win_rate:
            return self.treatment.name
        return None  # Tie

    def _build_conclusion(self, winner, chi2, p_win, t_stat, p_apm) -> str:
        ctrl = self.control.stats
        trt = self.treatment.stats

        if not winner:
            if ctrl.total_games + trt.total_games < self.min_games:
                return f"Insufficient data (need {self.min_games} games, have {ctrl.total_games + trt.total_games})"
            return f"No significant difference detected (p={p_win:.3f} > {self.significance_level})"

        diff_pct = abs(ctrl.win_rate - trt.win_rate) * 100
        return (
            f"Winner: {winner} with {diff_pct:.1f}% higher win rate "
            f"(chi2={chi2:.2f}, p={p_win:.4f}). "
            f"APM difference: t={t_stat:.2f}, p={p_apm:.4f}."
        )

    def is_ready_to_conclude(self) -> bool:
        total = self.control.stats.total_games + self.treatment.stats.total_games
        return total >= self.min_games

    def status(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "control": self.control.stats.summary(),
            "treatment": self.treatment.stats.summary(),
            "total_games": self.control.stats.total_games
            + self.treatment.stats.total_games,
            "ready_to_conclude": self.is_ready_to_conclude(),
        }


# ---------------------------------------------------------------------------
# ABTestRunner
# ---------------------------------------------------------------------------


class ABTestRunner:
    """
    Manages multiple A/B experiments for the SC2 bot.
    Handles game assignment, result recording, and automated analysis.
    """

    def __init__(self):
        self._experiments: dict[str, Experiment] = {}

    def create_experiment(
        self,
        name: str,
        control_config: dict,
        treatment_config: dict,
        min_games: int = 100,
        significance_level: float = 0.05,
    ) -> Experiment:
        """Create and register a new A/B experiment."""
        control = Variant(
            name=f"{name}_control",
            description="Control variant",
            config=control_config,
        )
        treatment = Variant(
            name=f"{name}_treatment",
            description="Treatment variant",
            config=treatment_config,
        )
        exp = Experiment(
            name=name,
            control=control,
            treatment=treatment,
            min_games=min_games,
            significance_level=significance_level,
        )
        self._experiments[exp.experiment_id] = exp
        return exp

    def run_simulation(
        self,
        experiment: Experiment,
        n_games: int = 200,
        control_true_win_rate: float = 0.38,
        treatment_true_win_rate: float = 0.42,
    ) -> ExperimentResult:
        """
        Simulate A/B test games and return statistical results.
        Used for testing the framework without running real SC2 games.
        """
        logger.info(
            f"Running simulation: {n_games} games for experiment '{experiment.name}'"
        )
        rng = random.Random(42)

        for i in range(n_games):
            game_id = f"game_{i:05d}"
            variant = experiment.assign_variant(game_id)

            true_wr = (
                control_true_win_rate
                if variant.name == experiment.control.name
                else treatment_true_win_rate
            )

            result = GameResult(
                game_id=game_id,
                variant_name=variant.name,
                won=rng.random() < true_wr,
                apm=rng.gauss(
                    120 if variant.name == experiment.control.name else 135,
                    20,
                ),
                game_length_s=rng.gauss(420, 90),
            )
            experiment.record_result(result)

        return experiment.calculate_significance()

    def get_active_experiments(self) -> list[dict]:
        return [exp.status() for exp in self._experiments.values()]

    def conclude_experiment(self, experiment_id: str) -> ExperimentResult:
        exp = self._experiments.get(experiment_id)
        if exp is None:
            raise KeyError(f"Experiment not found: {experiment_id}")
        return exp.calculate_significance()


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    runner = ABTestRunner()

    exp = runner.create_experiment(
        name="roach_hydra_vs_ling_bane",
        control_config={"strategy": "roach_hydra", "aggression": 0.5},
        treatment_config={"strategy": "ling_bane", "aggression": 0.7},
        min_games=100,
        significance_level=0.05,
    )

    result = runner.run_simulation(
        experiment=exp,
        n_games=200,
        control_true_win_rate=0.38,
        treatment_true_win_rate=0.44,
    )

    print(f"\n{'='*60}")
    print(f"A/B Test Results: {exp.name}")
    print(f"{'='*60}")
    print(f"Experiment ID:     {result.experiment_id}")
    print(f"Control:           {result.control_stats['name']}")
    print(f"  Games:           {result.control_stats['total_games']}")
    print(f"  Win Rate:        {result.control_stats['win_rate']:.2%}")
    print(f"  Avg APM:         {result.control_stats['avg_apm']:.1f}")
    print(f"Treatment:         {result.treatment_stats['name']}")
    print(f"  Games:           {result.treatment_stats['total_games']}")
    print(f"  Win Rate:        {result.treatment_stats['win_rate']:.2%}")
    print(f"  Avg APM:         {result.treatment_stats['avg_apm']:.1f}")
    print(
        f"Chi2 (win rate):   {result.win_rate_chi2:.4f} (p={result.win_rate_p_value:.4f})"
    )
    print(f"T-stat (APM):      {result.apm_t_stat:.4f} (p={result.apm_p_value:.4f})")
    print(f"Significant:       {'YES' if result.is_significant else 'NO'}")
    print(f"Winner:            {result.winner or 'None (no significant difference)'}")
    print(f"Conclusion:        {result.conclusion}")
    print(f"{'='*60}")
