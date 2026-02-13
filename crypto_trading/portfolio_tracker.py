"""
Portfolio Tracker
- 보유 자산 스냅샷 기록
- 자산 추이 그래프 생성 (matplotlib)
- 거래 내역 로깅
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
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

    @staticmethod
    def _load_json(path: Path, default):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save_history(self):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self._history, f, ensure_ascii=False, indent=2)

    def _save_trades(self):
        with open(self.trade_log_file, "w", encoding="utf-8") as f:
            json.dump(self._trades, f, ensure_ascii=False, indent=2)

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