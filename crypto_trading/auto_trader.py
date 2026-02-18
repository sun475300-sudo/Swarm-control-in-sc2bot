"""
Auto Trader Engine
- 전략 기반 자동 매매 루프
- 손절/익절 자동 관리
- 포트폴리오 스냅샷 자동 기록
"""
import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config
from .upbit_client import UpbitClient
from .strategies import Signal, get_strategy, AVAILABLE_STRATEGIES
from .risk_manager import RiskManager
from .portfolio_tracker import PortfolioTracker
from .market_analyzer import MarketAnalyzer
from .security import trade_safety

logger = logging.getLogger("crypto.auto_trader")


class AutoTrader:
    """자동매매 엔진"""

    def __init__(self):
        self.client = UpbitClient()
        self.risk = RiskManager()
        self.tracker = PortfolioTracker()
        self.strategy_name: str = "volatility_breakout"
        self.strategy = get_strategy(self.strategy_name)
        self.watch_list: list = list(config.DEFAULT_WATCH_LIST)
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self.interval: int = config.AUTO_TRADE_INTERVAL
        self._last_status: dict = {}
        self.analyzer = MarketAnalyzer(self.client)
        self.smart_mode: bool = True          # True = 종합 분석 기반, False = 단일 전략
        self.buy_threshold: int = 20           # analyzer BUY 임계값과 통일 (20점)
        self.sell_threshold: int = -20         # analyzer SELL 임계값과 통일 (-20점)
        self.max_positions: int = 5            # 동시 보유 최대 종목 수
        self.cooldown_minutes: int = 30        # 같은 코인 재매매 대기 시간(분)
        self._trade_cooldown: dict = {}        # {ticker: last_trade_timestamp}
        self._cycle_count: int = 0             # 누적 사이클 수
        self.max_budget: float = 0             # 0 = 제한 없음, >0 이면 이 금액까지만 매수
        self._total_spent: float = 0           # 이번 세션에서 사용한 총 매수 금액
        # 동시성 보호
        self._cycle_lock = threading.Lock()    # run_cycle 동시 실행 방지
        self._in_flight: set = set()           # 현재 주문 진행 중인 티커
        self._thread: Optional[threading.Thread] = None  # 백그라운드 스레드 참조
        # #30 Price Alerts
        self._price_alerts: dict = {}          # {ticker: {"above": float, "below": float}}
        self._alerts_file = config.DATA_DIR / "price_alerts.json"
        self._load_price_alerts()
        # #35 DCA
        self._dca_tasks: list = []             # DCA 진행 목록
        # #36 Trailing Stop
        self._trailing_stops: dict = {}        # {ticker: {"trail_pct": float, "highest_price": float, "activated": bool}}

    # ─────────── 쿨다운 / 포지션 관리 ───────────

    def _is_on_cooldown(self, ticker: str) -> bool:
        """해당 코인이 쿨다운 중인지 확인"""
        last_trade = self._trade_cooldown.get(ticker)
        if last_trade is None:
            return False
        elapsed = (datetime.now() - last_trade).total_seconds() / 60
        return elapsed < self.cooldown_minutes

    def _record_cooldown(self, ticker: str):
        """매매 후 쿨다운 기록"""
        self._trade_cooldown[ticker] = datetime.now()

    def _count_current_positions(self, balances: list) -> int:
        """현재 보유 종목 수"""
        count = 0
        for b in balances:
            if b.get("currency") == "KRW":
                continue
            if float(b.get("balance", 0)) > 0:
                count += 1
        return count

    def _calc_sell_ratio(self, score: int) -> float:
        """점수 기반 매도 비율 (점진적 매도)
        -30 ~ -50: 50% 매도, -50 ~ -70: 75% 매도, -70 이하: 전량 매도
        """
        if score <= -70:
            return 1.0
        elif score <= -50:
            return 0.75
        elif score <= self.sell_threshold:
            return 0.5
        return 0.0

    # ─────────── #30 Price Alerts ───────────

    def _load_price_alerts(self):
        """파일에서 가격 알림 로드"""
        if self._alerts_file.exists():
            try:
                with open(self._alerts_file, "r", encoding="utf-8") as f:
                    self._price_alerts = json.load(f)
            except Exception:
                self._price_alerts = {}

    def _save_price_alerts(self):
        """가격 알림을 파일에 저장"""
        try:
            with open(self._alerts_file, "w", encoding="utf-8") as f:
                json.dump(self._price_alerts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"가격 알림 저장 실패: {e}")

    def set_price_alert(self, ticker: str, above: float = None, below: float = None) -> dict:
        """가격 알림 설정"""
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
        alert = {}
        if above is not None:
            alert["above"] = above
        if below is not None:
            alert["below"] = below
        if not alert:
            return {"error": "above 또는 below 값이 필요합니다"}
        alert["created"] = datetime.now().isoformat()
        self._price_alerts[ticker] = alert
        self._save_price_alerts()
        logger.info(f"가격 알림 설정: {ticker} {alert}")
        return {"ticker": ticker, "alert": alert, "status": "set"}

    def check_price_alerts(self) -> list:
        """가격 알림 확인 — 트리거된 알림 반환"""
        triggered = []
        to_remove = []
        for ticker, alert in self._price_alerts.items():
            try:
                price = self.client.get_current_price(ticker)
                if price is None:
                    continue
                if "above" in alert and price >= alert["above"]:
                    triggered.append({
                        "ticker": ticker, "type": "above",
                        "target": alert["above"], "current": price,
                        "message": f"{ticker} 가격 {price:,.0f}원 - 상한 알림({alert['above']:,.0f}원) 도달"
                    })
                    to_remove.append(ticker)
                    logger.info(f"가격 알림 트리거: {ticker} >= {alert['above']:,.0f}")
                elif "below" in alert and price <= alert["below"]:
                    triggered.append({
                        "ticker": ticker, "type": "below",
                        "target": alert["below"], "current": price,
                        "message": f"{ticker} 가격 {price:,.0f}원 - 하한 알림({alert['below']:,.0f}원) 도달"
                    })
                    to_remove.append(ticker)
                    logger.info(f"가격 알림 트리거: {ticker} <= {alert['below']:,.0f}")
            except Exception as e:
                logger.error(f"가격 알림 확인 오류 ({ticker}): {e}")
        for t in to_remove:
            self._price_alerts.pop(t, None)
        if to_remove:
            self._save_price_alerts()
        return triggered

    def get_price_alerts(self) -> dict:
        """현재 활성 가격 알림 목록"""
        return dict(self._price_alerts)

    # ─────────── #35 DCA (Dollar Cost Averaging) ───────────

    def start_dca(self, ticker: str, total_amount: float, num_splits: int, interval_minutes: int) -> dict:
        """분할 매수(DCA) 시작"""
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
        split_amount = total_amount / num_splits
        if split_amount < config.MIN_ORDER_AMOUNT:
            return {"error": f"분할 금액({split_amount:,.0f}원)이 최소 주문 금액({config.MIN_ORDER_AMOUNT:,.0f}원) 미만"}

        dca_task = {
            "ticker": ticker,
            "total_amount": total_amount,
            "split_amount": split_amount,
            "num_splits": num_splits,
            "interval_minutes": interval_minutes,
            "completed_splits": 0,
            "total_spent": 0,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "orders": [],
        }
        self._dca_tasks.append(dca_task)

        # 백그라운드 스레드로 DCA 실행
        def _run_dca(task):
            for i in range(task["num_splits"]):
                if task["status"] != "running":
                    break
                try:
                    order = self.client.buy_market_order(task["ticker"], task["split_amount"])
                    if order is not None:
                        task["completed_splits"] += 1
                        task["total_spent"] += task["split_amount"]
                        task["orders"].append({
                            "split": i + 1, "amount": task["split_amount"],
                            "timestamp": datetime.now().isoformat(),
                        })
                        self.tracker.log_trade(
                            "buy", task["ticker"], task["split_amount"],
                            0, f"DCA {i+1}/{task['num_splits']}", order
                        )
                        logger.info(f"DCA 매수 {i+1}/{task['num_splits']}: {task['ticker']} {task['split_amount']:,.0f}원")
                    else:
                        logger.error(f"DCA 매수 실패: {task['ticker']} split {i+1}")
                except Exception as e:
                    logger.error(f"DCA 오류: {e}")

                if i < task["num_splits"] - 1:
                    time.sleep(task["interval_minutes"] * 60)

            task["status"] = "completed"
            logger.info(f"DCA 완료: {task['ticker']} {task['completed_splits']}/{task['num_splits']} splits")

        t = threading.Thread(target=_run_dca, args=(dca_task,), daemon=True)
        t.start()

        return {
            "status": "started",
            "ticker": ticker,
            "total_amount": total_amount,
            "split_amount": split_amount,
            "num_splits": num_splits,
            "interval_minutes": interval_minutes,
        }

    def get_dca_status(self) -> list:
        """DCA 작업 상태 조회"""
        return [
            {
                "ticker": t["ticker"], "status": t["status"],
                "completed": t["completed_splits"], "total": t["num_splits"],
                "spent": t["total_spent"], "target": t["total_amount"],
            }
            for t in self._dca_tasks
        ]

    # ─────────── #36 Trailing Stop ───────────

    def set_trailing_stop(self, ticker: str, trail_pct: float) -> dict:
        """트레일링 스탑 설정"""
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
        current_price = self.client.get_current_price(ticker)
        if not current_price:
            return {"error": f"시세 조회 실패: {ticker}"}

        self._trailing_stops[ticker] = {
            "trail_pct": trail_pct,
            "highest_price": current_price,
            "activated": True,
            "set_at": datetime.now().isoformat(),
        }
        logger.info(f"트레일링 스탑 설정: {ticker} {trail_pct}% (현재가: {current_price:,.0f})")
        return {
            "ticker": ticker, "trail_pct": trail_pct,
            "highest_price": current_price, "status": "set",
        }

    def _check_trailing_stops(self) -> list:
        """트레일링 스탑 확인 및 실행"""
        triggered = []
        to_remove = []
        for ticker, ts in self._trailing_stops.items():
            if not ts["activated"]:
                continue
            try:
                price = self.client.get_current_price(ticker)
                if price is None:
                    continue

                # 최고가 갱신
                if price > ts["highest_price"]:
                    ts["highest_price"] = price

                # 최고가 대비 하락률 확인
                drop_pct = ((ts["highest_price"] - price) / ts["highest_price"]) * 100
                if drop_pct >= ts["trail_pct"]:
                    # 매도 실행
                    coin_balance = self.client.get_balance(ticker)
                    if coin_balance > 0:
                        order = self.client.sell_market_order(ticker, coin_balance)
                        if order is not None:
                            sell_value = coin_balance * price
                            self.tracker.log_trade(
                                "sell", ticker, sell_value, price,
                                f"트레일링스탑 ({ts['trail_pct']}%, 최고가:{ts['highest_price']:,.0f})", order
                            )
                            triggered.append({
                                "ticker": ticker, "action": "sell",
                                "price": price, "highest": ts["highest_price"],
                                "drop_pct": round(drop_pct, 2),
                            })
                            logger.info(f"트레일링 스탑 실행: {ticker} 매도 (하락 {drop_pct:.1f}%)")
                    to_remove.append(ticker)
            except Exception as e:
                logger.error(f"트레일링 스탑 확인 오류 ({ticker}): {e}")
        for t in to_remove:
            self._trailing_stops.pop(t, None)
        return triggered

    # ─────────── #50 자동 리밸런싱 ───────────

    def auto_rebalance(self, target_weights: dict) -> dict:
        """
        자동 리밸런싱 (#50)
        현재 포트폴리오를 목표 비중에 맞게 자동 조정

        Args:
            target_weights: 목표 비중 dict (예: {"BTC": 40, "ETH": 30, "KRW": 30})
                           값은 퍼센트 (합계 100이어야 함)

        Returns:
            리밸런싱 실행 결과 dict
        """
        # 입력 검증
        total_weight = sum(target_weights.values())
        if abs(total_weight - 100) > 0.01:
            return {"error": f"목표 비중 합계가 100이 아닙니다: {total_weight:.2f}%"}

        # 현재 잔고 조회
        balances = self.client.get_balances()
        if not balances:
            return {"error": "잔고 조회 실패"}

        # 현재 포트폴리오 가치 계산
        portfolio = {}
        total_value_krw = 0.0
        tickers_for_price = []

        for b in balances:
            currency = b.get("currency", "")
            balance = float(b.get("balance", 0)) + float(b.get("locked", 0))
            if balance <= 0:
                continue
            if currency == "KRW":
                portfolio["KRW"] = {"balance": balance, "value_krw": balance}
                total_value_krw += balance
            else:
                tickers_for_price.append(f"KRW-{currency}")
                portfolio[currency] = {"balance": balance}

        prices = self.client.get_prices(tickers_for_price) if tickers_for_price else {}

        for currency, info in portfolio.items():
            if currency == "KRW":
                continue
            ticker = f"KRW-{currency}"
            price = prices.get(ticker, 0)
            value = info["balance"] * price
            info["price"] = price
            info["value_krw"] = value
            total_value_krw += value

        if total_value_krw <= 0:
            return {"error": "총 자산 가치가 0입니다"}

        # 현재 비중 계산
        current_weights = {}
        for currency, info in portfolio.items():
            current_weights[currency] = round(info["value_krw"] / total_value_krw * 100, 2)

        # 리밸런싱 액션 계산
        actions = []
        executed = []
        errors = []

        for currency, target_pct in target_weights.items():
            currency = currency.upper()
            current_pct = current_weights.get(currency, 0)
            diff_pct = target_pct - current_pct
            diff_krw = total_value_krw * (diff_pct / 100)

            if abs(diff_pct) < 1.0:
                # 1% 미만 차이는 무시
                actions.append({
                    "currency": currency,
                    "action": "skip",
                    "current_pct": current_pct,
                    "target_pct": target_pct,
                    "reason": "차이 1% 미만",
                })
                continue

            if currency == "KRW":
                # KRW는 직접 매매 불가, 다른 코인 매매로 조정
                actions.append({
                    "currency": "KRW",
                    "action": "adjust_via_trades",
                    "current_pct": current_pct,
                    "target_pct": target_pct,
                    "diff_krw": round(diff_krw, 0),
                })
                continue

            ticker = f"KRW-{currency}"

            if diff_pct > 0:
                # 비중 부족 → 매수 필요
                buy_amount = abs(diff_krw)
                if buy_amount < config.MIN_ORDER_AMOUNT:
                    actions.append({
                        "currency": currency, "action": "skip_buy",
                        "current_pct": current_pct, "target_pct": target_pct,
                        "reason": f"매수 금액 {buy_amount:,.0f}원 < 최소주문 {config.MIN_ORDER_AMOUNT}원",
                    })
                    continue

                safe, safe_msg = trade_safety.check_trade(buy_amount)
                if not safe:
                    errors.append(f"매수 차단 ({currency}): {safe_msg}")
                    continue

                order = self.client.buy_market_order(ticker, buy_amount)
                if order is not None:
                    self.tracker.log_trade("buy", ticker, buy_amount, 0,
                                           f"리밸런싱 매수 ({current_pct:.1f}%→{target_pct:.1f}%)", order)
                    trade_safety.record_trade(buy_amount)
                    executed.append({
                        "currency": currency, "action": "buy",
                        "amount_krw": round(buy_amount, 0),
                        "from_pct": current_pct, "to_pct": target_pct,
                    })
                else:
                    errors.append(f"매수 실패: {ticker}")

            elif diff_pct < 0:
                # 비중 초과 → 매도 필요
                sell_value_krw = abs(diff_krw)
                price = prices.get(ticker, 0)
                if price <= 0:
                    errors.append(f"시세 조회 실패: {ticker}")
                    continue

                sell_volume = sell_value_krw / price
                current_balance = portfolio.get(currency, {}).get("balance", 0)
                sell_volume = min(sell_volume, current_balance)

                if sell_volume <= 0:
                    continue

                safe, safe_msg = trade_safety.check_trade(sell_value_krw)
                if not safe:
                    errors.append(f"매도 차단 ({currency}): {safe_msg}")
                    continue

                order = self.client.sell_market_order(ticker, sell_volume)
                if order is not None:
                    actual_value = sell_volume * price
                    self.tracker.log_trade("sell", ticker, actual_value, price,
                                           f"리밸런싱 매도 ({current_pct:.1f}%→{target_pct:.1f}%)", order)
                    trade_safety.record_trade(actual_value)
                    executed.append({
                        "currency": currency, "action": "sell",
                        "volume": round(sell_volume, 8),
                        "value_krw": round(actual_value, 0),
                        "from_pct": current_pct, "to_pct": target_pct,
                    })
                else:
                    errors.append(f"매도 실패: {ticker}")

        logger.info(f"리밸런싱 완료: {len(executed)}건 실행, {len(errors)}건 오류")

        return {
            "total_value_krw": round(total_value_krw, 0),
            "current_weights": current_weights,
            "target_weights": target_weights,
            "executed": executed,
            "skipped": [a for a in actions if "skip" in a.get("action", "")],
            "errors": errors,
            "dry_run": config.DRY_RUN,
        }

    # ─────────── #53 지정가 주문 ───────────

    def place_limit_order(self, ticker: str, price: float, amount: float, side: str = "buy") -> dict:
        """
        지정가 주문 (#53)

        Args:
            ticker: 코인 티커 (예: "KRW-BTC" 또는 "BTC")
            price: 지정가 (KRW)
            amount: 주문 수량 (코인 수량). side='buy'이면 KRW 금액으로도 해석 가능
            side: 'buy' 또는 'sell'

        Returns:
            주문 결과 dict
        """
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"

        if price <= 0:
            return {"error": "가격은 0보다 커야 합니다"}
        if amount <= 0:
            return {"error": "수량은 0보다 커야 합니다"}

        # 현재가 조회
        current_price = self.client.get_current_price(ticker)
        if not current_price:
            return {"error": f"시세 조회 실패: {ticker}"}

        order_value_krw = price * amount

        if side == "buy":
            # 매수 지정가 주문
            if order_value_krw < config.MIN_ORDER_AMOUNT:
                return {
                    "error": f"주문 금액 {order_value_krw:,.0f}원이 최소 주문 금액 {config.MIN_ORDER_AMOUNT:,.0f}원 미만"
                }

            safe, safe_msg = trade_safety.check_trade(order_value_krw)
            if not safe:
                return {"error": f"안전 가드 차단: {safe_msg}"}

            price_diff_pct = ((price - current_price) / current_price) * 100

            order = self.client.buy_limit_order(ticker, price, amount)
            if order is not None:
                self.tracker.log_trade(
                    "buy", ticker, order_value_krw, price,
                    f"지정가 매수 ({price:,.0f}원, 현재가 대비 {price_diff_pct:+.2f}%)", order
                )
                trade_safety.record_trade(order_value_krw)
                logger.info(f"지정가 매수 주문: {ticker} {price:,.0f}원 x {amount}")
                return {
                    "status": "placed",
                    "side": "buy",
                    "ticker": ticker,
                    "price": price,
                    "volume": amount,
                    "total_krw": round(order_value_krw, 0),
                    "current_price": current_price,
                    "price_diff_pct": round(price_diff_pct, 2),
                    "order": order,
                    "dry_run": config.DRY_RUN,
                }
            return {"error": f"지정가 매수 주문 실패: {ticker}"}

        elif side == "sell":
            # 매도 지정가 주문
            coin_balance = self.client.get_balance(ticker)
            if amount > coin_balance:
                return {
                    "error": f"보유 수량 부족: 보유 {coin_balance}, 주문 {amount}",
                    "balance": coin_balance,
                }

            safe, safe_msg = trade_safety.check_trade(order_value_krw)
            if not safe:
                return {"error": f"안전 가드 차단: {safe_msg}"}

            price_diff_pct = ((price - current_price) / current_price) * 100

            order = self.client.sell_limit_order(ticker, price, amount)
            if order is not None:
                self.tracker.log_trade(
                    "sell", ticker, order_value_krw, price,
                    f"지정가 매도 ({price:,.0f}원, 현재가 대비 {price_diff_pct:+.2f}%)", order
                )
                trade_safety.record_trade(order_value_krw)
                logger.info(f"지정가 매도 주문: {ticker} {price:,.0f}원 x {amount}")
                return {
                    "status": "placed",
                    "side": "sell",
                    "ticker": ticker,
                    "price": price,
                    "volume": amount,
                    "total_krw": round(order_value_krw, 0),
                    "current_price": current_price,
                    "price_diff_pct": round(price_diff_pct, 2),
                    "order": order,
                    "dry_run": config.DRY_RUN,
                }
            return {"error": f"지정가 매도 주문 실패: {ticker}"}

        return {"error": f"알 수 없는 주문 유형: {side} (buy 또는 sell만 가능)"}

    # ─────────── #54 ATR 기반 동적 손절 ───────────

    def calculate_atr_stop(self, ticker: str, multiplier: float = 2.0, period: int = 14) -> dict:
        """
        ATR (Average True Range) 기반 동적 손절가 계산 (#54)

        ATR은 변동성을 측정하여 적절한 손절 폭을 동적으로 설정함.
        변동성이 크면 넓은 손절, 변동성이 작으면 좁은 손절.

        Args:
            ticker: 코인 티커 (예: "KRW-BTC")
            multiplier: ATR 배수 (기본 2.0배, 클수록 넓은 손절)
            period: ATR 계산 기간 (기본 14일)

        Returns:
            ATR 손절 분석 결과 dict
        """
        ticker = ticker.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"

        df = self.client.get_ohlcv(ticker, interval="day", count=period + 10)
        if df is None or len(df) < period + 1:
            return {"error": f"데이터 부족: {ticker}"}

        # True Range 계산
        high = df["high"]
        low = df["low"]
        prev_close = df["close"].shift(1)

        tr1 = high - low                      # 당일 고가 - 저가
        tr2 = abs(high - prev_close)           # 당일 고가 - 전일 종가
        tr3 = abs(low - prev_close)            # 당일 저가 - 전일 종가

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR = True Range의 이동 평균
        atr = true_range.rolling(window=period).mean()
        current_atr = float(atr.iloc[-1])

        if pd.isna(current_atr) or current_atr <= 0:
            return {"error": "ATR 계산 불가", "ticker": ticker}

        current_price = float(df["close"].iloc[-1])

        # 손절가 계산
        stop_loss_price = current_price - (current_atr * multiplier)
        stop_loss_pct = ((stop_loss_price - current_price) / current_price) * 100

        # ATR 기반 익절가 (손절 대비 2:1 보상비)
        take_profit_price = current_price + (current_atr * multiplier * 2)
        take_profit_pct = ((take_profit_price - current_price) / current_price) * 100

        # ATR 변동성 등급
        atr_pct = (current_atr / current_price) * 100
        if atr_pct > 5:
            volatility_level = "매우 높음"
        elif atr_pct > 3:
            volatility_level = "높음"
        elif atr_pct > 1.5:
            volatility_level = "보통"
        else:
            volatility_level = "낮음"

        # 최근 ATR 추세
        recent_atrs = [
            round(float(v), 0) for v in atr.iloc[-5:]
            if not pd.isna(v)
        ]

        logger.info(
            f"ATR 손절 계산: {ticker} 현재가={current_price:,.0f}, "
            f"ATR={current_atr:,.0f}, 손절가={stop_loss_price:,.0f} ({stop_loss_pct:+.2f}%)"
        )

        return {
            "ticker": ticker,
            "current_price": current_price,
            "atr": round(current_atr, 0),
            "atr_pct": round(atr_pct, 2),
            "multiplier": multiplier,
            "period": period,
            "stop_loss_price": round(stop_loss_price, 0),
            "stop_loss_pct": round(stop_loss_pct, 2),
            "take_profit_price": round(take_profit_price, 0),
            "take_profit_pct": round(take_profit_pct, 2),
            "volatility_level": volatility_level,
            "recent_atr_history": recent_atrs,
            "risk_reward_ratio": "1:2",
        }

    # ─────────── 설정 변경 ───────────

    def set_strategy(self, name: str, **kwargs):
        """전략 변경"""
        self.strategy = get_strategy(name, **kwargs)
        self.strategy_name = name
        logger.info(f"전략 변경: {name}")

    def set_watch_list(self, tickers: list):
        """관심 코인 목록 변경"""
        self.watch_list = tickers
        logger.info(f"관심 목록 변경: {tickers}")

    def set_risk_params(self, stop_loss: float = None, take_profit: float = None,
                        max_order_ratio: float = None):
        """리스크 파라미터 변경"""
        if stop_loss is not None:
            self.risk.stop_loss_pct = stop_loss
        if take_profit is not None:
            self.risk.take_profit_pct = take_profit
        if max_order_ratio is not None:
            self.risk.max_single_order_ratio = max_order_ratio
        logger.info(f"리스크 설정 변경: SL={self.risk.stop_loss_pct}% TP={self.risk.take_profit_pct}%")

    # ─────────── 1회 사이클 ───────────

    def run_cycle(self) -> dict:
        """매매 사이클 1회 실행 (동기, thread-safe)"""
        if not self._cycle_lock.acquire(blocking=False):
            logger.warning("이전 사이클이 아직 실행 중 — 스킵")
            return {"skipped": True, "reason": "이전 사이클 실행 중"}
        try:
            if self.smart_mode:
                return self._run_smart_cycle()
            return self._run_strategy_cycle()
        finally:
            self._cycle_lock.release()

    def _run_smart_cycle(self) -> dict:
        """스마트 모드: 종합 분석 기반 자동 매매"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "mode": "smart",
            "strategy": "multi_indicator",
            "dry_run": config.DRY_RUN,
            "analyses": [],
            "actions": [],
            "errors": [],
        }
        current_positions = 0

        # 가격 알림 & 트레일링 스탑 체크
        try:
            alerts = self.check_price_alerts()
            for a in alerts:
                result["actions"].append(a["message"])
            ts_triggered = self._check_trailing_stops()
            for ts in ts_triggered:
                result["actions"].append(f"트레일링스탑 매도: {ts['ticker']} (하락 {ts['drop_pct']}%)")
        except Exception as e:
            result["errors"].append(f"알림/트레일링 체크 오류: {str(e)}")

        try:
            # 1. 잔고 조회
            krw_balance = self.client.get_balance("KRW")
            balances = self.client.get_balances()
            result["krw_balance"] = krw_balance

            # 2. 보유 코인 손절/익절 체크 (이중 매도 방지)
            for b in balances:
                currency = b.get("currency", "")
                if currency == "KRW":
                    continue
                balance = float(b.get("balance", 0))
                if balance <= 0:
                    continue

                ticker = f"KRW-{currency}"
                if ticker in self._in_flight:
                    continue  # 주문 진행 중 스킵

                avg_price = float(b.get("avg_buy_price", 0))
                current_price = self.client.get_current_price(ticker)
                if not current_price or avg_price <= 0:
                    continue

                action = self.risk.check_position(avg_price, current_price)
                if action in ("stop_loss", "take_profit"):
                    # 실시간 잔고 재확인 (이중 매도 방지)
                    actual_balance = self.client.get_balance(ticker)
                    if actual_balance <= 0:
                        result["actions"].append(f"⚠️ {action} 스킵 ({ticker}): 잔고 없음")
                        continue
                    self._in_flight.add(ticker)
                    try:
                        reason_text = "손절" if action == "stop_loss" else "익절"
                        order = self.client.sell_market_order(ticker, actual_balance)
                        if order is not None:
                            self.tracker.log_trade("sell", ticker, actual_balance * current_price,
                                                   current_price, reason_text, order)
                            result["actions"].append(f"{reason_text} 매도: {ticker} x {actual_balance}")
                        else:
                            result["errors"].append(f"{reason_text} 매도 실패: {ticker}")
                    finally:
                        self._in_flight.discard(ticker)

            # 3. 종합 분석으로 매매 판단
            analyses = self.analyzer.analyze_watchlist(self.watch_list)
            current_positions = self._count_current_positions(balances)

            for a in analyses:
                result["analyses"].append({
                    "ticker": a.ticker,
                    "score": a.score,
                    "recommendation": a.recommendation,
                    "price": a.current_price,
                    "rsi": a.rsi_14,
                    "macd_h": a.macd_histogram,
                    "trend": a.trend_strength,
                    "reasons": a.reasons,
                })

                # 쿨다운 체크
                if self._is_on_cooldown(a.ticker):
                    result["actions"].append(f"⏳ 쿨다운 중: {a.ticker}")
                    continue

                # in-flight 체크 (동일 코인 중복 주문 방지)
                if a.ticker in self._in_flight:
                    result["actions"].append(f"⏳ 주문 진행 중: {a.ticker}")
                    continue

                # 매수: 스코어가 buy_threshold 이상 + 포지션 여유
                if a.score >= self.buy_threshold and a.recommendation in ("BUY", "STRONG_BUY"):
                    if current_positions >= self.max_positions:
                        result["actions"].append(f"매수 스킵 ({a.ticker}): 최대 포지션({self.max_positions}) 도달")
                        continue

                    # 예산 제한 체크
                    if self.max_budget > 0:
                        remaining_budget = self.max_budget - self._total_spent
                        if remaining_budget < config.MIN_ORDER_AMOUNT:
                            result["actions"].append(f"매수 스킵 ({a.ticker}): 예산 소진 ({self._total_spent:,.0f}/{self.max_budget:,.0f}원)")
                            continue

                    strength = min(a.score / 100.0, 1.0)
                    order_amount = self.risk.calculate_order_amount(krw_balance, strength)

                    # 예산 제한이 있으면 주문 금액 조정
                    if self.max_budget > 0:
                        remaining_budget = self.max_budget - self._total_spent
                        order_amount = min(order_amount, remaining_budget)

                    valid, msg = self.risk.validate_order(krw_balance, order_amount)
                    if valid:
                        # 보안 가드: 거래 안전 검증
                        safe, safe_msg = trade_safety.check_trade(order_amount)
                        if not safe:
                            result["actions"].append(f"🛡️ 매수 차단 ({a.ticker}): {safe_msg}")
                            continue
                        # 쿨다운 선기록 (중복 주문 방지)
                        self._record_cooldown(a.ticker)
                        self._in_flight.add(a.ticker)
                        try:
                            order = self.client.buy_market_order(a.ticker, order_amount)
                            if order is not None:
                                reason = f"스마트분석 매수 (점수:{a.score:+d}, {', '.join(a.reasons[:2])})"
                                self.tracker.log_trade("buy", a.ticker, order_amount, 0, reason, order)
                                trade_safety.record_trade(order_amount)
                                self._total_spent += order_amount
                                budget_info = f" [예산: {self._total_spent:,.0f}/{self.max_budget:,.0f}원]" if self.max_budget > 0 else ""
                                result["actions"].append(f"매수: {a.ticker} / {order_amount:,.0f}원 (점수:{a.score:+d}){budget_info}")
                                krw_balance -= order_amount
                                current_positions += 1
                            else:
                                result["errors"].append(f"매수 실패: {a.ticker} / {order_amount:,.0f}원")
                                # 실패 시 쿨다운 해제
                                self._trade_cooldown.pop(a.ticker, None)
                        finally:
                            self._in_flight.discard(a.ticker)
                    else:
                        result["actions"].append(f"매수 스킵 ({a.ticker}): {msg}")

                # 매도: 스코어가 sell_threshold 이하 + 보유 중 (점진적 매도)
                elif a.score <= self.sell_threshold and a.recommendation in ("SELL", "STRONG_SELL"):
                    coin_balance = self.client.get_balance(a.ticker)
                    if coin_balance > 0:
                        sell_ratio = self._calc_sell_ratio(a.score)
                        sell_amount = coin_balance * sell_ratio
                        sell_value = sell_amount * a.current_price
                        # 보안 가드: 거래 안전 검증
                        safe, safe_msg = trade_safety.check_trade(sell_value)
                        if not safe:
                            result["actions"].append(f"🛡️ 매도 차단 ({a.ticker}): {safe_msg}")
                            continue
                        self._in_flight.add(a.ticker)
                        try:
                            order = self.client.sell_market_order(a.ticker, sell_amount)
                            if order is not None:
                                reason = f"스마트분석 매도 (점수:{a.score:+d}, 비율:{sell_ratio:.0%}, {', '.join(a.reasons[:2])})"
                                self.tracker.log_trade("sell", a.ticker, sell_value,
                                                       a.current_price, reason, order)
                                trade_safety.record_trade(sell_value)
                                result["actions"].append(
                                    f"매도: {a.ticker} x {sell_amount:.4f} ({sell_ratio:.0%}) (점수:{a.score:+d})"
                                )
                                self._record_cooldown(a.ticker)
                            else:
                                result["errors"].append(f"매도 실패: {a.ticker}")
                        finally:
                            self._in_flight.discard(a.ticker)

            # 4. 포트폴리오 스냅샷
            tickers_for_price = [f"KRW-{b['currency']}" for b in balances
                                 if b.get("currency") != "KRW" and float(b.get("balance", 0)) > 0]
            prices = self.client.get_prices(tickers_for_price) if tickers_for_price else {}
            self.tracker.record_snapshot(balances, prices)

        except Exception as e:
            result["errors"].append(f"스마트 사이클 오류: {str(e)}")
            logger.error(f"스마트 매매 오류: {e}", exc_info=True)

        self._cycle_count += 1
        result["cycle_count"] = self._cycle_count
        result["positions"] = current_positions
        self._last_status = result
        return result

    def _run_strategy_cycle(self) -> dict:
        """단일 전략 모드: 기존 전략 기반 매매"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "mode": "strategy",
            "strategy": self.strategy_name,
            "dry_run": config.DRY_RUN,
            "signals": [],
            "actions": [],
            "errors": [],
        }

        # 가격 알림 & 트레일링 스탑 체크
        try:
            alerts = self.check_price_alerts()
            for a in alerts:
                result["actions"].append(a["message"])
            ts_triggered = self._check_trailing_stops()
            for ts in ts_triggered:
                result["actions"].append(f"트레일링스탑 매도: {ts['ticker']} (하락 {ts['drop_pct']}%)")
        except Exception as e:
            result["errors"].append(f"알림/트레일링 체크 오류: {str(e)}")

        try:
            # 1. 잔고 조회
            krw_balance = self.client.get_balance("KRW")
            balances = self.client.get_balances()
            result["krw_balance"] = krw_balance

            # 2. 보유 코인 손절/익절 체크 (이중 매도 방지)
            for b in balances:
                currency = b.get("currency", "")
                if currency == "KRW":
                    continue
                balance = float(b.get("balance", 0))
                if balance <= 0:
                    continue

                ticker = f"KRW-{currency}"
                if ticker in self._in_flight:
                    continue

                avg_price = float(b.get("avg_buy_price", 0))
                current_price = self.client.get_current_price(ticker)
                if not current_price or avg_price <= 0:
                    continue

                action = self.risk.check_position(avg_price, current_price)
                if action in ("stop_loss", "take_profit"):
                    actual_balance = self.client.get_balance(ticker)
                    if actual_balance <= 0:
                        continue
                    self._in_flight.add(ticker)
                    try:
                        reason_text = "손절" if action == "stop_loss" else "익절"
                        order = self.client.sell_market_order(ticker, actual_balance)
                        if order is not None:
                            self.tracker.log_trade("sell", ticker, actual_balance * current_price,
                                                   current_price, reason_text, order)
                            result["actions"].append(f"{reason_text} 매도: {ticker} x {actual_balance}")
                        else:
                            result["errors"].append(f"{reason_text} 매도 실패: {ticker}")
                    finally:
                        self._in_flight.discard(ticker)

            # 3. 관심 코인 전략 시그널 평가
            current_positions = self._count_current_positions(balances)
            for ticker in self.watch_list:
                try:
                    if ticker in self._in_flight:
                        continue

                    df = self.client.get_ohlcv(ticker, interval="day", count=30)
                    signal = self.strategy.evaluate(ticker, df)
                    result["signals"].append({
                        "ticker": ticker,
                        "signal": signal.signal.value,
                        "reason": signal.reason,
                        "strength": round(signal.strength, 2),
                    })

                    if signal.signal == Signal.BUY:
                        # 포지션 한도 체크
                        if current_positions >= self.max_positions:
                            result["actions"].append(f"매수 스킵 ({ticker}): 최대 포지션({self.max_positions}) 도달")
                            continue

                        # 쿨다운 체크
                        if self._is_on_cooldown(ticker):
                            result["actions"].append(f"⏳ 쿨다운 중: {ticker}")
                            continue

                        # 예산 제한 체크
                        if self.max_budget > 0:
                            remaining_budget = self.max_budget - self._total_spent
                            if remaining_budget < config.MIN_ORDER_AMOUNT:
                                result["actions"].append(f"매수 스킵 ({ticker}): 예산 소진")
                                continue

                        order_amount = self.risk.calculate_order_amount(krw_balance, signal.strength)
                        if self.max_budget > 0:
                            remaining_budget = self.max_budget - self._total_spent
                            order_amount = min(order_amount, remaining_budget)
                        valid, msg = self.risk.validate_order(krw_balance, order_amount)
                        if valid:
                            # 보안 가드: 거래 안전 검증
                            safe, safe_msg = trade_safety.check_trade(order_amount)
                            if not safe:
                                result["actions"].append(f"🛡️ 매수 차단 ({ticker}): {safe_msg}")
                                continue
                            self._record_cooldown(ticker)
                            self._in_flight.add(ticker)
                            try:
                                order = self.client.buy_market_order(ticker, order_amount)
                                if order is not None:
                                    self.tracker.log_trade("buy", ticker, order_amount,
                                                           0, signal.reason, order)
                                    trade_safety.record_trade(order_amount)
                                    self._total_spent += order_amount
                                    budget_info = f" [예산: {self._total_spent:,.0f}/{self.max_budget:,.0f}원]" if self.max_budget > 0 else ""
                                    result["actions"].append(f"매수: {ticker} / {order_amount:,.0f}원{budget_info}")
                                    krw_balance -= order_amount
                                    current_positions += 1
                                else:
                                    result["errors"].append(f"매수 실패: {ticker}")
                                    self._trade_cooldown.pop(ticker, None)
                            finally:
                                self._in_flight.discard(ticker)
                        else:
                            result["actions"].append(f"매수 스킵 ({ticker}): {msg}")

                    elif signal.signal == Signal.SELL:
                        coin_balance = self.client.get_balance(ticker)
                        if coin_balance > 0:
                            sell_value = coin_balance * (self.client.get_current_price(ticker) or 0)
                            # 보안 가드: 거래 안전 검증
                            safe, safe_msg = trade_safety.check_trade(sell_value)
                            if not safe:
                                result["actions"].append(f"🛡️ 매도 차단 ({ticker}): {safe_msg}")
                                continue
                            self._in_flight.add(ticker)
                            try:
                                order = self.client.sell_market_order(ticker, coin_balance)
                                if order is not None:
                                    price = self.client.get_current_price(ticker) or 0
                                    self.tracker.log_trade("sell", ticker, coin_balance * price,
                                                           price, signal.reason, order)
                                    trade_safety.record_trade(sell_value)
                                    result["actions"].append(f"매도: {ticker} x {coin_balance}")
                                else:
                                    result["errors"].append(f"매도 실패: {ticker}")
                            finally:
                                self._in_flight.discard(ticker)

                except Exception as e:
                    result["errors"].append(f"{ticker}: {str(e)}")

            # 4. 포트폴리오 스냅샷
            tickers_for_price = [f"KRW-{b['currency']}" for b in balances
                                 if b.get("currency") != "KRW" and float(b.get("balance", 0)) > 0]
            prices = self.client.get_prices(tickers_for_price) if tickers_for_price else {}
            self.tracker.record_snapshot(balances, prices)

        except Exception as e:
            result["errors"].append(f"사이클 오류: {str(e)}")
            logger.error(f"매매 사이클 오류: {e}", exc_info=True)

        self._cycle_count += 1
        self._last_status = result
        return result

    # ─────────── 자동매매 루프 (비동기) ───────────

    async def _loop(self):
        """자동매매 메인 루프"""
        mode = "스마트" if self.smart_mode else self.strategy_name
        logger.info(f"자동매매 시작 (모드: {mode}, 간격: {self.interval}초, DRY_RUN: {config.DRY_RUN})")
        while self.is_running:
            try:
                result = self.run_cycle()
                actions = result.get("actions", [])
                if actions:
                    logger.info(f"사이클 결과: {actions}")
            except Exception as e:
                logger.error(f"자동매매 루프 오류: {e}")
            await asyncio.sleep(self.interval)
        logger.info("자동매매 중지됨")

    def start(self):
        """자동매매 시작"""
        if self.is_running:
            return "이미 실행 중입니다."
        self.is_running = True
        self._total_spent = 0  # 세션 시작 시 사용 금액 초기화
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._loop())
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성
            import threading
            def _run():
                asyncio.run(self._loop())
            t = threading.Thread(target=_run, daemon=True)
            t.start()
            self._thread = t
        mode = "스마트 분석" if self.smart_mode else self.strategy_name
        budget_msg = f", 예산: {self.max_budget:,.0f}원" if self.max_budget > 0 else ""
        return f"자동매매 시작 (모드: {mode}, DRY_RUN: {config.DRY_RUN}{budget_msg})"

    def stop(self):
        """자동매매 중지"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            self._thread = None
        return "자동매매 중지됨"

    def get_status(self) -> dict:
        """현재 자동매매 상태"""
        st = self._last_status
        
        # 분석 정보 매핑 (bot은 market, reason 기대)
        analyses = []
        for a in st.get("analyses", []):
            analyses.append({
                "market": a.get("ticker", ""),
                "score": a.get("score", 0),
                "recommendation": a.get("recommendation", ""),
                "reason": ", ".join(a.get("reasons", [])) if isinstance(a.get("reasons"), list) else str(a.get("reasons", "")),
                "current_price": a.get("price", 0)
            })

        # 거래 정보 매핑 (bot은 action, market 기대)
        trades = []
        for t in self.tracker.get_recent_trades(10):
            trades.append({
                "timestamp": t.get("timestamp", ""),
                "action": t.get("side", ""),
                "market": t.get("ticker", ""),
                "price": t.get("price", 0),
                "amount": t.get("amount", 0),
                "reason": t.get("reason", "")
            })

        return {
            "is_running": self.is_running,
            "smart_mode": self.smart_mode,
            "strategy": self.strategy_name,
            "buy_threshold": self.buy_threshold,
            "sell_threshold": self.sell_threshold,
            "watch_list": self.watch_list,
            "interval_seconds": self.interval,
            "dry_run": config.DRY_RUN,
            "stop_loss_pct": self.risk.stop_loss_pct,
            "take_profit_pct": self.risk.take_profit_pct,
            "max_positions": self.max_positions,
            "cooldown_minutes": self.cooldown_minutes,
            "cycle_count": self._cycle_count,
            "last_cycle": st.get("timestamp", "없음"),
            "last_actions": st.get("actions", []),
            "last_analysis": analyses,
            "recent_trades": trades,
        }