# -*- coding: utf-8 -*-
"""ModelSelector 단위 테스트 — 모델 캐스케이드, full_cascade, 메트릭 기록 검증."""

import pytest
from jarvis_features.model_selector import (
    ModelSelector,
    ModelPlan,
    CLAUDE_CASCADE,
    GEMINI_CASCADE,
)


@pytest.fixture
def selector():
    return ModelSelector()


class TestModelCascade:
    """모델 힌트별 캐스케이드 순서 테스트."""

    def test_haiku_cascade(self, selector):
        plan = selector.select("haiku")
        assert plan.claude_models[0] == "claude-haiku-4-5-20251001"
        assert plan.proxy_model == "haiku"

    def test_sonnet_cascade(self, selector):
        plan = selector.select("sonnet")
        assert plan.claude_models[0] == "claude-sonnet-4-5-20250929"
        assert plan.proxy_model == "sonnet"

    def test_opus_cascade(self, selector):
        plan = selector.select("opus")
        assert plan.claude_models[0] == "claude-opus-4-6"
        assert plan.proxy_model == "opus"

    def test_unknown_hint_defaults_to_sonnet(self, selector):
        plan = selector.select("nonexistent")
        assert plan.hint == "sonnet"
        assert plan.claude_models[0] == "claude-sonnet-4-5-20250929"


class TestFullCascade:
    """B10 검증: full_cascade 크로스 프로바이더 폴백 프로퍼티."""

    def test_full_cascade_contains_both_providers(self, selector):
        plan = selector.select("sonnet")
        cascade = plan.full_cascade
        providers = [provider for provider, _ in cascade]
        assert "claude" in providers
        assert "gemini" in providers

    def test_full_cascade_claude_first(self, selector):
        plan = selector.select("haiku")
        cascade = plan.full_cascade
        # Claude 모델이 Gemini보다 먼저 나와야 함
        claude_indices = [i for i, (p, _) in enumerate(cascade) if p == "claude"]
        gemini_indices = [i for i, (p, _) in enumerate(cascade) if p == "gemini"]
        assert max(claude_indices) < min(gemini_indices)

    def test_full_cascade_length(self, selector):
        plan = selector.select("opus")
        expected_len = len(CLAUDE_CASCADE["opus"]) + len(GEMINI_CASCADE["opus"])
        assert len(plan.full_cascade) == expected_len


class TestMetrics:
    """모델 성능 메트릭 기록 테스트."""

    def test_record_success(self, selector):
        selector.record_result("claude-sonnet-4-5-20250929", True, 500.0)
        m = selector._metrics["claude-sonnet-4-5-20250929"]
        assert m.total_calls == 1
        assert m.successes == 1
        assert m.failures == 0

    def test_record_failure(self, selector):
        selector.record_result("claude-haiku-4-5-20251001", False, 100.0)
        m = selector._metrics["claude-haiku-4-5-20251001"]
        assert m.total_calls == 1
        assert m.successes == 0
        assert m.failures == 1

    def test_selection_count_increments(self, selector):
        selector.select("haiku")
        selector.select("sonnet")
        assert selector._selection_count == 2
