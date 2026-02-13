"""
Smart Market Analyzer
- 다중 지표 종합 분석 (JARVIS AI가 판단할 수 있는 데이터 제공)
- 종합 스코어링 (-100 ~ +100)
- 자동 매매 의사결정 지원
"""
import logging
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np

from .upbit_client import UpbitClient
from .strategies import VolatilityBreakout, MACrossover, RSIStrategy, Signal

logger = logging.getLogger("crypto.analyzer")


@dataclass
class CoinAnalysis:
    """개별 코인 분석 결과"""
    ticker: str
    current_price: float = 0
    price_change_24h_pct: float = 0       # 24시간 변동률
    volume_change_pct: float = 0           # 거래량 변화율
    rsi_14: float = 50                     # RSI(14)
    ma5: float = 0                         # 5일 이동평균
    ma20: float = 0                        # 20일 이동평균
    ma60: float = 0                        # 60일 이동평균
    bb_upper: float = 0                    # 볼린저 밴드 상단
    bb_lower: float = 0                    # 볼린저 밴드 하단
    macd: float = 0                        # MACD 값
    macd_signal: float = 0                 # MACD 시그널선
    macd_histogram: float = 0              # MACD 히스토그램
    trend_strength: float = 0              # 추세 강도 (0~1)
    consecutive_candles: int = 0           # 연속 양봉(+) / 음봉(-) 수
    price_ma20_distance_pct: float = 0     # 현재가와 MA20 이격률
    volatility_signal: str = "hold"        # 변동성 돌파 신호
    ma_signal: str = "hold"                # 이동평균 신호
    rsi_signal: str = "hold"               # RSI 신호
    support_price: float = 0               # 지지선
    resistance_price: float = 0            # 저항선
    bid_ask_ratio: float = 0.5             # 매수/매도 비율
    score: int = 0                         # 종합 점수 (-100 ~ +100)
    recommendation: str = "HOLD"           # BUY / SELL / HOLD
    reasons: list = field(default_factory=list)  # 판단 근거


def _calc_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if not pd.isna(val) else 50.0


def _calc_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0):
    ma = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return float(upper.iloc[-1]), float(ma.iloc[-1]), float(lower.iloc[-1])


def _calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD 계산: (macd_line, signal_line, histogram)"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])


def _calc_consecutive_candles(df: pd.DataFrame) -> int:
    """연속 양봉(+) / 음봉(-) 수"""
    count = 0
    for i in range(len(df) - 1, 0, -1):
        is_green = df["close"].iloc[i] > df["open"].iloc[i]
        if count == 0:
            count = 1 if is_green else -1
        elif (count > 0 and is_green) or (count < 0 and not is_green):
            count += 1 if is_green else -1
        else:
            break
    return count


def _calc_trend_strength(df: pd.DataFrame) -> float:
    """추세 강도 계산 (0~1). ADX 간이 버전."""
    if len(df) < 14:
        return 0.0
    closes = df["close"].iloc[-14:]
    highs = df["high"].iloc[-14:]
    lows = df["low"].iloc[-14:]
    # 방향성: 가격이 일관되게 한 방향으로 움직이는 정도
    changes = closes.diff().dropna()
    if len(changes) == 0:
        return 0.0
    pos_sum = changes[changes > 0].sum()
    neg_sum = abs(changes[changes < 0].sum())
    total = pos_sum + neg_sum
    if total == 0:
        return 0.0
    return abs(pos_sum - neg_sum) / total


