"""
Smart Market Analyzer
- 다중 지표 종합 분석 (JARVIS AI가 판단할 수 있는 데이터 제공)
- 종합 스코어링 (-100 ~ +100)
- 자동 매매 의사결정 지원
"""
import logging
import time
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np
import requests

from . import config
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
    avg_loss = avg_loss.replace(0, 1e-10)
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
        # Fear & Greed cache (#31)
        self._fng_cache = None
        self._fng_cache_time = 0

    def analyze_coin(self, ticker: str, timeframes: list = None) -> CoinAnalysis:
        """개별 코인 종합 분석. timeframes: 분석할 타임프레임 목록 (예: ["day", "minute240"])"""
        if timeframes and len(timeframes) > 1:
            return self._analyze_multi_timeframe(ticker, timeframes)
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
        if isinstance(ob, list):
            ob = ob[0] if ob else {}
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

    # ─────────── #41 Multi Timeframe ───────────

    def _analyze_multi_timeframe(self, ticker: str, timeframes: list) -> CoinAnalysis:
        """여러 타임프레임을 분석하고 점수를 평균"""
        scores = []
        all_reasons = []
        base_result = None

        for tf in timeframes:
            try:
                result = CoinAnalysis(ticker=ticker)
                result.current_price = self.client.get_current_price(ticker) or 0
                if result.current_price == 0:
                    continue

                df = self.client.get_ohlcv(ticker, interval=tf, count=60)
                if df is None or len(df) < 20:
                    continue

                # RSI
                rsi_val = round(_calc_rsi(df["close"], 14), 1)
                # MA
                ma5 = float(df["close"].rolling(5).mean().iloc[-1])
                ma20 = float(df["close"].rolling(20).mean().iloc[-1])
                # MACD
                macd_val, macd_sig, macd_hist = (0, 0, 0)
                if len(df) >= 26:
                    macd_val, macd_sig, macd_hist = _calc_macd(df["close"])

                # Simple scoring per timeframe
                tf_score = 0
                if rsi_val < 30:
                    tf_score += 15
                elif rsi_val > 70:
                    tf_score -= 15
                if ma5 > ma20:
                    tf_score += 15
                elif ma5 < ma20:
                    tf_score -= 15
                if macd_hist > 0:
                    tf_score += 10
                elif macd_hist < 0:
                    tf_score -= 10

                scores.append(tf_score)
                all_reasons.append(f"[{tf}] RSI={rsi_val} MA5{'>' if ma5 > ma20 else '<'}MA20 MACD_H={macd_hist:+.0f} => {tf_score:+d}")

                if base_result is None:
                    base_result = self.analyze_coin(ticker)
            except Exception as e:
                logger.error(f"Multi-TF 분석 실패 ({ticker}/{tf}): {e}")

        if base_result is None:
            base_result = self.analyze_coin(ticker)

        if scores:
            avg_score = int(sum(scores) / len(scores))
            # Blend: 70% base analysis + 30% multi-TF average
            blended = int(base_result.score * 0.7 + avg_score * 0.3)
            base_result.score = max(-100, min(100, blended))
            base_result.reasons.append(f"멀티TF({','.join(timeframes)}) 보정: {avg_score:+d}")
            for r in all_reasons:
                base_result.reasons.append(r)

            # Re-classify recommendation
            if base_result.score >= 40:
                base_result.recommendation = "STRONG_BUY"
            elif base_result.score >= 20:
                base_result.recommendation = "BUY"
            elif base_result.score <= -40:
                base_result.recommendation = "STRONG_SELL"
            elif base_result.score <= -20:
                base_result.recommendation = "SELL"
            else:
                base_result.recommendation = "HOLD"

        return base_result

    # ─────────── #29 Kimchi Premium ───────────

    def get_kimchi_premium(self, ticker: str = "KRW-BTC") -> dict:
        """업비트 KRW 가격과 글로벌 USD 추정 가격 비교 (김치 프리미엄)"""
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
        coin = ticker.replace("KRW-", "")

        krw_price = self.client.get_current_price(ticker)
        if not krw_price:
            return {"error": f"KRW 시세 조회 실패: {ticker}"}

        usd_krw_rate = 1350  # 기본 환율
        usdt_ticker = f"USDT-{coin}"
        global_usd_price = None

        try:
            import pyupbit
            usdt_price = pyupbit.get_current_price(usdt_ticker)
            if usdt_price and usdt_price > 0:
                global_usd_price = usdt_price
        except Exception:
            pass

        if global_usd_price is None:
            # Fallback: Binance public API
            try:
                resp = requests.get(
                    f"https://api.binance.com/api/v3/ticker/price?symbol={coin}USDT",
                    timeout=5
                )
                if resp.status_code == 200:
                    global_usd_price = float(resp.json().get("price", 0))
            except Exception:
                pass

        if not global_usd_price or global_usd_price <= 0:
            return {"error": f"글로벌 USD 시세 조회 실패: {coin}", "krw_price": krw_price}

        estimated_global_krw = global_usd_price * usd_krw_rate
        premium_pct = ((krw_price - estimated_global_krw) / estimated_global_krw) * 100

        return {
            "ticker": ticker,
            "krw_price": krw_price,
            "global_usd_price": global_usd_price,
            "usd_krw_rate": usd_krw_rate,
            "estimated_global_krw": round(estimated_global_krw, 0),
            "premium_pct": round(premium_pct, 2),
        }

    # ─────────── #31 Fear & Greed Index ───────────

    def get_fear_greed_index(self) -> dict:
        """공포/탐욕 지수 조회 (1시간 캐시)"""
        now = time.time()
        if self._fng_cache and (now - self._fng_cache_time) < 3600:
            return self._fng_cache

        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", [{}])[0]
                result = {
                    "value": int(data.get("value", 0)),
                    "classification": data.get("value_classification", "Unknown"),
                    "timestamp": data.get("timestamp", ""),
                }
                self._fng_cache = result
                self._fng_cache_time = now
                return result
        except Exception as e:
            logger.error(f"Fear & Greed 조회 실패: {e}")

        return {"value": 0, "classification": "Unknown", "timestamp": "", "error": "조회 실패"}

    # ─────────── #32 Analysis Report File Saving ───────────

    def save_analysis_report(self, results: list, filepath=None) -> str:
        """분석 결과를 텍스트 파일로 저장"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = config.REPORTS_DIR / f"analysis_{timestamp}.txt"

        report = self.format_watchlist_report(results)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n")
            f.write(report)
            f.write("\n")

        logger.info(f"분석 리포트 저장: {filepath}")
        return str(filepath)

    # ─────────── #40 Market Summary ───────────

    def get_market_summary(self) -> dict:
        """전체 시장 요약 (상승/하락/보합, 상위 상승/하락 등)"""
        tickers = self.client.get_tickers(fiat="KRW")
        if not tickers:
            return {"error": "마켓 목록 조회 실패"}

        changes = []
        total_volume = 0.0

        for t in tickers:
            try:
                df = self.client.get_ohlcv(t, interval="day", count=2)
                if df is None or len(df) < 2:
                    continue
                prev = float(df["close"].iloc[-2])
                cur = float(df["close"].iloc[-1])
                vol = float(df["volume"].iloc[-1]) * cur  # KRW volume estimate
                chg = ((cur - prev) / prev * 100) if prev > 0 else 0
                changes.append({"ticker": t, "price": cur, "change_pct": round(chg, 2), "volume_krw": vol})
                total_volume += vol
            except Exception:
                continue

        rising = [c for c in changes if c["change_pct"] > 0.5]
        falling = [c for c in changes if c["change_pct"] < -0.5]
        flat = [c for c in changes if -0.5 <= c["change_pct"] <= 0.5]

        changes_sorted = sorted(changes, key=lambda x: x["change_pct"], reverse=True)
        avg_change = sum(c["change_pct"] for c in changes) / len(changes) if changes else 0

        return {
            "total_coins": len(changes),
            "rising_count": len(rising),
            "falling_count": len(falling),
            "flat_count": len(flat),
            "avg_change_pct": round(avg_change, 2),
            "top_gainers": changes_sorted[:5],
            "top_losers": changes_sorted[-5:][::-1],
            "total_volume_krw": round(total_volume, 0),
        }

    # ─────────── #46 이격도 분석 ───────────

    def calculate_disparity(self, ticker: str, period: int = 20) -> dict:
        """
        이격도 분석 (#46)
        현재가와 이동평균선 간의 괴리 정도를 측정하여 과매수/과매도 판단

        Args:
            ticker: 코인 티커 (예: "KRW-BTC")
            period: 이동평균 기간 (기본 20일)

        Returns:
            이격도 분석 결과 dict
        """
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"

        df = self.client.get_ohlcv(ticker, interval="day", count=max(period + 10, 60))
        if df is None or len(df) < period:
            return {"error": f"데이터 부족: {ticker}", "ticker": ticker}

        close = df["close"]
        ma = close.rolling(window=period).mean()

        current_price = float(close.iloc[-1])
        current_ma = float(ma.iloc[-1])

        if pd.isna(current_ma) or current_ma == 0:
            return {"error": "이동평균 계산 불가", "ticker": ticker}

        # 이격도 = (현재가 / 이동평균) * 100
        disparity = (current_price / current_ma) * 100
        disparity_pct = disparity - 100  # 100 기준 편차

        # 최근 N개 이격도 시계열
        disparity_series = (close / ma) * 100
        recent_disparities = [
            round(float(v), 2) for v in disparity_series.iloc[-10:]
            if not pd.isna(v)
        ]

        # 이격도 통계
        valid_disparities = disparity_series.dropna()
        disp_mean = float(valid_disparities.mean())
        disp_std = float(valid_disparities.std())

        # 판단
        if disparity < 95:
            signal = "과매도 (강력 매수 고려)"
            level = "oversold_strong"
        elif disparity < 98:
            signal = "과매도 (매수 고려)"
            level = "oversold"
        elif disparity > 105:
            signal = "과매수 (강력 매도 고려)"
            level = "overbought_strong"
        elif disparity > 102:
            signal = "과매수 (매도 고려)"
            level = "overbought"
        else:
            signal = "중립"
            level = "neutral"

        return {
            "ticker": ticker,
            "period": period,
            "current_price": current_price,
            "ma_price": round(current_ma, 0),
            "disparity": round(disparity, 2),
            "disparity_pct": round(disparity_pct, 2),
            "signal": signal,
            "level": level,
            "mean": round(disp_mean, 2),
            "std": round(disp_std, 2),
            "recent_history": recent_disparities,
        }

    # ─────────── #47 거래량 분석 강화 ───────────

    def analyze_volume_profile(self, ticker: str) -> dict:
        """
        거래량 프로파일 분석 (#47)
        가격대별 거래량 분포, 거래량 이동평균 비교, 거래량 이상 감지

        Args:
            ticker: 코인 티커 (예: "KRW-BTC")

        Returns:
            거래량 프로파일 분석 결과 dict
        """
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"

        df = self.client.get_ohlcv(ticker, interval="day", count=60)
        if df is None or len(df) < 20:
            return {"error": f"데이터 부족: {ticker}", "ticker": ticker}

        volume = df["volume"]
        close = df["close"]

        # 거래량 이동평균 (5일, 20일)
        vol_ma5 = float(volume.rolling(5).mean().iloc[-1])
        vol_ma20 = float(volume.rolling(20).mean().iloc[-1])
        current_vol = float(volume.iloc[-1])

        # 거래량 비율
        vol_ratio_5 = (current_vol / vol_ma5 * 100) if vol_ma5 > 0 else 0
        vol_ratio_20 = (current_vol / vol_ma20 * 100) if vol_ma20 > 0 else 0

        # 가격대별 거래량 분포 (10개 구간)
        price_min = float(close.min())
        price_max = float(close.max())
        num_bins = 10
        bin_size = (price_max - price_min) / num_bins if price_max > price_min else 1

        price_volume_profile = []
        for i in range(num_bins):
            bin_low = price_min + (i * bin_size)
            bin_high = bin_low + bin_size
            mask = (close >= bin_low) & (close < bin_high)
            if i == num_bins - 1:
                mask = (close >= bin_low) & (close <= bin_high)
            bin_vol = float(volume[mask].sum())
            price_volume_profile.append({
                "price_range": f"{bin_low:,.0f} ~ {bin_high:,.0f}",
                "volume": round(bin_vol, 4),
            })

        # POC (Point of Control): 거래량이 가장 많은 가격대
        poc_idx = max(range(len(price_volume_profile)),
                      key=lambda i: price_volume_profile[i]["volume"])
        poc = price_volume_profile[poc_idx]

        # 거래량 추세 (최근 5일 기울기)
        recent_vols = volume.iloc[-5:].values
        if len(recent_vols) >= 2:
            vol_slope = float(np.polyfit(range(len(recent_vols)), recent_vols, 1)[0])
            vol_trend = "증가" if vol_slope > 0 else "감소"
        else:
            vol_slope = 0
            vol_trend = "판단불가"

        # 이상 거래량 감지 (20일 MA 대비 2배 이상)
        is_anomaly = current_vol > vol_ma20 * 2

        # OBV (On-Balance Volume) 추세
        obv = 0.0
        obv_series = []
        for i in range(1, len(df)):
            if float(close.iloc[i]) > float(close.iloc[i - 1]):
                obv += float(volume.iloc[i])
            elif float(close.iloc[i]) < float(close.iloc[i - 1]):
                obv -= float(volume.iloc[i])
            obv_series.append(obv)

        obv_trend = "상승" if len(obv_series) >= 2 and obv_series[-1] > obv_series[-5] else "하락"

        return {
            "ticker": ticker,
            "current_volume": round(current_vol, 4),
            "volume_ma5": round(vol_ma5, 4),
            "volume_ma20": round(vol_ma20, 4),
            "volume_ratio_vs_ma5_pct": round(vol_ratio_5, 1),
            "volume_ratio_vs_ma20_pct": round(vol_ratio_20, 1),
            "volume_trend": vol_trend,
            "is_anomaly": is_anomaly,
            "obv_trend": obv_trend,
            "poc": poc,
            "price_volume_profile": price_volume_profile,
        }

    # ─────────── #48 캔들 패턴 인식 ───────────

    def detect_candle_patterns(self, ticker: str) -> dict:
        """
        캔들 패턴 인식 (#48)
        도지(Doji), 해머(Hammer), 잉승(Engulfing) 패턴 감지

        Args:
            ticker: 코인 티커 (예: "KRW-BTC")

        Returns:
            감지된 캔들 패턴 dict
        """
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"

        df = self.client.get_ohlcv(ticker, interval="day", count=10)
        if df is None or len(df) < 3:
            return {"error": f"데이터 부족: {ticker}", "ticker": ticker}

        patterns = []

        # 최근 캔들 데이터
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        c_open = float(curr["open"])
        c_close = float(curr["close"])
        c_high = float(curr["high"])
        c_low = float(curr["low"])
        c_body = abs(c_close - c_open)
        c_range = c_high - c_low

        p_open = float(prev["open"])
        p_close = float(prev["close"])
        p_body = abs(p_close - p_open)

        # 도지 (Doji): 몸통이 전체 범위의 10% 이하
        if c_range > 0 and (c_body / c_range) < 0.1:
            patterns.append({
                "pattern": "도지 (Doji)",
                "description": "시가와 종가가 거의 같음 - 추세 전환 가능성",
                "signal": "neutral",
                "reliability": "medium",
            })

        # 해머 (Hammer): 아래 그림자가 몸통의 2배 이상, 위 그림자 작음
        lower_shadow = min(c_open, c_close) - c_low
        upper_shadow = c_high - max(c_open, c_close)
        if c_body > 0 and lower_shadow >= c_body * 2 and upper_shadow <= c_body * 0.5:
            # 하락 추세 후 해머 = 강세 반전 신호
            is_downtrend = float(df["close"].iloc[-3]) > float(df["close"].iloc[-2])
            if is_downtrend:
                patterns.append({
                    "pattern": "해머 (Hammer)",
                    "description": "하락 추세 후 긴 아래꼬리 - 강세 반전 신호",
                    "signal": "bullish",
                    "reliability": "high",
                })
            else:
                patterns.append({
                    "pattern": "교수형 (Hanging Man)",
                    "description": "상승 추세 후 긴 아래꼬리 - 약세 반전 가능",
                    "signal": "bearish",
                    "reliability": "medium",
                })

        # 역해머 (Inverted Hammer): 위 그림자가 몸통의 2배 이상, 아래 그림자 작음
        if c_body > 0 and upper_shadow >= c_body * 2 and lower_shadow <= c_body * 0.5:
            is_downtrend = float(df["close"].iloc[-3]) > float(df["close"].iloc[-2])
            if is_downtrend:
                patterns.append({
                    "pattern": "역해머 (Inverted Hammer)",
                    "description": "하락 추세 후 긴 위꼬리 - 강세 반전 가능",
                    "signal": "bullish",
                    "reliability": "medium",
                })

        # 강세 잉승 (Bullish Engulfing): 이전 음봉을 현재 양봉이 감싸는 패턴
        if (p_close < p_open and  # 이전: 음봉
                c_close > c_open and  # 현재: 양봉
                c_open <= p_close and  # 현재 시가 <= 이전 종가
                c_close >= p_open):    # 현재 종가 >= 이전 시가
            patterns.append({
                "pattern": "강세 잉승 (Bullish Engulfing)",
                "description": "이전 음봉을 완전히 감싸는 양봉 - 강한 상승 반전 신호",
                "signal": "bullish",
                "reliability": "high",
            })

        # 약세 잉승 (Bearish Engulfing): 이전 양봉을 현재 음봉이 감싸는 패턴
        if (p_close > p_open and  # 이전: 양봉
                c_close < c_open and  # 현재: 음봉
                c_open >= p_close and  # 현재 시가 >= 이전 종가
                c_close <= p_open):    # 현재 종가 <= 이전 시가
            patterns.append({
                "pattern": "약세 잉승 (Bearish Engulfing)",
                "description": "이전 양봉을 완전히 감싸는 음봉 - 강한 하락 반전 신호",
                "signal": "bearish",
                "reliability": "high",
            })

        # 모닝스타 (Morning Star): 3개 캔들 패턴
        if len(df) >= 3:
            pp = df.iloc[-3]  # 2일 전
            pp_open = float(pp["open"])
            pp_close = float(pp["close"])
            pp_body = abs(pp_close - pp_open)

            # 2일전: 큰 음봉, 어제: 작은 몸통(갭다운), 오늘: 큰 양봉
            if (pp_close < pp_open and pp_body > 0 and  # 큰 음봉
                    p_body < pp_body * 0.3 and              # 작은 몸통
                    c_close > c_open and c_body > 0 and     # 양봉
                    c_close > (pp_open + pp_close) / 2):    # 2일전 중간 이상 회복
                patterns.append({
                    "pattern": "모닝스타 (Morning Star)",
                    "description": "강한 하락 후 소형 캔들, 큰 양봉 반등 - 강세 반전",
                    "signal": "bullish",
                    "reliability": "high",
                })

        # 종합 판단
        bullish_count = sum(1 for p in patterns if p["signal"] == "bullish")
        bearish_count = sum(1 for p in patterns if p["signal"] == "bearish")

        if bullish_count > bearish_count:
            overall = "bullish"
        elif bearish_count > bullish_count:
            overall = "bearish"
        else:
            overall = "neutral"

        return {
            "ticker": ticker,
            "patterns": patterns,
            "pattern_count": len(patterns),
            "overall_signal": overall,
            "current_candle": {
                "open": c_open,
                "close": c_close,
                "high": c_high,
                "low": c_low,
                "body_ratio": round(c_body / c_range * 100, 1) if c_range > 0 else 0,
                "type": "양봉" if c_close > c_open else "음봉" if c_close < c_open else "도지",
            },
        }

    # ─────────── #49 BTC-알트코인 상관관계 ───────────

    def calculate_correlation(self, ticker1: str, ticker2: str, period: int = 30) -> dict:
        """
        두 코인 간의 가격 상관관계 분석 (#49)

        Args:
            ticker1: 첫 번째 코인 티커 (예: "KRW-BTC")
            ticker2: 두 번째 코인 티커 (예: "KRW-ETH")
            period: 분석 기간 (일)

        Returns:
            상관관계 분석 결과 dict
        """
        ticker1 = ticker1.upper()
        ticker2 = ticker2.upper()
        if not ticker1.startswith("KRW-"):
            ticker1 = f"KRW-{ticker1}"
        if not ticker2.startswith("KRW-"):
            ticker2 = f"KRW-{ticker2}"

        df1 = self.client.get_ohlcv(ticker1, interval="day", count=period + 5)
        df2 = self.client.get_ohlcv(ticker2, interval="day", count=period + 5)

        if df1 is None or df2 is None or len(df1) < period or len(df2) < period:
            return {"error": "데이터 부족", "ticker1": ticker1, "ticker2": ticker2}

        # 최근 period일 종가 수익률
        returns1 = df1["close"].pct_change().dropna().iloc[-period:]
        returns2 = df2["close"].pct_change().dropna().iloc[-period:]

        # 길이 맞추기
        min_len = min(len(returns1), len(returns2))
        returns1 = returns1.iloc[-min_len:]
        returns2 = returns2.iloc[-min_len:]

        if min_len < 5:
            return {"error": "충분한 수익률 데이터 없음", "ticker1": ticker1, "ticker2": ticker2}

        # 피어슨 상관계수
        correlation = float(returns1.corr(returns2))

        # 롤링 상관계수 (10일 윈도우)
        if min_len >= 15:
            combined = pd.DataFrame({"r1": returns1.values, "r2": returns2.values})
            rolling_corr = combined["r1"].rolling(10).corr(combined["r2"])
            recent_rolling = [
                round(float(v), 4) for v in rolling_corr.dropna().iloc[-5:]
            ]
        else:
            recent_rolling = []

        # 베타 계산 (ticker2 = ticker1 * beta + alpha)
        cov = float(returns1.cov(returns2))
        var1 = float(returns1.var())
        beta = cov / var1 if var1 > 0 else 0

        # 해석
        if correlation > 0.8:
            interpretation = "매우 강한 양의 상관관계 (거의 동조)"
        elif correlation > 0.5:
            interpretation = "강한 양의 상관관계"
        elif correlation > 0.2:
            interpretation = "약한 양의 상관관계"
        elif correlation > -0.2:
            interpretation = "상관관계 거의 없음 (독립적)"
        elif correlation > -0.5:
            interpretation = "약한 음의 상관관계"
        elif correlation > -0.8:
            interpretation = "강한 음의 상관관계"
        else:
            interpretation = "매우 강한 음의 상관관계 (역행)"

        return {
            "ticker1": ticker1,
            "ticker2": ticker2,
            "period": period,
            "correlation": round(correlation, 4),
            "beta": round(beta, 4),
            "interpretation": interpretation,
            "rolling_correlation": recent_rolling,
            "returns1_mean_pct": round(float(returns1.mean()) * 100, 4),
            "returns2_mean_pct": round(float(returns2.mean()) * 100, 4),
            "returns1_std_pct": round(float(returns1.std()) * 100, 4),
            "returns2_std_pct": round(float(returns2.std()) * 100, 4),
        }

    # ─────────── #42 Spread Analysis ───────────

    def analyze_spread(self, ticker: str) -> dict:
        """호가 스프레드 분석"""
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"

        ob = self.client.get_orderbook(ticker)
        if not ob:
            return {"error": f"호가 조회 실패: {ticker}"}

        # Handle list response
        if isinstance(ob, list):
            ob = ob[0] if ob else {}

        units = ob.get("orderbook_units", [])
        if not units:
            return {"error": f"호가 데이터 없음: {ticker}"}

        best_ask = float(units[0].get("ask_price", 0))
        best_bid = float(units[0].get("bid_price", 0))

        if best_ask <= 0 or best_bid <= 0:
            return {"error": "유효하지 않은 호가"}

        spread = best_ask - best_bid
        spread_pct = (spread / best_bid) * 100

        # Depth calculation
        bid_depth_krw = sum(float(u.get("bid_price", 0)) * float(u.get("bid_size", 0)) for u in units)
        ask_depth_krw = sum(float(u.get("ask_price", 0)) * float(u.get("ask_size", 0)) for u in units)

        # Liquidity score (0~100): low spread + high depth = high score
        spread_score = max(0, 100 - spread_pct * 50)  # 2% spread = 0
        depth_score = min(100, (bid_depth_krw + ask_depth_krw) / 1_000_000_000 * 100)  # 10B KRW = 100
        liquidity_score = int(spread_score * 0.6 + depth_score * 0.4)

        result = {
            "ticker": ticker,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread_krw": round(spread, 0),
            "spread_pct": round(spread_pct, 4),
            "bid_depth_krw": round(bid_depth_krw, 0),
            "ask_depth_krw": round(ask_depth_krw, 0),
            "liquidity_score": liquidity_score,
        }

        if spread_pct > 1.0:
            result["warning"] = f"스프레드 {spread_pct:.2f}% - 유동성 낮음 주의"
            logger.warning(f"높은 스프레드 경고: {ticker} {spread_pct:.2f}%")

        return result
