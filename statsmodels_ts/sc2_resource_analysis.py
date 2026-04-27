# Phase 594: statsmodels
"""
sc2_resource_analysis.py — StarCraft II Resource Time Series Analysis with statsmodels

Provides ARIMA mineral forecasting, seasonal decomposition of game economy
cycles, stationarity testing (ADF), ACF/PACF lag selection, VAR multi-resource
interaction modelling, Holt-Winters exponential smoothing, Granger causality
tests, OLS/logistic regression, and residual diagnostics.

Graceful fallback to a pure-NumPy implementation when statsmodels is absent.
"""

from __future__ import annotations

import logging
import math
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_resource_analysis")

# ---------------------------------------------------------------------------
# Optional statsmodels imports — graceful fallback
# ---------------------------------------------------------------------------
try:
    import statsmodels.api as sm
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.stattools import adfuller, acf, pacf, grangercausalitytests
    from statsmodels.tsa.vector_ar.var_model import VAR
    from statsmodels.stats.stattools import durbin_watson
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.graphics.gofplots import qqplot

    SM_AVAILABLE = True
    log.info("statsmodels available.")
except ImportError:
    SM_AVAILABLE = False
    log.warning(
        "statsmodels not installed. Running pure-NumPy fallback. "
        "Install with: pip install statsmodels"
    )

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ResourceSnapshot:
    """Single point-in-time observation of the in-game economy."""

    game_time_s: float
    minerals: float
    gas: float
    supply_used: int
    army_supply: int
    worker_count: int
    base_count: int
    income_minerals: float
    income_gas: float


@dataclass
class GameRecord:
    """Aggregate record for one completed game (for regression models)."""

    avg_mineral_income: float
    avg_gas_income: float
    avg_army_supply: float
    avg_worker_count: float
    avg_base_count: float
    avg_apm: float
    tech_tier_reached: int  # 1-3
    game_length_s: float
    opponent_race: str  # "zerg", "terran", "protoss"
    win: bool


@dataclass
class AnalysisResult:
    """Container for any analysis output."""

    name: str
    summary: Dict[str, Any] = field(default_factory=dict)
    values: Optional[np.ndarray] = None
    residuals: Optional[np.ndarray] = None
    forecast: Optional[np.ndarray] = None
    plot_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Pure-NumPy fallback helpers
# ---------------------------------------------------------------------------


def _np_linear_trend(y: np.ndarray) -> Tuple[float, float]:
    """OLS slope and intercept via closed-form normal equation."""
    n = len(y)
    x = np.arange(n, dtype=np.float64)
    x_mean, y_mean = x.mean(), y.mean()
    slope = np.sum((x - x_mean) * (y - y_mean)) / max(np.sum((x - x_mean) ** 2), 1e-12)
    intercept = y_mean - slope * x_mean
    return slope, intercept


def _np_acf(y: np.ndarray, nlags: int = 20) -> np.ndarray:
    """Autocorrelation function via brute-force."""
    y = y - y.mean()
    n = len(y)
    var = np.sum(y**2)
    if var < 1e-12:
        return np.zeros(nlags + 1)
    result = np.array([np.sum(y[: n - k] * y[k:]) / var for k in range(nlags + 1)])
    return result


def _np_adf_approx(y: np.ndarray) -> Dict[str, Any]:
    """Rough stationarity heuristic: variance-ratio test (not real ADF)."""
    n = len(y)
    if n < 10:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "stationary": False,
            "note": "too few observations",
        }
    half = n // 2
    var1 = np.var(y[:half])
    var2 = np.var(y[half:])
    ratio = var2 / max(var1, 1e-12)
    pseudo_p = min(1.0, abs(ratio - 1.0))
    return {
        "statistic": ratio,
        "p_value": pseudo_p,
        "stationary": pseudo_p < 0.05,
        "note": "fallback variance-ratio heuristic, not real ADF",
    }


def _np_simple_ema(y: np.ndarray, alpha: float = 0.3) -> np.ndarray:
    """Simple exponential moving average (fallback for Holt-Winters)."""
    result = np.empty_like(y, dtype=np.float64)
    result[0] = y[0]
    for i in range(1, len(y)):
        result[i] = alpha * y[i] + (1 - alpha) * result[i - 1]
    return result


def _np_durbin_watson(residuals: np.ndarray) -> float:
    """Durbin-Watson statistic from residuals."""
    diff = np.diff(residuals)
    return float(np.sum(diff**2) / max(np.sum(residuals**2), 1e-12))


def _np_sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -500, 500)
    return 1.0 / (1.0 + np.exp(-z))


