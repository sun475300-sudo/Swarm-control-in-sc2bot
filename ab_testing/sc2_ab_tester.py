# Phase 644: A/B Testing Framework for SC2 Strategy Comparison
# Statistical A/B testing for build orders, macro strategies, and micro behaviors

from __future__ import annotations

import json
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np

    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False

# ============================================================
# NumPy Fallback Utilities
# ============================================================


def _np_mean(values: list) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _np_std(values: list) -> float:
    if not values:
        return 0.0
    m = _np_mean(values)
    var = sum((v - m) ** 2 for v in values) / max(len(values), 1)
    return math.sqrt(var)


def _np_random_beta(alpha: float, beta_param: float) -> float:
    """Beta distribution sample via Gamma variates (Joehnk method fallback)."""
    if NP_AVAILABLE:
        return float(np.random.beta(alpha, beta_param))

    # Gamma sampling via Marsaglia-Tsang for shape >= 1
    def _gamma_sample(shape: float) -> float:
        if shape < 1.0:
            u = random.random()
            return _gamma_sample(shape + 1.0) * (u ** (1.0 / shape))
        d = shape - 1.0 / 3.0
        c = 1.0 / math.sqrt(9.0 * d)
        while True:
            x = random.gauss(0, 1)
            v = (1.0 + c * x) ** 3
            if v > 0:
                u = random.random()
                if u < 1.0 - 0.0331 * x**4 or math.log(u) < 0.5 * x**2 + d * (
                    1.0 - v + math.log(v)
                ):
                    return d * v

    g1 = _gamma_sample(alpha)
    g2 = _gamma_sample(beta_param)
    return g1 / (g1 + g2) if (g1 + g2) > 0 else 0.5


def _norm_cdf(z: float) -> float:
    """Standard normal CDF approximation (Abramowitz and Stegun)."""
    a1, a2, a3, a4, a5 = (
        0.254829592,
        -0.284496736,
        1.421413741,
        -1.453152027,
        1.061405429,
    )
    p = 0.3275911
    sign = 1.0 if z >= 0 else -1.0
    z = abs(z)
    t = 1.0 / (1.0 + p * z)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(
        -z * z / 2.0
    )
    return 0.5 * (1.0 + sign * y)


def _norm_ppf(p: float) -> float:
    """Inverse normal CDF (rational approximation by Peter Acklam)."""
    if p <= 0:
        return -6.0
    if p >= 1:
        return 6.0
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


def _chi2_cdf(x: float, k: int) -> float:
    """Chi-squared CDF via incomplete gamma regularized (series expansion)."""
    if x <= 0:
        return 0.0
    a = k / 2.0
    s = math.exp(-x / 2.0) * (x / 2.0) ** a / math.gamma(a + 1.0)
    partial = s
    for n in range(1, 200):
        partial *= (x / 2.0) / (a + n)
        s += partial
        if abs(partial) < 1e-12:
            break
    return min(max(s, 0.0), 1.0)


# ============================================================
# Variant / Experiment Data Classes
# ============================================================


@dataclass
class Variant:
    """A single variant (treatment) in an A/B test."""

    name: str
    variant_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    successes: int = 0
    failures: int = 0
    values: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.successes / self.total

    @property
    def mean_value(self) -> float:
        return _np_mean(self.values)

    @property
    def std_value(self) -> float:
        return _np_std(self.values)

    def record_binary(self, success: bool) -> None:
        if success:
            self.successes += 1
        else:
            self.failures += 1

    def record_value(self, value: float) -> None:
        self.values.append(value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "variant_id": self.variant_id,
            "successes": self.successes,
            "failures": self.failures,
            "total": self.total,
            "rate": round(self.rate, 6),
            "mean_value": round(self.mean_value, 4),
            "metadata": self.metadata,
        }


@dataclass
class Experiment:
    """Container for an A/B test experiment."""

    name: str
    experiment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    variants: List[Variant] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: str = "running"  # running, stopped, concluded
    winner: Optional[str] = None
    confidence: float = 0.0
    sc2_context: Dict[str, Any] = field(default_factory=dict)

    def add_variant(self, name: str, **metadata: Any) -> Variant:
        v = Variant(name=name, metadata=metadata)
        self.variants.append(v)
        return v

    def get_variant(self, name: str) -> Optional[Variant]:
        for v in self.variants:
            if v.name == name:
                return v
        return None

    def total_samples(self) -> int:
        return sum(v.total for v in self.variants)

    def conclude(self, winner_name: str, confidence: float) -> None:
        self.status = "concluded"
        self.winner = winner_name
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "experiment_id": self.experiment_id,
            "status": self.status,
            "winner": self.winner,
            "confidence": round(self.confidence, 6),
            "variants": [v.to_dict() for v in self.variants],
            "sc2_context": self.sc2_context,
        }


