"""
Portfolio Tracker
- 보유 자산 스냅샷 기록
- 자산 추이 그래프 생성 (matplotlib)
- 거래 내역 로깅
"""
import csv
import json
import logging
import os
import tempfile
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np

from . import config

logger = logging.getLogger("crypto.portfolio_tracker")


class PortfolioTracker:
    """포트폴리오 추적기"""

    def __init__(self):
        self.history_file = config.PORTFOLIO_HISTORY_FILE
        self.trade_log_file = config.TRADE_LOG_FILE
        self.graph_dir = config.GRAPH_OUTPUT_DIR
        self._history = self._load_json(self.history_file, [])
        self._trades = self._load_json(self.trade_log_file, [])
        self._lock = threading.Lock()  # 파일 I/O thread-safe 보호

    @staticmethod
    def _load_json(path: Path, default):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"JSON 로드 실패 ({path}): {e}. 데이터 손상 가능. 빈 기본값 사용.")
        return default

    def _atomic_write(self, filepath: Path, data):
        """원자적 파일 쓰기 (크래시 시 데이터 손실 방지)"""
        tmp_fd, tmp_path = tempfile.mkstemp(dir=filepath.parent, suffix='.tmp')
        try:
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, filepath)  # 원자적 교체
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _save_history(self):
        with self._lock:
            self._atomic_write(self.history_file, self._history)

    def _save_trades(self):
        with self._lock:
            self._atomic_write(self.trade_log_file, self._trades)

    # ─────────── 스냅샷 기록 ───────────

    def record_snapshot(self, balances: list, prices: dict):
        """현재 보유 자산 스냅샷 저장"""
        total_krw = 0.0
        holdings = {}

        for b in balances:
            currency = b.get("currency", "")
            balance = float(b.get("balance", 0))
            locked = float(b.get("locked", 0))
            amount = balance + locked
            if amount <= 0:
                continue

            if currency == "KRW":
                total_krw += amount
                holdings["KRW"] = {"amount": amount, "value_krw": amount}
            else:
                ticker = f"KRW-{currency}"
                price = prices.get(ticker, 0)
                value = amount * price
                total_krw += value
                holdings[currency] = {
                    "amount": round(amount, 8),
                    "price": price,
                    "value_krw": round(value, 0),
                }

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "total_value_krw": round(total_krw, 0),
            "holdings": holdings,
        }
        self._history.append(snapshot)
        if len(self._history) > 10000:
            self._history = self._history[-10000:]
        self._save_history()
        logger.info(f"포트폴리오 스냅샷: 총 {total_krw:,.0f}원 ({len(holdings)}개 자산)")
        return snapshot

    def log_trade(self, side: str, ticker: str, amount: float,
                  price: float = 0, reason: str = "", order_result: dict = None):
        """거래 내역 기록"""
        trade = {
            "timestamp": datetime.now().isoformat(),
            "side": side,
            "ticker": ticker,
            "amount": amount,
            "price": price,
            "reason": reason,
            "dry_run": config.DRY_RUN,
            "order_uuid": (order_result or {}).get("uuid", ""),
        }
        self._trades.append(trade)
        self._save_trades()
        logger.info(f"거래 기록: {side} {ticker} / {amount:,.0f} / {reason}")

    # ─────────── 그래프 생성 ───────────

    def generate_portfolio_graph(self, days: int = 30) -> Optional[str]:
        """
        보유 자산 추이 그래프 생성
        Returns: 생성된 이미지 파일 경로 (또는 None)
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
        except ImportError:
            logger.error("matplotlib가 설치되지 않았습니다: pip install matplotlib")
            return None

        if len(self._history) < 2:
            logger.warning("그래프 생성에 최소 2개의 스냅샷이 필요합니다.")
            return None

        # 최근 N일치 필터
        timestamps = []
        values = []
        for snap in self._history:
            try:
                ts = datetime.fromisoformat(snap["timestamp"])
                timestamps.append(ts)
                values.append(snap["total_value_krw"])
            except Exception:
                continue

        if len(timestamps) < 2:
            return None

        # 최근 days일만
        cutoff = datetime.now().replace(hour=0, minute=0, second=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)
        filtered = [(t, v) for t, v in zip(timestamps, values) if t >= cutoff]
        if len(filtered) < 2:
            filtered = list(zip(timestamps[-50:], values[-50:]))

        ts_list, val_list = zip(*filtered)

        # 그래프 그리기
        plt.rcParams["font.family"] = "Malgun Gothic"
        plt.rcParams["axes.unicode_minus"] = False

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(ts_list, val_list, linewidth=2, color="#2196F3", marker="o", markersize=3)
        ax.fill_between(ts_list, val_list, alpha=0.1, color="#2196F3")

        # 시작/끝 값 표시
        start_val = val_list[0]
        end_val = val_list[-1]
        change_pct = ((end_val - start_val) / start_val * 100) if start_val > 0 else 0
        color = "#4CAF50" if change_pct >= 0 else "#F44336"
        sign = "+" if change_pct >= 0 else ""

        ax.set_title(
            f"보유 자산 추이  |  현재: {end_val:,.0f}원  ({sign}{change_pct:.1f}%)",
            fontsize=14, fontweight="bold", color=color
        )
        ax.set_ylabel("총 자산 (KRW)", fontsize=11)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        plt.tight_layout()

        # 저장
        filename = f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.graph_dir / filename
        fig.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close(fig)

        logger.info(f"포트폴리오 그래프 저장: {filepath}")
        return str(filepath)

    def generate_holdings_pie_chart(self) -> Optional[str]:
        """보유 자산 비중 파이차트 생성"""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        if not self._history:
            return None

        latest = self._history[-1]
        holdings = latest.get("holdings", {})
        if len(holdings) < 1:
            return None

        labels = []
        sizes = []
        for currency, info in holdings.items():
            value = info.get("value_krw", 0)
            if value > 0:
                labels.append(currency)
                sizes.append(value)

        if not sizes:
            return None

        plt.rcParams["font.family"] = "Malgun Gothic"
        plt.rcParams["axes.unicode_minus"] = False

        fig, ax = plt.subplots(figsize=(8, 8))
        colors = ["#2196F3", "#4CAF50", "#FF9800", "#F44336", "#9C27B0",
                   "#00BCD4", "#FFEB3B", "#795548", "#607D8B", "#E91E63"]

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct="%1.1f%%",
            colors=colors[:len(sizes)], startangle=90,
            textprops={"fontsize": 11}
        )
        ax.set_title(
            f"보유 자산 비중  |  총: {sum(sizes):,.0f}원",
            fontsize=14, fontweight="bold"
        )
        plt.tight_layout()

        filename = f"holdings_pie_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.graph_dir / filename
        fig.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(filepath)

    # ─────────── 요약 ───────────

    def get_summary(self) -> dict:
        """최신 포트폴리오 요약"""
        if not self._history:
            return {"status": "no_data", "message": "아직 기록된 스냅샷이 없습니다."}

        latest = self._history[-1]
        total = latest["total_value_krw"]

        # 수익률 계산 (첫 스냅샷 대비)
        first = self._history[0]
        initial = first["total_value_krw"]
        pnl = total - initial
        pnl_pct = (pnl / initial * 100) if initial > 0 else 0

        return {
            "timestamp": latest["timestamp"],
            "total_value_krw": total,
            "initial_value_krw": initial,
            "pnl_krw": pnl,
            "pnl_pct": round(pnl_pct, 2),
            "holdings_count": len(latest.get("holdings", {})),
            "snapshots_count": len(self._history),
            "trades_count": len(self._trades),
        }

    def get_recent_trades(self, count: int = 10) -> list:
        """최근 거래 내역"""
        return self._trades[-count:]

    # ─────────── #33 Trade Statistics ───────────

    def get_trade_statistics(self, period: str = "all") -> dict:
        """거래 통계 계산. period: 'day', 'week', 'month', 'all'"""
        now = datetime.now()
        if period == "day":
            cutoff = now - timedelta(days=1)
        elif period == "week":
            cutoff = now - timedelta(weeks=1)
        elif period == "month":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None

        trades = self._trades
        if cutoff:
            trades = [t for t in trades if datetime.fromisoformat(t["timestamp"]) >= cutoff]

        if not trades:
            return {"period": period, "total_trades": 0, "message": "해당 기간 거래 없음"}

        buys = [t for t in trades if t.get("side") == "buy"]
        sells = [t for t in trades if t.get("side") == "sell"]

        # Win rate: estimate from sell trades with price info
        profitable_sells = 0
        total_sells_with_info = 0
        sell_profits = []
        for s in sells:
            sell_price = s.get("price", 0)
            sell_amount = s.get("amount", 0)
            if sell_price > 0 and sell_amount > 0:
                total_sells_with_info += 1
                # Check if reason indicates profit or loss
                reason = s.get("reason", "")
                if "익절" in reason or "take_profit" in reason:
                    profitable_sells += 1
                    sell_profits.append(1)
                elif "손절" in reason or "stop_loss" in reason:
                    sell_profits.append(0)
                else:
                    # Estimate: positive if we assume average scenario
                    sell_profits.append(0.5)

        win_rate = (profitable_sells / total_sells_with_info * 100) if total_sells_with_info > 0 else 0

        # Consecutive wins/losses
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        for p in sell_profits:
            if p >= 0.5:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        # PnL by period
        buy_total = sum(t.get("amount", 0) for t in buys)
        sell_total = sum(t.get("amount", 0) for t in sells)
        pnl = sell_total - buy_total
        avg_profit_pct = (pnl / buy_total * 100) if buy_total > 0 else 0

        return {
            "period": period,
            "total_trades": len(trades),
            "buy_count": len(buys),
            "sell_count": len(sells),
            "win_rate": round(win_rate, 1),
            "avg_profit_pct": round(avg_profit_pct, 2),
            "max_consecutive_wins": max_wins,
            "max_consecutive_losses": max_losses,
            "total_buy_krw": round(buy_total, 0),
            "total_sell_krw": round(sell_total, 0),
            "pnl_krw": round(pnl, 0),
        }

    # ─────────── #38 Portfolio Weight Warning ───────────

    def check_weight_warnings(self, max_weight_pct: float = 30) -> list:
        """포트폴리오 비중 경고 (특정 코인 비중 초과 확인)"""
        if not self._history:
            return []

        latest = self._history[-1]
        total = latest.get("total_value_krw", 0)
        if total <= 0:
            return []

        warnings = []
        for currency, info in latest.get("holdings", {}).items():
            if currency == "KRW":
                continue
            value = info.get("value_krw", 0)
            weight_pct = (value / total) * 100
            if weight_pct > max_weight_pct:
                warning = {
                    "currency": currency,
                    "value_krw": value,
                    "weight_pct": round(weight_pct, 1),
                    "max_weight_pct": max_weight_pct,
                    "message": f"{currency} 비중 {weight_pct:.1f}% > 기준 {max_weight_pct}%"
                }
                warnings.append(warning)
                logger.warning(f"포트폴리오 비중 경고: {warning['message']}")

        return warnings

    # ─────────── #39 Trade History CSV Export ───────────

    def export_trades_csv(self, filepath=None) -> str:
        """거래 내역을 CSV로 내보내기"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = config.DATA_DIR / f"trades_{timestamp}.csv"

        columns = ["timestamp", "side", "ticker", "amount", "price", "reason", "dry_run"]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for trade in self._trades:
                writer.writerow(trade)

        logger.info(f"거래 내역 CSV 내보내기: {filepath} ({len(self._trades)}건)")
        return str(filepath)

    # ─────────── #52 성과 리포트 생성 ───────────

    def generate_performance_report(self, period: str = "all") -> dict:
        """
        종합 성과 리포트 생성 (#52)

        포트폴리오 히스토리와 거래 내역을 기반으로
        수익률, MDD, Sharpe Ratio, 종목별 성과 등을 종합 분석

        Args:
            period: 분석 기간 ('day', 'week', 'month', 'all')

        Returns:
            종합 성과 리포트 dict
        """
        now = datetime.now()
        if period == "day":
            cutoff = now - timedelta(days=1)
        elif period == "week":
            cutoff = now - timedelta(weeks=1)
        elif period == "month":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None

        # 스냅샷 필터링
        snapshots = self._history
        if cutoff:
            snapshots = [
                s for s in snapshots
                if datetime.fromisoformat(s["timestamp"]) >= cutoff
            ]

        # 거래 내역 필터링
        trades = self._trades
        if cutoff:
            trades = [
                t for t in trades
                if datetime.fromisoformat(t["timestamp"]) >= cutoff
            ]

        report = {
            "period": period,
            "generated_at": now.isoformat(),
            "snapshot_count": len(snapshots),
            "trade_count": len(trades),
        }

        # 스냅샷 기반 수익률 분석
        if len(snapshots) >= 2:
            values = [s["total_value_krw"] for s in snapshots]
            initial_value = values[0]
            final_value = values[-1]
            pnl = final_value - initial_value
            pnl_pct = (pnl / initial_value * 100) if initial_value > 0 else 0

            report["portfolio"] = {
                "initial_value": round(initial_value, 0),
                "final_value": round(final_value, 0),
                "pnl_krw": round(pnl, 0),
                "pnl_pct": round(pnl_pct, 2),
                "peak_value": round(max(values), 0),
                "trough_value": round(min(values), 0),
            }

            # MDD 계산
            peak = values[0]
            max_dd = 0.0
            max_dd_start = 0
            max_dd_end = 0
            current_dd_start = 0

            for i, val in enumerate(values):
                if val > peak:
                    peak = val
                    current_dd_start = i
                dd = (peak - val) / peak * 100 if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
                    max_dd_start = current_dd_start
                    max_dd_end = i

            report["risk"] = {
                "max_drawdown_pct": round(max_dd, 2),
            }

            # 일간 수익률 기반 Sharpe Ratio
            if len(values) >= 3:
                returns = np.diff(values) / np.array(values[:-1])
                daily_rf = (1.035) ** (1 / 365) - 1  # 연간 3.5% 무위험수익률
                excess_returns = returns - daily_rf
                mean_excess = float(np.mean(excess_returns))
                std_excess = float(np.std(excess_returns, ddof=1))

                if std_excess > 0:
                    sharpe = (mean_excess / std_excess) * np.sqrt(365)
                    report["risk"]["sharpe_ratio"] = round(float(sharpe), 4)
                else:
                    report["risk"]["sharpe_ratio"] = 0.0

                # 변동성 (연간화)
                daily_vol = float(np.std(returns, ddof=1))
                annual_vol = daily_vol * np.sqrt(365)
                report["risk"]["daily_volatility_pct"] = round(daily_vol * 100, 4)
                report["risk"]["annual_volatility_pct"] = round(float(annual_vol) * 100, 2)
            else:
                report["risk"]["sharpe_ratio"] = 0.0
                report["risk"]["daily_volatility_pct"] = 0.0
                report["risk"]["annual_volatility_pct"] = 0.0
        else:
            report["portfolio"] = {"message": "스냅샷 부족 (최소 2개 필요)"}
            report["risk"] = {"message": "스냅샷 부족"}

        # 거래 분석
        if trades:
            buys = [t for t in trades if t.get("side") == "buy"]
            sells = [t for t in trades if t.get("side") == "sell"]

            # 종목별 거래 분석
            by_ticker = defaultdict(lambda: {"buy_count": 0, "sell_count": 0,
                                              "buy_total": 0, "sell_total": 0})
            for t in trades:
                ticker = t.get("ticker", "unknown")
                side = t.get("side", "")
                amount = t.get("amount", 0)
                if side == "buy":
                    by_ticker[ticker]["buy_count"] += 1
                    by_ticker[ticker]["buy_total"] += amount
                elif side == "sell":
                    by_ticker[ticker]["sell_count"] += 1
                    by_ticker[ticker]["sell_total"] += amount

            ticker_stats = []
            for ticker, stats in by_ticker.items():
                net_pnl = stats["sell_total"] - stats["buy_total"]
                ticker_stats.append({
                    "ticker": ticker,
                    "buy_count": stats["buy_count"],
                    "sell_count": stats["sell_count"],
                    "buy_total_krw": round(stats["buy_total"], 0),
                    "sell_total_krw": round(stats["sell_total"], 0),
                    "net_pnl_krw": round(net_pnl, 0),
                })
            ticker_stats.sort(key=lambda x: x["net_pnl_krw"], reverse=True)

            # 승률 분석
            profitable_sells = 0
            total_sells_analyzed = 0
            for s in sells:
                reason = s.get("reason", "")
                if "익절" in reason or "take_profit" in reason:
                    profitable_sells += 1
                    total_sells_analyzed += 1
                elif "손절" in reason or "stop_loss" in reason:
                    total_sells_analyzed += 1

            win_rate = (profitable_sells / total_sells_analyzed * 100) if total_sells_analyzed > 0 else 0

            # 시간대별 거래 분포
            hourly_dist = defaultdict(int)
            for t in trades:
                try:
                    ts = datetime.fromisoformat(t["timestamp"])
                    hourly_dist[ts.hour] += 1
                except Exception:
                    pass

            # 가장 활발한 시간대
            most_active_hour = max(hourly_dist, key=hourly_dist.get) if hourly_dist else 0

            buy_total = sum(t.get("amount", 0) for t in buys)
            sell_total = sum(t.get("amount", 0) for t in sells)

            report["trades"] = {
                "total": len(trades),
                "buy_count": len(buys),
                "sell_count": len(sells),
                "buy_total_krw": round(buy_total, 0),
                "sell_total_krw": round(sell_total, 0),
                "net_pnl_krw": round(sell_total - buy_total, 0),
                "win_rate_pct": round(win_rate, 1),
                "most_active_hour": most_active_hour,
                "by_ticker": ticker_stats,
            }
        else:
            report["trades"] = {"message": "해당 기간 거래 없음"}

        # 최근 보유 현황
        if self._history:
            latest = self._history[-1]
            holdings = latest.get("holdings", {})
            holdings_summary = []
            total_val = latest.get("total_value_krw", 0)

            for currency, info in holdings.items():
                value = info.get("value_krw", 0)
                weight = (value / total_val * 100) if total_val > 0 else 0
                holdings_summary.append({
                    "currency": currency,
                    "amount": info.get("amount", 0),
                    "value_krw": round(value, 0),
                    "weight_pct": round(weight, 1),
                })
            holdings_summary.sort(key=lambda x: x["value_krw"], reverse=True)

            report["current_holdings"] = holdings_summary
        else:
            report["current_holdings"] = []

        # 텍스트 요약 생성
        report["summary_text"] = self._format_performance_summary(report)

        logger.info(f"성과 리포트 생성 완료 (기간: {period})")
        return report

    def _format_performance_summary(self, report: dict) -> str:
        """성과 리포트를 사람이 읽기 좋은 텍스트로 변환"""
        lines = [
            f"=== 성과 리포트 ({report['period']}) ===",
            f"생성 시각: {report['generated_at']}",
            "",
        ]

        # 포트폴리오 성과
        portfolio = report.get("portfolio", {})
        if "initial_value" in portfolio:
            pnl = portfolio["pnl_krw"]
            sign = "+" if pnl >= 0 else ""
            lines.extend([
                "[포트폴리오 성과]",
                f"  초기 자산: {portfolio['initial_value']:>15,.0f} 원",
                f"  최종 자산: {portfolio['final_value']:>15,.0f} 원",
                f"  손익:      {sign}{pnl:>14,.0f} 원 ({sign}{portfolio['pnl_pct']:.2f}%)",
                f"  최고점:    {portfolio['peak_value']:>15,.0f} 원",
                f"  최저점:    {portfolio['trough_value']:>15,.0f} 원",
                "",
            ])

        # 위험 지표
        risk = report.get("risk", {})
        if "max_drawdown_pct" in risk:
            lines.extend([
                "[위험 지표]",
                f"  최대 낙폭(MDD): {risk['max_drawdown_pct']:>10.2f} %",
                f"  Sharpe Ratio:   {risk.get('sharpe_ratio', 0):>10.4f}",
                f"  일간 변동성:    {risk.get('daily_volatility_pct', 0):>10.4f} %",
                f"  연간 변동성:    {risk.get('annual_volatility_pct', 0):>10.2f} %",
                "",
            ])

        # 거래 통계
        trades_info = report.get("trades", {})
        if "total" in trades_info:
            net = trades_info["net_pnl_krw"]
            sign = "+" if net >= 0 else ""
            lines.extend([
                "[거래 통계]",
                f"  총 거래: {trades_info['total']}건 (매수 {trades_info['buy_count']} / 매도 {trades_info['sell_count']})",
                f"  매수 총액:   {trades_info['buy_total_krw']:>15,.0f} 원",
                f"  매도 총액:   {trades_info['sell_total_krw']:>15,.0f} 원",
                f"  순 손익:     {sign}{net:>14,.0f} 원",
                f"  승률:        {trades_info['win_rate_pct']:>10.1f} %",
                "",
            ])

            # 종목별 성과
            by_ticker = trades_info.get("by_ticker", [])
            if by_ticker:
                lines.append("[종목별 성과]")
                for ts in by_ticker[:10]:
                    pnl = ts["net_pnl_krw"]
                    sign = "+" if pnl >= 0 else ""
                    coin = ts["ticker"].replace("KRW-", "")
                    lines.append(
                        f"  {coin:>6s}: 매수 {ts['buy_count']}회 / 매도 {ts['sell_count']}회 "
                        f"| 순익 {sign}{pnl:,.0f}원"
                    )
                lines.append("")

        # 현재 보유
        holdings = report.get("current_holdings", [])
        if holdings:
            lines.append("[현재 보유]")
            for h in holdings:
                lines.append(
                    f"  {h['currency']:>6s}: {h['value_krw']:>12,.0f}원 ({h['weight_pct']:.1f}%)"
                )

        return "\n".join(lines)