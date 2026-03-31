# Phase 595: Prophet
"""
sc2_winrate_forecast.py — StarCraft II Win Rate Trend Forecasting with Prophet

Models ladder win rate over time, detects strategy shift changepoints,
applies daily play-pattern seasonality and patch/tournament holiday effects,
performs rolling-origin cross-validation with MAE/RMSE/MAPE metrics,
forecasts multiple game metrics (APM, win_rate, MMR), detects performance
anomalies, and visualises forecast components with confidence intervals.

Graceful fallback to a pure-NumPy implementation when Prophet is absent.
"""

from __future__ import annotations

import datetime
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
log = logging.getLogger("sc2_winrate_forecast")

# ---------------------------------------------------------------------------
# Optional Prophet import — graceful fallback
# ---------------------------------------------------------------------------
try:
    from prophet import Prophet
    from prophet.diagnostics import cross_validation, performance_metrics
    PROPHET_AVAILABLE = True
    log.info("Prophet available.")
except ImportError:
    PROPHET_AVAILABLE = False
    log.warning(
        "Prophet not installed. Running pure-NumPy fallback. "
        "Install with: pip install prophet"
    )

try:
    import pandas as pd
    PD_AVAILABLE = True
except ImportError:
    PD_AVAILABLE = False

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
class LadderGame:
    """One completed ladder game."""
    timestamp: datetime.datetime
    win: bool
    mmr: float
    apm: float
    game_length_s: float
    opponent_race: str
    map_name: str


@dataclass
class PatchEvent:
    """A game patch or tournament date used as a Prophet holiday."""
    date: datetime.datetime
    name: str
    lower_window: int = 0   # days before the event to include
    upper_window: int = 1   # days after the event to include


@dataclass
class ForecastResult:
    """Container for forecast outputs."""
    name: str
    summary: Dict[str, Any] = field(default_factory=dict)
    dates: Optional[List[datetime.datetime]] = None
    actual: Optional[np.ndarray] = None
    predicted: Optional[np.ndarray] = None
    lower: Optional[np.ndarray] = None
    upper: Optional[np.ndarray] = None
    changepoints: Optional[List[datetime.datetime]] = None
    anomalies: Optional[List[int]] = None
    plot_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Pure-NumPy fallback helpers
# ---------------------------------------------------------------------------

