# -*- coding: utf-8 -*-
"""WorkflowOrchestrator 단위 테스트 — 병렬/순차 실행, 에러 처리, 타임아웃 검증."""

import asyncio
import pytest
from jarvis_features.workflow_orchestrator import (
    WorkflowOrchestrator,
    PipelineStep,
    StepResult,
)


@pytest.fixture
def orchestrator():
    return WorkflowOrchestrator(tool_registry=None)


# ── 테스트용 스텝 함수 ──

async def _success_fn():
    return "ok"

async def _slow_fn():
    await asyncio.sleep(5)
    return "slow"

async def _fail_fn():
    raise ValueError("test error")

async def _delayed_success():
    await asyncio.sleep(0.1)
    return "delayed_ok"


class TestParallelExecution:
    """execute_parallel 테스트."""

    @pytest.mark.asyncio
    async def test_all_success(self, orchestrator):
        steps = [
            PipelineStep("a", _success_fn, timeout=5),
            PipelineStep("b", _success_fn, timeout=5),
            PipelineStep("c", _delayed_success, timeout=5),
        ]
        results = await orchestrator.execute_parallel(steps)
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_one_failure_doesnt_crash_others(self, orchestrator):
        """B1 검증: 1개 실패해도 나머지 결과 정상 반환."""
        steps = [
            PipelineStep("ok1", _success_fn, timeout=5),
            PipelineStep("fail", _fail_fn, timeout=5),
            PipelineStep("ok2", _success_fn, timeout=5),
        ]
        results = await orchestrator.execute_parallel(steps)
        assert len(results) == 3
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) == 2
        assert len(failures) == 1
        assert "test error" in failures[0].error

    @pytest.mark.asyncio
    async def test_timeout_handling(self, orchestrator):
        steps = [
            PipelineStep("slow", _slow_fn, timeout=0.1),
        ]
        results = await orchestrator.execute_parallel(steps)
        assert len(results) == 1
        assert not results[0].success
        assert "Timeout" in results[0].error


class TestPipelineExecution:
    """execute_pipeline (순차 실행) 테스트."""

    @pytest.mark.asyncio
    async def test_required_step_abort(self, orchestrator):
        """required=True 스텝 실패 시 파이프라인 중단."""
        steps = [
            PipelineStep("step1", _success_fn, required=True, timeout=5),
            PipelineStep("fail_step", _fail_fn, required=True, timeout=5),
            PipelineStep("step3", _success_fn, timeout=5),
        ]
        results = await orchestrator.execute_pipeline(steps)
        # step3는 실행되지 않음
        assert len(results) == 2
        assert results[0].success
        assert not results[1].success

    @pytest.mark.asyncio
    async def test_non_required_failure_continues(self, orchestrator):
        """required=False 스텝 실패 시 계속 진행."""
        steps = [
            PipelineStep("step1", _success_fn, timeout=5),
            PipelineStep("optional_fail", _fail_fn, required=False, timeout=5),
            PipelineStep("step3", _success_fn, timeout=5),
        ]
        results = await orchestrator.execute_pipeline(steps)
        assert len(results) == 3
        assert results[0].success
        assert not results[1].success
        assert results[2].success


class TestRetryErrorHistory:
    """B6 검증: 재시도 시 에러 히스토리 누적."""

    @pytest.mark.asyncio
    async def test_error_history_preserved(self, orchestrator):
        steps = [
            PipelineStep("retryable", _fail_fn, retry=2, timeout=5),
        ]
        results = await orchestrator.execute_parallel(steps)
        assert len(results) == 1
        r = results[0]
        assert not r.success
        # 3번 시도 (1 + retry 2) → 에러 메시지에 3개 attempt 기록
        assert "attempt 1" in r.error
        assert "attempt 2" in r.error
        assert "attempt 3" in r.error


class TestFormatResults:
    """format_results, get_execution_report 테스트."""

    def test_format_results_success(self, orchestrator):
        results = [
            StepResult("weather", True, "맑음", 100.0),
            StepResult("news", True, "뉴스 없음", 200.0),
        ]
        output = orchestrator.format_results(results)
        assert "맑음" in output
        assert "뉴스 없음" in output

    def test_format_results_with_failure(self, orchestrator):
        results = [
            StepResult("ok", True, "data", 50.0),
            StepResult("fail", False, "", 100.0, error="timeout"),
        ]
        output = orchestrator.format_results(results, include_failed=True)
        assert "data" in output
        assert "timeout" in output

    def test_execution_report(self, orchestrator):
        results = [
            StepResult("a", True, "", 50.0),
            StepResult("b", False, "", 100.0, error="err"),
        ]
        report = orchestrator.get_execution_report(results)
        assert "a: OK" in report
        assert "b: FAIL" in report
        assert "1/2 succeeded" in report
