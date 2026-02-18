"""
Trading Strategies
- 변동성 돌파 (Volatility Breakout)
- 이동평균 크로스오버 (MA Crossover)
- RSI 기반 매매
- VWAP 기반 매매 (#44)
- 스토캐스틱 RSI (#45)
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import numpy as np
import pandas as pd

logger = logging.getLogger("crypto.strategies")


class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradeSignal:
    signal: Signal
    ticker: str
    reason: str
    strength: float = 0.0  # 0.0 ~ 1.0 (신호 강도)


def _calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI (Relative Strength Index) 계산"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    avg_loss = avg_loss.replace(0, 1e-10)
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


class VolatilityBreakout:
    """
    래리 윌리엄스 변동성 돌파 전략
    - 전일 고가-저가 범위의 k% 이상 상승 시 매수
    - 다음날 시가에 매도 (또는 손절)
    """

    def __init__(self, k: float = 0.5):
        self.k = k
        self.name = "volatility_breakout"

    def evaluate(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < 2:
            return TradeSignal(Signal.HOLD, ticker, "데이터 부족")

        today = df.iloc[-1]
        yesterday = df.iloc[-2]

        target_range = (yesterday["high"] - yesterday["low"]) * self.k
        target_price = today["open"] + target_range
        current_price = today["close"]

        if current_price > target_price:
            strength = min((current_price - target_price) / target_range, 1.0) if target_range > 0 else 0.5
            return TradeSignal(
                Signal.BUY, ticker,
                f"변동성 돌파: 현재가 {current_price:,.0f} > 목표가 {target_price:,.0f}",
                strength=strength
            )
        return TradeSignal(Signal.HOLD, ticker, f"돌파 미달: {current_price:,.0f} < {target_price:,.0f}")


class MACrossover:
    """
    이동평균 크로스오버 전략
    - 단기 MA가 장기 MA 위로 골든크로스 → 매수
    - 단기 MA가 장기 MA 아래로 데드크로스 → 매도
    """

    def __init__(self, short_period: int = 5, long_period: int = 20):
        self.short_period = short_period
        self.long_period = long_period
        self.name = "ma_crossover"

    def evaluate(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < self.long_period + 1:
            return TradeSignal(Signal.HOLD, ticker, "데이터 부족")

        df = df.copy()
        df["ma_short"] = df["close"].rolling(window=self.short_period).mean()
        df["ma_long"] = df["close"].rolling(window=self.long_period).mean()

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        # 골든크로스 (아래→위)
        if prev["ma_short"] <= prev["ma_long"] and curr["ma_short"] > curr["ma_long"]:
            gap = (curr["ma_short"] - curr["ma_long"]) / curr["ma_long"]
            return TradeSignal(
                Signal.BUY, ticker,
                f"골든크로스: MA{self.short_period}={curr['ma_short']:,.0f} > MA{self.long_period}={curr['ma_long']:,.0f}",
                strength=min(gap * 10, 1.0)
            )

        # 데드크로스 (위→아래)
        if prev["ma_short"] >= prev["ma_long"] and curr["ma_short"] < curr["ma_long"]:
            gap = (curr["ma_long"] - curr["ma_short"]) / curr["ma_long"]
            return TradeSignal(
                Signal.SELL, ticker,
                f"데드크로스: MA{self.short_period}={curr['ma_short']:,.0f} < MA{self.long_period}={curr['ma_long']:,.0f}",
                strength=min(gap * 10, 1.0)
            )

        return TradeSignal(Signal.HOLD, ticker, "크로스 신호 없음")


class RSIStrategy:
    """
    RSI 기반 매매 전략
    - RSI < oversold → 매수 (과매도)
    - RSI > overbought → 매도 (과매수)
    """

    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = "rsi"

    def evaluate(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < self.period + 1:
            return TradeSignal(Signal.HOLD, ticker, "데이터 부족")

        rsi_series = _calc_rsi(df["close"], self.period)
        rsi = rsi_series.iloc[-1]

        if pd.isna(rsi):
            return TradeSignal(Signal.HOLD, ticker, "RSI 계산 불가")

        if rsi < self.oversold:
            strength = (self.oversold - rsi) / self.oversold
            return TradeSignal(
                Signal.BUY, ticker,
                f"RSI 과매도: {rsi:.1f} < {self.oversold}",
                strength=min(strength, 1.0)
            )

        if rsi > self.overbought:
            strength = (rsi - self.overbought) / (100 - self.overbought)
            return TradeSignal(
                Signal.SELL, ticker,
                f"RSI 과매수: {rsi:.1f} > {self.overbought}",
                strength=min(strength, 1.0)
            )

        return TradeSignal(Signal.HOLD, ticker, f"RSI 중립: {rsi:.1f}")


class VWAPStrategy:
    """
    VWAP (거래량 가중 평균 가격) 기반 매매 전략 (#44)
    - 현재가가 VWAP 아래에서 위로 돌파 시 매수
    - 현재가가 VWAP 위에서 아래로 이탈 시 매도
    - VWAP과의 괴리율로 신호 강도 결정
    """

    def __init__(self, period: int = 20, deviation_threshold: float = 2.0):
        """
        VWAP 전략 초기화

        Args:
            period: VWAP 계산 기간 (캔들 수)
            deviation_threshold: 매매 신호 발생 기준 괴리율 (%)
        """
        self.period = period
        self.deviation_threshold = deviation_threshold
        self.name = "vwap"

    @staticmethod
    def _calc_vwap(df: pd.DataFrame, period: int) -> pd.Series:
        """VWAP (Volume Weighted Average Price) 계산"""
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        tp_volume = typical_price * df["volume"]
        cum_tp_vol = tp_volume.rolling(window=period).sum()
        cum_vol = df["volume"].rolling(window=period).sum()
        cum_vol = cum_vol.replace(0, np.nan)
        vwap = cum_tp_vol / cum_vol
        return vwap

    def evaluate(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        """VWAP 기반 매매 신호 평가"""
        if df is None or len(df) < self.period + 1:
            return TradeSignal(Signal.HOLD, ticker, "데이터 부족")

        df = df.copy()
        vwap = self._calc_vwap(df, self.period)

        curr_close = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2]
        curr_vwap = vwap.iloc[-1]
        prev_vwap = vwap.iloc[-2]

        if pd.isna(curr_vwap) or pd.isna(prev_vwap):
            return TradeSignal(Signal.HOLD, ticker, "VWAP 계산 불가")

        # VWAP 대비 괴리율 (%)
        deviation_pct = ((curr_close - curr_vwap) / curr_vwap) * 100

        # VWAP 상향 돌파: 이전에 아래, 현재 위
        if prev_close <= prev_vwap and curr_close > curr_vwap:
            strength = min(abs(deviation_pct) / self.deviation_threshold, 1.0)
            return TradeSignal(
                Signal.BUY, ticker,
                f"VWAP 상향 돌파: 현재가 {curr_close:,.0f} > VWAP {curr_vwap:,.0f} (괴리 {deviation_pct:+.2f}%)",
                strength=strength,
            )

        # VWAP 하향 이탈: 이전에 위, 현재 아래
        if prev_close >= prev_vwap and curr_close < curr_vwap:
            strength = min(abs(deviation_pct) / self.deviation_threshold, 1.0)
            return TradeSignal(
                Signal.SELL, ticker,
                f"VWAP 하향 이탈: 현재가 {curr_close:,.0f} < VWAP {curr_vwap:,.0f} (괴리 {deviation_pct:+.2f}%)",
                strength=strength,
            )

        # 과도한 괴리 시 반전 신호
        if deviation_pct < -self.deviation_threshold:
            strength = min(abs(deviation_pct) / (self.deviation_threshold * 2), 1.0)
            return TradeSignal(
                Signal.BUY, ticker,
                f"VWAP 하방 과괴리: {deviation_pct:+.2f}% (기준: {self.deviation_threshold}%)",
                strength=strength * 0.7,
            )

        if deviation_pct > self.deviation_threshold:
            strength = min(abs(deviation_pct) / (self.deviation_threshold * 2), 1.0)
            return TradeSignal(
                Signal.SELL, ticker,
                f"VWAP 상방 과괴리: {deviation_pct:+.2f}% (기준: {self.deviation_threshold}%)",
                strength=strength * 0.7,
            )

        return TradeSignal(
            Signal.HOLD, ticker,
            f"VWAP 중립: 현재가 {curr_close:,.0f}, VWAP {curr_vwap:,.0f} (괴리 {deviation_pct:+.2f}%)"
        )


class StochasticRSIStrategy:
    """
    스토캐스틱 RSI 기반 매매 전략 (#45)
    - RSI 값에 스토캐스틱 오실레이터를 적용
    - %K가 %D를 상향 돌파 + 과매도 영역 → 매수
    - %K가 %D를 하향 돌파 + 과매수 영역 → 매도
    """

    def __init__(
        self,
        rsi_period: int = 14,
        stoch_period: int = 14,
        k_smooth: int = 3,
        d_smooth: int = 3,
        oversold: float = 20.0,
        overbought: float = 80.0,
    ):
        """
        스토캐스틱 RSI 전략 초기화

        Args:
            rsi_period: RSI 계산 기간
            stoch_period: 스토캐스틱 적용 기간
            k_smooth: %K 스무딩 기간
            d_smooth: %D 스무딩 기간 (%K의 이동평균)
            oversold: 과매도 기준
            overbought: 과매수 기준
        """
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.k_smooth = k_smooth
        self.d_smooth = d_smooth
        self.oversold = oversold
        self.overbought = overbought
        self.name = "stochastic_rsi"

    def _calc_stochastic_rsi(self, series: pd.Series) -> tuple:
        """
        스토캐스틱 RSI 계산

        Returns:
            (stoch_k, stoch_d) Series 튜플
        """
        rsi = _calc_rsi(series, self.rsi_period)

        # 스토캐스틱 공식: (RSI - RSI_Low) / (RSI_High - RSI_Low) * 100
        rsi_low = rsi.rolling(window=self.stoch_period).min()
        rsi_high = rsi.rolling(window=self.stoch_period).max()

        denom = rsi_high - rsi_low
        denom = denom.replace(0, np.nan)

        stoch_rsi = ((rsi - rsi_low) / denom) * 100

        # %K: 스무딩
        stoch_k = stoch_rsi.rolling(window=self.k_smooth).mean()
        # %D: %K의 이동평균
        stoch_d = stoch_k.rolling(window=self.d_smooth).mean()

        return stoch_k, stoch_d

    def evaluate(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        """스토캐스틱 RSI 기반 매매 신호 평가"""
        min_data = self.rsi_period + self.stoch_period + self.k_smooth + self.d_smooth + 2
        if df is None or len(df) < min_data:
            return TradeSignal(Signal.HOLD, ticker, "데이터 부족")

        stoch_k, stoch_d = self._calc_stochastic_rsi(df["close"])

        curr_k = stoch_k.iloc[-1]
        prev_k = stoch_k.iloc[-2]
        curr_d = stoch_d.iloc[-1]
        prev_d = stoch_d.iloc[-2]

        if any(pd.isna(v) for v in [curr_k, prev_k, curr_d, prev_d]):
            return TradeSignal(Signal.HOLD, ticker, "Stoch RSI 계산 불가")

        # %K가 %D를 상향 돌파 + 과매도 영역
        if prev_k <= prev_d and curr_k > curr_d and curr_k < self.oversold:
            strength = (self.oversold - curr_k) / self.oversold
            return TradeSignal(
                Signal.BUY, ticker,
                f"Stoch RSI 매수: %K({curr_k:.1f})가 %D({curr_d:.1f}) 상향돌파 (과매도영역)",
                strength=min(strength, 1.0),
            )

        # 과매도 영역에서 반등 (크로스 없이도 극단 영역)
        if curr_k < self.oversold * 0.5 and curr_k > prev_k:
            strength = (self.oversold - curr_k) / self.oversold
            return TradeSignal(
                Signal.BUY, ticker,
                f"Stoch RSI 극과매도 반등: %K={curr_k:.1f} (기준: {self.oversold})",
                strength=min(strength * 0.6, 1.0),
            )

        # %K가 %D를 하향 돌파 + 과매수 영역
        if prev_k >= prev_d and curr_k < curr_d and curr_k > self.overbought:
            strength = (curr_k - self.overbought) / (100 - self.overbought)
            return TradeSignal(
                Signal.SELL, ticker,
                f"Stoch RSI 매도: %K({curr_k:.1f})가 %D({curr_d:.1f}) 하향돌파 (과매수영역)",
                strength=min(strength, 1.0),
            )

        # 과매수 영역에서 하락 (크로스 없이도 극단 영역)
        if curr_k > self.overbought + (100 - self.overbought) * 0.5 and curr_k < prev_k:
            strength = (curr_k - self.overbought) / (100 - self.overbought)
            return TradeSignal(
                Signal.SELL, ticker,
                f"Stoch RSI 극과매수 하락: %K={curr_k:.1f} (기준: {self.overbought})",
                strength=min(strength * 0.6, 1.0),
            )

        return TradeSignal(
            Signal.HOLD, ticker,
            f"Stoch RSI 중립: %K={curr_k:.1f}, %D={curr_d:.1f}"
        )


# ── 전략 팩토리 ──
AVAILABLE_STRATEGIES = {
    "volatility_breakout": VolatilityBreakout,
    "ma_crossover": MACrossover,
    "rsi": RSIStrategy,
    "vwap": VWAPStrategy,
    "stochastic_rsi": StochasticRSIStrategy,
}


def get_strategy(name: str, **kwargs):
    """이름으로 전략 인스턴스 생성"""
    cls = AVAILABLE_STRATEGIES.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(AVAILABLE_STRATEGIES.keys())}")
    return cls(**kwargs)