# ============================================================
# ABTester - Frequentist Methods
# ============================================================


class ABTester:
    """Frequentist A/B testing engine with z-test and chi-squared."""

    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
        self.experiments: Dict[str, Experiment] = {}

    def create_experiment(
        self, name: str, variant_names: List[str], sc2_context: Optional[Dict] = None
    ) -> Experiment:
        exp = Experiment(name=name, sc2_context=sc2_context or {})
        for vname in variant_names:
            exp.add_variant(vname)
        self.experiments[exp.experiment_id] = exp
        return exp

    # ---- Z-Test for two proportions ----

    def z_test_proportions(self, v1: Variant, v2: Variant) -> Dict[str, Any]:
        """Two-proportion z-test for binary outcomes."""
        n1, n2 = v1.total, v2.total
        if n1 == 0 or n2 == 0:
            return {"z_stat": 0.0, "p_value": 1.0, "significant": False}
        p1, p2 = v1.rate, v2.rate
        p_pool = (v1.successes + v2.successes) / (n1 + n2)
        se = math.sqrt(max(p_pool * (1 - p_pool) * (1.0 / n1 + 1.0 / n2), 1e-15))
        z = (p1 - p2) / se
        p_value = 2.0 * (1.0 - _norm_cdf(abs(z)))
        return {
            "z_stat": round(z, 6),
            "p_value": round(p_value, 6),
            "significant": p_value < self.significance_level,
            "effect_size": round(p1 - p2, 6),
        }

    # ---- Z-Test for two means ----

    def z_test_means(self, v1: Variant, v2: Variant) -> Dict[str, Any]:
        """Two-sample z-test for continuous outcomes."""
        n1, n2 = len(v1.values), len(v2.values)
        if n1 < 2 or n2 < 2:
            return {"z_stat": 0.0, "p_value": 1.0, "significant": False}
        m1, m2 = v1.mean_value, v2.mean_value
        s1, s2 = v1.std_value, v2.std_value
        se = math.sqrt(max(s1**2 / n1 + s2**2 / n2, 1e-15))
        z = (m1 - m2) / se
        p_value = 2.0 * (1.0 - _norm_cdf(abs(z)))
        return {
            "z_stat": round(z, 6),
            "p_value": round(p_value, 6),
            "significant": p_value < self.significance_level,
            "effect_size": round(m1 - m2, 4),
        }

    # ---- Chi-Squared Goodness of Fit ----

    def chi_squared_test(self, experiment: Experiment) -> Dict[str, Any]:
        """Chi-squared test across all variants (k-way comparison)."""
        k = len(experiment.variants)
        if k < 2:
            return {"chi2": 0.0, "p_value": 1.0, "significant": False}
        total_success = sum(v.successes for v in experiment.variants)
        total_fail = sum(v.failures for v in experiment.variants)
        grand_total = total_success + total_fail
        if grand_total == 0:
            return {"chi2": 0.0, "p_value": 1.0, "significant": False}
        chi2 = 0.0
        for v in experiment.variants:
            n = v.total
            if n == 0:
                continue
            e_success = n * total_success / grand_total
            e_fail = n * total_fail / grand_total
            if e_success > 0:
                chi2 += (v.successes - e_success) ** 2 / e_success
            if e_fail > 0:
                chi2 += (v.failures - e_fail) ** 2 / e_fail
        df = k - 1
        p_value = 1.0 - _chi2_cdf(chi2, df)
        return {
            "chi2": round(chi2, 6),
            "df": df,
            "p_value": round(p_value, 6),
            "significant": p_value < self.significance_level,
        }

    # ---- Sample Size Calculator ----

    @staticmethod
    def required_sample_size(
        baseline_rate: float, mde: float, alpha: float = 0.05, power: float = 0.80
    ) -> int:
        """Minimum sample size per variant for detecting a given MDE."""
        z_alpha = _norm_ppf(1.0 - alpha / 2.0)
        z_beta = _norm_ppf(power)
        p1 = baseline_rate
        p2 = baseline_rate + mde
        p_avg = (p1 + p2) / 2.0
        numerator = (
            z_alpha * math.sqrt(2 * p_avg * (1 - p_avg))
            + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        ) ** 2
        denominator = (p1 - p2) ** 2
        if denominator == 0:
            return 0
        return int(math.ceil(numerator / denominator))

    # ---- Sequential Testing with Bonferroni ----

    def sequential_test(
        self, experiment: Experiment, num_checks: int = 10
    ) -> Dict[str, Any]:
        """Sequential testing with Bonferroni correction for early stopping."""
        corrected_alpha = self.significance_level / num_checks
        if len(experiment.variants) < 2:
            return {"can_stop": False, "reason": "Need at least 2 variants"}
        v1, v2 = experiment.variants[0], experiment.variants[1]
        result = self.z_test_proportions(v1, v2)
        can_stop = result["p_value"] < corrected_alpha
        return {
            "can_stop": can_stop,
            "corrected_alpha": round(corrected_alpha, 6),
            "observed_p": result["p_value"],
            "z_stat": result["z_stat"],
            "winner": (
                v1.name if result["z_stat"] > 0 else v2.name if can_stop else None
            ),
        }