def _np_logistic_regression(
    X: np.ndarray, y: np.ndarray, lr: float = 0.01, epochs: int = 1000
) -> np.ndarray:
    """Mini gradient-descent logistic regression."""
    n, d = X.shape
    w = np.zeros(d)
    for _ in range(epochs):
        pred = _np_sigmoid(X @ w)
        grad = X.T @ (pred - y) / n
        w -= lr * grad
    return w


# ---------------------------------------------------------------------------
# SC2ResourceAnalysis
# ---------------------------------------------------------------------------


class SC2ResourceAnalysis:
    """Comprehensive statsmodels-based analysis of SC2 economy time series."""

    def __init__(
        self,
        snapshots: Optional[List[ResourceSnapshot]] = None,
        game_records: Optional[List[GameRecord]] = None,
    ):
        self.snapshots: List[ResourceSnapshot] = snapshots or []
        self.game_records: List[GameRecord] = game_records or []
        self._ts_cache: Dict[str, np.ndarray] = {}
        log.info(
            "SC2ResourceAnalysis initialised — %d snapshots, %d game records.",
            len(self.snapshots),
            len(self.game_records),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _series(self, attr: str) -> np.ndarray:
        """Extract a time series array from snapshots, with caching."""
        if attr not in self._ts_cache:
            self._ts_cache[attr] = np.array(
                [getattr(s, attr) for s in self.snapshots],
                dtype=np.float64,
            )
        return self._ts_cache[attr]

    def _require_snapshots(self, min_n: int = 10) -> None:
        if len(self.snapshots) < min_n:
            raise ValueError(f"Need >= {min_n} snapshots, got {len(self.snapshots)}.")

    def _require_records(self, min_n: int = 10) -> None:
        if len(self.game_records) < min_n:
            raise ValueError(
                f"Need >= {min_n} game records, got {len(self.game_records)}."
            )

    def add_snapshots(self, snaps: List[ResourceSnapshot]) -> None:
        self.snapshots.extend(snaps)
        self._ts_cache.clear()
        log.info("Added %d snapshots (total %d).", len(snaps), len(self.snapshots))

    def add_game_records(self, records: List[GameRecord]) -> None:
        self.game_records.extend(records)
        log.info(
            "Added %d game records (total %d).", len(records), len(self.game_records)
        )

    # ------------------------------------------------------------------
    # 1. Augmented Dickey-Fuller stationarity test
    # ------------------------------------------------------------------

    def test_stationarity(
        self, series_name: str = "income_minerals", significance: float = 0.05
    ) -> AnalysisResult:
        """Run ADF test on the given snapshot attribute."""
        self._require_snapshots()
        y = self._series(series_name)

        if SM_AVAILABLE:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                adf_stat, p_value, used_lag, n_obs, crit_values, icbest = adfuller(
                    y,
                    autolag="AIC",
                )
            stationary = p_value < significance
            summary = {
                "adf_statistic": float(adf_stat),
                "p_value": float(p_value),
                "used_lag": int(used_lag),
                "n_obs": int(n_obs),
                "critical_values": {k: float(v) for k, v in crit_values.items()},
                "ic_best": float(icbest),
                "stationary": stationary,
            }
        else:
            summary = _np_adf_approx(y)

        log.info(
            "ADF test on '%s': stat=%.4f  p=%.4f  stationary=%s",
            series_name,
            summary.get("adf_statistic", summary.get("statistic", 0)),
            summary["p_value"],
            summary.get("stationary"),
        )
        return AnalysisResult(name=f"adf_{series_name}", summary=summary, values=y)

    # ------------------------------------------------------------------
    # 2. ACF / PACF lag selection
    # ------------------------------------------------------------------

    def acf_pacf_analysis(
        self, series_name: str = "income_minerals", nlags: int = 20
    ) -> AnalysisResult:
        """Compute ACF and PACF and suggest ARIMA(p,d,q) orders."""
        self._require_snapshots(min_n=nlags + 5)
        y = self._series(series_name)
        nlags = min(nlags, len(y) // 2 - 1)

        if SM_AVAILABLE:
            acf_vals = acf(y, nlags=nlags, fft=True)
            pacf_vals = pacf(y, nlags=nlags)
        else:
            acf_vals = _np_acf(y, nlags)
            # Approximate PACF via Yule-Walker is non-trivial; use ACF only
            pacf_vals = _np_acf(y, nlags)  # rough approximation

        # Heuristic: p = first lag where PACF drops below 2/sqrt(n)
        threshold = 2.0 / math.sqrt(len(y))
        suggested_p = 1
        for k in range(1, len(pacf_vals)):
            if abs(pacf_vals[k]) < threshold:
                suggested_p = max(k - 1, 1)
                break

        # q from ACF
        suggested_q = 1
        for k in range(1, len(acf_vals)):
            if abs(acf_vals[k]) < threshold:
                suggested_q = max(k - 1, 1)
                break

        summary = {
            "nlags": nlags,
            "acf": acf_vals.tolist(),
            "pacf": pacf_vals.tolist(),
            "significance_threshold": float(threshold),
            "suggested_p": suggested_p,
            "suggested_q": suggested_q,
        }
        log.info(
            "ACF/PACF on '%s': suggested ARIMA order p=%d, q=%d",
            series_name,
            suggested_p,
            suggested_q,
        )
        return AnalysisResult(
            name=f"acf_pacf_{series_name}", summary=summary, values=acf_vals
        )

    # ------------------------------------------------------------------
    # 3. ARIMA mineral income forecasting
    # ------------------------------------------------------------------

    def arima_forecast(
        self,
        series_name: str = "income_minerals",
        order: Optional[Tuple[int, int, int]] = None,
        forecast_steps: int = 30,
    ) -> AnalysisResult:
        """Fit ARIMA model and forecast future values."""
        self._require_snapshots()
        y = self._series(series_name)

        if order is None:
            acf_result = self.acf_pacf_analysis(series_name)
            p = acf_result.summary["suggested_p"]
            q = acf_result.summary["suggested_q"]
            order = (p, 1, q)

        if SM_AVAILABLE:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = ARIMA(y, order=order)
                fitted = model.fit()
                fcast = fitted.forecast(steps=forecast_steps)
                residuals = fitted.resid

            summary = {
                "order": order,
                "aic": float(fitted.aic),
                "bic": float(fitted.bic),
                "log_likelihood": float(fitted.llf),
                "forecast_mean": float(np.mean(fcast)),
                "forecast_std": float(np.std(fcast)),
                "residual_mean": float(np.mean(residuals)),
                "residual_std": float(np.std(residuals)),
            }
        else:
            # Fallback: linear-trend extrapolation
            slope, intercept = _np_linear_trend(y)
            n = len(y)
            fcast = np.array(
                [slope * (n + i) + intercept for i in range(forecast_steps)]
            )
            residuals = y - (slope * np.arange(n) + intercept)
            summary = {
                "order": order,
                "aic": None,
                "bic": None,
                "log_likelihood": None,
                "forecast_mean": float(np.mean(fcast)),
                "forecast_std": float(np.std(fcast)),
                "residual_mean": float(np.mean(residuals)),
                "residual_std": float(np.std(residuals)),
                "note": "linear-trend fallback (statsmodels not available)",
            }

        log.info(
            "ARIMA%s forecast on '%s': mean=%.2f  std=%.2f",
            order,
            series_name,
            summary["forecast_mean"],
            summary["forecast_std"],
        )
        return AnalysisResult(
            name=f"arima_{series_name}",
            summary=summary,
            values=y,
            forecast=fcast,
            residuals=residuals,
        )

    # ------------------------------------------------------------------
    # 4. Seasonal decomposition of game economy cycles
    # ------------------------------------------------------------------

    def seasonal_decomposition(
        self,
        series_name: str = "income_minerals",
        period: int = 30,
        model: str = "additive",
    ) -> AnalysisResult:
        """Decompose time series into trend, seasonal, and residual components."""
        self._require_snapshots(min_n=period * 2)
        y = self._series(series_name)

        if SM_AVAILABLE:
            import pandas as pd

            ts = pd.Series(y)
            decomp = seasonal_decompose(ts, model=model, period=period)
            trend = decomp.trend.values
            seasonal = decomp.seasonal.values
            resid = decomp.resid.values

            summary = {
                "model": model,
                "period": period,
                "trend_mean": float(np.nanmean(trend)),
                "seasonal_amplitude": float(np.nanmax(seasonal) - np.nanmin(seasonal)),
                "residual_std": float(np.nanstd(resid)),
            }
        else:
            # Fallback: simple moving-average decomposition
            kernel = np.ones(period) / period
            trend = np.convolve(y, kernel, mode="same")
            detrended = y - trend
            # Average each season position
            seasonal = np.zeros_like(y)
            for i in range(period):
                indices = np.arange(i, len(y), period)
                seasonal[indices] = np.mean(detrended[indices])
            resid = y - trend - seasonal
            summary = {
                "model": model,
                "period": period,
                "trend_mean": float(np.mean(trend)),
                "seasonal_amplitude": float(np.max(seasonal) - np.min(seasonal)),
                "residual_std": float(np.std(resid)),
                "note": "moving-average fallback",
            }

        log.info(
            "Seasonal decomposition (%s, period=%d): amplitude=%.2f  resid_std=%.2f",
            model,
            period,
            summary["seasonal_amplitude"],
            summary["residual_std"],
        )
        return AnalysisResult(
            name=f"seasonal_{series_name}",
            summary=summary,
            values=trend,
            residuals=resid,
        )

    # ------------------------------------------------------------------
    # 5. VAR — multi-resource interaction
    # ------------------------------------------------------------------

    def var_analysis(
        self, series_names: Optional[List[str]] = None, maxlags: int = 5
    ) -> AnalysisResult:
        """Fit Vector AutoRegression across multiple resource series."""
        series_names = series_names or ["income_minerals", "income_gas", "army_supply"]
        self._require_snapshots(min_n=maxlags * 3)

        data = np.column_stack([self._series(s) for s in series_names])

        if SM_AVAILABLE:
            import pandas as pd

            df = pd.DataFrame(data, columns=series_names)
            var_model = VAR(df)
            fitted = var_model.fit(maxlags=maxlags, ic="aic")
            fcast = fitted.forecast(data[-fitted.k_ar :], steps=10)

            summary = {
                "series": series_names,
                "selected_lag": fitted.k_ar,
                "aic": float(fitted.aic),
                "bic": float(fitted.bic),
                "forecast_means": {
                    s: float(fcast[:, i].mean()) for i, s in enumerate(series_names)
                },
                "det_order": fitted.det_order,
            }
        else:
            # Fallback: independent linear trends
            forecast_dict: Dict[str, float] = {}
            for i, s in enumerate(series_names):
                slope, intercept = _np_linear_trend(data[:, i])
                n = len(data[:, i])
                future = np.array([slope * (n + j) + intercept for j in range(10)])
                forecast_dict[s] = float(np.mean(future))

            summary = {
                "series": series_names,
                "selected_lag": maxlags,
                "aic": None,
                "bic": None,
                "forecast_means": forecast_dict,
                "note": "independent linear-trend fallback",
            }

        log.info("VAR analysis on %s: lag=%d", series_names, summary["selected_lag"])
        return AnalysisResult(name="var_multi_resource", summary=summary)

    # ------------------------------------------------------------------
    # 6. Exponential smoothing (Holt-Winters)
    # ------------------------------------------------------------------

    def holt_winters(
        self,
        series_name: str = "income_minerals",
        seasonal_periods: int = 30,
        trend: str = "add",
        seasonal: str = "add",
        forecast_steps: int = 20,
    ) -> AnalysisResult:
        """Fit Holt-Winters exponential smoothing and forecast."""
        self._require_snapshots(min_n=seasonal_periods * 2)
        y = self._series(series_name)

        if SM_AVAILABLE:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = ExponentialSmoothing(
                    y,
                    trend=trend,
                    seasonal=seasonal,
                    seasonal_periods=seasonal_periods,
                    initialization_method="estimated",
                )
                fitted = model.fit(optimized=True)
                fcast = fitted.forecast(forecast_steps)
                fitted_values = fitted.fittedvalues
                residuals = y - fitted_values

            summary = {
                "trend": trend,
                "seasonal": seasonal,
                "seasonal_periods": seasonal_periods,
                "aic": float(fitted.aic),
                "bic": float(fitted.bic),
                "sse": float(fitted.sse),
                "smoothing_level": float(fitted.params.get("smoothing_level", 0)),
                "smoothing_trend": float(fitted.params.get("smoothing_trend", 0)),
                "smoothing_seasonal": float(fitted.params.get("smoothing_seasonal", 0)),
                "forecast_mean": float(np.mean(fcast)),
            }
        else:
            smoothed = _np_simple_ema(y, alpha=0.3)
            slope, intercept = _np_linear_trend(y)
            n = len(y)
            fcast = np.array(
                [slope * (n + i) + intercept for i in range(forecast_steps)]
            )
            residuals = y - smoothed

            summary = {
                "trend": trend,
                "seasonal": seasonal,
                "seasonal_periods": seasonal_periods,
                "aic": None,
                "bic": None,
                "sse": float(np.sum(residuals**2)),
                "forecast_mean": float(np.mean(fcast)),
                "note": "EMA fallback (statsmodels not available)",
            }

        log.info(
            "Holt-Winters (%s/%s, period=%d) forecast mean=%.2f",
            trend,
            seasonal,
            seasonal_periods,
            summary["forecast_mean"],
        )
        return AnalysisResult(
            name=f"holt_winters_{series_name}",
            summary=summary,
            forecast=fcast,
            residuals=residuals,
        )

    # ------------------------------------------------------------------
    # 7. Granger causality — does gas income predict army growth?
    # ------------------------------------------------------------------

    def granger_causality(
        self,
        cause: str = "income_gas",
        effect: str = "army_supply",
        maxlag: int = 5,
        significance: float = 0.05,
    ) -> AnalysisResult:
        """Test whether *cause* Granger-causes *effect*."""
        self._require_snapshots(min_n=maxlag * 3)
        y_cause = self._series(cause)
        y_effect = self._series(effect)

        if SM_AVAILABLE:
            import pandas as pd

            df = pd.DataFrame({cause: y_cause, effect: y_effect})
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                results = grangercausalitytests(
                    df[[effect, cause]], maxlag=maxlag, verbose=False
                )

            lag_pvalues: Dict[int, float] = {}
            significant_lags: List[int] = []
            for lag in range(1, maxlag + 1):
                p = results[lag][0]["ssr_ftest"][1]
                lag_pvalues[lag] = float(p)
                if p < significance:
                    significant_lags.append(lag)

            summary = {
                "cause": cause,
                "effect": effect,
                "maxlag": maxlag,
                "lag_pvalues": lag_pvalues,
                "significant_lags": significant_lags,
                "granger_causes": len(significant_lags) > 0,
            }
        else:
            # Fallback: correlation-based heuristic
            max_corr_lag = 0
            max_corr = 0.0
            n = len(y_cause)
            for lag in range(1, maxlag + 1):
                c = np.corrcoef(y_cause[: n - lag], y_effect[lag:])[0, 1]
                if abs(c) > abs(max_corr):
                    max_corr = c
                    max_corr_lag = lag

            summary = {
                "cause": cause,
                "effect": effect,
                "maxlag": maxlag,
                "best_lag": max_corr_lag,
                "best_correlation": float(max_corr),
                "granger_causes": abs(max_corr) > 0.3,
                "note": "correlation-based heuristic, not real Granger test",
            }

        log.info(
            "Granger causality %s -> %s: causes=%s",
            cause,
            effect,
            summary["granger_causes"],
        )
        return AnalysisResult(name=f"granger_{cause}_to_{effect}", summary=summary)

    # ------------------------------------------------------------------
    # 8. OLS regression — win rate factors
    # ------------------------------------------------------------------

    def ols_winrate_factors(self) -> AnalysisResult:
        """OLS regression: which factors predict win rate across games?"""
        self._require_records()
        records = self.game_records

        # Build feature matrix
        race_map = {"zerg": 0, "terran": 1, "protoss": 2}
        X_list, y_list = [], []
        for r in records:
            X_list.append(
                [
                    r.avg_mineral_income,
                    r.avg_gas_income,
                    r.avg_army_supply,
                    r.avg_worker_count,
                    r.avg_base_count,
                    r.avg_apm,
                    r.tech_tier_reached,
                    r.game_length_s / 600.0,
                    race_map.get(r.opponent_race.lower(), 0),
                ]
            )
            y_list.append(1.0 if r.win else 0.0)

        X = np.array(X_list, dtype=np.float64)
        y = np.array(y_list, dtype=np.float64)

        feature_names = [
            "mineral_income",
            "gas_income",
            "army_supply",
            "worker_count",
            "base_count",
            "apm",
            "tech_tier",
            "game_length",
            "opponent_race",
        ]

        if SM_AVAILABLE:
            X_const = sm.add_constant(X)
            model = sm.OLS(y, X_const).fit()
            residuals = model.resid
            dw = durbin_watson(residuals)

            coef_dict: Dict[str, float] = {}
            pval_dict: Dict[str, float] = {}
            for i, name in enumerate(["const"] + feature_names):
                coef_dict[name] = float(model.params[i])
                pval_dict[name] = float(model.pvalues[i])

            summary = {
                "r_squared": float(model.rsquared),
                "adj_r_squared": float(model.rsquared_adj),
                "f_statistic": float(model.fvalue),
                "f_pvalue": float(model.f_pvalue),
                "aic": float(model.aic),
                "bic": float(model.bic),
                "coefficients": coef_dict,
                "p_values": pval_dict,
                "durbin_watson": dw,
                "n_obs": len(y),
                "significant_factors": [
                    name
                    for name, p in pval_dict.items()
                    if p < 0.05 and name != "const"
                ],
            }
            res = residuals
        else:
            # Fallback: manual OLS via normal equation
            X_const = np.column_stack([np.ones(len(X)), X])
            try:
                beta = np.linalg.lstsq(X_const, y, rcond=None)[0]
            except np.linalg.LinAlgError:
                beta = np.zeros(X_const.shape[1])
            y_hat = X_const @ beta
            res = y - y_hat
            ss_res = np.sum(res**2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1 - ss_res / max(ss_tot, 1e-12)
            dw = _np_durbin_watson(res)

            coef_dict = {}
            for i, name in enumerate(["const"] + feature_names):
                coef_dict[name] = float(beta[i])

            summary = {
                "r_squared": float(r2),
                "adj_r_squared": float(
                    1 - (1 - r2) * (len(y) - 1) / max(len(y) - X.shape[1] - 1, 1)
                ),
                "coefficients": coef_dict,
                "durbin_watson": dw,
                "n_obs": len(y),
                "note": "normal-equation fallback",
            }

        log.info(
            "OLS win-rate regression: R²=%.4f  DW=%.4f",
            summary["r_squared"],
            summary.get("durbin_watson", 0),
        )
        return AnalysisResult(name="ols_winrate", summary=summary, residuals=res)

    # ------------------------------------------------------------------
    # 9. Logistic regression — battle outcome prediction
    # ------------------------------------------------------------------

    def logistic_battle_outcome(self) -> AnalysisResult:
        """Logistic regression to predict battle win/loss."""
        self._require_records()
        records = self.game_records

        race_map = {"zerg": 0, "terran": 1, "protoss": 2}
        X_list, y_list = [], []
        for r in records:
            X_list.append(
                [
                    r.avg_mineral_income / 1000.0,
                    r.avg_gas_income / 500.0,
                    r.avg_army_supply / 100.0,
                    r.avg_worker_count / 80.0,
                    r.avg_apm / 200.0,
                    r.tech_tier_reached / 3.0,
                    r.game_length_s / 600.0,
                    float(race_map.get(r.opponent_race.lower(), 0)) / 2.0,
                ]
            )
            y_list.append(1.0 if r.win else 0.0)

        X = np.array(X_list, dtype=np.float64)
        y = np.array(y_list, dtype=np.float64)

        feature_names = [
            "mineral_income",
            "gas_income",
            "army_supply",
            "worker_count",
            "apm",
            "tech_tier",
            "game_length",
            "opponent_race",
        ]

        if SM_AVAILABLE:
            X_const = sm.add_constant(X)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = sm.Logit(y, X_const).fit(disp=0, maxiter=100)

            coef_dict: Dict[str, float] = {}
            pval_dict: Dict[str, float] = {}
            for i, name in enumerate(["const"] + feature_names):
                coef_dict[name] = float(model.params[i])
                pval_dict[name] = float(model.pvalues[i])

            y_pred_prob = model.predict(X_const)
            y_pred = (y_pred_prob >= 0.5).astype(float)
            accuracy = float(np.mean(y_pred == y))

            summary = {
                "pseudo_r_squared": float(model.prsquared),
                "log_likelihood": float(model.llf),
                "aic": float(model.aic),
                "bic": float(model.bic),
                "coefficients": coef_dict,
                "p_values": pval_dict,
                "accuracy": accuracy,
                "n_obs": len(y),
                "converged": model.mle_retvals["converged"],
                "significant_factors": [
                    name
                    for name, p in pval_dict.items()
                    if p < 0.05 and name != "const"
                ],
            }
        else:
            X_const = np.column_stack([np.ones(len(X)), X])
            w = _np_logistic_regression(X_const, y)
            y_pred_prob = _np_sigmoid(X_const @ w)
            y_pred = (y_pred_prob >= 0.5).astype(float)
            accuracy = float(np.mean(y_pred == y))

            coef_dict = {}
            for i, name in enumerate(["const"] + feature_names):
                coef_dict[name] = float(w[i])

            summary = {
                "coefficients": coef_dict,
                "accuracy": accuracy,
                "n_obs": len(y),
                "note": "gradient-descent fallback",
            }

        log.info("Logistic battle outcome: accuracy=%.4f", accuracy)
        return AnalysisResult(name="logistic_battle", summary=summary)

    # ------------------------------------------------------------------
    # 10. QQ plot and residual analysis
    # ------------------------------------------------------------------

    def residual_analysis(
        self, result: AnalysisResult, save_path: Optional[str] = None
    ) -> AnalysisResult:
        """Perform residual diagnostics: QQ plot, Durbin-Watson, normality."""
        if result.residuals is None or len(result.residuals) == 0:
            raise ValueError("AnalysisResult has no residuals to analyse.")

        residuals = result.residuals
        # Remove NaN
        residuals = residuals[~np.isnan(residuals)]

        dw = _np_durbin_watson(residuals)
        resid_mean = float(np.mean(residuals))
        resid_std = float(np.std(residuals))
        resid_skew = float(
            np.mean(((residuals - resid_mean) / max(resid_std, 1e-12)) ** 3)
        )
        resid_kurtosis = float(
            np.mean(((residuals - resid_mean) / max(resid_std, 1e-12)) ** 4) - 3
        )

        # Jarque-Bera test for normality
        n = len(residuals)
        jb_stat = (n / 6.0) * (resid_skew**2 + (resid_kurtosis**2) / 4.0)

        summary = {
            "source_analysis": result.name,
            "n_residuals": n,
            "mean": resid_mean,
            "std": resid_std,
            "skewness": resid_skew,
            "excess_kurtosis": resid_kurtosis,
            "durbin_watson": dw,
            "dw_interpretation": (
                "positive autocorrelation"
                if dw < 1.5
                else "no autocorrelation" if dw < 2.5 else "negative autocorrelation"
            ),
            "jarque_bera_statistic": jb_stat,
            "likely_normal": jb_stat < 5.99,  # chi2(2) critical at 5%
        }

        # Optional QQ plot
        plot_path = save_path
        if MPL_AVAILABLE and save_path:
            fig, axes = plt.subplots(1, 3, figsize=(15, 4))

            # QQ plot
            if SM_AVAILABLE:
                qqplot(residuals, line="s", ax=axes[0])
            else:
                sorted_res = np.sort(residuals)
                theoretical = np.sort(np.random.randn(n))
                axes[0].scatter(theoretical, sorted_res, s=8, alpha=0.6)
                axes[0].plot(
                    [theoretical.min(), theoretical.max()],
                    [theoretical.min(), theoretical.max()],
                    "r--",
                )
            axes[0].set_title("QQ Plot")
            axes[0].set_xlabel("Theoretical Quantiles")
            axes[0].set_ylabel("Sample Quantiles")

            # Histogram
            axes[1].hist(residuals, bins=30, density=True, alpha=0.7, color="steelblue")
            axes[1].set_title("Residual Distribution")
            axes[1].set_xlabel("Residual")
            axes[1].set_ylabel("Density")

            # Residuals vs order
            axes[2].plot(residuals, linewidth=0.5, alpha=0.8)
            axes[2].axhline(0, color="red", linestyle="--", linewidth=0.8)
            axes[2].set_title(f"Residuals (DW={dw:.3f})")
            axes[2].set_xlabel("Observation")
            axes[2].set_ylabel("Residual")

            plt.tight_layout()
            plt.savefig(save_path, dpi=150)
            plt.close(fig)
            log.info("Residual diagnostics plot saved to %s", save_path)
        else:
            plot_path = None

        log.info(
            "Residual analysis for '%s': DW=%.3f  skew=%.3f  kurtosis=%.3f  normal=%s",
            result.name,
            dw,
            resid_skew,
            resid_kurtosis,
            summary["likely_normal"],
        )
        return AnalysisResult(
            name=f"residuals_{result.name}",
            summary=summary,
            residuals=residuals,
            plot_path=plot_path,
        )

    # ------------------------------------------------------------------
    # 11. Durbin-Watson autocorrelation test (standalone)
    # ------------------------------------------------------------------

    def durbin_watson_test(
        self, series_name: str = "income_minerals"
    ) -> AnalysisResult:
        """Compute Durbin-Watson statistic on a raw series' first differences."""
        self._require_snapshots()
        y = self._series(series_name)
        diffs = np.diff(y)

        if SM_AVAILABLE:
            dw = float(durbin_watson(diffs))
        else:
            dw = _np_durbin_watson(diffs)

        interpretation = (
            "strong positive autocorrelation"
            if dw < 1.0
            else (
                "positive autocorrelation"
                if dw < 1.5
                else (
                    "no significant autocorrelation"
                    if dw < 2.5
                    else (
                        "negative autocorrelation"
                        if dw < 3.0
                        else "strong negative autocorrelation"
                    )
                )
            )
        )

        summary = {
            "series": series_name,
            "durbin_watson": dw,
            "interpretation": interpretation,
            "n": len(diffs),
        }
        log.info("Durbin-Watson on '%s': DW=%.4f (%s)", series_name, dw, interpretation)
        return AnalysisResult(name=f"dw_{series_name}", summary=summary)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run_full_analysis(
        self, save_dir: Optional[str] = None
    ) -> Dict[str, AnalysisResult]:
        """Execute the complete analysis pipeline and return all results."""
        results: Dict[str, AnalysisResult] = {}

        # Time series analyses (require snapshots)
        if len(self.snapshots) >= 10:
            results["stationarity"] = self.test_stationarity()
            results["durbin_watson"] = self.durbin_watson_test()

        if len(self.snapshots) >= 45:
            results["acf_pacf"] = self.acf_pacf_analysis()

        if len(self.snapshots) >= 30:
            results["arima"] = self.arima_forecast()

        if len(self.snapshots) >= 60:
            results["seasonal"] = self.seasonal_decomposition()
            results["holt_winters"] = self.holt_winters()

        if len(self.snapshots) >= 15:
            results["var"] = self.var_analysis()
            results["granger"] = self.granger_causality()

        # Regression analyses (require game records)
        if len(self.game_records) >= 10:
            results["ols"] = self.ols_winrate_factors()
            results["logistic"] = self.logistic_battle_outcome()

        # Residual diagnostics on ARIMA if available
        if "arima" in results and results["arima"].residuals is not None:
            plot_path = f"{save_dir}/arima_residuals.png" if save_dir else None
            results["arima_residuals"] = self.residual_analysis(
                results["arima"], save_path=plot_path
            )

        if "ols" in results and results["ols"].residuals is not None:
            plot_path = f"{save_dir}/ols_residuals.png" if save_dir else None
            results["ols_residuals"] = self.residual_analysis(
                results["ols"], save_path=plot_path
            )

        log.info("Full analysis complete — %d results produced.", len(results))
        return results


# ---------------------------------------------------------------------------
# Synthetic data generator for testing / demo
# ---------------------------------------------------------------------------


def generate_synthetic_snapshots(
    n: int = 200, seed: int = 42
) -> List[ResourceSnapshot]:
    """Generate realistic SC2 economy snapshots for testing."""
    rng = np.random.RandomState(seed)
    snapshots: List[ResourceSnapshot] = []

    minerals = 50.0
    gas = 0.0
    workers = 12
    army = 0
    bases = 1
    time_step = 5.0  # seconds per snapshot

    for i in range(n):
        game_time = i * time_step
        # Income scales with workers and bases
        mineral_income = workers * 1.2 + rng.normal(0, 3)
        gas_income = (
            max(0, (workers - 16) * 0.8 + rng.normal(0, 2)) if workers > 16 else 0
        )

        # Economy evolves
        minerals += mineral_income * (time_step / 60.0)
        gas += gas_income * (time_step / 60.0)

        # Growth events
        if i % 40 == 0 and bases < 5:
            bases += 1
        if i % 5 == 0 and workers < 70:
            workers += rng.randint(0, 3)
        if i % 8 == 0:
            army += rng.randint(0, 5)

        # Spend resources
        if minerals > 300:
            minerals -= rng.uniform(50, 150)
        if gas > 200:
            gas -= rng.uniform(30, 80)

        supply_used = workers + army

        snapshots.append(
            ResourceSnapshot(
                game_time_s=game_time,
                minerals=max(0, minerals),
                gas=max(0, gas),
                supply_used=supply_used,
                army_supply=army,
                worker_count=workers,
                base_count=bases,
                income_minerals=max(0, mineral_income),
                income_gas=max(0, gas_income),
            )
        )

    return snapshots


def generate_synthetic_records(n: int = 100, seed: int = 42) -> List[GameRecord]:
    """Generate synthetic game records for regression testing."""
    rng = np.random.RandomState(seed)
    races = ["zerg", "terran", "protoss"]
    records: List[GameRecord] = []

    for _ in range(n):
        mineral_inc = rng.uniform(40, 100)
        gas_inc = rng.uniform(20, 60)
        army = rng.uniform(20, 100)
        workers = rng.uniform(30, 75)
        bases = rng.uniform(1, 5)
        apm = rng.uniform(60, 300)
        tech = rng.randint(1, 4)
        length = rng.uniform(180, 900)
        opp = rng.choice(races)

        # Win probability influenced by factors
        logit = (
            0.02 * mineral_inc
            + 0.01 * gas_inc
            + 0.03 * army
            + 0.01 * workers
            + 0.15 * bases
            + 0.005 * apm
            + 0.3 * tech
            - 0.001 * length
            - 6.0
        )
        win_prob = 1 / (1 + np.exp(-logit))
        win = rng.random() < win_prob

        records.append(
            GameRecord(
                avg_mineral_income=mineral_inc,
                avg_gas_income=gas_inc,
                avg_army_supply=army,
                avg_worker_count=workers,
                avg_base_count=bases,
                avg_apm=apm,
                tech_tier_reached=tech,
                game_length_s=length,
                opponent_race=opp,
                win=bool(win),
            )
        )

    return records


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run a demo analysis with synthetic data."""
    print("=" * 70)
    print("SC2 Resource Analysis — statsmodels (Phase 594)")
    print("=" * 70)

    snapshots = generate_synthetic_snapshots(200)
    records = generate_synthetic_records(100)

    analyser = SC2ResourceAnalysis(snapshots=snapshots, game_records=records)
    results = analyser.run_full_analysis()

    for name, result in results.items():
        print(f"\n{'─' * 50}")
        print(f"  {result.name}")
        print(f"{'─' * 50}")
        for k, v in result.summary.items():
            if isinstance(v, float):
                print(f"    {k:30s}: {v:.6f}")
            elif isinstance(v, dict):
                print(f"    {k}:")
                for kk, vv in v.items():
                    val_str = f"{vv:.6f}" if isinstance(vv, float) else str(vv)
                    print(f"      {str(kk):28s}: {val_str}")
            else:
                print(f"    {k:30s}: {v}")

    print(f"\n{'=' * 70}")
    print(f"Analysis complete — {len(results)} results produced.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
