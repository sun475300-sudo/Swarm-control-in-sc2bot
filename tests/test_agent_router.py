# -*- coding: utf-8 -*-
"""AgentRouter 단위 테스트 — 키워드 라우팅, 점수 정규화, 신뢰도 임계값 검증."""

import pytest
from jarvis_features.agent_router import AgentRouter, AgentDomain


@pytest.fixture
def router():
    return AgentRouter(memory_manager=None, tool_registry=None)


class TestKeywordRouting:
    """키워드 기반 도메인 분류 테스트."""

    def test_sc2_keyword_routing(self, router):
        decision = router.route("스타크래프트 저그 빌드오더 추천해줘")
        assert decision.domain == AgentDomain.SC2_GAMING
        assert decision.confidence > 0.5

    def test_crypto_keyword_routing(self, router):
        decision = router.route("비트코인 시세 알려줘")
        assert decision.domain == AgentDomain.CRYPTO_TRADING
        assert decision.confidence > 0.5

    def test_system_keyword_routing(self, router):
        decision = router.route("시스템 cpu 사용량 확인")
        assert decision.domain == AgentDomain.SYSTEM_ADMIN

    def test_briefing_keyword_routing(self, router):
        decision = router.route("모닝 브리핑 해줘")
        assert decision.domain == AgentDomain.DAILY_BRIEFING

    def test_empty_message_default(self, router):
        decision = router.route("")
        assert decision.domain == AgentDomain.GENERAL_CHAT

    def test_no_keyword_default(self, router):
        decision = router.route("안녕하세요 반갑습니다")
        assert decision.domain == AgentDomain.GENERAL_CHAT


class TestScoreNormalization:
    """B8: 도메인 크기 정규화 검증 — 작은 도메인이 불이익받지 않음."""

    def test_small_domain_not_penalized(self, router):
        """briefing(8키워드) 도메인이 SC2(25키워드)보다 키워드 수 때문에 불이익받지 않아야 함."""
        decision = router.route("브리핑 해줘")
        assert decision.domain == AgentDomain.DAILY_BRIEFING
        assert decision.confidence > 0.5


class TestConfidenceThreshold:
    """B9: 약한 단일 키워드 매치 필터링 검증."""

    def test_weak_single_keyword_filtered(self, router):
        """'게임'은 SC2의 약한 키워드 — 단독 사용 시 GENERAL_CHAT으로 빠져야 함."""
        decision = router.route("게임")
        # '게임'은 SC2 중간 신호이므로 confidence < 0.55면 GENERAL_CHAT
        assert decision.domain == AgentDomain.GENERAL_CHAT

    def test_strong_keywords_pass_threshold(self, router):
        """강한 키워드 여러 개 → 임계값 통과."""
        decision = router.route("sc2 저그 빌드오더")
        assert decision.domain == AgentDomain.SC2_GAMING
        assert decision.confidence >= 0.55


class TestRouterDisabled:
    """환경변수로 라우터 비활성화 시 항상 GENERAL_CHAT 반환."""

    def test_disabled_returns_general(self, monkeypatch):
        monkeypatch.setenv("JARVIS_AGENT_ROUTER", "0")
        router = AgentRouter()
        decision = router.route("비트코인 매수해줘")
        assert decision.domain == AgentDomain.GENERAL_CHAT
