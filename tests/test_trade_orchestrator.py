# -*- coding: utf-8 -*-
"""TradeOrchestrator 단위 테스트 — 승인 게이트, 리스크 판정, 만료 정리."""

import time
from unittest.mock import AsyncMock

import pytest

from jarvis_features.trade_orchestrator import (
    TradeOrchestrator,
    ApprovalStatus,
    AUTO_APPROVE_THRESHOLD_KRW,
)


@pytest.fixture
def orchestrator():
    return TradeOrchestrator(execute_fn=AsyncMock(return_value="OK"))


class TestAutoApproveUnderThreshold:
    def test_small_amount_auto_approved(self, orchestrator):
        req = orchestrator.create_request("buy", "BTC", 10_000)
        assert req.status == ApprovalStatus.AUTO_APPROVED
        assert req.needs_approval is False

    def test_exact_threshold_auto_approved(self, orchestrator):
        req = orchestrator.create_request("buy", "ETH", AUTO_APPROVE_THRESHOLD_KRW)
        assert req.needs_approval is False


class TestManualApproveOverThreshold:
    def test_large_amount_pending(self, orchestrator):
        req = orchestrator.create_request("buy", "BTC", 100_000)
        assert req.status == ApprovalStatus.PENDING
        assert req.needs_approval is True


class TestRiskAssessmentLevels:
    def test_low_risk(self, orchestrator):
        req = orchestrator.create_request("buy", "BTC", 10_000)
        assert req.risk_level == "low"

    def test_normal_risk(self, orchestrator):
        req = orchestrator.create_request("buy", "BTC", 200_000)
        assert req.risk_level == "normal"

    def test_high_risk(self, orchestrator):
        req = orchestrator.create_request("buy", "BTC", 600_000)
        assert req.risk_level == "high"

    def test_critical_risk(self, orchestrator):
        req = orchestrator.create_request("buy", "BTC", 2_000_000)
        assert req.risk_level == "critical"


class TestApproveChangesStatus:
    def test_approve_pending(self, orchestrator):
        req = orchestrator.create_request("buy", "BTC", 100_000)
        assert req.status == ApprovalStatus.PENDING
        ok = orchestrator.approve(req.request_id)
        assert ok is True
        assert req.status == ApprovalStatus.APPROVED

    def test_approve_nonexistent_returns_false(self, orchestrator):
        ok = orchestrator.approve("nonexistent-id")
        assert ok is False


class TestRejectChangesStatus:
    def test_reject_pending(self, orchestrator):
        req = orchestrator.create_request("sell", "ETH", 100_000)
        ok = orchestrator.reject(req.request_id, "사용자 취소")
        assert ok is True
        assert req.status == ApprovalStatus.REJECTED

    def test_reject_already_approved_fails(self, orchestrator):
        req = orchestrator.create_request("buy", "BTC", 100_000)
        orchestrator.approve(req.request_id)
        ok = orchestrator.reject(req.request_id)
        assert ok is False


class TestCleanupExpired:
    def test_expired_request_cleaned(self, orchestrator):
        req = orchestrator.create_request("buy", "BTC", 100_000)
        # 강제 만료
        req.created_at = time.time() - 999
        req.timeout_seconds = 1
        orchestrator.cleanup_expired()
        assert req.status == ApprovalStatus.EXPIRED