def _np_moving_average(y: np.ndarray, window: int = 7) -> np.ndarray:
    """Simple centred moving average."""
    kernel = np.ones(window) / window
    padded = np.pad(y, (window // 2, window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")[:len(y)]


def _np_linear_trend(y: np.ndarray) -> Tuple[float, float]:
    """OLS slope and intercept."""
    n = len(y)
    x = np.arange(n, dtype=np.float64)
    x_m, y_m = x.mean(), y.mean()
    denom = np.sum((x - x_m) ** 2)
    slope = np.sum((x - x_m) * (y - y_m)) / max(denom, 1e-12)
    return slope, float(y_m - slope * x_m)


def _np_detect_changepoints(y: np.ndarray, n_changepoints: int = 5,
                             window: int = 14) -> List[int]:
    """Detect changepoints via maximum absolute derivative."""
    if len(y) < window * 2:
        return []
    smoothed = _np_moving_average(y, window)
    deriv = np.abs(np.diff(smoothed))
    # Pick top-n indices, excluding boundary
    margin = window
    deriv[:margin] = 0
    deriv[-margin:] = 0
    indices = np.argsort(deriv)[::-1]
    # Ensure minimum separation
    selected: List[int] = []
    for idx in indices:
        if len(selected) >= n_changepoints:
            break
        if all(abs(idx - s) > window for s in selected):
            selected.append(int(idx))
    return sorted(selected)


def _np_seasonal_pattern(n: int, period: int = 7) -> np.ndarray:
    """Simple sinusoidal seasonality."""
    return np.sin(2 * np.pi * np.arange(n) / period) * 0.02


def _np_forecast(y: np.ndarray, steps: int, period: int = 7) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Trend + seasonal forecast with confidence bands."""
    slope, intercept = _np_linear_trend(y)
    n = len(y)
    residuals = y - (slope * np.arange(n) + intercept)
    std = max(np.std(residuals), 1e-6)

    future_x = np.arange(n, n + steps)
    trend = slope * future_x + intercept
    seasonal = _np_seasonal_pattern(steps, period)
    predicted = trend + seasonal
    lower = predicted - 1.96 * std
    upper = predicted + 1.96 * std
    return predicted, lower, upper


# ---------------------------------------------------------------------------
# SC2WinRateForecast
# ---------------------------------------------------------------------------

class SC2WinRateForecast:
    """Prophet-based forecasting of SC2 ladder performance metrics."""

    def __init__(self, games: Optional[List[LadderGame]] = None,
                 patch_events: Optional[List[PatchEvent]] = None):
        self.games: List[LadderGame] = games or []
        self.patch_events: List[PatchEvent] = patch_events or []
        self._daily_cache: Optional[Dict[str, Any]] = None
        log.info(
            "SC2WinRateForecast initialised — %d games, %d patch events.",
            len(self.games), len(self.patch_events),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def add_games(self, games: List[LadderGame]) -> None:
        self.games.extend(games)
        self._daily_cache = None
        log.info("Added %d games (total %d).", len(games), len(self.games))

    def add_patch_events(self, events: List[PatchEvent]) -> None:
        self.patch_events.extend(events)
        log.info("Added %d patch events (total %d).", len(events), len(self.patch_events))

    def _aggregate_daily(self) -> Dict[str, Any]:
        """Aggregate games into daily statistics."""
        if self._daily_cache is not None:
            return self._daily_cache

        daily: Dict[str, Dict[str, List[float]]] = {}
        for g in sorted(self.games, key=lambda x: x.timestamp):
            day = g.timestamp.strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = {"wins": [], "mmr": [], "apm": [], "lengths": []}
            daily[day]["wins"].append(1.0 if g.win else 0.0)
            daily[day]["mmr"].append(g.mmr)
            daily[day]["apm"].append(g.apm)
            daily[day]["lengths"].append(g.game_length_s)

        dates: List[datetime.datetime] = []
        win_rates: List[float] = []
        avg_mmr: List[float] = []
        avg_apm: List[float] = []
        games_played: List[int] = []

        for day_str in sorted(daily.keys()):
            d = daily[day_str]
            dates.append(datetime.datetime.strptime(day_str, "%Y-%m-%d"))
            win_rates.append(float(np.mean(d["wins"])))
            avg_mmr.append(float(np.mean(d["mmr"])))
            avg_apm.append(float(np.mean(d["apm"])))
            games_played.append(len(d["wins"]))

        self._daily_cache = {
            "dates": dates,
            "win_rate": np.array(win_rates),
            "mmr": np.array(avg_mmr),
            "apm": np.array(avg_apm),
            "games_played": np.array(games_played),
        }
        return self._daily_cache

    def _build_holidays_df(self) -> Any:
        """Build a pandas DataFrame of holidays for Prophet."""
        if not PD_AVAILABLE or not self.patch_events:
            return None
        rows = []
        for ev in self.patch_events:
            rows.append({
                "holiday": ev.name,
                "ds": ev.date,
                "lower_window": ev.lower_window,
                "upper_window": ev.upper_window,
            })
        return pd.DataFrame(rows)

    def _require_games(self, min_n: int = 30) -> None:
        if len(self.games) < min_n:
            raise ValueError(f"Need >= {min_n} games, got {len(self.games)}.")

    # ------------------------------------------------------------------
    # 1. Win rate time series forecast
    # ------------------------------------------------------------------

    def forecast_win_rate(self, forecast_days: int = 30,
                          changepoint_prior: float = 0.05,
                          interval_width: float = 0.95) -> ForecastResult:
        """Forecast daily win rate using Prophet (or fallback)."""
        self._require_games()
        daily = self._aggregate_daily()
        dates = daily["dates"]
        y = daily["win_rate"]

        if PROPHET_AVAILABLE and PD_AVAILABLE:
            df = pd.DataFrame({"ds": dates, "y": y})
            holidays_df = self._build_holidays_df()

            model = Prophet(
                changepoint_prior_scale=changepoint_prior,
                interval_width=interval_width,
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=False,
                holidays=holidays_df,
            )
            # Custom daily play pattern seasonality
            model.add_seasonality(name="daily_play", period=1, fourier_order=3)

            with _suppress_stdout():
                model.fit(df)

            future = model.make_future_dataframe(periods=forecast_days)
            forecast = model.predict(future)

            predicted = forecast["yhat"].values
            lower = forecast["yhat_lower"].values
            upper = forecast["yhat_upper"].values
            forecast_dates = forecast["ds"].dt.to_pydatetime().tolist()

            changepoints = model.changepoints.dt.to_pydatetime().tolist() if hasattr(model, "changepoints") else []

            summary = {
                "metric": "win_rate",
                "n_days_history": len(dates),
                "forecast_days": forecast_days,
                "changepoint_prior": changepoint_prior,
                "interval_width": interval_width,
                "n_changepoints": len(changepoints),
                "current_win_rate": float(y[-1]),
                "forecast_mean": float(np.mean(predicted[-forecast_days:])),
                "trend_direction": (
                    "improving" if predicted[-1] > predicted[-forecast_days - 1]
                    else "declining"
                ),
            }
        else:
            # Fallback
            predicted, lower, upper = _np_forecast(y, forecast_days)
            forecast_dates = dates + [
                dates[-1] + datetime.timedelta(days=i + 1) for i in range(forecast_days)
            ]
            full_pred = np.concatenate([y, predicted])
            full_lower = np.concatenate([y - 0.05, lower])
            full_upper = np.concatenate([y + 0.05, upper])
            predicted = full_pred
            lower = full_lower
            upper = full_upper

            cp_indices = _np_detect_changepoints(y)
            changepoints = [dates[i] for i in cp_indices if i < len(dates)]

            summary = {
                "metric": "win_rate",
                "n_days_history": len(dates),
                "forecast_days": forecast_days,
                "n_changepoints": len(changepoints),
                "current_win_rate": float(y[-1]),
                "forecast_mean": float(np.mean(predicted[-forecast_days:])),
                "trend_direction": (
                    "improving" if predicted[-1] > predicted[-forecast_days - 1]
                    else "declining"
                ),
                "note": "linear-trend fallback (Prophet not available)",
            }

        log.info(
            "Win rate forecast: current=%.3f  forecast_mean=%.3f  trend=%s  changepoints=%d",
            summary["current_win_rate"], summary["forecast_mean"],
            summary["trend_direction"], summary["n_changepoints"],
        )
        return ForecastResult(
            name="win_rate_forecast", summary=summary,
            dates=forecast_dates, predicted=predicted,
            lower=lower, upper=upper, changepoints=changepoints,
        )

    # ------------------------------------------------------------------
    # 2. Changepoint detection for strategy shifts
    # ------------------------------------------------------------------

    def detect_strategy_shifts(self, n_changepoints: int = 10,
                               changepoint_prior: float = 0.1) -> ForecastResult:
        """Identify moments where win rate trend shifted significantly."""
        self._require_games()
        daily = self._aggregate_daily()
        dates = daily["dates"]
        y = daily["win_rate"]

        if PROPHET_AVAILABLE and PD_AVAILABLE:
            df = pd.DataFrame({"ds": dates, "y": y})
            model = Prophet(
                n_changepoints=n_changepoints,
                changepoint_prior_scale=changepoint_prior,
                yearly_seasonality=False,
                weekly_seasonality=False,
            )
            with _suppress_stdout():
                model.fit(df)

            changepoints = model.changepoints.dt.to_pydatetime().tolist()
            deltas = model.params["delta"].flatten()
            # Magnitude of each changepoint
            cp_magnitudes = {
                str(cp.date()): float(abs(d))
                for cp, d in zip(changepoints, deltas[:len(changepoints)])
            }

            summary = {
                "n_changepoints_detected": len(changepoints),
                "changepoint_prior": changepoint_prior,
                "changepoint_magnitudes": cp_magnitudes,
                "largest_shift_date": max(cp_magnitudes, key=cp_magnitudes.get) if cp_magnitudes else None,
                "largest_shift_magnitude": max(cp_magnitudes.values()) if cp_magnitudes else 0,
            }
        else:
            cp_indices = _np_detect_changepoints(y, n_changepoints)
            changepoints = [dates[i] for i in cp_indices if i < len(dates)]
            # Approximate magnitudes from derivative
            smoothed = _np_moving_average(y, 7)
            deriv = np.diff(smoothed)
            cp_magnitudes = {}
            for idx in cp_indices:
                if idx < len(deriv):
                    cp_magnitudes[str(dates[idx].date())] = float(abs(deriv[idx]))

            summary = {
                "n_changepoints_detected": len(changepoints),
                "changepoint_magnitudes": cp_magnitudes,
                "largest_shift_date": max(cp_magnitudes, key=cp_magnitudes.get) if cp_magnitudes else None,
                "largest_shift_magnitude": max(cp_magnitudes.values()) if cp_magnitudes else 0,
                "note": "derivative-based fallback",
            }

        log.info(
            "Strategy shift detection: %d changepoints, largest at %s (%.4f)",
            summary["n_changepoints_detected"],
            summary.get("largest_shift_date"),
            summary.get("largest_shift_magnitude", 0),
        )
        return ForecastResult(
            name="strategy_shifts", summary=summary,
            dates=dates, actual=y, changepoints=changepoints,
        )

    # ------------------------------------------------------------------
    # 3. Cross-validation with rolling origin
    # ------------------------------------------------------------------

    def cross_validate(self, initial_days: int = 60,
                       period_days: int = 7,
                       horizon_days: int = 14) -> ForecastResult:
        """Rolling-origin cross-validation with MAE, RMSE, MAPE."""
        self._require_games(min_n=50)
        daily = self._aggregate_daily()
        dates = daily["dates"]
        y = daily["win_rate"]

        if PROPHET_AVAILABLE and PD_AVAILABLE:
            df = pd.DataFrame({"ds": dates, "y": y})
            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=True,
            )
            with _suppress_stdout():
                model.fit(df)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                cv_results = cross_validation(
                    model,
                    initial=f"{initial_days} days",
                    period=f"{period_days} days",
                    horizon=f"{horizon_days} days",
                )
                metrics = performance_metrics(cv_results)

            summary = {
                "initial_days": initial_days,
                "period_days": period_days,
                "horizon_days": horizon_days,
                "mae": float(metrics["mae"].mean()),
                "rmse": float(metrics["rmse"].mean()),
                "mape": float(metrics["mape"].mean()),
                "coverage": float(metrics["coverage"].mean()),
                "n_cutoffs": int(cv_results["cutoff"].nunique()),
            }
        else:
            # Manual rolling-origin CV
            n = len(y)
            initial = min(initial_days, n // 2)
            errors_abs: List[float] = []
            errors_sq: List[float] = []
            errors_pct: List[float] = []

            cutoff = initial
            n_cutoffs = 0
            while cutoff + horizon_days <= n:
                train = y[:cutoff]
                test = y[cutoff:cutoff + horizon_days]

                slope, intercept = _np_linear_trend(train)
                pred = np.array([slope * (len(train) + i) + intercept for i in range(len(test))])

                for p, a in zip(pred, test):
                    errors_abs.append(abs(p - a))
                    errors_sq.append((p - a) ** 2)
                    if abs(a) > 1e-6:
                        errors_pct.append(abs((p - a) / a))

                cutoff += period_days
                n_cutoffs += 1

            mae = float(np.mean(errors_abs)) if errors_abs else 0
            rmse = float(np.sqrt(np.mean(errors_sq))) if errors_sq else 0
            mape = float(np.mean(errors_pct)) if errors_pct else 0

            summary = {
                "initial_days": initial_days,
                "period_days": period_days,
                "horizon_days": horizon_days,
                "mae": mae,
                "rmse": rmse,
                "mape": mape,
                "n_cutoffs": n_cutoffs,
                "note": "manual rolling-origin CV fallback",
            }

        log.info(
            "Cross-validation: MAE=%.4f  RMSE=%.4f  MAPE=%.4f  cutoffs=%d",
            summary["mae"], summary["rmse"], summary["mape"], summary["n_cutoffs"],
        )
        return ForecastResult(name="cross_validation", summary=summary)

    # ------------------------------------------------------------------
    # 4. Multiple metrics forecasting (APM, win_rate, MMR)
    # ------------------------------------------------------------------

    def forecast_multiple_metrics(self, forecast_days: int = 30) -> Dict[str, ForecastResult]:
        """Forecast win_rate, MMR, and APM independently."""
        self._require_games()
        daily = self._aggregate_daily()
        dates = daily["dates"]

        metrics = {"win_rate": daily["win_rate"], "mmr": daily["mmr"], "apm": daily["apm"]}
        results: Dict[str, ForecastResult] = {}

        for metric_name, y in metrics.items():
            if PROPHET_AVAILABLE and PD_AVAILABLE:
                df = pd.DataFrame({"ds": dates, "y": y})
                model = Prophet(
                    yearly_seasonality=False,
                    weekly_seasonality=True,
                    daily_seasonality=False,
                )
                with _suppress_stdout():
                    model.fit(df)
                future = model.make_future_dataframe(periods=forecast_days)
                forecast = model.predict(future)

                predicted = forecast["yhat"].values
                lower = forecast["yhat_lower"].values
                upper = forecast["yhat_upper"].values
                fc_dates = forecast["ds"].dt.to_pydatetime().tolist()

                summary = {
                    "metric": metric_name,
                    "current_value": float(y[-1]),
                    "forecast_mean": float(np.mean(predicted[-forecast_days:])),
                    "forecast_std": float(np.std(predicted[-forecast_days:])),
                }
            else:
                predicted, lower, upper = _np_forecast(y, forecast_days)
                fc_dates = dates + [
                    dates[-1] + datetime.timedelta(days=i + 1) for i in range(forecast_days)
                ]
                full_pred = np.concatenate([y, predicted])
                full_lower = np.concatenate([y - np.std(y), lower])
                full_upper = np.concatenate([y + np.std(y), upper])
                predicted, lower, upper = full_pred, full_lower, full_upper

                summary = {
                    "metric": metric_name,
                    "current_value": float(y[-1]),
                    "forecast_mean": float(np.mean(predicted[-forecast_days:])),
                    "forecast_std": float(np.std(predicted[-forecast_days:])),
                    "note": "linear-trend fallback",
                }

            results[metric_name] = ForecastResult(
                name=f"forecast_{metric_name}", summary=summary,
                dates=fc_dates, actual=y, predicted=predicted,
                lower=lower, upper=upper,
            )
            log.info(
                "Forecast %s: current=%.3f  mean=%.3f",
                metric_name, summary["current_value"], summary["forecast_mean"],
            )

        return results

    # ------------------------------------------------------------------
    # 5. Anomaly detection — sudden performance drops
    # ------------------------------------------------------------------

    def detect_anomalies(self, threshold_sigma: float = 2.0) -> ForecastResult:
        """Find days where performance deviates beyond threshold from forecast."""
        self._require_games()
        daily = self._aggregate_daily()
        dates = daily["dates"]
        y = daily["win_rate"]

        if PROPHET_AVAILABLE and PD_AVAILABLE:
            df = pd.DataFrame({"ds": dates, "y": y})
            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=True,
                interval_width=0.95,
            )
            with _suppress_stdout():
                model.fit(df)
            forecast = model.predict(df)

            predicted = forecast["yhat"].values
            lower = forecast["yhat_lower"].values
            upper = forecast["yhat_upper"].values

            anomaly_indices: List[int] = []
            for i in range(len(y)):
                if y[i] < lower[i] or y[i] > upper[i]:
                    anomaly_indices.append(i)
        else:
            smoothed = _np_moving_average(y, 7)
            residuals = y - smoothed
            std = max(np.std(residuals), 1e-6)
            predicted = smoothed
            lower = smoothed - threshold_sigma * std
            upper = smoothed + threshold_sigma * std

            anomaly_indices = []
            for i in range(len(y)):
                if abs(residuals[i]) > threshold_sigma * std:
                    anomaly_indices.append(i)

        anomaly_dates = [dates[i] for i in anomaly_indices if i < len(dates)]
        anomaly_values = [float(y[i]) for i in anomaly_indices if i < len(y)]

        # Classify anomalies
        drops = sum(1 for i in anomaly_indices if i < len(y) and y[i] < predicted[i])
        spikes = len(anomaly_indices) - drops

        summary = {
            "threshold_sigma": threshold_sigma,
            "total_anomalies": len(anomaly_indices),
            "performance_drops": drops,
            "performance_spikes": spikes,
            "anomaly_dates": [str(d.date()) for d in anomaly_dates],
            "anomaly_values": anomaly_values,
            "anomaly_rate": float(len(anomaly_indices) / max(len(y), 1)),
        }

        log.info(
            "Anomaly detection: %d anomalies (%d drops, %d spikes) out of %d days (%.1f%%)",
            summary["total_anomalies"], drops, spikes, len(y),
            summary["anomaly_rate"] * 100,
        )
        return ForecastResult(
            name="anomaly_detection", summary=summary,
            dates=dates, actual=y, predicted=predicted,
            lower=lower, upper=upper, anomalies=anomaly_indices,
        )

    # ------------------------------------------------------------------
    # 6. Component plots (trend, seasonality, holidays)
    # ------------------------------------------------------------------

    def plot_components(self, save_path: str = "sc2_forecast_components.png") -> ForecastResult:
        """Generate component visualisation (trend + seasonality + holidays)."""
        self._require_games()
        daily = self._aggregate_daily()
        dates = daily["dates"]
        y = daily["win_rate"]

        if PROPHET_AVAILABLE and PD_AVAILABLE and MPL_AVAILABLE:
            df = pd.DataFrame({"ds": dates, "y": y})
            holidays_df = self._build_holidays_df()
            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=True,
                holidays=holidays_df,
            )
            model.add_seasonality(name="daily_play", period=1, fourier_order=3)
            with _suppress_stdout():
                model.fit(df)
            future = model.make_future_dataframe(periods=30)
            forecast = model.predict(future)

            fig = model.plot_components(forecast)
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

            summary = {
                "plot_saved": save_path,
                "components": ["trend", "weekly", "daily_play"]
                              + (["holidays"] if holidays_df is not None else []),
            }
        elif MPL_AVAILABLE:
            # Fallback component plots
            fig, axes = plt.subplots(3, 1, figsize=(12, 10))

            # Trend
            slope, intercept = _np_linear_trend(y)
            trend = slope * np.arange(len(y)) + intercept
            axes[0].plot(dates, y, alpha=0.4, label="Actual")
            axes[0].plot(dates, trend, "r-", linewidth=2, label="Trend")
            axes[0].set_title("Trend Component")
            axes[0].legend()
            axes[0].set_ylabel("Win Rate")

            # Seasonality (weekly pattern)
            detrended = y - trend
            weekly = np.zeros(7)
            counts = np.zeros(7)
            for i, d in enumerate(dates):
                dow = d.weekday()
                weekly[dow] += detrended[i]
                counts[dow] += 1
            weekly /= np.maximum(counts, 1)
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            axes[1].bar(day_names, weekly, color="steelblue", alpha=0.7)
            axes[1].set_title("Weekly Seasonality")
            axes[1].set_ylabel("Effect on Win Rate")

            # Residuals
            seasonal_component = np.array([weekly[d.weekday()] for d in dates])
            residuals = y - trend - seasonal_component
            axes[2].plot(dates, residuals, linewidth=0.5, alpha=0.7)
            axes[2].axhline(0, color="red", linestyle="--", linewidth=0.8)
            axes[2].set_title("Residuals")
            axes[2].set_ylabel("Residual")

            plt.tight_layout()
            plt.savefig(save_path, dpi=150)
            plt.close(fig)

            summary = {
                "plot_saved": save_path,
                "components": ["trend", "weekly", "residuals"],
                "note": "matplotlib fallback",
            }
        else:
            summary = {"plot_saved": None, "note": "matplotlib not available"}

        log.info("Component plot: %s", summary.get("plot_saved"))
        return ForecastResult(name="component_plots", summary=summary, plot_path=save_path)

    # ------------------------------------------------------------------
    # 7. Confidence intervals visualisation
    # ------------------------------------------------------------------

    def plot_forecast_with_ci(self, forecast_result: ForecastResult,
                              save_path: str = "sc2_forecast_ci.png") -> str:
        """Plot forecast with confidence intervals."""
        if not MPL_AVAILABLE:
            log.warning("matplotlib not available, skipping plot.")
            return ""

        fig, ax = plt.subplots(figsize=(14, 6))

        n_actual = len(forecast_result.actual) if forecast_result.actual is not None else 0
        dates = forecast_result.dates or []

        if forecast_result.actual is not None and n_actual > 0:
            ax.plot(dates[:n_actual], forecast_result.actual, "k.", markersize=3, alpha=0.6, label="Actual")

        if forecast_result.predicted is not None:
            ax.plot(dates[:len(forecast_result.predicted)], forecast_result.predicted,
                    "b-", linewidth=1.5, label="Forecast")

        if forecast_result.lower is not None and forecast_result.upper is not None:
            n = min(len(forecast_result.lower), len(forecast_result.upper), len(dates))
            ax.fill_between(
                dates[:n], forecast_result.lower[:n], forecast_result.upper[:n],
                alpha=0.2, color="steelblue", label="95% CI",
            )

        if forecast_result.changepoints:
            for cp in forecast_result.changepoints:
                ax.axvline(cp, color="red", linestyle="--", alpha=0.4, linewidth=0.8)
            ax.axvline(forecast_result.changepoints[0], color="red", linestyle="--",
                       alpha=0.4, linewidth=0.8, label="Changepoints")

        if forecast_result.anomalies and forecast_result.actual is not None:
            anom_dates = [dates[i] for i in forecast_result.anomalies if i < len(dates)]
            anom_vals = [forecast_result.actual[i] for i in forecast_result.anomalies if i < n_actual]
            ax.scatter(anom_dates, anom_vals, color="red", s=40, zorder=5, label="Anomalies")

        ax.set_title(f"SC2 Forecast: {forecast_result.name}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Value")
        ax.legend(loc="best")
        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
        log.info("Forecast CI plot saved to %s", save_path)
        return save_path

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run_full_forecast(self, save_dir: Optional[str] = None) -> Dict[str, Any]:
        """Execute the complete forecasting pipeline."""
        results: Dict[str, Any] = {}

        # Core forecast
        results["win_rate"] = self.forecast_win_rate()

        # Strategy shifts
        results["strategy_shifts"] = self.detect_strategy_shifts()

        # Cross-validation
        n_days = len(self._aggregate_daily()["dates"])
        if n_days >= 80:
            results["cross_validation"] = self.cross_validate()

        # Multi-metric forecasts
        results["multi_metric"] = self.forecast_multiple_metrics()

        # Anomaly detection
        results["anomalies"] = self.detect_anomalies()

        # Plots
        if save_dir and MPL_AVAILABLE:
            results["components"] = self.plot_components(
                save_path=f"{save_dir}/components.png"
            )
            wr = results["win_rate"]
            self.plot_forecast_with_ci(wr, save_path=f"{save_dir}/win_rate_ci.png")

            anom = results["anomalies"]
            self.plot_forecast_with_ci(anom, save_path=f"{save_dir}/anomalies.png")

        log.info("Full forecast pipeline complete — %d result groups.", len(results))
        return results


# ---------------------------------------------------------------------------
# Stdout suppressor for Prophet's verbose fitting
# ---------------------------------------------------------------------------

import contextlib
import io
import os

@contextlib.contextmanager
def _suppress_stdout():
    """Suppress stdout (Prophet prints fitting progress)."""
    with open(os.devnull, "w") as devnull:
        old = os.dup(1)
        os.dup2(devnull.fileno(), 1)
        try:
            yield
        finally:
            os.dup2(old, 1)
            os.close(old)


# ---------------------------------------------------------------------------
# Synthetic data generator
# ---------------------------------------------------------------------------

def generate_synthetic_games(n_days: int = 180, games_per_day_range: Tuple[int, int] = (3, 10),
                             seed: int = 42) -> Tuple[List[LadderGame], List[PatchEvent]]:
    """Generate realistic SC2 ladder games for testing."""
    rng = np.random.RandomState(seed)
    races = ["zerg", "terran", "protoss"]
    maps = ["Equilibrium", "Goldenaura", "Radhuset", "Altitude", "Oceanborn"]

    games: List[LadderGame] = []
    base_date = datetime.datetime(2025, 6, 1)
    mmr = 3500.0
    base_win_rate = 0.50

    for day in range(n_days):
        current_date = base_date + datetime.timedelta(days=day)
        n_games = rng.randint(games_per_day_range[0], games_per_day_range[1] + 1)

        # Simulate skill improvement with periodic regressions
        skill_trend = 0.0002 * day  # slow improvement
        if 60 < day < 80:
            skill_trend -= 0.05  # strategy transition dip
        if 120 < day < 135:
            skill_trend -= 0.03  # patch adaptation

        # Weekend effect: slightly different performance
        dow = current_date.weekday()
        weekend_effect = 0.02 if dow >= 5 else 0.0

        for g in range(n_games):
            hour = rng.choice([10, 14, 18, 20, 21, 22, 23])
            ts = current_date.replace(hour=hour, minute=rng.randint(0, 60))

            win_prob = base_win_rate + skill_trend + weekend_effect + rng.normal(0, 0.02)
            win_prob = np.clip(win_prob, 0.1, 0.9)
            win = rng.random() < win_prob

            mmr += (25 if win else -20) + rng.normal(0, 5)
            mmr = max(2000, min(6000, mmr))

            apm = 120 + 0.1 * day + rng.normal(0, 20)

            games.append(LadderGame(
                timestamp=ts,
                win=bool(win),
                mmr=mmr,
                apm=max(50, apm),
                game_length_s=rng.uniform(180, 900),
                opponent_race=rng.choice(races),
                map_name=rng.choice(maps),
            ))

    # Patch events
    patch_events = [
        PatchEvent(date=base_date + datetime.timedelta(days=30), name="balance_patch_5.0.13", lower_window=-1, upper_window=3),
        PatchEvent(date=base_date + datetime.timedelta(days=75), name="balance_patch_5.0.14", lower_window=-1, upper_window=3),
        PatchEvent(date=base_date + datetime.timedelta(days=90), name="dreamhack_summer", lower_window=-2, upper_window=2),
        PatchEvent(date=base_date + datetime.timedelta(days=120), name="balance_patch_5.1.0", lower_window=-1, upper_window=5),
        PatchEvent(date=base_date + datetime.timedelta(days=150), name="gsl_finals", lower_window=-1, upper_window=1),
    ]

    return games, patch_events


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run a demo forecast with synthetic data."""
    print("=" * 70)
    print("SC2 Win Rate Forecast — Prophet (Phase 595)")
    print("=" * 70)

    games, patches = generate_synthetic_games(180)

    forecaster = SC2WinRateForecast(games=games, patch_events=patches)
    results = forecaster.run_full_forecast()

    for key, value in results.items():
        if isinstance(value, ForecastResult):
            print(f"\n{'─' * 50}")
            print(f"  {value.name}")
            print(f"{'─' * 50}")
            for k, v in value.summary.items():
                if isinstance(v, float):
                    print(f"    {k:30s}: {v:.6f}")
                elif isinstance(v, list) and len(v) > 5:
                    print(f"    {k:30s}: [{len(v)} items]")
                elif isinstance(v, dict):
                    print(f"    {k}:")
                    items = list(v.items())[:10]
                    for kk, vv in items:
                        val_str = f"{vv:.6f}" if isinstance(vv, float) else str(vv)
                        print(f"      {str(kk):28s}: {val_str}")
                    if len(v) > 10:
                        print(f"      ... and {len(v) - 10} more")
                else:
                    print(f"    {k:30s}: {v}")
        elif isinstance(value, dict):
            print(f"\n{'─' * 50}")
            print(f"  Multi-metric: {key}")
            print(f"{'─' * 50}")
            for metric_name, fr in value.items():
                if isinstance(fr, ForecastResult):
                    print(f"    {metric_name}: current={fr.summary.get('current_value', '?'):.3f}"
                          f"  forecast_mean={fr.summary.get('forecast_mean', '?'):.3f}")

    print(f"\n{'=' * 70}")
    print(f"Forecast complete — {len(results)} result groups.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
