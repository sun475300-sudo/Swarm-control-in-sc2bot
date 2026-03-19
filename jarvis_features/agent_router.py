# -*- coding: utf-8 -*-
"""
Agent Router - 도메인 기반 메시지 라우팅

claude_skills의 card-dispatcher 패턴을 적용한 지능형 라우터.
사용자 메시지를 분석하여 최적의 도메인/도구/모델 조합을 결정합니다.

동작 방식:
1. 키워드 fast-path: 명확한 키워드가 있으면 즉시 라우팅 (<1ms)
2. 복잡도 기반 모델 힌트: 메시지 길이/내용에 따라 haiku/sonnet/opus 추천
3. 도구 필터링: 도메인별 필요 도구만 시스템 프롬프트에 포함

사용법:
    router = AgentRouter(memory_manager, tool_registry)
    decision = router.route("BTC 시세 알려줘", user_id="123")
    # → RoutingDecision(domain=CRYPTO_TRADING, confidence=0.9, ...)
"""

import os
import re
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("jarvis.agent_router")


class AgentDomain(Enum):
    """에이전트 도메인 (메시지 분류 카테고리)"""
    SC2_GAMING = "sc2"
    CRYPTO_TRADING = "crypto"
    SYSTEM_ADMIN = "system"
    DAILY_BRIEFING = "briefing"
    PRODUCTIVITY = "productivity"
    PC_CONTROL = "pc_control"
    GENERAL_CHAT = "general"


@dataclass
class RoutingDecision:
    """라우팅 결정 결과"""
    domain: AgentDomain
    confidence: float           # 0.0 ~ 1.0
    role: str                   # system_prompts.py ROLE_PROMPTS 키
    tool_categories: List[str]  # TOOL_CATALOG 카테고리 필터
    model_hint: str             # "haiku" | "sonnet" | "opus"
    matched_keywords: List[str] = field(default_factory=list)


# ── 도메인별 키워드 정의 ──
# 한국어/영어 혼합, 가중치 순서 (앞쪽일수록 강한 신호)

DOMAIN_KEYWORDS: Dict[AgentDomain, List[str]] = {
    AgentDomain.SC2_GAMING: [
        # 강한 신호
        "sc2", "스타크래프트", "스타2", "starcraft",
        "전적", "리플레이", "래더", "ladder",
        "저그", "zerg", "프로토스", "protoss", "테란", "terran",
        "빌드오더", "빌드 오더", "build order",
        # 중간 신호
        "봇", "게임", "훈련", "대전", "매치", "경기",
        "뮤탈", "저글링", "바퀴", "히드라", "울트라",
        "해처리", "레어", "하이브",
    ],
    AgentDomain.CRYPTO_TRADING: [
        # 강한 신호
        "btc", "eth", "xrp", "비트코인", "이더리움", "리플",
        "코인", "시세", "매매", "매수", "매도",
        "포트폴리오", "portfolio",
        "업비트", "upbit", "binance", "바이낸스",
        # 중간 신호
        "자동매매", "auto_trade", "거래", "차트",
        "수익률", "손절", "익절", "RSI", "MACD",
        "김프", "김치프리미엄", "호가",
    ],
    AgentDomain.SYSTEM_ADMIN: [
        # 강한 신호
        "시스템", "system", "cpu", "gpu", "ram", "메모리",
        "프로세스", "process", "서버", "server",
        "ssh", "터미널", "terminal",
        "디스크", "disk", "네트워크", "network",
        # 중간 신호
        "파일", "폴더", "디렉토리", "경로",
        "로그", "모니터링", "상태",
    ],
    AgentDomain.DAILY_BRIEFING: [
        # 강한 신호
        "브리핑", "briefing", "모닝", "morning",
        # 중간 신호 (다른 도메인과 겹칠 수 있음)
        "오늘", "날씨", "뉴스", "운세",
    ],
    AgentDomain.PRODUCTIVITY: [
        # 강한 신호
        "일정", "캘린더", "calendar", "스케줄", "schedule",
        "메모", "노트", "note", "노션", "notion",
        "번역", "translate", "계산", "calculate",
        "이메일", "email",
        # 중간 신호
        "리마인더", "reminder", "알림", "할일", "todo",
    ],
    AgentDomain.PC_CONTROL: [
        # 강한 신호
        "마우스", "mouse", "키보드", "keyboard",
        "클릭", "click", "스크린샷", "screenshot",
        "화면", "screen", "캡처", "capture",
        # 중간 신호
        "프로그램 실행", "실행해", "열어줘",
    ],
}