# ============================================================
# BayesianABTest
# ============================================================


class BayesianABTest:
    """Bayesian A/B testing with Beta-Binomial model."""

    def __init__(
        self,
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0,
        num_samples: int = 10000,
    ):
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        self.num_samples = num_samples

    def posterior_params(self, variant: Variant) -> Tuple[float, float]:
        """Return posterior Beta(alpha, beta) parameters."""
        alpha = self.prior_alpha + variant.successes
        beta_p = self.prior_beta + variant.failures
        return alpha, beta_p

    def credible_interval(
        self, variant: Variant, level: float = 0.95
    ) -> Tuple[float, float]:
        """Compute credible interval for a variant's win rate."""
        alpha, beta_p = self.posterior_params(variant)
        tail = (1.0 - level) / 2.0
        samples = sorted(
            [_np_random_beta(alpha, beta_p) for _ in range(self.num_samples)]
        )
        lo_idx = int(tail * len(samples))
        hi_idx = int((1.0 - tail) * len(samples)) - 1
        return round(samples[max(lo_idx, 0)], 6), round(
            samples[min(hi_idx, len(samples) - 1)], 6
        )

    def probability_b_beats_a(self, variant_a: Variant, variant_b: Variant) -> float:
        """Monte Carlo estimate of P(B > A)."""
        a_alpha, a_beta = self.posterior_params(variant_a)
        b_alpha, b_beta = self.posterior_params(variant_b)
        wins = 0
        for _ in range(self.num_samples):
            sa = _np_random_beta(a_alpha, a_beta)
            sb = _np_random_beta(b_alpha, b_beta)
            if sb > sa:
                wins += 1
        return round(wins / self.num_samples, 6)

    def expected_loss(self, variant_a: Variant, variant_b: Variant) -> Dict[str, float]:
        """Expected loss for choosing A or B."""
        a_alpha, a_beta = self.posterior_params(variant_a)
        b_alpha, b_beta = self.posterior_params(variant_b)
        loss_a, loss_b = 0.0, 0.0
        for _ in range(self.num_samples):
            sa = _np_random_beta(a_alpha, a_beta)
            sb = _np_random_beta(b_alpha, b_beta)
            loss_a += max(sb - sa, 0.0)
            loss_b += max(sa - sb, 0.0)
        n = self.num_samples
        return {
            "loss_choosing_a": round(loss_a / n, 6),
            "loss_choosing_b": round(loss_b / n, 6),
        }

    def full_analysis(self, experiment: Experiment) -> Dict[str, Any]:
        """Run full Bayesian analysis across all variant pairs."""
        results: Dict[str, Any] = {"experiment": experiment.name, "pairs": []}
        variants = experiment.variants
        for i in range(len(variants)):
            for j in range(i + 1, len(variants)):
                va, vb = variants[i], variants[j]
                prob_b = self.probability_b_beats_a(va, vb)
                ci_a = self.credible_interval(va)
                ci_b = self.credible_interval(vb)
                loss = self.expected_loss(va, vb)
                results["pairs"].append(
                    {
                        "a": va.name,
                        "b": vb.name,
                        "prob_b_beats_a": prob_b,
                        "ci_a": ci_a,
                        "ci_b": ci_b,
                        "expected_loss": loss,
                    }
                )
        return results


# ============================================================
# MultiArmedBandit
# ============================================================


