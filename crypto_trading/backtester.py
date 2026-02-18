"""
백테스팅 엔진 (#43)
- RSI 전략, MA 크로스오버 전략 백테스트
- 수수료/슬리피지 반영
- 수익률, MDD(Maximum Drawdown), Sharpe Ratio 계산
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from .strategies import _calc_rsi, Signal

logger = logging.getLogger("crypto.backtester")


@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_name: str = ""
    ticker: str = ""
    period: str = ""
    initial_capital: float = 0.0
    final_capital: float = 0.0
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate_pct: float = 0.0
    avg_profit_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0
    fee_total: float = 0.0
    slippage_total: float = 0.0
    equity_curve: list = field(default_factory=list)
    trades: list = field(default_factory=list)


class BacktestEngine:
    """백테스팅 엔진"""

    def __init__(
        self,
        initial_capital: float = 10_000_000,
        fee_rate: float = 0.0005,
        slippage_rate: float = 0.001,
    ):
        """
        백테스팅 엔진 초기화

        Args:
            initial_capital: 초기 자본금 (KRW)
            fee_rate: 거래 수수료율 (0.05% 기본, 업비트 기준)
            slippage_rate: 슬리피지율 (0.1% 기본)
        """
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate

    def run_rsi_strategy(
        self,
        df: pd.DataFrame,
        ticker: str = "KRW-BTC",
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> BacktestResult:
        """
        RSI 전략 백테스트 실행

        Args:
            df: OHLCV DataFrame (open, high, low, close, volume 컬럼 필요)
            ticker: 티커 심볼
            rsi_period: RSI 기간
            oversold: 과매도 기준 (매수 신호)
            overbought: 과매수 기준 (매도 신호)

        Returns:
            BacktestResult: 백테스트 결과
        """
        if df is None or len(df) < rsi_period + 2:
            logger.warning("RSI 백테스트: 데이터 부족")
            return BacktestResult(strategy_name="RSI", ticker=ticker)

        df = df.copy()
        rsi_series = _calc_rsi(df["close"], rsi_period)

        signals = []
        for i in range(len(df)):
            rsi_val = rsi_series.iloc[i]
            if pd.isna(rsi_val):
                signals.append(Signal.HOLD)
            elif rsi_val < oversold:
                signals.append(Signal.BUY)
            elif rsi_val > overbought:
                signals.append(Signal.SELL)
            else:
                signals.append(Signal.HOLD)

        return self._execute_backtest(
            df, signals, ticker,
            strategy_name=f"RSI({rsi_period}, {oversold}/{overbought})"
        )

    def run_ma_crossover_strategy(
        self,
        df: pd.DataFrame,
        ticker: str = "KRW-BTC",
        short_period: int = 5,
        long_period: int = 20,
    ) -> BacktestResult:
        """
        이동평균 크로스오버 전략 백테스트 실행

        Args:
            df: OHLCV DataFrame
            ticker: 티커 심볼
            short_period: 단기 이동평균 기간
            long_period: 장기 이동평균 기간

        Returns:
            BacktestResult: 백테스트 결과
        """
        if df is None or len(df) < long_period + 2:
            logger.warning("MA 크로스오버 백테스트: 데이터 부족")
            return BacktestResult(strategy_name="MA_Crossover", ticker=ticker)

        df = df.copy()
        ma_short = df["close"].rolling(window=short_period).mean()
        ma_long = df["close"].rolling(window=long_period).mean()

        signals = []
        for i in range(len(df)):
            if i < 1 or pd.isna(ma_short.iloc[i]) or pd.isna(ma_long.iloc[i]):
                signals.append(Signal.HOLD)
                continue

            prev_short = ma_short.iloc[i - 1]
            prev_long = ma_long.iloc[i - 1]
            curr_short = ma_short.iloc[i]
            curr_long = ma_long.iloc[i]

            if pd.isna(prev_short) or pd.isna(prev_long):
                signals.append(Signal.HOLD)
                continue

            # 골든크로스 (단기가 장기를 상향 돌파)
            if prev_short <= prev_long and curr_short > curr_long:
                signals.append(Signal.BUY)
            # 데드크로스 (단기가 장기를 하향 돌파)
            elif prev_short >= prev_long and curr_short < curr_long:
                signals.append(Signal.SELL)
            else:
                signals.append(Signal.HOLD)

        return self._execute_backtest(
            df, signals, ticker,
            strategy_name=f"MA_Crossover({short_period}/{long_period})"
        )

    def _execute_backtest(
        self,
        df: pd.DataFrame,
        signals: list,
        ticker: str,
        strategy_name: str,
    ) -> BacktestResult:
        """
        시그널 리스트를 기반으로 백테스트를 실행하고 결과를 계산

        Args:
            df: OHLCV DataFrame
            signals: Signal 리스트 (BUY/SELL/HOLD)
            ticker: 티커 심볼
            strategy_name: 전략 이름

        Returns:
            BacktestResult: 백테스트 결과
        """
        capital = self.initial_capital
        position = 0.0          # 보유 수량
        avg_buy_price = 0.0     # 평균 매수가
        equity_curve = []
        trades = []
        fee_total = 0.0
        slippage_total = 0.0

        for i in range(len(df)):
            close = float(df["close"].iloc[i])
            signal = signals[i]

            # 슬리피지 적용 가격
            if signal == Signal.BUY:
                exec_price = close * (1 + self.slippage_rate)
            elif signal == Signal.SELL:
                exec_price = close * (1 - self.slippage_rate)
            else:
                exec_price = close

            if signal == Signal.BUY and position == 0 and capital > 0:
                # 전액 매수
                fee = capital * self.fee_rate
                invest_amount = capital - fee
                slippage_cost = invest_amount * self.slippage_rate
                actual_invest = invest_amount - slippage_cost
                position = actual_invest / exec_price
                avg_buy_price = exec_price
                fee_total += fee
                slippage_total += slippage_cost
                capital = 0

                trades.append({
                    "index": i,
                    "side": "buy",
                    "price": exec_price,
                    "volume": position,
                    "fee": fee,
                    "slippage": slippage_cost,
                })

            elif signal == Signal.SELL and position > 0:
                # 전량 매도
                gross_value = position * exec_price
                fee = gross_value * self.fee_rate
                slippage_cost = gross_value * self.slippage_rate
                capital = gross_value - fee - slippage_cost
                fee_total += fee
                slippage_total += slippage_cost

                pnl_pct = ((exec_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0

                trades.append({
                    "index": i,
                    "side": "sell",
                    "price": exec_price,
                    "volume": position,
                    "fee": fee,
                    "slippage": slippage_cost,
                    "pnl_pct": round(pnl_pct, 2),
                })

                position = 0
                avg_buy_price = 0

            # 현재 자산 가치 (미실현 포함)
            equity = capital + (position * close)
            equity_curve.append(equity)

        # 마지막에 포지션이 남아있으면 현재가로 청산
        if position > 0:
            last_close = float(df["close"].iloc[-1])
            capital = position * last_close * (1 - self.fee_rate - self.slippage_rate)
            position = 0

        final_capital = capital if capital > 0 else equity_curve[-1] if equity_curve else self.initial_capital

        # 결과 통계 계산
        result = BacktestResult(
            strategy_name=strategy_name,
            ticker=ticker,
            initial_capital=self.initial_capital,
            final_capital=round(final_capital, 0),
            fee_total=round(fee_total, 0),
            slippage_total=round(slippage_total, 0),
            equity_curve=equity_curve,
            trades=trades,
        )

        # 수익률
        result.total_return_pct = round(
            (final_capital - self.initial_capital) / self.initial_capital * 100, 2
        )

        # 기간 정보
        if len(df) >= 2 and hasattr(df.index, 'dtype'):
            try:
                start_date = pd.Timestamp(df.index[0])
                end_date = pd.Timestamp(df.index[-1])
                result.period = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
                days = (end_date - start_date).days
                if days > 0:
                    result.annualized_return_pct = round(
                        ((final_capital / self.initial_capital) ** (365 / days) - 1) * 100, 2
                    )
            except Exception:
                result.period = f"{len(df)}캔들"

        # MDD (Maximum Drawdown)
        result.max_drawdown_pct = round(self._calc_mdd(equity_curve), 2)

        # Sharpe Ratio
        result.sharpe_ratio = round(self._calc_sharpe_ratio(equity_curve), 4)

        # 거래 통계
        sell_trades = [t for t in trades if t["side"] == "sell"]
        result.total_trades = len(sell_trades)
        wins = [t for t in sell_trades if t.get("pnl_pct", 0) > 0]
        losses = [t for t in sell_trades if t.get("pnl_pct", 0) <= 0]
        result.win_count = len(wins)
        result.loss_count = len(losses)
        result.win_rate_pct = round(
            (len(wins) / len(sell_trades) * 100) if sell_trades else 0, 1
        )
        result.avg_profit_pct = round(
            (sum(t["pnl_pct"] for t in wins) / len(wins)) if wins else 0, 2
        )
        result.avg_loss_pct = round(
            (sum(t["pnl_pct"] for t in losses) / len(losses)) if losses else 0, 2
        )

        # 프로핏 팩터
        gross_profit = sum(t["pnl_pct"] for t in wins) if wins else 0
        gross_loss = abs(sum(t["pnl_pct"] for t in losses)) if losses else 0
        result.profit_factor = round(
            (gross_profit / gross_loss) if gross_loss > 0 else float('inf'), 2
        )

        logger.info(
            f"백테스트 완료: {strategy_name} | {ticker} | "
            f"수익률: {result.total_return_pct:+.2f}% | MDD: {result.max_drawdown_pct:.2f}% | "
            f"Sharpe: {result.sharpe_ratio:.4f} | 승률: {result.win_rate_pct:.1f}%"
        )

        return result

    @staticmethod
    def _calc_mdd(equity_curve: list) -> float:
        """
        최대 낙폭(MDD) 계산

        Args:
            equity_curve: 자산 가치 시계열 리스트

        Returns:
            MDD 퍼센트 (양수값, 예: 15.3은 -15.3% 하락)
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100 if peak > 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    @staticmethod
    def _calc_sharpe_ratio(equity_curve: list, risk_free_rate: float = 0.035) -> float:
        """
        Sharpe Ratio 계산 (연간화)

        Args:
            equity_curve: 자산 가치 시계열 리스트
            risk_free_rate: 무위험 수익률 (연간, 기본 3.5%)

        Returns:
            Sharpe Ratio
        """
        if not equity_curve or len(equity_curve) < 3:
            return 0.0

        equity_arr = np.array(equity_curve, dtype=float)
        returns = np.diff(equity_arr) / equity_arr[:-1]

        if len(returns) == 0:
            return 0.0

        # 일간 무위험 수익률
        daily_rf = (1 + risk_free_rate) ** (1 / 365) - 1
        excess_returns = returns - daily_rf

        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns, ddof=1)

        if std_excess == 0 or np.isnan(std_excess):
            return 0.0

        # 연간화 (sqrt(365) 스케일링)
        sharpe = (mean_excess / std_excess) * np.sqrt(365)
        return float(sharpe)

    def format_result(self, result: BacktestResult) -> str:
        """
        백테스트 결과를 사람이 읽기 좋은 형식으로 포맷

        Args:
            result: BacktestResult 객체

        Returns:
            포맷된 문자열
        """
        lines = [
            f"=== 백테스트 결과: {result.strategy_name} ===",
            f"대상: {result.ticker} | 기간: {result.period}",
            f"",
            f"[수익 성과]",
            f"  초기 자본:     {result.initial_capital:>15,.0f} 원",
            f"  최종 자본:     {result.final_capital:>15,.0f} 원",
            f"  총 수익률:     {result.total_return_pct:>+14.2f} %",
            f"  연간 수익률:   {result.annualized_return_pct:>+14.2f} %",
            f"",
            f"[위험 지표]",
            f"  최대 낙폭(MDD):   {result.max_drawdown_pct:>10.2f} %",
            f"  Sharpe Ratio:     {result.sharpe_ratio:>10.4f}",
            f"  Profit Factor:    {result.profit_factor:>10.2f}",
            f"",
            f"[거래 통계]",
            f"  총 거래 횟수:  {result.total_trades:>10d} 회",
            f"  승리:          {result.win_count:>10d} 회",
            f"  패배:          {result.loss_count:>10d} 회",
            f"  승률:          {result.win_rate_pct:>10.1f} %",
            f"  평균 수익:     {result.avg_profit_pct:>+10.2f} %",
            f"  평균 손실:     {result.avg_loss_pct:>+10.2f} %",
            f"",
            f"[비용]",
            f"  총 수수료:     {result.fee_total:>15,.0f} 원",
            f"  총 슬리피지:   {result.slippage_total:>15,.0f} 원",
        ]
        return "\n".join(lines)