class MarketAnalyzer:
    """시장 종합 분석기"""

    def __init__(self, client: UpbitClient = None):
        self.client = client or UpbitClient()
        self._vb = VolatilityBreakout(k=0.5)
        self._ma = MACrossover(short_period=5, long_period=20)
        self._rsi = RSIStrategy(period=14, oversold=30, overbought=70)

    def analyze_coin(self, ticker: str) -> CoinAnalysis:
        """개별 코인 종합 분석"""
        result = CoinAnalysis(ticker=ticker)

        # 1. 현재가
        result.current_price = self.client.get_current_price(ticker) or 0
        if result.current_price == 0:
            result.reasons.append("시세 조회 실패")
            return result

        # 2. OHLCV 데이터
        df_day = self.client.get_ohlcv(ticker, interval="day", count=60)
        if df_day is None or len(df_day) < 20:
            result.reasons.append("캔들 데이터 부족")
            return result

        # 3. 24시간 변동률
        if len(df_day) >= 2:
            prev_close = df_day["close"].iloc[-2]
            if prev_close > 0:
                result.price_change_24h_pct = round(
                    (result.current_price - prev_close) / prev_close * 100, 2
                )

        # 4. 거래량 변화율
        if len(df_day) >= 6:
            recent_vol = df_day["volume"].iloc[-1]
            avg_vol = df_day["volume"].iloc[-6:-1].mean()
            if avg_vol > 0:
                result.volume_change_pct = round((recent_vol - avg_vol) / avg_vol * 100, 1)

        # 5. RSI
        result.rsi_14 = round(_calc_rsi(df_day["close"], 14), 1)

        # 6. 이동평균선
        result.ma5 = round(float(df_day["close"].rolling(5).mean().iloc[-1]), 0)
        result.ma20 = round(float(df_day["close"].rolling(20).mean().iloc[-1]), 0)
        if len(df_day) >= 60:
            result.ma60 = round(float(df_day["close"].rolling(60).mean().iloc[-1]), 0)

        # 7. 볼린저 밴드
        result.bb_upper, _, result.bb_lower = _calc_bollinger(df_day)
        result.bb_upper = round(result.bb_upper, 0)
        result.bb_lower = round(result.bb_lower, 0)

        # 8. 지지/저항선 (최근 20일 저점/고점)
        result.support_price = round(float(df_day["low"].iloc[-20:].min()), 0)
        result.resistance_price = round(float(df_day["high"].iloc[-20:].max()), 0)

        # 8b. MACD
        if len(df_day) >= 26:
            result.macd, result.macd_signal, result.macd_histogram = _calc_macd(df_day["close"])

        # 8c. 연속 캔들 패턴
        result.consecutive_candles = _calc_consecutive_candles(df_day)

        # 8d. 추세 강도
        result.trend_strength = round(_calc_trend_strength(df_day), 3)

        # 8e. 가격-MA20 이격률
        if result.ma20 > 0:
            result.price_ma20_distance_pct = round(
                (result.current_price - result.ma20) / result.ma20 * 100, 2
            )

        # 9. 호가 매수/매도 비율
        ob = self.client.get_orderbook(ticker)
        if ob:
            bid = ob.get("total_bid_size", 0)
            ask = ob.get("total_ask_size", 0)
            if bid + ask > 0:
                result.bid_ask_ratio = round(bid / (bid + ask), 3)

        # 10. 전략 시그널
        vb_sig = self._vb.evaluate(ticker, df_day)
        ma_sig = self._ma.evaluate(ticker, df_day)
        rsi_sig = self._rsi.evaluate(ticker, df_day)
        result.volatility_signal = vb_sig.signal.value
        result.ma_signal = ma_sig.signal.value
        result.rsi_signal = rsi_sig.signal.value

        # ═══ 종합 스코어 계산 (-100 ~ +100) ═══
        score = 0
        reasons = []

        # RSI 기반 (가중치 25)
        if result.rsi_14 < 30:
            s = int((30 - result.rsi_14) / 30 * 25)
            score += s
            reasons.append(f"RSI 과매도({result.rsi_14}) +{s}")
        elif result.rsi_14 > 70:
            s = int((result.rsi_14 - 70) / 30 * 25)
            score -= s
            reasons.append(f"RSI 과매수({result.rsi_14}) -{s}")

        # 이동평균 배열 (가중치 25)
        if result.ma5 > result.ma20:
            if result.ma20 > result.ma60 > 0:
                score += 25
                reasons.append("정배열(MA5>MA20>MA60) +25")
            else:
                score += 15
                reasons.append(f"단기 상승(MA5>MA20) +15")
        elif result.ma5 < result.ma20:
            if result.ma60 > 0 and result.ma20 < result.ma60:
                score -= 25
                reasons.append("역배열(MA5<MA20<MA60) -25")
            else:
                score -= 15
                reasons.append(f"단기 하락(MA5<MA20) -15")

        # 변동성 돌파 (가중치 20)
        if vb_sig.signal == Signal.BUY:
            s = int(vb_sig.strength * 20)
            score += s
            reasons.append(f"변동성 돌파 +{s}")

        # 거래량 (가중치 15)
        if result.volume_change_pct > 100:
            if result.price_change_24h_pct > 0:
                score += 15
                reasons.append(f"거래량 급증+상승 +15")
            else:
                score -= 10
                reasons.append(f"거래량 급증+하락 -10")
        elif result.volume_change_pct > 50 and result.price_change_24h_pct > 0:
            score += 8
            reasons.append(f"거래량 증가+상승 +8")

        # 볼린저 밴드 (가중치 15)
        if result.current_price < result.bb_lower:
            score += 12
            reasons.append(f"볼린저 하단 이탈(과매도) +12")
        elif result.current_price > result.bb_upper:
            score -= 12
            reasons.append(f"볼린저 상단 돌파(과매수) -12")

        # 호가 비율 (가중치 5)
        if result.bid_ask_ratio > 0.6:
            score += 5
            reasons.append(f"매수세 우위({result.bid_ask_ratio:.1%}) +5")
        elif result.bid_ask_ratio < 0.4:
            score -= 5
            reasons.append(f"매도세 우위({result.bid_ask_ratio:.1%}) -5")

        # MACD (가중치 15)
        if result.macd_histogram > 0 and result.macd > result.macd_signal:
            s = min(15, int(abs(result.macd_histogram) / max(abs(result.macd_signal), 1) * 15))
            score += s
            reasons.append(f"MACD 상승({result.macd_histogram:+.0f}) +{s}")
        elif result.macd_histogram < 0 and result.macd < result.macd_signal:
            s = min(15, int(abs(result.macd_histogram) / max(abs(result.macd_signal), 1) * 15))
            score -= s
            reasons.append(f"MACD 하락({result.macd_histogram:+.0f}) -{s}")

        # 추세 강도 보너스 (가중치 10) - 강한 추세에서 기존 방향 강화
        if result.trend_strength > 0.5:
            trend_bonus = int(result.trend_strength * 10)
            if result.consecutive_candles >= 3:
                score += trend_bonus
                reasons.append(f"강한 상승추세(연속{result.consecutive_candles}양봉) +{trend_bonus}")
            elif result.consecutive_candles <= -3:
                score -= trend_bonus
                reasons.append(f"강한 하락추세(연속{abs(result.consecutive_candles)}음봉) -{trend_bonus}")

        # MA20 이격률 반전 신호 (가중치 8) - 과도한 이탈 시 평균회귀 기대
        if result.price_ma20_distance_pct < -8:
            score += 8
            reasons.append(f"MA20 대비 과이격 하방({result.price_ma20_distance_pct:+.1f}%) +8")
        elif result.price_ma20_distance_pct > 12:
            score -= 8
            reasons.append(f"MA20 대비 과이격 상방({result.price_ma20_distance_pct:+.1f}%) -8")

        # 스코어 클램핑
        result.score = max(-100, min(100, score))
        result.reasons = reasons

        # 최종 추천
        if result.score >= 40:
            result.recommendation = "STRONG_BUY"
        elif result.score >= 20:
            result.recommendation = "BUY"
        elif result.score <= -40:
            result.recommendation = "STRONG_SELL"
        elif result.score <= -20:
            result.recommendation = "SELL"
        else:
            result.recommendation = "HOLD"

        return result

    def analyze_watchlist(self, tickers: list) -> list[CoinAnalysis]:
        """관심 코인 전체 분석"""
        results = []
        for ticker in tickers:
            try:
                analysis = self.analyze_coin(ticker)
                results.append(analysis)
            except Exception as e:
                logger.error(f"분석 실패 ({ticker}): {e}")
                results.append(CoinAnalysis(ticker=ticker, reasons=[f"분석 오류: {str(e)}"]))
        # 스코어 순 정렬 (높은 것 = 매수 기회)
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def format_analysis(self, analysis: CoinAnalysis) -> str:
        """분석 결과를 자연어 리포트로 포맷"""
        coin = analysis.ticker.replace("KRW-", "")
        rec_emoji = {
            "STRONG_BUY": "🟢🟢", "BUY": "🟢", "HOLD": "⚪",
            "SELL": "🔴", "STRONG_SELL": "🔴🔴"
        }.get(analysis.recommendation, "⚪")
        rec_kr = {
            "STRONG_BUY": "강력 매수", "BUY": "매수", "HOLD": "관망",
            "SELL": "매도", "STRONG_SELL": "강력 매도"
        }.get(analysis.recommendation, "관망")

        macd_dir = "▲" if analysis.macd_histogram > 0 else "▼" if analysis.macd_histogram < 0 else "─"
        candle_str = f"{analysis.consecutive_candles:+d}봉" if analysis.consecutive_candles != 0 else "중립"
        lines = [
            f"{rec_emoji} {coin} | {rec_kr} (점수: {analysis.score:+d}/100)",
            f"  현재가: {analysis.current_price:,.0f}원 ({analysis.price_change_24h_pct:+.1f}%) MA20이격: {analysis.price_ma20_distance_pct:+.1f}%",
            f"  RSI: {analysis.rsi_14} | MA5: {analysis.ma5:,.0f} | MA20: {analysis.ma20:,.0f} | MA60: {analysis.ma60:,.0f}",
            f"  MACD: {analysis.macd:,.0f} / 시그널: {analysis.macd_signal:,.0f} / 히스토그램: {macd_dir}{abs(analysis.macd_histogram):,.0f}",
            f"  볼린저: {analysis.bb_lower:,.0f} ~ {analysis.bb_upper:,.0f}",
            f"  추세강도: {analysis.trend_strength:.1%} | 연속캔들: {candle_str} | 거래량: {analysis.volume_change_pct:+.0f}%",
            f"  지지/저항: {analysis.support_price:,.0f} ~ {analysis.resistance_price:,.0f} | 매수비율: {analysis.bid_ask_ratio:.1%}",
        ]
        if analysis.reasons:
            lines.append(f"  근거: {' / '.join(analysis.reasons)}")
        return "\n".join(lines)

    def format_watchlist_report(self, analyses: list[CoinAnalysis]) -> str:
        """관심 코인 전체 리포트"""
        lines = ["📊 시장 종합 분석 리포트", "=" * 50]
        buy_candidates = []
        sell_candidates = []

        for a in analyses:
            lines.append(self.format_analysis(a))
            lines.append("")
            if a.recommendation in ("BUY", "STRONG_BUY"):
                buy_candidates.append(a)
            elif a.recommendation in ("SELL", "STRONG_SELL"):
                sell_candidates.append(a)

        lines.append("=" * 50)
        if buy_candidates:
            coins = ", ".join(f"{a.ticker.replace('KRW-', '')}({a.score:+d})" for a in buy_candidates)
            lines.append(f"🟢 매수 후보: {coins}")
        if sell_candidates:
            coins = ", ".join(f"{a.ticker.replace('KRW-', '')}({a.score:+d})" for a in sell_candidates)
            lines.append(f"🔴 매도 후보: {coins}")
        if not buy_candidates and not sell_candidates:
            lines.append("⚪ 현재 뚜렷한 매매 시그널 없음 - 관망 추천")

        return "\n".join(lines)
