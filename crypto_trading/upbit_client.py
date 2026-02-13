"""
Upbit API Client Wrapper
- pyupbit 라이브러리 위에 안전한 래핑 레이어
- 에러 핸들링, 로깅, rate-limit 보호
"""
import time
import logging
from typing import Optional
import pyupbit
from pyupbit import Upbit
from . import config

logger = logging.getLogger("crypto.upbit_client")


class UpbitClient:
    """Upbit 거래소 API 클라이언트"""

    def __init__(self, access_key: str = "", secret_key: str = ""):
        self.access_key = access_key or config.UPBIT_ACCESS_KEY
        self.secret_key = secret_key or config.UPBIT_SECRET_KEY
        self._upbit: Optional[Upbit] = None
        self._last_request_time = 0.0
        self._min_interval = 0.12  # rate-limit 보호 (초)

    def _get_upbit(self) -> Upbit:
        """인증된 Upbit 인스턴스 (lazy init)"""
        if self._upbit is None:
            if not self.access_key or not self.secret_key:
                raise ValueError("Upbit API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
            self._upbit = Upbit(self.access_key, self.secret_key)
        return self._upbit

    def _throttle(self):
        """API 호출 간격 제어"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    # ─────────── 시세 조회 (공개 API) ───────────

    def get_tickers(self, fiat: str = "KRW") -> list:
        """KRW 마켓 전체 티커 목록"""
        self._throttle()
        tickers = pyupbit.get_tickers(fiat=fiat)
        return tickers or []

    def get_current_price(self, ticker: str) -> Optional[float]:
        """단일 코인 현재가 조회"""
        self._throttle()
        try:
            price = pyupbit.get_current_price(ticker)
            return float(price) if price else None
        except Exception as e:
            logger.error(f"시세 조회 실패 ({ticker}): {e}")
            return None

    def get_prices(self, tickers: list) -> dict:
        """복수 코인 현재가 조회"""
        self._throttle()
        try:
            prices = pyupbit.get_current_price(tickers)
            return prices if isinstance(prices, dict) else {}
        except Exception as e:
            logger.error(f"복수 시세 조회 실패: {e}")
            return {}

    def get_ohlcv(self, ticker: str, interval: str = "day", count: int = 200):
        """OHLCV 캔들 데이터 (DataFrame 반환)"""
        self._throttle()
        try:
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
            return df
        except Exception as e:
            logger.error(f"OHLCV 조회 실패 ({ticker}): {e}")
            return None

    def get_orderbook(self, ticker: str) -> Optional[dict]:
        """호가 정보 조회"""
        self._throttle()
        try:
            ob = pyupbit.get_orderbook(ticker)
            return ob
        except Exception as e:
            logger.error(f"호가 조회 실패 ({ticker}): {e}")
            return None

    # ─────────── 잔고 조회 (인증 필요) ───────────

    def get_balances(self) -> list:
        """전체 잔고 조회"""
        self._throttle()
        try:
            result = self._get_upbit().get_balances()
            if not result:
                logger.warning("잔고 조회 결과가 비어있음 - API 키 또는 네트워크 확인 필요")
            return result if result else []
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return []

    def get_balance(self, ticker: str = "KRW") -> float:
        """특정 코인/원화 잔고"""
        self._throttle()
        try:
            bal = self._get_upbit().get_balance(ticker)
            return float(bal) if bal else 0.0
        except Exception as e:
            logger.error(f"잔고 조회 실패 ({ticker}): {e}")
            return 0.0

    def get_avg_buy_price(self, ticker: str) -> float:
        """평균 매수가"""
        self._throttle()
        try:
            price = self._get_upbit().get_avg_buy_price(ticker)
            return float(price) if price else 0.0
        except Exception as e:
            logger.error(f"평균 매수가 조회 실패 ({ticker}): {e}")
            return 0.0

    def get_total_balance_krw(self) -> float:
        """총 보유 자산 KRW 환산 가치"""
        balances = self.get_balances()
        total = 0.0
        for b in balances:
            currency = b.get("currency", "")
            balance = float(b.get("balance", 0))
            locked = float(b.get("locked", 0))
            amount = balance + locked
            if amount <= 0:
                continue
            if currency == "KRW":
                total += amount
            else:
                ticker = f"KRW-{currency}"
                price = self.get_current_price(ticker)
                if price:
                    total += amount * price
        return total

    # ─────────── 주문 (인증 필요) ───────────

    def buy_market_order(self, ticker: str, krw_amount: float) -> Optional[dict]:
        """시장가 매수 (KRW 금액 지정)"""
        if config.DRY_RUN:
            logger.info(f"[DRY-RUN] 시장가 매수: {ticker} / {krw_amount:,.0f}원")
            return {"dry_run": True, "side": "bid", "ticker": ticker, "price": krw_amount}
        if krw_amount < config.MIN_ORDER_AMOUNT:
            logger.warning(f"최소 주문 금액 미달: {krw_amount} < {config.MIN_ORDER_AMOUNT}")
            return None
        self._throttle()
        try:
            result = self._get_upbit().buy_market_order(ticker, krw_amount)
            logger.info(f"시장가 매수 완료: {ticker} / {krw_amount:,.0f}원 → {result}")
            return result
        except Exception as e:
            logger.error(f"매수 실패 ({ticker}): {e}")
            return None

    def sell_market_order(self, ticker: str, volume: float) -> Optional[dict]:
        """시장가 매도 (수량 지정)"""
        if config.DRY_RUN:
            logger.info(f"[DRY-RUN] 시장가 매도: {ticker} / {volume}")
            return {"dry_run": True, "side": "ask", "ticker": ticker, "volume": volume}
        self._throttle()
        try:
            result = self._get_upbit().sell_market_order(ticker, volume)
            logger.info(f"시장가 매도 완료: {ticker} / {volume} → {result}")
            return result
        except Exception as e:
            logger.error(f"매도 실패 ({ticker}): {e}")
            return None

    def buy_limit_order(self, ticker: str, price: float, volume: float) -> Optional[dict]:
        """지정가 매수"""
        if config.DRY_RUN:
            logger.info(f"[DRY-RUN] 지정가 매수: {ticker} / {price:,.0f}원 x {volume}")
            return {"dry_run": True, "side": "bid", "ticker": ticker, "price": price, "volume": volume}
        self._throttle()
        try:
            return self._get_upbit().buy_limit_order(ticker, price, volume)
        except Exception as e:
            logger.error(f"지정가 매수 실패 ({ticker}): {e}")
            return None

    def sell_limit_order(self, ticker: str, price: float, volume: float) -> Optional[dict]:
        """지정가 매도"""
        if config.DRY_RUN:
            logger.info(f"[DRY-RUN] 지정가 매도: {ticker} / {price:,.0f}원 x {volume}")
            return {"dry_run": True, "side": "ask", "ticker": ticker, "price": price, "volume": volume}
        self._throttle()
        try:
            return self._get_upbit().sell_limit_order(ticker, price, volume)
        except Exception as e:
            logger.error(f"지정가 매도 실패 ({ticker}): {e}")
            return None

    def cancel_order(self, uuid: str) -> Optional[dict]:
        """주문 취소"""
        self._throttle()
        try:
            return self._get_upbit().cancel_order(uuid)
        except Exception as e:
            logger.error(f"주문 취소 실패 ({uuid}): {e}")
            return None

    def get_order(self, ticker_or_uuid: str, state: str = "wait") -> list:
        """주문 내역 조회"""
        self._throttle()
        try:
            return self._get_upbit().get_order(ticker_or_uuid, state=state)
        except Exception as e:
            logger.error(f"주문 조회 실패: {e}")
            return []