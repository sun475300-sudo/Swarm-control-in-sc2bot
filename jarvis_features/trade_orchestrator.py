# -*- coding: utf-8 -*-
"""
Trade Orchestrator - 거래 승인 파이프라인

claude_skills의 human-in-the-loop 패턴 적용:
- 거래 요청 → 미리보기 생성 → 사용자 승인 대기 → 실행/취소
- 금액 기반 자동 승인 임계값 (소액은 자동, 고액은 확인 필요)
- 승인 타임아웃 시 자동 취소
- 모든 거래 결정을 로그에 기록

사용법:
    orchestrator = TradeOrchestrator(notify_fn=discord_notify)

    # 거래 요청 생성
    request = orchestrator.create_request("buy", "BTC", 100000)

    # 사용자 승인 대기 (Discord 버튼 등)
    if request.needs_approval:
        # 승인 메시지 전송 → 사용자 반응 대기
        ...
        orchestrator.approve(request.request_id)  # 또는 reject()

    # 실행
    result = await orchestrator.execute(request.request_id)
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("jarvis.trade_orchestrator")


class TradeAction(Enum):
    BUY = "buy"
    SELL = "sell"
    AUTO_BUY = "auto_buy"
    AUTO_SELL = "auto_sell"


class ApprovalStatus(Enum):
    PENDING = "pending"          # 승인 대기
    APPROVED = "approved"        # 승인됨
    REJECTED = "rejected"        # 거부됨
    AUTO_APPROVED = "auto_approved"  # 소액 자동 승인
    EXPIRED = "expired"          # 타임아웃 만료
    EXECUTED = "executed"        # 실행 완료
    FAILED = "failed"            # 실행 실패


# ── 승인 정책 설정 ──

# 자동 승인 임계값 (원) — 이 금액 이하는 확인 없이 실행
AUTO_APPROVE_THRESHOLD_KRW = 50_000  # 5만원

# 고액 거래 경고 임계값 (원)
HIGH_VALUE_THRESHOLD_KRW = 500_000  # 50만원

# 승인 대기 타임아웃 (초)
APPROVAL_TIMEOUT_SECONDS = 300  # 5분

# 자동매매 승인 대기 타임아웃 (초) — 자동매매는 더 짧게
AUTO_TRADE_TIMEOUT_SECONDS = 120  # 2분

# 보류 요청 최대 수 (메모리 관리)
MAX_PENDING_REQUESTS = 50


@dataclass
class TradeRequest:
    """거래 승인 요청"""
    request_id: str
    action: TradeAction
    symbol: str                # "BTC", "ETH" 등
    amount_krw: float          # 거래 금액 (원)
    sell_percent: float = 100.0  # 매도 비율 (매도 시)
    status: ApprovalStatus = ApprovalStatus.PENDING
    needs_approval: bool = True
    risk_level: str = "normal"  # "low", "normal", "high", "critical"
    analysis_summary: str = ""  # 분석 요약 (auto_trade 시)
    created_at: float = 0.0
    resolved_at: float = 0.0
    executed_result: str = ""
    user_id: str = ""
    timeout_seconds: float = APPROVAL_TIMEOUT_SECONDS

    @property
    def market(self) -> str:
        """Upbit 마켓 코드"""
        s = self.symbol.upper()
        return s if s.startswith("KRW-") else f"KRW-{s}"

    @property
    def is_expired(self) -> bool:
        if self.status != ApprovalStatus.PENDING:
            return False
        return (time.time() - self.created_at) > self.timeout_seconds

    def preview_text(self) -> str:
        """사용자에게 보여줄 거래 미리보기"""
        action_kr = {
            TradeAction.BUY: "매수",
            TradeAction.SELL: "매도",
            TradeAction.AUTO_BUY: "자동매수",
            TradeAction.AUTO_SELL: "자동매도",
        }
        action_str = action_kr.get(self.action, str(self.action.value))
        risk_emoji = {"low": "", "normal": "", "high": " **[주의]**", "critical": " **[위험]**"}

        lines = [
            f"**{action_str} 승인 요청**{risk_emoji.get(self.risk_level, '')}",
            f"  코인: {self.symbol}",
        ]

        if self.action in (TradeAction.BUY, TradeAction.AUTO_BUY):
            lines.append(f"  금액: {self.amount_krw:,.0f}원")
        else:
            lines.append(f"  매도 비율: {self.sell_percent:.0f}%")

        if self.analysis_summary:
            lines.append(f"  분석: {self.analysis_summary}")

        lines.append(f"  요청 ID: `{self.request_id[:8]}`")
        timeout_min = self.timeout_seconds / 60
        lines.append(f"  자동 취소: {timeout_min:.0f}분 후")

        return "\n".join(lines)


class TradeOrchestrator:
    """
    거래 승인 오케스트레이터

    human-in-the-loop 패턴:
    - create_request(): 거래 요청 생성 + 승인 필요 여부 판단
    - approve() / reject(): 사용자 승인/거부
    - execute(): 승인된 거래 실행
    - cleanup_expired(): 만료된 요청 정리
    """

    def __init__(
        self,
        execute_fn: Optional[Callable] = None,
        notify_fn: Optional[Callable] = None,
        auto_approve_threshold: float = AUTO_APPROVE_THRESHOLD_KRW,
    ):
        """
        Args:
            execute_fn: async fn(action, symbol, amount_krw, sell_percent) → result str
            notify_fn: async fn(user_id, message) → None (Discord 알림)
            auto_approve_threshold: 자동 승인 금액 임계값 (원)
        """
        self._execute_fn = execute_fn
        self._notify_fn = notify_fn
        self._auto_approve_threshold = auto_approve_threshold
        self._requests: Dict[str, TradeRequest] = {}
        self._history: List[Dict] = []  # 최근 100건 기록

    def create_request(
        self,
        action: str,
        symbol: str,
        amount_krw: float = 0,
        sell_percent: float = 100.0,
        user_id: str = "",
        analysis_summary: str = "",
        is_auto: bool = False,
    ) -> TradeRequest:
        """
        거래 승인 요청 생성.

        금액 기반 자동 승인 판단:
        - amount_krw <= auto_approve_threshold: 자동 승인
        - amount_krw > high_value_threshold: 고위험 표시
        - 자동매매: 별도 타임아웃 적용

        Args:
            action: "buy" or "sell"
            symbol: 코인 심볼
            amount_krw: 거래 금액 (매수 시)
            sell_percent: 매도 비율 (매도 시)
            user_id: 요청 사용자 ID
            analysis_summary: 분석 요약 (자동매매 시)
            is_auto: 자동매매 여부

        Returns:
            TradeRequest (needs_approval=False이면 바로 실행 가능)
        """
        # 보류 요청 정리
        self.cleanup_expired()

        request_id = str(uuid.uuid4())

        # TradeAction 결정
        if action == "buy":
            trade_action = TradeAction.AUTO_BUY if is_auto else TradeAction.BUY
        else:
            trade_action = TradeAction.AUTO_SELL if is_auto else TradeAction.SELL

        # 리스크 레벨 판단
        risk_level = self._assess_risk(amount_krw, is_auto)

        # 승인 필요 여부 판단
        needs_approval = amount_krw > self._auto_approve_threshold
        timeout = AUTO_TRADE_TIMEOUT_SECONDS if is_auto else APPROVAL_TIMEOUT_SECONDS

        # 자동 승인 상태 설정
        status = ApprovalStatus.PENDING
        if not needs_approval:
            status = ApprovalStatus.AUTO_APPROVED

        req = TradeRequest(
            request_id=request_id,
            action=trade_action,
            symbol=symbol.upper().replace("KRW-", ""),
            amount_krw=amount_krw,
            sell_percent=sell_percent,
            status=status,
            needs_approval=needs_approval,
            risk_level=risk_level,
            analysis_summary=analysis_summary,
            created_at=time.time(),
            user_id=user_id,
            timeout_seconds=timeout,
        )

        self._requests[request_id] = req

        logger.info(
            f"[TRADE_ORCH] Request created: {request_id[:8]} "
            f"{trade_action.value} {symbol} {amount_krw:,.0f}원 "
            f"(approval={'required' if needs_approval else 'auto'}, "
            f"risk={risk_level})"
        )

        return req

    def approve(self, request_id: str) -> bool:
        """거래 요청 승인"""
        req = self._requests.get(request_id)
        if not req:
            logger.warning(f"[TRADE_ORCH] Approve failed: request {request_id[:8]} not found")
            return False

        if req.is_expired:
            req.status = ApprovalStatus.EXPIRED
            req.resolved_at = time.time()
            logger.info(f"[TRADE_ORCH] Request {request_id[:8]} expired before approval")
            return False

        if req.status != ApprovalStatus.PENDING:
            logger.warning(f"[TRADE_ORCH] Request {request_id[:8]} already {req.status.value}")
            return False

        req.status = ApprovalStatus.APPROVED
        req.resolved_at = time.time()
        logger.info(f"[TRADE_ORCH] Request {request_id[:8]} APPROVED")
        return True

    def reject(self, request_id: str, reason: str = "") -> bool:
        """거래 요청 거부"""
        req = self._requests.get(request_id)
        if not req:
            return False

        if req.status != ApprovalStatus.PENDING:
            return False

        req.status = ApprovalStatus.REJECTED
        req.resolved_at = time.time()
        logger.info(f"[TRADE_ORCH] Request {request_id[:8]} REJECTED ({reason})")
        return True

    async def execute(self, request_id: str) -> str:
        """
        승인된 거래 실행.

        APPROVED 또는 AUTO_APPROVED 상태인 요청만 실행 가능.

        Returns:
            실행 결과 문자열
        """
        req = self._requests.get(request_id)
        if not req:
            return "거래 요청을 찾을 수 없습니다."

        # 만료 확인
        if req.is_expired:
            req.status = ApprovalStatus.EXPIRED
            req.resolved_at = time.time()
            self._record_history(req)
            return f"거래 요청이 만료되었습니다 ({req.timeout_seconds / 60:.0f}분 초과)."

        # 승인 상태 확인
        if req.status not in (ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED):
            return f"거래가 승인되지 않았습니다 (상태: {req.status.value})."

        # 실행
        if not self._execute_fn:
            req.status = ApprovalStatus.FAILED
            req.executed_result = "실행 함수가 설정되지 않았습니다."
            self._record_history(req)
            return req.executed_result

        try:
            result = await self._execute_fn(
                action=req.action.value.replace("auto_", ""),
                symbol=req.market,
                amount_krw=req.amount_krw,
                sell_percent=req.sell_percent,
            )
            req.status = ApprovalStatus.EXECUTED
            req.executed_result = str(result) if result else "실행 완료"
            req.resolved_at = time.time()

            logger.info(
                f"[TRADE_ORCH] Request {request_id[:8]} EXECUTED: {req.executed_result[:100]}"
            )

            # 실행 성공 알림
            if self._notify_fn and req.user_id:
                try:
                    await self._notify_fn(
                        req.user_id,
                        f"거래 실행 완료: {req.action.value} {req.symbol} "
                        f"({req.amount_krw:,.0f}원)\n결과: {req.executed_result[:200]}",
                    )
                except Exception:
                    pass

        except Exception as e:
            req.status = ApprovalStatus.FAILED
            req.executed_result = f"실행 오류: {e}"
            req.resolved_at = time.time()
            logger.error(f"[TRADE_ORCH] Request {request_id[:8]} FAILED: {e}")

        self._record_history(req)
        return req.executed_result

    def get_pending_requests(self, user_id: str = "") -> List[TradeRequest]:
        """보류 중인 거래 요청 조회"""
        self.cleanup_expired()
        pending = [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING
            and (not user_id or r.user_id == user_id)
        ]
        return sorted(pending, key=lambda r: r.created_at)

    def cleanup_expired(self):
        """만료된 요청 정리"""
        expired_ids = []
        for rid, req in self._requests.items():
            if req.is_expired:
                req.status = ApprovalStatus.EXPIRED
                req.resolved_at = time.time()
                self._record_history(req)
                expired_ids.append(rid)

        for rid in expired_ids:
            del self._requests[rid]

        # 전체 크기 제한
        if len(self._requests) > MAX_PENDING_REQUESTS:
            oldest = sorted(self._requests.values(), key=lambda r: r.created_at)
            for req in oldest[:len(self._requests) - MAX_PENDING_REQUESTS]:
                if req.status == ApprovalStatus.PENDING:
                    req.status = ApprovalStatus.EXPIRED
                    self._record_history(req)
                del self._requests[req.request_id]

    def get_stats(self) -> dict:
        """오케스트레이터 통계"""
        status_counts = {}
        for req in self._requests.values():
            status_counts[req.status.value] = status_counts.get(req.status.value, 0) + 1

        history_counts = {}
        for entry in self._history:
            s = entry.get("status", "unknown")
            history_counts[s] = history_counts.get(s, 0) + 1

        return {
            "active_requests": len(self._requests),
            "active_status": status_counts,
            "history_total": len(self._history),
            "history_status": history_counts,
            "auto_approve_threshold": self._auto_approve_threshold,
        }

    def _assess_risk(self, amount_krw: float, is_auto: bool) -> str:
        """거래 리스크 레벨 평가"""
        if amount_krw <= self._auto_approve_threshold:
            return "low"
        if amount_krw <= HIGH_VALUE_THRESHOLD_KRW:
            return "normal"
        if amount_krw <= 1_000_000:
            return "high"
        return "critical"

    def _record_history(self, req: TradeRequest):
        """완료된 요청을 히스토리에 기록"""
        self._history.append({
            "request_id": req.request_id[:8],
            "action": req.action.value,
            "symbol": req.symbol,
            "amount_krw": req.amount_krw,
            "status": req.status.value,
            "risk_level": req.risk_level,
            "created_at": req.created_at,
            "resolved_at": req.resolved_at,
        })
        # 최근 100건만 유지
        if len(self._history) > 100:
            self._history = self._history[-100:]
