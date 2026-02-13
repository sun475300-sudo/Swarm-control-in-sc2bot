"""
Trading Strategies
- 변동성 돌파 (Volatility Breakout)
- 이동평균 크로스오버 (MA Crossover)
- RSI 기반 매매
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
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


# ── 전략 팩토리 ──
AVAILABLE_STRATEGIES = {
    "volatility_breakout": VolatilityBreakout,
    "ma_crossover": MACrossover,
    "rsi": RSIStrategy,
}


def get_strategy(name: str, **kwargs):
    """이름으로 전략 인스턴스 생성"""
    cls = AVAILABLE_STRATEGIES.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(AVAILABLE_STRATEGIES.keys())}")
    return cls(**kwargs)