# ── 도메인 → 도구 카테고리/역할/모델 매핑 ──

DOMAIN_CONFIG: Dict[AgentDomain, dict] = {
    AgentDomain.SC2_GAMING: {
        "role": "default",
        "tool_categories": ["sc2"],
        "model": "sonnet",
    },
    AgentDomain.CRYPTO_TRADING: {
        "role": "trader",
        "tool_categories": ["crypto"],
        "model": "sonnet",
    },
    AgentDomain.SYSTEM_ADMIN: {
        "role": "developer",
        "tool_categories": ["system", "agentic"],
        "model": "sonnet",
    },
    AgentDomain.DAILY_BRIEFING: {
        "role": "default",
        "tool_categories": ["info", "productivity"],
        "model": "haiku",
    },
    AgentDomain.PRODUCTIVITY: {
        "role": "default",
        "tool_categories": ["productivity", "info"],
        "model": "haiku",
    },
    AgentDomain.PC_CONTROL: {
        "role": "developer",
        "tool_categories": ["pc_control", "system"],
        "model": "sonnet",
    },
    AgentDomain.GENERAL_CHAT: {
        "role": "default",
        "tool_categories": None,  # 전체 도구 포함 (일반 대화에서도 도구 사용 가능)
        "model": "sonnet",
    },
}

# ── 복잡도 기반 모델 오버라이드 키워드 ──

COMPLEXITY_OPUS_KEYWORDS = [
    "분석해", "analyze", "코드", "code", "디버그", "debug",
    "전략", "strategy", "설계", "design", "리팩토링", "refactor",
    "비교해", "compare", "평가해", "evaluate",
]

COMPLEXITY_HAIKU_KEYWORDS = [
    "안녕", "hello", "hi", "감사", "thanks", "고마워",
    "뭐해", "ㅎㅇ", "ㅋㅋ", "네", "응",
]


