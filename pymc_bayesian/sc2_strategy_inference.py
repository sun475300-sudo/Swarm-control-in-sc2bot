# Phase 593: PyMC
"""
sc2_strategy_inference.py — Bayesian Strategy Inference for StarCraft II with PyMC

Provides probabilistic models for enemy strategy prediction, win-rate estimation,
timing prediction via Gaussian Processes, hierarchical matchup modelling,
and full MCMC diagnostics.

Graceful fallback to a pure-NumPy implementation when PyMC is absent.
"""

from __future__ import annotations

import logging
import math
import random
import warnings
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as sp_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_strategy_inference")

# ---------------------------------------------------------------------------
# Optional PyMC / ArviZ imports — graceful fallback
# ---------------------------------------------------------------------------
try:
    import pymc as pm
    import arviz as az

    PYMC_AVAILABLE = True
    log.info("PyMC %s / ArviZ %s available.", pm.__version__, az.__version__)
except ImportError:
    PYMC_AVAILABLE = False
    pm = None  # type: ignore[assignment]
    az = None  # type: ignore[assignment]
    log.warning(
        "PyMC/ArviZ not installed. Running pure-NumPy fallback. "
        "Install with: pip install pymc arviz"
    )

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False
    plt = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# SC2 strategy / matchup enumerations
# ---------------------------------------------------------------------------
class ZergStrategy(Enum):
    """Common Zerg strategies."""

    TWELVE_POOL = auto()
    HATCH_FIRST = auto()
    LING_BANE_MUTA = auto()
    ROACH_RAVAGER = auto()
    HYDRA_LURKER = auto()
    SWARM_HOST_NYDUS = auto()
    ULTRA_LING = auto()
    BROOD_LORD_CORRUPTOR = auto()
    MASS_MUTA = auto()
    MACRO_HATCH = auto()


class EnemyStrategy(Enum):
    """Generalised enemy strategies (observable via scouting)."""

    RUSH = auto()
    TIMING_ATTACK = auto()
    TWO_BASE_ALL_IN = auto()
    MACRO_EXPAND = auto()
    AIR_TECH = auto()
    TURTLE_DEATHBALL = auto()
    HARASSMENT = auto()
    CHEESE = auto()


class Matchup(Enum):
    ZVZ = "ZvZ"
    ZVT = "ZvT"
    ZVP = "ZvP"


# ---------------------------------------------------------------------------
# Observation data structures
# ---------------------------------------------------------------------------
@dataclass
class ScoutingObservation:
    """A single scouting observation at a game time."""

    game_time_seconds: float
    enemy_worker_count: int = 0
    enemy_gas_count: int = 0
    enemy_base_count: int = 1
    enemy_barracks_or_gateway: int = 0
    enemy_tech_structures: int = 0
    enemy_army_supply: float = 0.0
    expansion_timing: Optional[float] = None
    detected_air_tech: bool = False
    detected_aggression: bool = False


@dataclass
class MatchHistory:
    """Win/loss record for a specific matchup or strategy."""

    wins: int = 0
    losses: int = 0

    @property
    def total(self) -> int:
        return self.wins + self.losses

    @property
    def win_rate(self) -> float:
        return self.wins / self.total if self.total > 0 else 0.5


# ---------------------------------------------------------------------------
# Meta-game prior knowledge
# ---------------------------------------------------------------------------
META_GAME_PRIORS: Dict[str, Dict[str, float]] = {
    Matchup.ZVZ.value: {
        EnemyStrategy.RUSH.name: 0.25,
        EnemyStrategy.TIMING_ATTACK.name: 0.15,
        EnemyStrategy.TWO_BASE_ALL_IN.name: 0.10,
        EnemyStrategy.MACRO_EXPAND.name: 0.20,
        EnemyStrategy.AIR_TECH.name: 0.10,
        EnemyStrategy.TURTLE_DEATHBALL.name: 0.05,
        EnemyStrategy.HARASSMENT.name: 0.10,
        EnemyStrategy.CHEESE.name: 0.05,
    },
    Matchup.ZVT.value: {
        EnemyStrategy.RUSH.name: 0.10,
        EnemyStrategy.TIMING_ATTACK.name: 0.20,
        EnemyStrategy.TWO_BASE_ALL_IN.name: 0.15,
        EnemyStrategy.MACRO_EXPAND.name: 0.25,
        EnemyStrategy.AIR_TECH.name: 0.05,
        EnemyStrategy.TURTLE_DEATHBALL.name: 0.10,
        EnemyStrategy.HARASSMENT.name: 0.10,
        EnemyStrategy.CHEESE.name: 0.05,
    },
    Matchup.ZVP.value: {
        EnemyStrategy.RUSH.name: 0.08,
        EnemyStrategy.TIMING_ATTACK.name: 0.18,
        EnemyStrategy.TWO_BASE_ALL_IN.name: 0.12,
        EnemyStrategy.MACRO_EXPAND.name: 0.22,
        EnemyStrategy.AIR_TECH.name: 0.15,
        EnemyStrategy.TURTLE_DEATHBALL.name: 0.12,
        EnemyStrategy.HARASSMENT.name: 0.08,
        EnemyStrategy.CHEESE.name: 0.05,
    },
}

