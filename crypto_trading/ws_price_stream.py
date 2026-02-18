"""
WebSocket 실시간 가격 스트리밍 (#51)
- pyupbit WebSocket API를 활용한 실시간 시세 수신
- 콜백 기반 가격 업데이트 알림
- 다중 티커 동시 구독 지원
- 자동 재연결 메커니즘
"""
import json
import logging
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger("crypto.ws_stream")


class PriceStreamManager:
    """
    WebSocket 실시간 가격 스트리밍 매니저

    pyupbit의 WebSocketManager를 활용하여 실시간 시세를 수신하고,
    등록된 콜백 함수들에게 가격 업데이트를 전달한다.
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._latest_prices: dict[str, dict] = {}
        self._ws_thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._tickers: list[str] = []
        self._lock = threading.Lock()
        self._reconnect_delay: float = 5.0
        self._max_reconnect_delay: float = 60.0

    def subscribe(self, ticker: str, callback: Callable[[dict], None]) -> None:
        """
        특정 티커의 가격 업데이트 구독

        Args:
            ticker: 코인 티커 (예: "KRW-BTC")
            callback: 가격 업데이트 시 호출될 콜백 함수.
                      dict 매개변수: {"ticker", "price", "volume", "timestamp", ...}
        """
        ticker = ticker.upper()
        with self._lock:
            self._subscribers[ticker].append(callback)
            if ticker not in self._tickers:
                self._tickers.append(ticker)
        logger.info(f"가격 스트림 구독: {ticker} (콜백 {len(self._subscribers[ticker])}개)")

    def unsubscribe(self, ticker: str, callback: Callable = None) -> None:
        """
        구독 해제

        Args:
            ticker: 코인 티커
            callback: 특정 콜백만 해제. None이면 해당 티커 전체 해제.
        """
        ticker = ticker.upper()
        with self._lock:
            if callback is None:
                self._subscribers.pop(ticker, None)
            else:
                subs = self._subscribers.get(ticker, [])
                self._subscribers[ticker] = [cb for cb in subs if cb != callback]
                if not self._subscribers[ticker]:
                    self._subscribers.pop(ticker, None)

            # 구독자가 없는 티커 제거
            if ticker not in self._subscribers:
                self._tickers = [t for t in self._tickers if t != ticker]
        logger.info(f"가격 스트림 구독 해제: {ticker}")

    def start(self, tickers: list[str] = None) -> str:
        """
        WebSocket 스트리밍 시작

        Args:
            tickers: 구독할 티커 목록. None이면 이미 등록된 티커 사용.

        Returns:
            시작 상태 메시지
        """
        if self._is_running:
            return "이미 실행 중입니다."

        if tickers:
            with self._lock:
                for t in tickers:
                    t = t.upper()
                    if t not in self._tickers:
                        self._tickers.append(t)

        if not self._tickers:
            return "구독할 티커가 없습니다. subscribe()를 먼저 호출하세요."

        self._is_running = True
        self._ws_thread = threading.Thread(
            target=self._stream_loop,
            daemon=True,
            name="ws_price_stream"
        )
        self._ws_thread.start()

        tickers_str = ", ".join(self._tickers)
        logger.info(f"WebSocket 가격 스트리밍 시작: {tickers_str}")
        return f"실시간 가격 스트리밍 시작: {tickers_str}"

    def stop(self) -> str:
        """WebSocket 스트리밍 중지"""
        self._is_running = False
        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=10)
            self._ws_thread = None
        logger.info("WebSocket 가격 스트리밍 중지")
        return "실시간 가격 스트리밍 중지됨"

    def get_latest_price(self, ticker: str) -> Optional[dict]:
        """
        특정 티커의 최신 가격 정보 조회

        Args:
            ticker: 코인 티커

        Returns:
            최신 가격 정보 dict 또는 None
        """
        return self._latest_prices.get(ticker.upper())

    def get_all_latest_prices(self) -> dict:
        """모든 구독 중인 티커의 최신 가격 반환"""
        return dict(self._latest_prices)

    def get_status(self) -> dict:
        """스트리밍 상태 조회"""
        return {
            "is_running": self._is_running,
            "subscribed_tickers": list(self._tickers),
            "subscriber_counts": {
                t: len(cbs) for t, cbs in self._subscribers.items()
            },
            "latest_prices": {
                t: info.get("price", 0) for t, info in self._latest_prices.items()
            },
        }

    def _stream_loop(self):
        """WebSocket 메인 스트리밍 루프 (재연결 포함)"""
        reconnect_delay = self._reconnect_delay

        while self._is_running:
            try:
                self._run_websocket()
            except Exception as e:
                if not self._is_running:
                    break
                logger.error(f"WebSocket 오류: {e}. {reconnect_delay:.0f}초 후 재연결...")
                time.sleep(reconnect_delay)
                # 지수 백오프
                reconnect_delay = min(reconnect_delay * 2, self._max_reconnect_delay)
            else:
                # 정상 종료 시 딜레이 리셋
                reconnect_delay = self._reconnect_delay

    def _run_websocket(self):
        """pyupbit WebSocket을 통한 실시간 데이터 수신"""
        try:
            from pyupbit import WebSocketManager
        except ImportError:
            logger.error("pyupbit WebSocketManager를 import할 수 없습니다. pyupbit 버전을 확인하세요.")
            # Fallback: REST polling
            self._run_polling_fallback()
            return

        with self._lock:
            tickers = list(self._tickers)

        if not tickers:
            logger.warning("구독 티커 없음 - 스트리밍 대기")
            time.sleep(5)
            return

        wm = WebSocketManager("ticker", tickers)

        try:
            logger.info(f"WebSocket 연결 시작: {tickers}")
            while self._is_running:
                data = wm.get()
                if data is None:
                    time.sleep(0.1)
                    continue

                self._process_ws_data(data)
        finally:
            try:
                wm.terminate()
            except Exception:
                pass

    def _run_polling_fallback(self):
        """WebSocket 사용 불가 시 REST API 폴링 대안"""
        import pyupbit

        logger.info("WebSocket 대안: REST 폴링 모드 시작")

        while self._is_running:
            with self._lock:
                tickers = list(self._tickers)

            if not tickers:
                time.sleep(5)
                continue

            try:
                prices = pyupbit.get_current_price(tickers)
                if isinstance(prices, dict):
                    for ticker, price in prices.items():
                        if price is not None:
                            price_info = {
                                "ticker": ticker,
                                "price": float(price),
                                "timestamp": datetime.now().isoformat(),
                                "source": "polling",
                            }
                            self._latest_prices[ticker] = price_info
                            self._notify_subscribers(ticker, price_info)
                elif isinstance(prices, (int, float)) and len(tickers) == 1:
                    ticker = tickers[0]
                    price_info = {
                        "ticker": ticker,
                        "price": float(prices),
                        "timestamp": datetime.now().isoformat(),
                        "source": "polling",
                    }
                    self._latest_prices[ticker] = price_info
                    self._notify_subscribers(ticker, price_info)
            except Exception as e:
                logger.error(f"폴링 오류: {e}")

            time.sleep(1)  # 1초 간격 폴링

    def _process_ws_data(self, data: dict):
        """WebSocket 데이터 처리"""
        if not isinstance(data, dict):
            return

        ticker = data.get("code", "")
        if not ticker:
            return

        price_info = {
            "ticker": ticker,
            "price": float(data.get("trade_price", 0)),
            "opening_price": float(data.get("opening_price", 0)),
            "high_price": float(data.get("high_price", 0)),
            "low_price": float(data.get("low_price", 0)),
            "prev_closing_price": float(data.get("prev_closing_price", 0)),
            "trade_volume": float(data.get("trade_volume", 0)),
            "acc_trade_volume_24h": float(data.get("acc_trade_volume_24h", 0)),
            "acc_trade_price_24h": float(data.get("acc_trade_price_24h", 0)),
            "signed_change_rate": float(data.get("signed_change_rate", 0)),
            "change": data.get("change", ""),
            "timestamp": datetime.now().isoformat(),
            "source": "websocket",
        }

        self._latest_prices[ticker] = price_info
        self._notify_subscribers(ticker, price_info)

    def _notify_subscribers(self, ticker: str, price_info: dict):
        """구독자들에게 가격 업데이트 알림"""
        with self._lock:
            callbacks = list(self._subscribers.get(ticker, []))

        for callback in callbacks:
            try:
                callback(price_info)
            except Exception as e:
                logger.error(f"콜백 실행 오류 ({ticker}): {e}")