class AgentRouter:
    """
    도메인 기반 메시지 라우터

    card-dispatcher 패턴:
    - 명확한 키워드 → 즉시 라우팅
    - 애매한 메시지 → GENERAL_CHAT 기본값
    - 라우팅 기록을 memory_manager에 저장
    - tool_registry에서 도구 성공률 참조 (향후)
    """

    def __init__(self, memory_manager=None, tool_registry=None):
        self.memory = memory_manager
        self.tool_registry = tool_registry
        # P2-16: 스레드 안전성 — asyncio 단일 스레드 이벤트 루프에서만 사용.
        # _routing_count, _domain_stats는 async 컨텍스트 내에서만 접근되므로 별도 Lock 불필요.
        self._routing_count = 0
        self._domain_stats: Dict[str, int] = {}

        # 환경변수로 라우터 비활성화 가능
        self.enabled = os.environ.get("JARVIS_AGENT_ROUTER", "1") != "0"

        if self.enabled:
            logger.info("[AGENT_ROUTER] AgentRouter initialized (enabled)")
        else:
            logger.info("[AGENT_ROUTER] AgentRouter disabled by JARVIS_AGENT_ROUTER=0")

    def route(self, message: str, user_id: str = "", has_image: bool = False) -> RoutingDecision:
        """
        메시지를 분석하여 최적 도메인으로 라우팅.

        Args:
            message: 사용자 메시지
            user_id: 사용자 ID (라우팅 기록용)
            has_image: 이미지 첨부파일 존재 여부

        Returns:
            RoutingDecision with domain, confidence, role, tool_categories, model_hint
        """
        if not self.enabled:
            return self._default_decision()

        start = time.perf_counter()

        # 0단계: 이미지 첨부 시 — 강한 도메인 신호가 없으면 GENERAL_CHAT 강제
        # 이미지 분석은 전체 도구 + 범용 역할이 필요
        if has_image:
            keyword_decision = self._keyword_classify(message)
            # 이미지+강한 도메인 신호(confidence >= 0.7)가 아니면 범용으로 라우팅
            if keyword_decision.confidence < 0.7 or keyword_decision.domain == AgentDomain.GENERAL_CHAT:
                decision = self._default_decision()
                decision.matched_keywords = ["[image_attachment]"]
                decision = self._adjust_model_hint(message, decision)
                # 통계 기록
                elapsed_ms = (time.perf_counter() - start) * 1000
                self._routing_count += 1
                domain_key = decision.domain.value
                self._domain_stats[domain_key] = self._domain_stats.get(domain_key, 0) + 1
                logger.info(
                    f"[AGENT_ROUTER] '{message[:50]}' [+image] → GENERAL_CHAT "
                    f"(image override, {elapsed_ms:.1f}ms)"
                )
                return decision
            # 강한 도메인 신호가 있으면 해당 도메인 유지 (예: 차트 이미지 + "코인" 언급)
            decision = keyword_decision
        else:
            # 1단계: 키워드 fast-path
            decision = self._keyword_classify(message)

        # 2단계: 복잡도 기반 모델 힌트 조정
        decision = self._adjust_model_hint(message, decision)

        # 통계 기록
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._routing_count += 1
        domain_key = decision.domain.value
        self._domain_stats[domain_key] = self._domain_stats.get(domain_key, 0) + 1

        logger.info(
            f"[AGENT_ROUTER] '{message[:50]}' → {decision.domain.name} "
            f"(conf={decision.confidence:.2f}, model={decision.model_hint}, "
            f"keywords={decision.matched_keywords}, {elapsed_ms:.1f}ms)"
        )

        # 메모리에 라우팅 기록 (향후 학습용)
        if self.memory and user_id:
            try:
                self.memory.update_user_memory(
                    user_id, "last_domain", domain_key
                )
            except Exception:
                pass

        return decision

    def _keyword_classify(self, message: str) -> RoutingDecision:
        """키워드 매칭으로 도메인 분류"""
        msg_lower = message.lower().strip()

        # 각 도메인별 매칭 점수 계산
        scores: List[Tuple[AgentDomain, float, List[str]]] = []

        for domain, keywords in DOMAIN_KEYWORDS.items():
            matched = []
            raw_score = 0.0

            for i, kw in enumerate(keywords):
                if kw.lower() in msg_lower:
                    matched.append(kw)
                    # 앞쪽 키워드일수록 높은 가중치 (강한 신호)
                    weight = 1.0 if i < len(keywords) * 0.4 else 0.5
                    raw_score += weight

            if matched:
                # B8: 도메인 크기 정규화 — 키워드 수가 적은 도메인이 불이익받지 않도록
                normalized = raw_score / max(len(keywords), 1) * 10
                scores.append((domain, normalized, matched))

        if not scores:
            return self._default_decision()

        # 최고 점수 도메인 선택
        scores.sort(key=lambda x: x[1], reverse=True)
        best_domain, best_score, best_keywords = scores[0]

        # 신뢰도 계산: 1위와 2위 점수 차이 기반
        if len(scores) >= 2:
            gap = best_score - scores[1][1]
            confidence = min(0.95, 0.5 + gap * 0.15)
        else:
            confidence = min(0.95, 0.5 + best_score * 0.15)

        # B9: 신뢰도가 너무 낮으면 GENERAL_CHAT (0.4 → 0.55: 약한 단일 키워드 매치 방지)
        if confidence < 0.55:
            return self._default_decision()

        config = DOMAIN_CONFIG[best_domain]
        return RoutingDecision(
            domain=best_domain,
            confidence=confidence,
            role=config["role"],
            tool_categories=config["tool_categories"],
            model_hint=config["model"],
            matched_keywords=best_keywords,
        )

    def _adjust_model_hint(
        self, message: str, decision: RoutingDecision
    ) -> RoutingDecision:
        """메시지 복잡도에 따른 모델 힌트 조정"""
        msg_lower = message.lower()

        # 복잡한 분석 요청 → opus로 업그레이드
        if any(kw in msg_lower for kw in COMPLEXITY_OPUS_KEYWORDS):
            if len(message) > 100:
                decision.model_hint = "opus"
                return decision

        # 매우 긴 메시지 → opus
        if len(message) > 500:
            decision.model_hint = "opus"
            return decision

        # 짧은 인사/감탄 → haiku로 다운그레이드
        if len(message) < 30:
            if any(kw in msg_lower for kw in COMPLEXITY_HAIKU_KEYWORDS):
                decision.model_hint = "haiku"
                return decision

        return decision

    def _default_decision(self) -> RoutingDecision:
        """기본 라우팅 (GENERAL_CHAT)"""
        config = DOMAIN_CONFIG[AgentDomain.GENERAL_CHAT]
        return RoutingDecision(
            domain=AgentDomain.GENERAL_CHAT,
            confidence=0.3,
            role=config["role"],
            tool_categories=config["tool_categories"],
            model_hint=config["model"],
            matched_keywords=[],
        )

    def get_stats(self) -> dict:
        """라우터 통계 반환"""
        return {
            "enabled": self.enabled,
            "total_routes": self._routing_count,
            "domain_distribution": dict(self._domain_stats),
        }