# Likelihood features: P(observation_feature | strategy)
# Each strategy has expected feature distributions
STRATEGY_LIKELIHOODS: Dict[str, Dict[str, Tuple[float, float]]] = {
    # strategy -> {feature -> (mean, std)}
    EnemyStrategy.RUSH.name: {
        "worker_count_2min": (14.0, 2.0),
        "gas_timing": (30.0, 10.0),
        "army_supply_3min": (8.0, 3.0),
        "base_count_4min": (1.0, 0.1),
        "expansion_timing": (300.0, 60.0),
    },
    EnemyStrategy.TIMING_ATTACK.name: {
        "worker_count_2min": (18.0, 2.0),
        "gas_timing": (60.0, 15.0),
        "army_supply_3min": (5.0, 2.0),
        "base_count_4min": (2.0, 0.3),
        "expansion_timing": (120.0, 30.0),
    },
    EnemyStrategy.TWO_BASE_ALL_IN.name: {
        "worker_count_2min": (20.0, 2.0),
        "gas_timing": (50.0, 12.0),
        "army_supply_3min": (4.0, 2.0),
        "base_count_4min": (2.0, 0.2),
        "expansion_timing": (90.0, 20.0),
    },
    EnemyStrategy.MACRO_EXPAND.name: {
        "worker_count_2min": (22.0, 3.0),
        "gas_timing": (80.0, 20.0),
        "army_supply_3min": (2.0, 1.5),
        "base_count_4min": (3.0, 0.5),
        "expansion_timing": (60.0, 15.0),
    },
    EnemyStrategy.AIR_TECH.name: {
        "worker_count_2min": (19.0, 2.0),
        "gas_timing": (40.0, 10.0),
        "army_supply_3min": (3.0, 2.0),
        "base_count_4min": (2.0, 0.3),
        "expansion_timing": (100.0, 25.0),
    },
    EnemyStrategy.TURTLE_DEATHBALL.name: {
        "worker_count_2min": (20.0, 2.0),
        "gas_timing": (60.0, 15.0),
        "army_supply_3min": (2.0, 1.0),
        "base_count_4min": (2.0, 0.3),
        "expansion_timing": (110.0, 30.0),
    },
    EnemyStrategy.HARASSMENT.name: {
        "worker_count_2min": (17.0, 2.0),
        "gas_timing": (45.0, 12.0),
        "army_supply_3min": (6.0, 2.5),
        "base_count_4min": (2.0, 0.4),
        "expansion_timing": (95.0, 25.0),
    },
    EnemyStrategy.CHEESE.name: {
        "worker_count_2min": (12.0, 2.0),
        "gas_timing": (25.0, 8.0),
        "army_supply_3min": (10.0, 3.0),
        "base_count_4min": (1.0, 0.1),
        "expansion_timing": (400.0, 80.0),
    },
}


# ---------------------------------------------------------------------------
# Pure-NumPy fallback implementations
# ---------------------------------------------------------------------------
class _FallbackBetaBinomial:
    """Beta-Binomial conjugate model for win rate estimation."""

    def __init__(self, alpha_prior: float = 1.0, beta_prior: float = 1.0):
        self.alpha = alpha_prior
        self.beta = beta_prior

    def update(self, wins: int, losses: int) -> None:
        self.alpha += wins
        self.beta += losses

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    def credible_interval(self, level: float = 0.95) -> Tuple[float, float]:
        tail = (1 - level) / 2
        lo = sp_stats.beta.ppf(tail, self.alpha, self.beta)
        hi = sp_stats.beta.ppf(1 - tail, self.alpha, self.beta)
        return (float(lo), float(hi))

    def sample(self, n: int = 1000) -> np.ndarray:
        return np.random.beta(self.alpha, self.beta, size=n)


