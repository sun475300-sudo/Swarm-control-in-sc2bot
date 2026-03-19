# -*- coding: utf-8 -*-
"""
Model Selector - 지능형 모델 선택 엔진

claude_skills의 specialist-chain 패턴 적용:
- AgentRouter의 model_hint를 받아 구체적 모델 ID와 폴백 순서 결정
- 프로바이더별 rate-limit 상태 고려
- 모델 성능 메트릭 추적 (성공률, 평균 지연시간)
- 비용 최적화: 간단한 요청은 가벼운 모델, 복잡한 요청은 고성능 모델

사용법:
    selector = ModelSelector()
    plan = selector.select("sonnet", image_required=False)
    # → ModelPlan(claude_models=["claude-sonnet-4-5-20250929", ...],
    #             proxy_model="sonnet", gemini_models=[...])
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("jarvis.model_selector")


# ── 프로바이더별 모델 정의 ──

CLAUDE_MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-6",
}

GEMINI_MODELS = {
    "fast": "gemini-2.5-flash",
    "balanced": "gemini-2.0-flash",
    "lite": "gemini-2.0-flash-lite",
}

# model_hint → Claude 모델 우선순위
CLAUDE_CASCADE = {
    "haiku": ["claude-haiku-4-5-20251001", "claude-sonnet-4-5-20250929"],
    "sonnet": ["claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"],
    "opus": ["claude-opus-4-6", "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"],
}

# model_hint → Gemini 폴백 순서
GEMINI_CASCADE = {
    "haiku": ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash"],
    "sonnet": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"],
    "opus": ["gemini-2.5-flash", "gemini-2.0-flash"],
}

# model_hint → claude_proxy.js에 전달할 모델 힌트
PROXY_MODEL_MAP = {
    "haiku": "haiku",
    "sonnet": "sonnet",
    "opus": "opus",
}


@dataclass
class ModelPlan:
    """모델 선택 계획 — 각 프로바이더별 시도 순서"""
    claude_models: List[str]     # Claude API 시도 순서
    proxy_model: str             # claude_proxy.js에 전달할 모델 키
    gemini_models: List[str]     # Gemini 폴백 시도 순서
    hint: str                    # 원본 model_hint
    reason: str = ""             # 선택 사유 (로깅용)

    @property
    def full_cascade(self) -> list:
        """크로스 프로바이더 전체 폴백 순서: Claude → Gemini"""
        return [("claude", m) for m in self.claude_models] + [("gemini", m) for m in self.gemini_models]


@dataclass
class ModelMetrics:
    """단일 모델의 성능 메트릭"""
    total_calls: int = 0
    successes: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.successes / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.successes == 0:
            return 0.0
        return self.total_latency_ms / self.successes


class ModelSelector:
    """
    지능형 모델 선택 엔진

    specialist-chain 패턴:
    - model_hint에서 기본 캐스케이드 결정
    - rate-limit 상태로 사용 불가 모델 제외
    - 성능 메트릭으로 캐스케이드 순서 미세 조정
    """

    def __init__(self, rate_limit_checker=None):
        """
        Args:
            rate_limit_checker: callable(model_name) → bool (True이면 rate-limited)
        """
        self._rate_limit_checker = rate_limit_checker
        self._metrics: Dict[str, ModelMetrics] = {}
        self._selection_count = 0

    def select(
        self,
        model_hint: str = "sonnet",
        image_required: bool = False,
    ) -> ModelPlan:
        """
        모델 선택 계획 생성.

        Args:
            model_hint: AgentRouter의 model_hint ("haiku", "sonnet", "opus")
            image_required: 이미지 처리가 필요한지 (Claude text-only → Gemini 우선)

        Returns:
            ModelPlan with provider-specific model cascades
        """
        self._selection_count += 1
        hint = model_hint if model_hint in CLAUDE_CASCADE else "sonnet"

        # 기본 캐스케이드
        claude_models = list(CLAUDE_CASCADE[hint])
        proxy_model = PROXY_MODEL_MAP[hint]
        gemini_models = list(GEMINI_CASCADE[hint])
        reason = f"hint={hint}"

        # 이미지 요청 시 Gemini 우선 (Claude Vision도 지원하므로 제거하지 않음)
        if image_required:
            reason += ", image→gemini_priority(claude_kept)"

        # rate-limit된 모델 후순위로 이동
        if self._rate_limit_checker:
            claude_models = self._reorder_by_availability(
                claude_models, prefix="claude-"
            )
            gemini_models = self._reorder_by_availability(
                gemini_models, prefix="gemini-"
            )

        # 성능 메트릭 기반 미세 조정
        claude_models = self._reorder_by_metrics(claude_models)
        gemini_models = self._reorder_by_metrics(gemini_models)

        plan = ModelPlan(
            claude_models=claude_models,
            proxy_model=proxy_model,
            gemini_models=gemini_models,
            hint=hint,
            reason=reason,
        )

        logger.info(
            f"[MODEL_SELECTOR] #{self._selection_count} "
            f"hint={hint} → claude={claude_models}, proxy={proxy_model}, "
            f"gemini={gemini_models} ({reason})"
        )

        return plan

    def record_result(
        self, model_name: str, success: bool, latency_ms: float = 0.0
    ):
        """모델 호출 결과 기록 (적응형 라우팅용)"""
        if model_name not in self._metrics:
            self._metrics[model_name] = ModelMetrics()

        m = self._metrics[model_name]
        m.total_calls += 1
        now = time.time()

        if success:
            m.successes += 1
            m.total_latency_ms += latency_ms
            m.last_success = now
        else:
            m.failures += 1
            m.last_failure = now

    def get_stats(self) -> dict:
        """전체 모델 성능 통계 반환"""
        stats = {
            "total_selections": self._selection_count,
            "models": {},
        }
        for name, m in self._metrics.items():
            stats["models"][name] = {
                "total": m.total_calls,
                "success_rate": round(m.success_rate, 3),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
            }
        return stats

    def _reorder_by_availability(
        self, models: List[str], prefix: str = ""
    ) -> List[str]:
        """rate-limited 모델을 리스트 뒤로 이동"""
        available = []
        limited = []
        for model in models:
            check_name = f"{prefix}{model}" if prefix else model
            try:
                if self._rate_limit_checker(check_name):
                    limited.append(model)
                else:
                    available.append(model)
            except Exception:
                available.append(model)
        return available + limited

    def _reorder_by_metrics(self, models: List[str]) -> List[str]:
        """성능이 나쁜 모델(연속 실패)을 후순위로 이동"""
        if len(models) <= 1:
            return models

        now = time.time()
        good = []
        degraded = []

        for model in models:
            m = self._metrics.get(model)
            if m is None:
                good.append(model)
                continue

            # 최근 5분 내 연속 3회 이상 실패 → 후순위
            recent_failure = (now - m.last_failure) < 300 if m.last_failure else False
            if recent_failure and m.failures >= 3 and m.success_rate < 0.5:
                degraded.append(model)
            else:
                good.append(model)

        return good + degraded