class MultiArmedBandit:
    """Multi-armed bandit algorithms for adaptive strategy allocation."""

    def __init__(self, variant_names: List[str], algorithm: str = "thompson"):
        self.variant_names = variant_names
        self.algorithm = algorithm  # "thompson", "ucb", "epsilon_greedy"
        self.successes: Dict[str, int] = {n: 0 for n in variant_names}
        self.failures: Dict[str, int] = {n: 0 for n in variant_names}
        self.pulls: Dict[str, int] = {n: 0 for n in variant_names}
        self.total_pulls: int = 0
        self.epsilon: float = 0.1
        self.ucb_c: float = 2.0
        self.history: List[Dict[str, Any]] = []

    def select_arm(self) -> str:
        """Select an arm based on the configured algorithm."""
        if self.algorithm == "thompson":
            return self._thompson_select()
        elif self.algorithm == "ucb":
            return self._ucb_select()
        elif self.algorithm == "epsilon_greedy":
            return self._epsilon_greedy_select()
        return random.choice(self.variant_names)

    def _thompson_select(self) -> str:
        """Thompson Sampling: draw from Beta posteriors, pick highest."""
        best_name = self.variant_names[0]
        best_sample = -1.0
        for name in self.variant_names:
            alpha = self.successes[name] + 1
            beta_p = self.failures[name] + 1
            sample = _np_random_beta(float(alpha), float(beta_p))
            if sample > best_sample:
                best_sample = sample
                best_name = name
        return best_name

    def _ucb_select(self) -> str:
        """Upper Confidence Bound arm selection."""
        best_name = self.variant_names[0]
        best_ucb = -1.0
        for name in self.variant_names:
            n = self.pulls[name]
            if n == 0:
                return name  # explore unvisited
            rate = self.successes[name] / n
            bonus = self.ucb_c * math.sqrt(math.log(max(self.total_pulls, 1)) / n)
            ucb_val = rate + bonus
            if ucb_val > best_ucb:
                best_ucb = ucb_val
                best_name = name
        return best_name

    def _epsilon_greedy_select(self) -> str:
        """Epsilon-Greedy: exploit best arm with 1-epsilon, explore otherwise."""
        if random.random() < self.epsilon:
            return random.choice(self.variant_names)
        best_name = self.variant_names[0]
        best_rate = -1.0
        for name in self.variant_names:
            n = self.pulls[name]
            rate = self.successes[name] / n if n > 0 else 0.0
            if rate > best_rate:
                best_rate = rate
                best_name = name
        return best_name

    def update(self, arm_name: str, reward: bool) -> None:
        """Record outcome for a pulled arm."""
        self.pulls[arm_name] += 1
        self.total_pulls += 1
        if reward:
            self.successes[arm_name] += 1
        else:
            self.failures[arm_name] += 1
        self.history.append(
            {
                "step": self.total_pulls,
                "arm": arm_name,
                "reward": int(reward),
            }
        )

    def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics per arm."""
        stats = {}
        for name in self.variant_names:
            n = self.pulls[name]
            rate = self.successes[name] / n if n > 0 else 0.0
            stats[name] = {
                "pulls": n,
                "successes": self.successes[name],
                "failures": self.failures[name],
                "win_rate": round(rate, 6),
            }
        return stats

    def cumulative_regret(self, true_rates: Dict[str, float]) -> float:
        """Compute cumulative regret given true arm win rates."""
        best_rate = max(true_rates.values())
        regret = 0.0
        for entry in self.history:
            arm = entry["arm"]
            regret += best_rate - true_rates.get(arm, 0.0)
        return round(regret, 4)


# ============================================================
# SC2-Specific A/B Testing Helpers
# ============================================================


class SC2StrategyTester:
    """High-level A/B tester specialized for StarCraft II strategies."""

    def __init__(self, significance_level: float = 0.05):
        self.freq_tester = ABTester(significance_level=significance_level)
        self.bayes_tester = BayesianABTest(num_samples=5000)
        self.experiments: Dict[str, Experiment] = {}

    def compare_build_orders(
        self, build_a: str, build_b: str, results_a: List[bool], results_b: List[bool]
    ) -> Dict[str, Any]:
        """Compare two build orders by win/loss records."""
        exp = self.freq_tester.create_experiment(
            name=f"BuildOrder: {build_a} vs {build_b}",
            variant_names=[build_a, build_b],
            sc2_context={"type": "build_order_comparison"},
        )
        va, vb = exp.variants[0], exp.variants[1]
        for r in results_a:
            va.record_binary(r)
        for r in results_b:
            vb.record_binary(r)
        freq_result = self.freq_tester.z_test_proportions(va, vb)
        bayes_result = self.bayes_tester.probability_b_beats_a(va, vb)
        ci_a = self.bayes_tester.credible_interval(va)
        ci_b = self.bayes_tester.credible_interval(vb)
        return {
            "build_a": {
                "name": build_a,
                "win_rate": va.rate,
                "n": va.total,
                "ci": ci_a,
            },
            "build_b": {
                "name": build_b,
                "win_rate": vb.rate,
                "n": vb.total,
                "ci": ci_b,
            },
            "frequentist": freq_result,
            "prob_b_better": bayes_result,
        }

    def compare_macro_strategies(
        self,
        strategy_a: str,
        strategy_b: str,
        scores_a: List[float],
        scores_b: List[float],
    ) -> Dict[str, Any]:
        """Compare macro strategies by continuous score (e.g., resource collection rate)."""
        exp = Experiment(
            name=f"Macro: {strategy_a} vs {strategy_b}",
            sc2_context={"type": "macro_comparison"},
        )
        va = exp.add_variant(strategy_a)
        vb = exp.add_variant(strategy_b)
        for s in scores_a:
            va.record_value(s)
        for s in scores_b:
            vb.record_value(s)
        result = self.freq_tester.z_test_means(va, vb)
        return {
            "strategy_a": {
                "name": strategy_a,
                "mean": va.mean_value,
                "std": va.std_value,
                "n": len(va.values),
            },
            "strategy_b": {
                "name": strategy_b,
                "mean": vb.mean_value,
                "std": vb.std_value,
                "n": len(vb.values),
            },
            "test_result": result,
        }

    def compare_micro_behaviors(
        self,
        behavior_a: str,
        behavior_b: str,
        kd_a: List[Tuple[int, int]],
        kd_b: List[Tuple[int, int]],
    ) -> Dict[str, Any]:
        """Compare micro behaviors by kill/death ratios."""

        def kd_ratios(kd_list: List[Tuple[int, int]]) -> List[float]:
            return [k / max(d, 1) for k, d in kd_list]

        ratios_a = kd_ratios(kd_a)
        ratios_b = kd_ratios(kd_b)
        exp = Experiment(
            name=f"Micro: {behavior_a} vs {behavior_b}",
            sc2_context={"type": "micro_comparison"},
        )
        va = exp.add_variant(behavior_a)
        vb = exp.add_variant(behavior_b)
        for r in ratios_a:
            va.record_value(r)
        for r in ratios_b:
            vb.record_value(r)
        result = self.freq_tester.z_test_means(va, vb)
        return {
            "behavior_a": {
                "name": behavior_a,
                "mean_kd": round(_np_mean(ratios_a), 4),
                "n": len(ratios_a),
            },
            "behavior_b": {
                "name": behavior_b,
                "mean_kd": round(_np_mean(ratios_b), 4),
                "n": len(ratios_b),
            },
            "test_result": result,
        }

    def adaptive_strategy_selection(
        self,
        strategy_names: List[str],
        num_rounds: int = 100,
        true_rates: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Run adaptive multi-armed bandit for strategy selection."""
        if true_rates is None:
            true_rates = {name: random.uniform(0.3, 0.7) for name in strategy_names}
        bandit = MultiArmedBandit(strategy_names, algorithm="thompson")
        for _ in range(num_rounds):
            arm = bandit.select_arm()
            reward = random.random() < true_rates[arm]
            bandit.update(arm, reward)
        return {
            "algorithm": "thompson_sampling",
            "rounds": num_rounds,
            "stats": bandit.get_stats(),
            "cumulative_regret": bandit.cumulative_regret(true_rates),
            "true_rates": {k: round(v, 4) for k, v in true_rates.items()},
        }


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate A/B testing framework for SC2 strategies."""
    print("=" * 70)
    print("Phase 644: A/B Testing Framework for SC2 Strategy Comparison")
    print("=" * 70)

    # --- Sample Size Calculator ---
    print("\n[1] Sample Size Calculator")
    n = ABTester.required_sample_size(baseline_rate=0.50, mde=0.05)
    print(f"    Baseline=50%, MDE=5% -> need {n} samples per variant")

    # --- Frequentist Build Order Test ---
    print("\n[2] Frequentist Build Order Comparison")
    tester = SC2StrategyTester()
    results_a = [random.random() < 0.55 for _ in range(200)]
    results_b = [random.random() < 0.48 for _ in range(200)]
    bo_result = tester.compare_build_orders(
        "12Pool", "HatchFirst", results_a, results_b
    )
    print(f"    12Pool win rate: {bo_result['build_a']['win_rate']:.3f}")
    print(f"    HatchFirst win rate: {bo_result['build_b']['win_rate']:.3f}")
    print(f"    P-value: {bo_result['frequentist']['p_value']:.4f}")
    print(f"    Significant: {bo_result['frequentist']['significant']}")

    # --- Bayesian Analysis ---
    print("\n[3] Bayesian Analysis")
    print(f"    P(HatchFirst beats 12Pool): {bo_result['prob_b_better']:.4f}")
    print(f"    12Pool 95% CI: {bo_result['build_a']['ci']}")
    print(f"    HatchFirst 95% CI: {bo_result['build_b']['ci']}")

    # --- Macro Strategy Comparison ---
    print("\n[4] Macro Strategy Comparison (Resource Collection)")
    scores_greedy = [random.gauss(4200, 300) for _ in range(50)]
    scores_balanced = [random.gauss(4000, 250) for _ in range(50)]
    macro_result = tester.compare_macro_strategies(
        "GreedyExpand", "Balanced", scores_greedy, scores_balanced
    )
    print(f"    GreedyExpand mean: {macro_result['strategy_a']['mean']:.1f}")
    print(f"    Balanced mean: {macro_result['strategy_b']['mean']:.1f}")
    print(f"    P-value: {macro_result['test_result']['p_value']:.4f}")

    # --- Micro Behavior Comparison ---
    print("\n[5] Micro Behavior Comparison (K/D Ratio)")
    kd_split = [(random.randint(5, 20), random.randint(2, 10)) for _ in range(40)]
    kd_focus = [(random.randint(8, 25), random.randint(3, 12)) for _ in range(40)]
    micro_result = tester.compare_micro_behaviors(
        "SplitMicro", "FocusFire", kd_split, kd_focus
    )
    print(f"    SplitMicro mean K/D: {micro_result['behavior_a']['mean_kd']:.3f}")
    print(f"    FocusFire mean K/D: {micro_result['behavior_b']['mean_kd']:.3f}")

    # --- Multi-Armed Bandit ---
    print("\n[6] Adaptive Strategy Selection (Thompson Sampling)")
    bandit_result = tester.adaptive_strategy_selection(
        ["ZergRush", "MacroHatch", "LingBane", "RoachRavager"],
        num_rounds=500,
        true_rates={
            "ZergRush": 0.45,
            "MacroHatch": 0.60,
            "LingBane": 0.52,
            "RoachRavager": 0.55,
        },
    )
    print(f"    Cumulative Regret: {bandit_result['cumulative_regret']:.2f}")
    for name, stat in bandit_result["stats"].items():
        print(f"    {name}: pulls={stat['pulls']}, win_rate={stat['win_rate']:.3f}")

    # --- Sequential Testing ---
    print("\n[7] Sequential Testing (Early Stopping)")
    freq = ABTester(significance_level=0.05)
    exp = freq.create_experiment("SeqTest", ["ControlBuild", "NewBuild"])
    for _ in range(150):
        exp.variants[0].record_binary(random.random() < 0.50)
        exp.variants[1].record_binary(random.random() < 0.58)
    seq_result = freq.sequential_test(exp, num_checks=5)
    print(f"    Can stop early: {seq_result['can_stop']}")
    print(f"    Corrected alpha: {seq_result['corrected_alpha']:.4f}")
    print(f"    Observed p-value: {seq_result['observed_p']:.4f}")

    # --- Chi-Squared Multi-Variant ---
    print("\n[8] Chi-Squared Test (3 variants)")
    exp3 = freq.create_experiment("MultiVar", ["BuildA", "BuildB", "BuildC"])
    for _ in range(100):
        exp3.variants[0].record_binary(random.random() < 0.50)
        exp3.variants[1].record_binary(random.random() < 0.55)
        exp3.variants[2].record_binary(random.random() < 0.60)
    chi_result = freq.chi_squared_test(exp3)
    print(
        f"    Chi2={chi_result['chi2']:.4f}, df={chi_result['df']}, p={chi_result['p_value']:.4f}"
    )

    print("\n" + "=" * 70)
    print("Phase 644 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 644: A/B Testing registered
