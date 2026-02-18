"""
Auto Trader Engine
- 전략 기반 자동 매매 루프
- 손절/익절 자동 관리
- 포트폴리오 스냅샷 자동 기록
"""
import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Optional

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
        mode = "스마트 분석" if self.smart_mode else self.strategy_name
        budget_msg = f", 예산: {self.max_budget:,.0f}원" if self.max_budget > 0 else ""
        return f"자동매매 시작 (모드: {mode}, DRY_RUN: {config.DRY_RUN}{budget_msg})"

    def stop(self):
        """자동매매 중지"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
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