class _FallbackGaussianProcess:
    """Simple GP regression with squared exponential kernel (NumPy only)."""

    def __init__(
        self,
        length_scale: float = 60.0,
        signal_variance: float = 1.0,
        noise_variance: float = 0.1,
    ):
        self.l = length_scale
        self.sf2 = signal_variance
        self.sn2 = noise_variance
        self.X_train: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None
        self._K_inv: Optional[np.ndarray] = None

    def _kernel(self, X1: np.ndarray, X2: np.ndarray) -> np.ndarray:
        sq_dist = np.subtract.outer(X1.ravel(), X2.ravel()) ** 2
        return self.sf2 * np.exp(-0.5 * sq_dist / self.l**2)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.X_train = X.ravel()
        self.y_train = y.ravel()
        K = self._kernel(self.X_train, self.X_train)
        K += self.sn2 * np.eye(len(self.X_train))
        self._K_inv = np.linalg.inv(K)

    def predict(self, X_new: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if self.X_train is None or self._K_inv is None:
            raise RuntimeError("GP not fitted yet.")
        X_new = X_new.ravel()
        K_s = self._kernel(self.X_train, X_new)
        K_ss = self._kernel(X_new, X_new)

        mu = K_s.T @ self._K_inv @ self.y_train
        cov = K_ss - K_s.T @ self._K_inv @ K_s
        std = np.sqrt(np.maximum(np.diag(cov), 0.0))
        return mu, std


class _FallbackMCMC:
    """
    Lightweight Metropolis-Hastings sampler for strategy posterior.
    Used when PyMC is not available.
    """

    def __init__(self, n_strategies: int, prior: np.ndarray):
        self.n = n_strategies
        self.prior = prior / prior.sum()

    def sample_posterior(
        self,
        log_likelihood_fn,
        n_samples: int = 2000,
        n_warmup: int = 500,
        proposal_scale: float = 0.1,
    ) -> np.ndarray:
        """Run MH on a Dirichlet-distributed strategy probability vector."""
        current = self.prior.copy()
        samples = []
        accepted = 0

        def log_prior(x: np.ndarray) -> float:
            if np.any(x <= 0):
                return -np.inf
            return float(np.sum((self.prior * 10 - 1) * np.log(x)))

        current_lp = log_prior(current) + log_likelihood_fn(current)

        for i in range(n_samples + n_warmup):
            proposal = current + np.random.normal(0, proposal_scale, self.n)
            proposal = np.abs(proposal)
            proposal /= proposal.sum()

            prop_lp = log_prior(proposal) + log_likelihood_fn(proposal)
            log_alpha = prop_lp - current_lp

            if np.log(np.random.uniform()) < log_alpha:
                current = proposal
                current_lp = prop_lp
                accepted += 1

            if i >= n_warmup:
                samples.append(current.copy())

        acceptance_rate = accepted / (n_samples + n_warmup)
        log.info("MH acceptance rate: %.2f%%", acceptance_rate * 100)
        return np.array(samples)


# ---------------------------------------------------------------------------
# Main SC2StrategyInference class
# ---------------------------------------------------------------------------
class SC2StrategyInference:
    """
    Bayesian strategy inference engine for StarCraft II.

    Features
    --------
    * Prior distributions from meta-game statistics
    * Posterior updating with scouting observations
    * MCMC sampling (NUTS via PyMC or MH fallback)
    * Hierarchical model for matchup-specific parameters
    * Win probability estimation with credible intervals
    * Beta-Binomial model for win rate estimation
    * Gaussian Process for attack timing prediction
    * Model comparison (WAIC, LOO)
    * Trace analysis and convergence diagnostics
    """

    def __init__(self, matchup: Matchup = Matchup.ZVT) -> None:
        self.matchup = matchup
        self._use_pymc = PYMC_AVAILABLE
        self.strategies = list(EnemyStrategy)
        self.strategy_names = [s.name for s in self.strategies]
        self.n_strategies = len(self.strategies)

        # Prior probabilities
        priors = META_GAME_PRIORS.get(matchup.value, {})
        self.prior = np.array(
            [priors.get(s.name, 1.0 / self.n_strategies) for s in self.strategies]
        )
        self.prior /= self.prior.sum()

        # Posterior (starts as prior)
        self.posterior = self.prior.copy()

        # Observations
        self.observations: List[ScoutingObservation] = []

        # Match history for Beta-Binomial
        self.match_histories: Dict[str, _FallbackBetaBinomial] = {
            m.value: _FallbackBetaBinomial(alpha_prior=5.0, beta_prior=5.0)
            for m in Matchup
        }

        # GP for timing prediction
        self.timing_gp = _FallbackGaussianProcess(
            length_scale=60.0,
            signal_variance=1.0,
            noise_variance=0.1,
        )
        self._timing_data_X: List[float] = []
        self._timing_data_y: List[float] = []

        # MCMC traces
        self._trace: Optional[Any] = None
        self._pymc_model: Optional[Any] = None

        log.info(
            "SC2StrategyInference initialised — matchup=%s, backend=%s, "
            "%d strategies tracked",
            matchup.value,
            "pymc" if self._use_pymc else "numpy-fallback",
            self.n_strategies,
        )

    # -- prior & likelihood -------------------------------------------------
    def _compute_observation_features(
        self,
        obs: ScoutingObservation,
    ) -> Dict[str, float]:
        """Extract features from a scouting observation for likelihood calc."""
        return {
            "worker_count_2min": float(obs.enemy_worker_count),
            "gas_timing": float(obs.enemy_gas_count * 30),
            "army_supply_3min": obs.enemy_army_supply,
            "base_count_4min": float(obs.enemy_base_count),
            "expansion_timing": obs.expansion_timing or 120.0,
        }

    def _log_likelihood_observation(
        self,
        obs: ScoutingObservation,
        strategy_name: str,
    ) -> float:
        """Log-likelihood of an observation given a strategy."""
        features = self._compute_observation_features(obs)
        likelihoods = STRATEGY_LIKELIHOODS.get(strategy_name, {})
        log_lik = 0.0
        for feat_name, feat_val in features.items():
            if feat_name in likelihoods:
                mu, sigma = likelihoods[feat_name]
                log_lik += sp_stats.norm.logpdf(feat_val, loc=mu, scale=sigma)
        return log_lik

    # -- posterior updating --------------------------------------------------
    def update_with_observation(self, obs: ScoutingObservation) -> np.ndarray:
        """
        Update strategy posterior given a new scouting observation.
        Uses Bayes' rule: P(strategy|obs) proportional to P(obs|strategy) * P(strategy).
        Returns the updated posterior.
        """
        self.observations.append(obs)
        log_posteriors = np.zeros(self.n_strategies)
        for i, strat in enumerate(self.strategies):
            log_prior = np.log(self.posterior[i] + 1e-12)
            log_lik = self._log_likelihood_observation(obs, strat.name)
            log_posteriors[i] = log_prior + log_lik

        # Normalise in log-space for numerical stability
        log_posteriors -= np.max(log_posteriors)
        posteriors = np.exp(log_posteriors)
        posteriors /= posteriors.sum()
        self.posterior = posteriors

        log.info(
            "Posterior updated with observation at t=%.0fs — top strategy: %s (%.1f%%)",
            obs.game_time_seconds,
            self.strategy_names[np.argmax(posteriors)],
            np.max(posteriors) * 100,
        )
        return self.posterior

    def get_strategy_probabilities(self) -> Dict[str, float]:
        """Return current posterior probabilities for all strategies."""
        return {
            name: float(prob) for name, prob in zip(self.strategy_names, self.posterior)
        }

    def most_likely_strategy(self) -> Tuple[str, float]:
        """Return the most probable enemy strategy and its probability."""
        idx = int(np.argmax(self.posterior))
        return self.strategy_names[idx], float(self.posterior[idx])

    # -- MCMC sampling (NUTS / MH) ------------------------------------------
    def run_mcmc(
        self,
        n_samples: int = 2000,
        n_warmup: int = 500,
        chains: int = 2,
        target_accept: float = 0.9,
    ) -> Dict[str, Any]:
        """
        Run full MCMC sampling for strategy posterior.
        Uses PyMC NUTS sampler if available, otherwise Metropolis-Hastings.
        Returns trace summary.
        """
        if self._use_pymc:
            return self._run_pymc_mcmc(n_samples, n_warmup, chains, target_accept)
        return self._run_fallback_mcmc(n_samples, n_warmup)

    def _run_pymc_mcmc(
        self,
        n_samples: int,
        n_warmup: int,
        chains: int,
        target_accept: float,
    ) -> Dict[str, Any]:
        """Full PyMC model with NUTS sampler."""
        with pm.Model() as model:
            # Dirichlet prior over strategy probabilities
            strategy_probs = pm.Dirichlet(
                "strategy_probs",
                a=self.prior * 10 + 1,
                shape=self.n_strategies,
            )

            # Likelihood for each observation
            for i, obs in enumerate(self.observations):
                features = self._compute_observation_features(obs)
                for j, strat in enumerate(self.strategies):
                    likelihoods = STRATEGY_LIKELIHOODS.get(strat.name, {})
                    for feat_name, feat_val in features.items():
                        if feat_name in likelihoods:
                            mu_prior, sigma_prior = likelihoods[feat_name]
                            pm.Normal(
                                f"obs_{i}_{strat.name}_{feat_name}",
                                mu=mu_prior,
                                sigma=sigma_prior,
                                observed=feat_val,
                            )

            # Sample
            self._trace = pm.sample(
                draws=n_samples,
                tune=n_warmup,
                chains=chains,
                target_accept=target_accept,
                return_inferencedata=True,
                progressbar=True,
            )
            self._pymc_model = model

        # Extract posterior means
        post_means = (
            self._trace.posterior["strategy_probs"].mean(dim=("chain", "draw")).values
        )
        self.posterior = post_means / post_means.sum()

        summary = az.summary(self._trace, var_names=["strategy_probs"])
        log.info("PyMC MCMC complete — %d samples x %d chains", n_samples, chains)

        return {
            "backend": "pymc_nuts",
            "n_samples": n_samples,
            "n_chains": chains,
            "strategy_posteriors": self.get_strategy_probabilities(),
            "summary": (
                summary.to_dict() if hasattr(summary, "to_dict") else str(summary)
            ),
        }

    def _run_fallback_mcmc(
        self,
        n_samples: int,
        n_warmup: int,
    ) -> Dict[str, Any]:
        """Metropolis-Hastings fallback."""

        def log_likelihood_fn(probs: np.ndarray) -> float:
            total = 0.0
            for obs in self.observations:
                for i, strat in enumerate(self.strategies):
                    ll = self._log_likelihood_observation(obs, strat.name)
                    total += probs[i] * ll
            return total

        sampler = _FallbackMCMC(self.n_strategies, self.prior)
        samples = sampler.sample_posterior(
            log_likelihood_fn,
            n_samples=n_samples,
            n_warmup=n_warmup,
        )

        self.posterior = samples.mean(axis=0)
        self.posterior /= self.posterior.sum()
        self._trace = samples

        # Convergence diagnostics
        diagnostics = self._convergence_diagnostics(samples)

        log.info("Fallback MH MCMC complete — %d samples", n_samples)
        return {
            "backend": "numpy_mh",
            "n_samples": n_samples,
            "strategy_posteriors": self.get_strategy_probabilities(),
            "convergence": diagnostics,
        }

    # -- hierarchical model -------------------------------------------------
    def hierarchical_matchup_model(
        self,
        all_matchup_histories: Dict[str, MatchHistory],
        n_samples: int = 2000,
    ) -> Dict[str, Any]:
        """
        Hierarchical Bayesian model where matchup-specific win rates
        are drawn from a shared population distribution.

        Parameters
        ----------
        all_matchup_histories : {matchup_name: MatchHistory}
        n_samples : MCMC draws

        Returns
        -------
        Posterior estimates for each matchup and the population mean.
        """
        matchups = list(all_matchup_histories.keys())
        wins = np.array([all_matchup_histories[m].wins for m in matchups])
        totals = np.array([all_matchup_histories[m].total for m in matchups])

        if self._use_pymc:
            with pm.Model() as hier_model:
                # Population-level hyperpriors
                mu_pop = pm.Beta("mu_population", alpha=2, beta=2)
                kappa = pm.HalfNormal("kappa", sigma=10)

                alpha_k = mu_pop * kappa
                beta_k = (1 - mu_pop) * kappa

                # Matchup-level win rates
                theta = pm.Beta(
                    "theta",
                    alpha=alpha_k,
                    beta=beta_k,
                    shape=len(matchups),
                )

                # Likelihood
                pm.Binomial("wins", n=totals, p=theta, observed=wins)

                trace = pm.sample(
                    draws=n_samples,
                    tune=500,
                    chains=2,
                    return_inferencedata=True,
                    progressbar=True,
                )

            post = trace.posterior
            result = {
                "population_mean": float(post["mu_population"].mean()),
                "matchup_win_rates": {},
            }
            for i, m in enumerate(matchups):
                theta_samples = post["theta"].values[:, :, i].flatten()
                result["matchup_win_rates"][m] = {
                    "mean": float(theta_samples.mean()),
                    "std": float(theta_samples.std()),
                    "ci_95": (
                        float(np.percentile(theta_samples, 2.5)),
                        float(np.percentile(theta_samples, 97.5)),
                    ),
                }
            return result

        # Fallback: conjugate Beta-Binomial per matchup with empirical Bayes
        all_wr = [w / t if t > 0 else 0.5 for w, t in zip(wins, totals)]
        pop_mean = float(np.mean(all_wr))
        pop_std = float(np.std(all_wr)) if len(all_wr) > 1 else 0.1

        result = {
            "population_mean": pop_mean,
            "matchup_win_rates": {},
        }
        for i, m in enumerate(matchups):
            # Shrink towards population mean
            n = totals[i]
            shrinkage = 10.0 / (10.0 + n)
            est = shrinkage * pop_mean + (1 - shrinkage) * (wins[i] / max(n, 1))
            alpha_post = est * (n + 10)
            beta_post = (1 - est) * (n + 10)
            ci = (
                float(sp_stats.beta.ppf(0.025, alpha_post, beta_post)),
                float(sp_stats.beta.ppf(0.975, alpha_post, beta_post)),
            )
            result["matchup_win_rates"][m] = {
                "mean": float(est),
                "std": float(math.sqrt(est * (1 - est) / max(n + 10, 1))),
                "ci_95": ci,
            }
        return result

    # -- Beta-Binomial win rate estimation ----------------------------------
    def update_win_rate(
        self,
        matchup: str,
        wins: int,
        losses: int,
    ) -> Dict[str, Any]:
        """
        Update Beta-Binomial win rate model with new match results.
        Returns posterior mean, variance, and 95% credible interval.
        """
        if matchup not in self.match_histories:
            self.match_histories[matchup] = _FallbackBetaBinomial()

        model = self.match_histories[matchup]
        model.update(wins, losses)

        ci = model.credible_interval(0.95)
        result = {
            "matchup": matchup,
            "posterior_mean": model.mean,
            "posterior_variance": model.variance,
            "credible_interval_95": ci,
            "total_games": model.alpha + model.beta - 2,  # subtract initial priors
        }
        log.info(
            "Win rate updated for %s: %.1f%% [%.1f%%, %.1f%%]",
            matchup,
            model.mean * 100,
            ci[0] * 100,
            ci[1] * 100,
        )
        return result

    def win_probability_estimate(
        self,
        matchup: str,
        n_samples: int = 5000,
    ) -> Dict[str, Any]:
        """
        Monte Carlo estimate of win probability with credible intervals.
        """
        if matchup not in self.match_histories:
            return {"error": f"No history for matchup {matchup}"}

        model = self.match_histories[matchup]
        samples = model.sample(n_samples)

        return {
            "matchup": matchup,
            "win_probability": float(samples.mean()),
            "std": float(samples.std()),
            "credible_interval_80": (
                float(np.percentile(samples, 10)),
                float(np.percentile(samples, 90)),
            ),
            "credible_interval_95": (
                float(np.percentile(samples, 2.5)),
                float(np.percentile(samples, 97.5)),
            ),
            "credible_interval_99": (
                float(np.percentile(samples, 0.5)),
                float(np.percentile(samples, 99.5)),
            ),
            "p_above_50": float((samples > 0.5).mean()),
        }

    # -- Gaussian Process for timing prediction -----------------------------
    def add_timing_data(self, game_time: float, attack_time: float) -> None:
        """Record an observed attack timing at a given game time."""
        self._timing_data_X.append(game_time)
        self._timing_data_y.append(attack_time)

    def predict_attack_timing(
        self,
        query_times: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Predict when the enemy will attack using a Gaussian Process.
        Returns predicted timing with uncertainty bands.
        """
        if len(self._timing_data_X) < 2:
            log.warning("Need at least 2 timing observations for GP prediction.")
            return {"error": "Insufficient timing data (need >= 2 observations)."}

        X = np.array(self._timing_data_X)
        y = np.array(self._timing_data_y)

        if self._use_pymc:
            return self._gp_predict_pymc(X, y, query_times)

        # Fallback GP
        self.timing_gp.fit(X, y)
        mu, std = self.timing_gp.predict(query_times)

        return {
            "backend": "numpy_gp",
            "query_times": query_times.tolist(),
            "predicted_timing": mu.tolist(),
            "uncertainty_std": std.tolist(),
            "ci_95_lower": (mu - 1.96 * std).tolist(),
            "ci_95_upper": (mu + 1.96 * std).tolist(),
        }

    def _gp_predict_pymc(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_new: np.ndarray,
    ) -> Dict[str, Any]:
        """GP prediction with PyMC."""
        with pm.Model() as gp_model:
            ell = pm.HalfNormal("length_scale", sigma=60.0)
            eta = pm.HalfNormal("signal_variance", sigma=2.0)
            sigma = pm.HalfNormal("noise", sigma=0.5)

            cov = eta**2 * pm.gp.cov.ExpQuad(1, ls=ell)
            gp = pm.gp.Marginal(cov_func=cov)

            gp.marginal_likelihood(
                "y",
                X=X[:, None],
                y=y,
                sigma=sigma,
            )

            trace = pm.sample(
                draws=1000,
                tune=500,
                chains=2,
                return_inferencedata=True,
                progressbar=False,
            )

            mu, var = gp.predict(
                X_new[:, None],
                point=trace.posterior.mean(dim=("chain", "draw")),
                diag=True,
            )
            std = np.sqrt(var)

        return {
            "backend": "pymc_gp",
            "query_times": X_new.tolist(),
            "predicted_timing": mu.tolist(),
            "uncertainty_std": std.tolist(),
            "ci_95_lower": (mu - 1.96 * std).tolist(),
            "ci_95_upper": (mu + 1.96 * std).tolist(),
        }

    # -- model comparison (WAIC, LOO) ---------------------------------------
    def model_comparison(self) -> Dict[str, Any]:
        """
        Compare models using WAIC and LOO-CV.
        Requires PyMC trace; falls back to AIC/BIC approximation.
        """
        if self._use_pymc and self._trace is not None:
            try:
                waic = az.waic(self._trace)
                loo = az.loo(self._trace)
                return {
                    "backend": "arviz",
                    "waic": {
                        "waic_value": (
                            float(waic.waic)
                            if hasattr(waic, "waic")
                            else float(waic.elpd_waic * -2)
                        ),
                        "p_waic": float(waic.p_waic),
                    },
                    "loo": {
                        "loo_value": (
                            float(loo.loo)
                            if hasattr(loo, "loo")
                            else float(loo.elpd_loo * -2)
                        ),
                        "p_loo": float(loo.p_loo),
                    },
                }
            except Exception as e:
                log.warning("ArviZ model comparison failed: %s", e)

        # Fallback: compute approximate log-likelihood and AIC/BIC
        if len(self.observations) == 0:
            return {"error": "No observations to compare."}

        total_ll = 0.0
        for obs in self.observations:
            obs_ll = 0.0
            for i, strat in enumerate(self.strategies):
                ll = self._log_likelihood_observation(obs, strat.name)
                obs_ll += self.posterior[i] * np.exp(ll)
            total_ll += np.log(max(obs_ll, 1e-300))

        n_params = self.n_strategies - 1  # Dirichlet has K-1 free params
        n_obs = len(self.observations)
        aic = -2 * total_ll + 2 * n_params
        bic = -2 * total_ll + n_params * np.log(max(n_obs, 1))

        return {
            "backend": "numpy_approximation",
            "log_likelihood": float(total_ll),
            "aic": float(aic),
            "bic": float(bic),
            "n_parameters": n_params,
            "n_observations": n_obs,
        }

    # -- convergence diagnostics --------------------------------------------
    def _convergence_diagnostics(self, samples: np.ndarray) -> Dict[str, Any]:
        """Compute basic convergence diagnostics for MCMC samples."""
        n = len(samples)
        if n < 10:
            return {"warning": "Too few samples for diagnostics."}

        diagnostics: Dict[str, Any] = {"n_samples": n}

        # Effective sample size (simple autocorrelation-based estimate)
        for j, name in enumerate(self.strategy_names):
            chain = samples[:, j]
            mean_val = chain.mean()
            var_val = chain.var()
            if var_val < 1e-12:
                diagnostics[name] = {"ess": n, "mean": float(mean_val), "std": 0.0}
                continue

            # Autocorrelation at lag 1
            ac1 = np.corrcoef(chain[:-1], chain[1:])[0, 1] if n > 1 else 0.0
            ess = n / (1 + 2 * abs(ac1)) if abs(ac1) < 1 else n
            diagnostics[name] = {
                "mean": float(mean_val),
                "std": float(chain.std()),
                "ess": int(ess),
                "autocorr_lag1": float(ac1),
            }

        return diagnostics

    def trace_diagnostics(self) -> Dict[str, Any]:
        """
        Full trace analysis and convergence diagnostics.
        """
        if self._use_pymc and self._trace is not None:
            try:
                summary = az.summary(
                    self._trace,
                    var_names=["strategy_probs"],
                    hdi_prob=0.95,
                )
                rhat = summary["r_hat"].to_dict() if "r_hat" in summary.columns else {}
                ess_bulk = (
                    summary["ess_bulk"].to_dict()
                    if "ess_bulk" in summary.columns
                    else {}
                )
                return {
                    "backend": "arviz",
                    "r_hat": rhat,
                    "ess_bulk": ess_bulk,
                    "summary": summary.to_dict(),
                    "converged": all(v < 1.05 for v in rhat.values()) if rhat else None,
                }
            except Exception as e:
                log.warning("ArviZ diagnostics failed: %s", e)

        # Fallback diagnostics from stored MH samples
        if self._trace is not None and isinstance(self._trace, np.ndarray):
            return self._convergence_diagnostics(self._trace)

        return {"warning": "No trace available. Run run_mcmc() first."}

    # -- visualization helpers ----------------------------------------------
    def plot_posterior(self, output_path: str = "sc2_strategy_posterior.png") -> str:
        """Plot posterior strategy probabilities as a bar chart."""
        if not MPL_AVAILABLE:
            log.warning("matplotlib not available.")
            return ""

        fig, ax = plt.subplots(figsize=(12, 6))
        colors = plt.cm.Set3(np.linspace(0, 1, self.n_strategies))

        bars = ax.bar(
            range(self.n_strategies),
            self.posterior,
            color=colors,
            edgecolor="black",
            alpha=0.85,
        )
        ax.set_xticks(range(self.n_strategies))
        ax.set_xticklabels(
            [n.replace("_", " ").title() for n in self.strategy_names],
            rotation=45,
            ha="right",
            fontsize=9,
        )
        ax.set_ylabel("Posterior Probability")
        ax.set_title(
            f"Enemy Strategy Posterior — {self.matchup.value}",
            fontsize=13,
            fontweight="bold",
        )
        ax.set_ylim(0, min(1.0, max(self.posterior) * 1.3))

        for bar, prob in zip(bars, self.posterior):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005,
                f"{prob:.1%}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        log.info("Posterior plot saved to %s", output_path)
        return output_path

    def plot_win_rate_distribution(
        self,
        matchup: str,
        output_path: str = "sc2_win_rate_dist.png",
    ) -> str:
        """Plot the Beta posterior distribution for win rate."""
        if not MPL_AVAILABLE:
            return ""
        if matchup not in self.match_histories:
            return ""

        model = self.match_histories[matchup]
        x = np.linspace(0, 1, 500)
        y = sp_stats.beta.pdf(x, model.alpha, model.beta)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.fill_between(x, y, alpha=0.3, color="steelblue")
        ax.plot(x, y, color="steelblue", lw=2)
        ax.axvline(
            model.mean, color="red", ls="--", lw=1.5, label=f"Mean={model.mean:.3f}"
        )

        ci = model.credible_interval(0.95)
        ax.axvspan(
            ci[0],
            ci[1],
            alpha=0.15,
            color="orange",
            label=f"95% CI [{ci[0]:.3f}, {ci[1]:.3f}]",
        )

        ax.set_xlabel("Win Rate")
        ax.set_ylabel("Density")
        ax.set_title(f"Win Rate Posterior — {matchup}", fontsize=13, fontweight="bold")
        ax.legend(fontsize=9)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        log.info("Win rate distribution saved to %s", output_path)
        return output_path

    # -- full report --------------------------------------------------------
    def full_report(self) -> Dict[str, Any]:
        """Generate a comprehensive Bayesian analysis report."""
        return {
            "matchup": self.matchup.value,
            "backend": "pymc" if self._use_pymc else "numpy",
            "n_observations": len(self.observations),
            "strategy_posteriors": self.get_strategy_probabilities(),
            "most_likely_strategy": self.most_likely_strategy(),
            "win_rates": {
                m: {
                    "mean": model.mean,
                    "ci_95": model.credible_interval(0.95),
                }
                for m, model in self.match_histories.items()
            },
            "model_comparison": self.model_comparison(),
            "trace_diagnostics": self.trace_diagnostics(),
        }


# ---------------------------------------------------------------------------
# CLI / demo entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Demonstrate SC2StrategyInference capabilities."""
    engine = SC2StrategyInference(matchup=Matchup.ZVT)

    print("=" * 70)
    print("SC2 Bayesian Strategy Inference — Phase 593: PyMC")
    print("=" * 70)

    # 1. Initial priors
    print("\n--- Initial Priors (ZvT meta-game) ---")
    for name, prob in engine.get_strategy_probabilities().items():
        print(f"  {name:25s}  {prob:.1%}")

    # 2. Scouting observations
    print("\n--- Scouting Updates ---")
    obs1 = ScoutingObservation(
        game_time_seconds=120,
        enemy_worker_count=22,
        enemy_gas_count=2,
        enemy_base_count=2,
        enemy_army_supply=3.0,
        expansion_timing=75.0,
    )
    engine.update_with_observation(obs1)
    print("  After obs1 (t=120s, 22 workers, 2 bases, expand@75s):")
    strat, prob = engine.most_likely_strategy()
    print(f"    Most likely: {strat} ({prob:.1%})")

    obs2 = ScoutingObservation(
        game_time_seconds=240,
        enemy_worker_count=40,
        enemy_gas_count=4,
        enemy_base_count=3,
        enemy_army_supply=8.0,
        expansion_timing=60.0,
    )
    engine.update_with_observation(obs2)
    print("  After obs2 (t=240s, 40 workers, 3 bases, expand@60s):")
    strat, prob = engine.most_likely_strategy()
    print(f"    Most likely: {strat} ({prob:.1%})")

    # 3. Updated posteriors
    print("\n--- Updated Posteriors ---")
    for name, prob in engine.get_strategy_probabilities().items():
        bar = "#" * int(prob * 50)
        print(f"  {name:25s}  {prob:.1%}  {bar}")

    # 4. MCMC sampling
    print("\n--- MCMC Sampling ---")
    mcmc_result = engine.run_mcmc(n_samples=1000, n_warmup=200)
    print(f"  Backend: {mcmc_result['backend']}")
    print(f"  Strategy posteriors:")
    for name, prob in mcmc_result["strategy_posteriors"].items():
        print(f"    {name:25s}  {prob:.1%}")

    # 5. Win rate estimation (Beta-Binomial)
    print("\n--- Win Rate Estimation (Beta-Binomial) ---")
    engine.update_win_rate("ZvT", wins=35, losses=25)
    engine.update_win_rate("ZvP", wins=28, losses=32)
    engine.update_win_rate("ZvZ", wins=20, losses=20)

    for mu in ["ZvT", "ZvP", "ZvZ"]:
        wp = engine.win_probability_estimate(mu)
        if "error" not in wp:
            print(
                f"  {mu}: {wp['win_probability']:.1%} "
                f"[{wp['credible_interval_95'][0]:.1%}, {wp['credible_interval_95'][1]:.1%}] "
                f"P(>50%)={wp['p_above_50']:.1%}"
            )

    # 6. Hierarchical model
    print("\n--- Hierarchical Matchup Model ---")
    hier_result = engine.hierarchical_matchup_model(
        {
            "ZvT": MatchHistory(wins=35, losses=25),
            "ZvP": MatchHistory(wins=28, losses=32),
            "ZvZ": MatchHistory(wins=20, losses=20),
        }
    )
    print(f"  Population mean: {hier_result['population_mean']:.1%}")
    for m, data in hier_result["matchup_win_rates"].items():
        print(f"  {m}: {data['mean']:.1%} +/- {data['std']:.1%} CI={data['ci_95']}")

    # 7. GP timing prediction
    print("\n--- Gaussian Process Timing Prediction ---")
    engine.add_timing_data(60.0, 180.0)
    engine.add_timing_data(120.0, 240.0)
    engine.add_timing_data(180.0, 300.0)
    engine.add_timing_data(240.0, 330.0)
    engine.add_timing_data(300.0, 360.0)

    query_times = np.array([150.0, 200.0, 250.0, 350.0])
    gp_result = engine.predict_attack_timing(query_times)
    if "error" not in gp_result:
        print(f"  Backend: {gp_result['backend']}")
        for t, pred, lo, hi in zip(
            gp_result["query_times"],
            gp_result["predicted_timing"],
            gp_result["ci_95_lower"],
            gp_result["ci_95_upper"],
        ):
            print(f"  t={t:.0f}s -> attack@{pred:.0f}s [{lo:.0f}s, {hi:.0f}s]")

    # 8. Model comparison
    print("\n--- Model Comparison ---")
    mc = engine.model_comparison()
    print(f"  Backend: {mc.get('backend', 'n/a')}")
    if "aic" in mc:
        print(f"  AIC: {mc['aic']:.2f}")
        print(f"  BIC: {mc['bic']:.2f}")
    if "waic" in mc:
        print(f"  WAIC: {mc['waic']}")
    if "loo" in mc:
        print(f"  LOO: {mc['loo']}")

    # 9. Trace diagnostics
    print("\n--- Convergence Diagnostics ---")
    diag = engine.trace_diagnostics()
    if "warning" not in diag:
        for key, val in diag.items():
            if isinstance(val, dict) and "ess" in val:
                print(f"  {key:25s}  ESS={val['ess']}  mean={val['mean']:.4f}")

    # 10. Visualisation
    engine.plot_posterior()
    engine.plot_win_rate_distribution("ZvT")

    print("\n" + "=" * 70)
    print("Phase 593 complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
