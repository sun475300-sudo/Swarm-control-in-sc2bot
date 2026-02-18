"""
Risk Manager
- 포지션 사이징 (총 자산 대비 비율)
- 손절/익절 관리
- 최대 투자 한도 제어
"""
import logging
from typing import Optional
from . import config

logger = logging.getLogger("crypto.risk_manager")


class RiskManager:
    """리스크 관리자"""

    def __init__(
        self,
        max_single_order_ratio: float = config.MAX_SINGLE_ORDER_RATIO,
        max_total_investment_ratio: float = config.MAX_TOTAL_INVESTMENT_RATIO,
        stop_loss_pct: float = config.DEFAULT_STOP_LOSS_PCT,
        take_profit_pct: float = config.DEFAULT_TAKE_PROFIT_PCT,
    ):
        self.max_single_order_ratio = max_single_order_ratio
        self.max_total_investment_ratio = max_total_investment_ratio
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def calculate_order_amount(self, total_krw: float, signal_strength: float = 0.5) -> float:
        """
        주문 금액 산출
        - total_krw: 총 보유 원화
        - signal_strength: 0.0~1.0 (신호 강도에 따라 비율 조절)
        """
        base = total_krw * self.max_single_order_ratio
        amount = base * max(0.2, min(signal_strength, 1.0))
        amount = max(amount, config.MIN_ORDER_AMOUNT)
        # 총 투자 한도 초과 방지
        max_allowed = total_krw * self.max_total_investment_ratio
        amount = min(amount, max_allowed)
        return round(amount, 0)

    def should_stop_loss(self, avg_buy_price: float, current_price: float) -> bool:
        """손절 여부 판단"""
        if avg_buy_price <= 0:
            return False
        pnl_pct = ((current_price - avg_buy_price) / avg_buy_price) * 100
        if pnl_pct <= self.stop_loss_pct:
            logger.warning(f"손절 조건 충족: 수익률 {pnl_pct:.2f}% <= {self.stop_loss_pct}%")
            return True
        return False

    def should_take_profit(self, avg_buy_price: float, current_price: float) -> bool:
        """익절 여부 판단"""
        if avg_buy_price <= 0:
            return False
        pnl_pct = ((current_price - avg_buy_price) / avg_buy_price) * 100
        if pnl_pct >= self.take_profit_pct:
            logger.info(f"익절 조건 충족: 수익률 {pnl_pct:.2f}% >= {self.take_profit_pct}%")
            return True
        return False

    def check_position(self, avg_buy_price: float, current_price: float) -> Optional[str]:
        """
        보유 포지션 체크: 'stop_loss', 'take_profit', 또는 None
        """
        if self.should_stop_loss(avg_buy_price, current_price):
            return "stop_loss"
        if self.should_take_profit(avg_buy_price, current_price):
            return "take_profit"
        return None

    def validate_order(self, krw_balance: float, order_amount: float) -> tuple[bool, str]:
        """주문 유효성 검증"""
        if order_amount < config.MIN_ORDER_AMOUNT:
            return False, f"최소 주문 금액 미달: {order_amount:,.0f} < {config.MIN_ORDER_AMOUNT:,.0f}"
        if order_amount > krw_balance:
            return False, f"잔고 부족: 주문 {order_amount:,.0f} > 잔고 {krw_balance:,.0f}"
        # 1회 주문 한도: 잔고의 50% 또는 MIN_ORDER_AMOUNT 중 큰 값
        max_single = max(krw_balance * self.max_single_order_ratio * 2, config.MIN_ORDER_AMOUNT)
        if order_amount > max_single:
            return False, f"1회 주문 한도 초과: {order_amount:,.0f} > {max_single:,.0f}"
        return True, "OK"